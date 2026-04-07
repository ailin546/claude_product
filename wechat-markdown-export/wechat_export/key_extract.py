"""
从微信进程内存中提取数据库解密密钥

Windows: 使用 pymem 读取 WeChatWin.dll 中的密钥偏移
macOS: 使用 lldb 或从 Keychain / 进程内存读取

密钥为 32 字节 (256-bit AES)，用于 SQLCipher 加密
"""

import os
import sys
import struct
import ctypes
from pathlib import Path


# SQLCipher 密钥长度
KEY_SIZE = 32


def extract_key_windows() -> bytes:
    """
    从 Windows 微信进程内存中提取密钥

    原理：微信将 SQLCipher 密钥存储在 WeChatWin.dll 模块的特定内存偏移处。
    通过扫描进程内存中的特征模式定位密钥地址。
    """
    try:
        import pymem
        import pymem.process
    except ImportError:
        raise RuntimeError(
            "需要安装 pymem: pip install pymem\n"
            "注意: 需要以管理员权限运行"
        )

    # 查找微信进程
    try:
        pm = pymem.Pymem("WeChat.exe")
    except pymem.exception.ProcessNotFound:
        raise RuntimeError(
            "未找到微信进程，请确保微信正在运行并已登录"
        )

    pid = pm.process_id
    print(f"[*] 找到微信进程 PID: {pid}")

    # 查找 WeChatWin.dll 模块
    wechat_win = None
    for module in pymem.process.enum_process_module(pm.process_handle):
        if module.name and "WeChatWin.dll" in module.name:
            wechat_win = module
            break

    if wechat_win is None:
        pm.close_process()
        raise RuntimeError("未找到 WeChatWin.dll 模块")

    base_addr = wechat_win.lpBaseOfDll
    module_size = wechat_win.SizeOfImage
    print(f"[*] WeChatWin.dll 基址: 0x{base_addr:X}, 大小: {module_size}")

    # 策略1: 在模块内存中搜索密钥特征
    # 微信的密钥通常存储在 .data 段中，前后有特定的内存模式
    key = _scan_for_key_pattern(pm, base_addr, module_size)

    if key is None:
        # 策略2: 搜索已知的偏移量列表（不同微信版本）
        key = _try_known_offsets(pm, base_addr)

    pm.close_process()

    if key is None:
        raise RuntimeError(
            "无法自动提取密钥。可能原因：\n"
            "1. 微信版本不兼容\n"
            "2. 需要管理员权限\n"
            "3. 杀毒软件阻止了内存读取\n\n"
            "你可以使用 --key 参数手动指定密钥"
        )

    return key


def _scan_for_key_pattern(pm, base_addr: int, module_size: int) -> bytes | None:
    """
    扫描微信进程内存，查找密钥特征模式

    密钥特征：32字节非零数据，后跟特定的对齐填充
    """
    CHUNK_SIZE = 1024 * 1024  # 1MB 分块读取
    offset = 0

    while offset < module_size:
        read_size = min(CHUNK_SIZE, module_size - offset)
        try:
            data = pm.read_bytes(base_addr + offset, read_size)
        except Exception:
            offset += CHUNK_SIZE
            continue

        # 在块中搜索可能的密钥位置
        # 密钥特征: 32字节看起来像随机数据（高熵），且地址对齐
        for i in range(0, len(data) - KEY_SIZE, 8):  # 8字节对齐
            candidate = data[i : i + KEY_SIZE]

            # 跳过全零或全相同字节
            if len(set(candidate)) < 10:
                continue

            # 检查是否像一个有效的 AES 密钥（高熵）
            byte_freq = {}
            for b in candidate:
                byte_freq[b] = byte_freq.get(b, 0) + 1
            max_freq = max(byte_freq.values())
            # 真正的密钥不会有某个字节出现太多次
            if max_freq > 6:
                continue

            # 检查后续内存特征（密钥后通常是特定结构）
            if i + KEY_SIZE + 8 <= len(data):
                after = data[i + KEY_SIZE : i + KEY_SIZE + 8]
                # 密钥后面经常是 0 填充或特定标记
                if after == b"\x00" * 8:
                    return candidate

        offset += CHUNK_SIZE - KEY_SIZE  # 重叠读取，防止密钥跨块

    return None


