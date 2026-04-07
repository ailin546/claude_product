"""
Markdown 导出器

将解析后的微信消息导出为 Markdown 文件，
按联系人/群聊分目录，按日期分段。
"""

import shutil
from datetime import datetime, timedelta
from pathlib import Path

from .parser import Contact, Message, MsgType


def export_to_markdown(
    messages_by_talker: dict[str, list[Message]],
    contacts: dict[str, Contact],
    output_dir: Path,
    my_name: str = "我",
    media_source_dir: Path | None = None,
) -> dict[str, int]:
    """
    将消息导出为 Markdown 文件

    目录结构:
        output_dir/
        ├── 好友备注名/
        │   ├── chat.md           # 完整聊天记录
        │   ├── 2024-01.md        # 按月份分割（可选）
        │   └── media/            # 媒体文件
        │       ├── image_xxx.jpg
        │       └── ...
        └── 群聊名称/
            └── chat.md

    Returns:
        统计信息 {talker: message_count}
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    stats = {}

    for talker, messages in messages_by_talker.items():
        if not messages:
            continue

        contact = contacts.get(talker)
        display_name = _safe_dirname(
            contact.display_name if contact else talker
        )

        chat_dir = output_dir / display_name
        chat_dir.mkdir(parents=True, exist_ok=True)

        # 导出完整聊天记录
        md_content = _render_chat_markdown(
            messages, contacts, talker, my_name
        )

        chat_file = chat_dir / "chat.md"
        chat_file.write_text(md_content, encoding="utf-8")

        # 按月份分割导出
        monthly = _split_by_month(messages)
        for month_key, month_msgs in monthly.items():
            month_md = _render_chat_markdown(
                month_msgs, contacts, talker, my_name
            )
            month_file = chat_dir / f"{month_key}.md"
            month_file.write_text(month_md, encoding="utf-8")

        # 复制相关媒体文件
        if media_source_dir:
            _copy_media_files(messages, media_source_dir, chat_dir / "media")

        stats[display_name] = len(messages)

    return stats


def _render_chat_markdown(
    messages: list[Message],
    contacts: dict[str, Contact],
    talker: str,
    my_name: str,
) -> str:
    """将消息列表渲染为 Markdown 文本"""
    contact = contacts.get(talker)
    title = contact.display_name if contact else talker
    is_group = contact.is_group if contact else talker.endswith("@chatroom")

    lines = []
    lines.append(f"# {title}")
    lines.append("")

    if messages:
        first_time = datetime.fromtimestamp(messages[0].timestamp)
        last_time = datetime.fromtimestamp(messages[-1].timestamp)
        lines.append(
            f"> 时间范围：{first_time.strftime('%Y-%m-%d')} ~ "
            f"{last_time.strftime('%Y-%m-%d')}  "
        )
        lines.append(f"> 消息数量：{len(messages)}")
        lines.append("")

    current_date = ""

    for msg in messages:
        # 日期分隔线
        msg_date = msg.time.strftime("%Y-%m-%d")
        if msg_date != current_date:
            current_date = msg_date
            weekday = ["一", "二", "三", "四", "五", "六", "日"][
                msg.time.weekday()
            ]
            lines.append("")
            lines.append(f"---")
            lines.append(f"### {msg_date} 星期{weekday}")
            lines.append("")

        # 发送者名称
        sender = _get_sender_name(msg, contacts, my_name, is_group)

        # 时间
        time_str = msg.time.strftime("%H:%M:%S")

        # 消息内容
        text = msg.parsed_text or msg.content or ""

        # 系统消息居中显示
        if msg.msg_type in (MsgType.SYSTEM, MsgType.SYSTEM_REVOKE):
            lines.append(f"*{text}*")
            lines.append("")
            continue

        # 普通消息
        lines.append(f"**{sender}** `{time_str}`")
        lines.append("")

        # 多行内容缩进处理
        for content_line in text.split("\n"):
            lines.append(content_line)
        lines.append("")

    return "\n".join(lines)


def _get_sender_name(
    msg: Message,
    contacts: dict[str, Contact],
    my_name: str,
    is_group: bool,
) -> str:
    """获取消息发送者的显示名"""
    if msg.is_sender:
        return my_name

    if msg.sender_name:
        return msg.sender_name

    if is_group:
        # 群聊消息，content 中可能包含发送者
        # 格式: "wxid_xxx:\n实际内容"
        if msg.content and ":\n" in msg.content:
            sender_id = msg.content.split(":\n", 1)[0]
            contact = contacts.get(sender_id)
            if contact:
                return contact.display_name
            return sender_id

    # 私聊消息，发送者就是对话对象
    contact = contacts.get(msg.talker)
    if contact:
        return contact.display_name
    return msg.talker


def _split_by_month(
    messages: list[Message],
) -> dict[str, list[Message]]:
    """将消息按月份分组"""
    monthly: dict[str, list[Message]] = {}
    for msg in messages:
        key = msg.time.strftime("%Y-%m")
        if key not in monthly:
            monthly[key] = []
        monthly[key].append(msg)
    return monthly


def _safe_dirname(name: str) -> str:
    """将名称转为安全的目录名"""
    # 替换文件系统不允许的字符
    safe = name.replace("/", "_").replace("\\", "_")
    safe = safe.replace(":", "_").replace("*", "_")
    safe = safe.replace("?", "_").replace('"', "_")
    safe = safe.replace("<", "_").replace(">", "_")
    safe = safe.replace("|", "_").replace("\n", "_")
    safe = safe.strip(". ")
    return safe or "unknown"


def _copy_media_files(
    messages: list[Message],
    source_dir: Path,
    target_dir: Path,
) -> None:
    """复制消息引用的媒体文件"""
    if not source_dir.exists():
        return

    target_dir.mkdir(parents=True, exist_ok=True)

    for msg in messages:
        if not msg.media_path:
            continue
        src = source_dir / msg.media_path
        if src.exists():
            dst = target_dir / src.name
            try:
                shutil.copy2(src, dst)
            except OSError:
                pass
