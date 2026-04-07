"""
WeChat 数据路径发现 - 支持 Windows 和 macOS
"""

import os
import sys
import glob
from pathlib import Path
from dataclasses import dataclass


@dataclass
class WeChatDataPaths:
    """微信数据路径集合"""

    wxid: str
    base_dir: Path
    msg_dir: Path  # 消息数据库目录
    image_dir: Path  # 图片缓存目录
    voice_dir: Path  # 语音缓存目录
    video_dir: Path  # 视频缓存目录
    file_dir: Path  # 文件缓存目录
    avatar_dir: Path  # 头像缓存目录


def find_wechat_data_windows() -> list[WeChatDataPaths]:
    """在 Windows 上查找微信数据目录"""
    results = []

    # 默认路径: Documents\WeChat Files\
    base_candidates = [
        Path(os.environ.get("USERPROFILE", "")) / "Documents" / "WeChat Files",
        Path(os.environ.get("APPDATA", "")) / "Tencent" / "WeChat",
    ]

    # 也检查自定义安装路径（从注册表获取）
    try:
        import winreg

        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Tencent\WeChat",
        )
        custom_path = winreg.QueryValueEx(key, "FileSavePath")[0]
        winreg.CloseKey(key)
        if custom_path and custom_path != "MyDocument:":
            base_candidates.insert(0, Path(custom_path))
    except Exception:
        pass

    for base in base_candidates:
        if not base.exists():
            continue
        # 每个 wxid_xxx 子目录是一个微信账号
        for entry in base.iterdir():
            if not entry.is_dir():
                continue
            name = entry.name
            if name in ("All Users", "Applet", "WMPF"):
                continue
            msg_dir = entry / "Msg"
            if not msg_dir.exists():
                # 新版微信可能用 msg 目录
                msg_dir = entry / "msg"
            if msg_dir.exists():
                results.append(
                    WeChatDataPaths(
                        wxid=name,
                        base_dir=entry,
                        msg_dir=msg_dir,
                        image_dir=entry / "FileStorage" / "Image",
                        voice_dir=entry / "FileStorage" / "Voice",
                        video_dir=entry / "FileStorage" / "Video",
                        file_dir=entry / "FileStorage" / "File",
                        avatar_dir=entry / "FileStorage" / "General" / "Data",
                    )
                )

    return results


def find_wechat_data_macos() -> list[WeChatDataPaths]:
    """在 macOS 上查找微信数据目录"""
    results = []

    container = Path.home() / "Library" / "Containers" / "com.tencent.xinWeChat"
    if not container.exists():
        return results

    # 微信 Mac 版的数据在 Data/Library/Application Support/com.tencent.xinWeChat/xxx/xxx/
    app_support = container / "Data" / "Library" / "Application Support" / "com.tencent.xinWeChat"
    if not app_support.exists():
        return results

    # 版本号目录 -> 用户 hash 目录
    for version_dir in app_support.iterdir():
        if not version_dir.is_dir() or version_dir.name.startswith("."):
            continue
        for user_dir in version_dir.iterdir():
            if not user_dir.is_dir() or user_dir.name.startswith("."):
                continue
            msg_dir = user_dir / "Message"
            if not msg_dir.exists():
                msg_dir = user_dir / "Msg"
            if not msg_dir.exists():
                # 检查是否有 .db 文件直接在此目录
                db_files = list(user_dir.glob("*.db")) + list(user_dir.glob("msg_*.db"))
                if db_files:
                    msg_dir = user_dir

            if msg_dir.exists():
                results.append(
                    WeChatDataPaths(
                        wxid=user_dir.name,
                        base_dir=user_dir,
                        msg_dir=msg_dir,
                        image_dir=user_dir / "Data" / "Image",
                        voice_dir=user_dir / "Data" / "Voice",
                        video_dir=user_dir / "Data" / "Video",
                        file_dir=user_dir / "Data" / "File",
                        avatar_dir=user_dir / "Data" / "Avatar",
                    )
                )

    return results


def find_wechat_data() -> list[WeChatDataPaths]:
    """自动检测平台并查找微信数据目录"""
    if sys.platform == "win32":
        return find_wechat_data_windows()
    elif sys.platform == "darwin":
        return find_wechat_data_macos()
    else:
        raise RuntimeError(
            f"不支持的平台: {sys.platform}，仅支持 Windows 和 macOS"
        )


def find_db_files(msg_dir: Path) -> list[Path]:
    """查找消息数据库文件"""
    patterns = [
        "MSG*.db",
        "msg_*.db",
        "MicroMsg.db",
        "EnMicroMsg.db",
        "MediaMSG*.db",
    ]
    db_files = []
    for pattern in patterns:
        db_files.extend(msg_dir.glob(pattern))
    # 去重并排序
    return sorted(set(db_files))
