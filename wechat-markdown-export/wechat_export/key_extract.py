"""
从微信进程内存中提取数据库解密密钥

支持两种微信版本：
- 旧版 (WeChat.exe + WeChatWin.dll)
- 新版 xwechat (Weixin.exe + WeChatAppEx.exe)

密钥为 32 字节 (256-bit AES)，用于 SQLCipher 加密
"""

import os
import sys
import struct
from pathlib import Path


# SQLCipher 密钥长度
KEY_SIZE = 32

# 微信进程名候选列表
WECHAT_PROCESS_NAMES = [
    "Weixin.exe",      # 新版 xwechat
    "WeChat.exe",      # 旧版
]

# 旧版微信关键模块
OLD_KEY_MODULES = ["WeChatWin.dll"]

# 新版微信关键模块（密钥可能在这些模块中）
NEW_KEY_MODULES = [
    "WeChatAppEx.exe",
    "xwechat.dll",
    "wechatocr.dll",
    "wechat.dll",
    "WCDB.dll",
    "wcdb.dll",
]


def extract_key_windows() -> bytes:
    """
    从 Windows 微信进程内存中提取密钥
    自动检测旧版 (WeChat.exe) 和新版 (Weixin.exe)
    """
    try:
        import pymem
        import pymem.process
    except ImportError:
        raise RuntimeError(
            "需要安装 pymem: pip install pymem\n"
            "注意: 需要以管理员权限运行"
        )

    # 尝试所有已知的进程名
    pm = None
    process_name = None
    for name in WECHAT_PROCESS_NAMES:
        try:
            pm = pymem.Pymem(name)
            process_name = name
            break
        except pymem.exception.ProcessNotFound:
            continue

    if pm is None:
        raise RuntimeError(
            "未找到微信进程，请确保微信正在运行并已登录。\n"
            f"已尝试的进程名: {', '.join(WECHAT_PROCESS_NAMES)}"
        )

    pid = pm.process_id
    is_new = process_name == "Weixin.exe"
    version_label = "新版 xwechat" if is_new else "旧版 WeChat"
    print(f"[*] 找到微信进程: {process_name} (PID: {pid}, {version_label})")

    # 枚举所有模块
    modules = list(pymem.process.enum_process_module(pm.process_handle))
    module_names = [m.name for m in modules if m.name]
    print(f"[*] 已加载 {len(modules)} 个模块")

    key = None

    if is_new:
        key = _extract_key_new_wechat(pm, modules)
    else:
        key = _extract_key_old_wechat(pm, modules)

    pm.close_process()

    if key is None:
        raise RuntimeError(
            "无法自动提取密钥。可能原因：\n"
            "1. 微信版本不兼容（新版 xwechat 架构变化大）\n"
            "2. 需要以管理员权限运行\n"
            "3. 杀毒软件阻止了内存读取\n\n"
            "替代方案：\n"
            "  使用 PyWxDump 提取密钥: https://github.com/Aeron1-bit/PyWxDump\n"
            "  然后用 --key 参数传入: wechat-export --key 你的密钥"
        )

    return key


def _extract_key_old_wechat(pm, modules: list) -> bytes | None:
    """旧版 WeChat.exe + WeChatWin.dll 密钥提取"""
    wechat_win = None
    for module in modules:
        if module.name and "WeChatWin.dll" in module.name:
            wechat_win = module
            break

    if wechat_win is None:
        print("[!] 未找到 WeChatWin.dll，尝试通用扫描...")
        return _scan_all_modules(pm, modules)

    base_addr = wechat_win.lpBaseOfDll
    module_size = wechat_win.SizeOfImage
    print(f"[*] WeChatWin.dll 基址: 0x{base_addr:X}, 大小: {module_size}")

    # 策略1: 扫描内存特征
    key = _scan_memory_for_key(pm, base_addr, module_size)
    if key:
        return key

    # 策略2: 已知偏移量
    return _try_known_offsets(pm, base_addr)


