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
    contact_db: Path | None  # 联系人数据库
    image_dir: Path  # 图片缓存目录
    voice_dir: Path  # 语音缓存目录
    video_dir: Path  # 视频缓存目录
    file_dir: Path  # 文件缓存目录
    avatar_dir: Path  # 头像缓存目录
    is_new_format: bool = False  # 是否为新版 db_storage 格式


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

        for reg_path in [
            r"Software\Tencent\WeChat",
            r"Software\Tencent\xwechat",
        ]:
            try:
                key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, reg_path)
                custom_path = winreg.QueryValueEx(key, "FileSavePath")[0]
                winreg.CloseKey(key)
                if custom_path and custom_path != "MyDocument:":
                    base_candidates.insert(0, Path(custom_path))
            except OSError:
                continue
    except ImportError:
        pass

    for base in base_candidates:
        if not base.exists():
            continue
        # 每个 wxid_xxx 子目录是一个微信账号
        for entry in base.iterdir():
            if not entry.is_dir():
                continue
            name = entry.name
            if name.lower() in ("all_users", "all users", "applet", "wmpf", "backup"):
                continue

            paths = _detect_account_paths(entry, name)
            if paths is not None:
                results.append(paths)

    return results


def _detect_account_paths(entry: Path, name: str) -> WeChatDataPaths | None:
    """检测单个账号目录，支持新旧两种格式"""
    # 新版格式: db_storage/message/
    db_storage = entry / "db_storage"
    if db_storage.exists():
        msg_dir = db_storage / "message"
        contact_db_path = db_storage / "contact" / "contact.db"
        if msg_dir.exists():
            return WeChatDataPaths(
                wxid=name,
                base_dir=entry,
                msg_dir=msg_dir,
                contact_db=contact_db_path if contact_db_path.exists() else None,
                image_dir=entry / "msg" / "attach",
                voice_dir=entry / "msg" / "voice",
                video_dir=entry / "msg" / "video",
                file_dir=entry / "msg" / "file",
                avatar_dir=db_storage / "head_image",
                is_new_format=True,
            )

    # 旧版格式: Msg/
    msg_dir = entry / "Msg"
    if not msg_dir.exists():
        msg_dir = entry / "msg"
    if msg_dir.exists():
        return WeChatDataPaths(
            wxid=name,
            base_dir=entry,
            msg_dir=msg_dir,
            contact_db=None,
            image_dir=entry / "FileStorage" / "Image",
            voice_dir=entry / "FileStorage" / "Voice",
            video_dir=entry / "FileStorage" / "Video",
            file_dir=entry / "FileStorage" / "File",
            avatar_dir=entry / "FileStorage" / "General" / "Data",
            is_new_format=False,
        )

    return None


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

            paths = _detect_account_paths(user_dir, user_dir.name)
            if paths is not None:
                results.append(paths)
                continue

            # macOS 旧版兜底: Message/ 目录
            msg_dir = user_dir / "Message"
            if not msg_dir.exists():
                msg_dir = user_dir / "Msg"
            if msg_dir.exists():
                results.append(
                    WeChatDataPaths(
                        wxid=user_dir.name,
                        base_dir=user_dir,
                        msg_dir=msg_dir,
                        contact_db=None,
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


def find_db_files(data_paths: WeChatDataPaths) -> list[Path]:
    """查找消息数据库文件"""
    msg_dir = data_paths.msg_dir

    if data_paths.is_new_format:
        # 新版: db_storage/message/ 下的 message_*.db
        patterns = [
            "message_*.db",
            "biz_message_*.db",
            "media_*.db",
        ]
    else:
        # 旧版: Msg/ 下的 MSG*.db
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

    # 联系人数据库也加入
    if data_paths.contact_db and data_paths.contact_db.exists():
        db_files.append(data_paths.contact_db)

    # 去重并排序
    return sorted(set(db_files))