def _try_known_offsets(pm, base_addr: int) -> bytes | None:
    """尝试已知微信版本的密钥偏移量"""
    # 这些偏移量来自不同微信版本的逆向分析
    # 格式: (版本描述, 偏移量)
    known_offsets = [
        ("3.9.x", 0x3A68B10),
        ("3.9.x alt", 0x3A68B50),
        ("3.8.x", 0x2FFD4D0),
        ("3.7.x", 0x2CEBF30),
        ("3.6.x", 0x2C29E10),
    ]

    for desc, offset in known_offsets:
        try:
            data = pm.read_bytes(base_addr + offset, KEY_SIZE)
            if data and len(set(data)) >= 10 and data != b"\x00" * KEY_SIZE:
                print(f"[*] 使用偏移量 {desc} (0x{offset:X}) 找到候选密钥")
                return data
        except Exception:
            continue

    return None


def extract_key_macos() -> bytes:
    """
    从 macOS 微信进程内存中提取密钥

    macOS 上需要使用 lldb attach 到微信进程来读取内存。
    需要关闭 SIP 或给终端赋予调试权限。
    """
    import subprocess

    # 查找微信进程
    result = subprocess.run(
        ["pgrep", "-x", "WeChat"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError("未找到微信进程，请确保微信正在运行并已登录")

    pid = result.stdout.strip().split("\n")[0]
    print(f"[*] 找到微信进程 PID: {pid}")

    # 使用 lldb 提取密钥
    # 构造 lldb 脚本
    lldb_script = f"""
import lldb
import struct

debugger = lldb.SBDebugger.Create()
debugger.SetAsync(False)
target = debugger.CreateTarget("")
error = lldb.SBError()
process = target.AttachToProcessWithID(debugger.GetListener(), {pid}, error)

if error.Fail():
    print(f"LLDB_ERROR:{{error.GetCString()}}")
else:
    # 搜索 WCDB 相关模块
    for module in target.module_iter():
        name = module.GetFileSpec().GetFilename()
        if name and "WCDB" in name:
            for section in module.section_iter():
                if section.GetName() == "__DATA":
                    addr = section.GetLoadAddress(target)
                    size = section.GetByteSize()
                    # 读取并搜索密钥
                    data = process.ReadMemory(addr, min(size, 1024*1024), error)
                    if data:
                        for i in range(0, len(data) - 32, 8):
                            candidate = data[i:i+32]
                            if len(set(candidate)) >= 10:
                                after = data[i+32:i+40] if i+40 <= len(data) else b""
                                if after == b"\\x00" * 8:
                                    print(f"KEY_FOUND:{{candidate.hex()}}")
                                    break
    process.Detach()
    lldb.SBDebugger.Destroy(debugger)
"""

    # 尝试通过 lldb Python 执行
    try:
        result = subprocess.run(
            ["python3", "-c", lldb_script],
            capture_output=True,
            text=True,
            timeout=30,
        )

        for line in result.stdout.split("\n"):
            if line.startswith("KEY_FOUND:"):
                hex_key = line.split(":")[1].strip()
                return bytes.fromhex(hex_key)
            if line.startswith("LLDB_ERROR:"):
                raise RuntimeError(
                    f"LLDB 附加失败: {line.split(':', 1)[1]}\n"
                    "可能需要：\n"
                    "1. 关闭 SIP (csrutil disable)\n"
                    "2. 授予终端调试权限 (DevToolsSecurity -enable)"
                )
    except FileNotFoundError:
        pass
    except subprocess.TimeoutExpired:
        pass

    raise RuntimeError(
        "无法自动提取 macOS 微信密钥。\n\n"
        "替代方案：\n"
        "1. 使用 https://github.com/cocohahaha/wechat-decrypt-macos 提取密钥\n"
        "2. 然后用 --key 参数传入密钥\n\n"
        "示例: wechat-export --key YOUR_HEX_KEY"
    )


def extract_key() -> bytes:
    """自动检测平台并提取密钥"""
    if sys.platform == "win32":
        return extract_key_windows()
    elif sys.platform == "darwin":
        return extract_key_macos()
    else:
        raise RuntimeError(f"不支持的平台: {sys.platform}")


def parse_hex_key(hex_str: str) -> bytes:
    """解析用户手动输入的十六进制密钥"""
    hex_str = hex_str.strip().replace(" ", "").replace("0x", "")
    try:
        key = bytes.fromhex(hex_str)
    except ValueError:
        raise ValueError(f"无效的十六进制密钥: {hex_str}")

    if len(key) != KEY_SIZE:
        raise ValueError(
            f"密钥长度错误: 期望 {KEY_SIZE} 字节, 实际 {len(key)} 字节"
        )
    return key