def _extract_key_new_wechat(pm, modules: list) -> bytes | None:
    """
    新版 Weixin.exe (xwechat) 密钥提取

    新版架构使用多进程模型 (Weixin.exe + WeChatAppEx.exe)，
    密钥可能存储在主进程的堆内存或特定模块中。

    策略：
    1. 扫描主进程 (Weixin.exe) 的模块
    2. 扫描所有已加载 DLL 的 .data 段
    3. 在进程堆内存中搜索密钥特征
    """
    print("[*] 新版微信密钥提取...")

    # 策略1: 扫描已知相关模块
    for module in modules:
        if not module.name:
            continue
        name_lower = module.name.lower()

        # 检查是否是可能包含密钥的模块
        is_target = any(
            target.lower() in name_lower
            for target in NEW_KEY_MODULES + ["weixin", "wechat", "wcdb", "sqlcipher"]
        )
        if not is_target:
            continue

        base = module.lpBaseOfDll
        size = module.SizeOfImage
        print(f"[*] 扫描模块: {module.name} (0x{base:X}, {size})")

        key = _scan_memory_for_key(pm, base, size)
        if key:
            print(f"[+] 在 {module.name} 中找到密钥")
            return key

    # 策略2: 扫描主进程所有可读内存区域
    print("[*] 扫描进程内存区域...")
    key = _scan_process_memory(pm)
    if key:
        return key

    # 策略3: 扫描所有模块（兜底）
    print("[*] 全模块扫描...")
    return _scan_all_modules(pm, modules)


def _scan_memory_for_key(pm, base_addr: int, region_size: int) -> bytes | None:
    """在指定内存区域中搜索密钥特征"""
    CHUNK_SIZE = 1024 * 1024  # 1MB
    offset = 0

    while offset < region_size:
        read_size = min(CHUNK_SIZE, region_size - offset)
        try:
            data = pm.read_bytes(base_addr + offset, read_size)
        except Exception:
            offset += CHUNK_SIZE
            continue

        result = _find_key_in_data(data)
        if result is not None:
            return result

        offset += CHUNK_SIZE - KEY_SIZE  # 重叠防跨块

    return None


def _scan_process_memory(pm) -> bytes | None:
    """扫描进程的虚拟内存空间寻找密钥"""
    try:
        import ctypes
        from ctypes import wintypes

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

        class MEMORY_BASIC_INFORMATION(ctypes.Structure):
            _fields_ = [
                ("BaseAddress", ctypes.c_void_p),
                ("AllocationBase", ctypes.c_void_p),
                ("AllocationProtect", wintypes.DWORD),
                ("RegionSize", ctypes.c_size_t),
                ("State", wintypes.DWORD),
                ("Protect", wintypes.DWORD),
                ("Type", wintypes.DWORD),
            ]

        MEM_COMMIT = 0x1000
        PAGE_READWRITE = 0x04
        PAGE_READONLY = 0x02

        mbi = MEMORY_BASIC_INFORMATION()
        address = 0
        max_address = 0x7FFFFFFFFFFF  # 64-bit user space
        candidates = []

        while address < max_address:
            result = kernel32.VirtualQueryEx(
                pm.process_handle,
                ctypes.c_void_p(address),
                ctypes.byref(mbi),
                ctypes.sizeof(mbi),
            )
            if result == 0:
                break

            # 只扫描已提交的可读写内存（堆、全局变量等）
            if (
                mbi.State == MEM_COMMIT
                and mbi.Protect in (PAGE_READWRITE, PAGE_READONLY, 0x04 | 0x100)
                and 4096 <= mbi.RegionSize <= 10 * 1024 * 1024  # 4KB - 10MB
            ):
                try:
                    data = pm.read_bytes(mbi.BaseAddress, min(mbi.RegionSize, 2 * 1024 * 1024))
                    key = _find_key_in_data(data)
                    if key is not None:
                        candidates.append(key)
                        if len(candidates) >= 3:
                            # 如果找到多个候选，返回出现最多的那个
                            break
                except Exception:
                    pass

            address = mbi.BaseAddress + mbi.RegionSize
            if address <= mbi.BaseAddress:
                break

        if candidates:
            # 返回最可能的密钥（出现最多的）
            from collections import Counter
            counter = Counter(c.hex() for c in candidates)
            best = counter.most_common(1)[0][0]
            print(f"[+] 在进程内存中找到 {len(candidates)} 个候选密钥")
            return bytes.fromhex(best)

    except Exception as e:
        print(f"[!] 进程内存扫描失败: {e}")

    return None


def _scan_all_modules(pm, modules: list) -> bytes | None:
    """扫描所有非系统模块"""
    system_prefixes = ("c:\\windows", "c:/windows")

    for module in modules:
        if not module.name:
            continue
        # 跳过系统 DLL
        path = (module.name or "").lower()
        if any(path.startswith(p) for p in system_prefixes):
            continue

        base = module.lpBaseOfDll
        size = module.SizeOfImage

        if size > 50 * 1024 * 1024:  # 跳过超大模块
            continue

        try:
            key = _scan_memory_for_key(pm, base, size)
            if key:
                print(f"[+] 在 {module.name} 中找到密钥")
                return key
        except Exception:
            continue

    return None


def _find_key_in_data(data: bytes) -> bytes | None:
    """在数据块中查找符合密钥特征的 32 字节序列"""
    for i in range(0, len(data) - KEY_SIZE - 8, 8):  # 8 字节对齐
        candidate = data[i : i + KEY_SIZE]

        # 全零或低熵跳过
        unique_bytes = len(set(candidate))
        if unique_bytes < 10:
            continue

        # 检查字节分布（高熵特征）
        byte_freq = {}
        for b in candidate:
            byte_freq[b] = byte_freq.get(b, 0) + 1
        if max(byte_freq.values()) > 6:
            continue

        # 检查密钥后的内存特征
        after = data[i + KEY_SIZE : i + KEY_SIZE + 8]
        if after == b"\x00" * 8:
            return candidate

    return None


def _try_known_offsets(pm, base_addr: int) -> bytes | None:
    """尝试已知微信版本的密钥偏移量（旧版）"""
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

    # 查找微信进程（支持新旧进程名）
    pid = None
    for proc_name in ["Weixin", "WeChat"]:
        result = subprocess.run(
            ["pgrep", "-x", proc_name],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            pid = result.stdout.strip().split("\n")[0]
            print(f"[*] 找到微信进程: {proc_name} (PID: {pid})")
            break

    if pid is None:
        raise RuntimeError(
            "未找到微信进程，请确保微信正在运行并已登录。\n"
            "已尝试: Weixin, WeChat"
        )

    # 使用 lldb 提取密钥
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
    found = False
    for module in target.module_iter():
        name = module.GetFileSpec().GetFilename() or ""
        if any(kw in name for kw in ["WCDB", "wcdb", "WeChat", "Weixin", "sqlcipher"]):
            for section in module.section_iter():
                if section.GetName() == "__DATA":
                    addr = section.GetLoadAddress(target)
                    size = section.GetByteSize()
                    data = process.ReadMemory(addr, min(size, 2*1024*1024), error)
                    if data:
                        for i in range(0, len(data) - 40, 8):
                            candidate = data[i:i+32]
                            if len(set(candidate)) >= 10:
                                after = data[i+32:i+40]
                                if after == b"\\x00" * 8:
                                    print(f"KEY_FOUND:{{candidate.hex()}}")
                                    found = True
                                    break
                if found:
                    break
        if found:
            break
    process.Detach()
    lldb.SBDebugger.Destroy(debugger)
"""

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
