"""
微信消息解析器

解析解密后的 SQLite 数据库，提取联系人和消息数据。
支持多种消息类型的解析。
"""

import json
import re
import sqlite3
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import datetime
from enum import IntEnum
from pathlib import Path


class MsgType(IntEnum):
    """微信消息类型"""

    TEXT = 1
    IMAGE = 3
    VOICE = 34
    VIDEO = 43
    EMOJI = 47
    LOCATION = 48
    LINK = 49  # 链接/文件/小程序/引用 等复合类型
    VOIP = 50
    SYSTEM = 10000
    SYSTEM_REVOKE = 10002


class LinkSubType(IntEnum):
    """链接消息子类型 (type=49 时的 sub_type)"""

    FILE = 6
    QUOTE = 57  # 引用回复
    MINI_PROGRAM = 33
    MINI_PROGRAM_ALT = 36
    MUSIC = 3
    VIDEO_LINK = 4
    ARTICLE = 5
    TRANSFER = 2000
    RED_PACKET = 2001
    STICKER = 8


@dataclass
class Contact:
    """联系人信息"""

    username: str  # wxid 或微信号
    nickname: str  # 昵称
    remark: str  # 备注名
    is_group: bool = False

    @property
    def display_name(self) -> str:
        return self.remark or self.nickname or self.username


@dataclass
class Message:
    """解析后的消息"""

    msg_id: int
    msg_type: int
    sub_type: int
    is_sender: bool  # True = 自己发的
    talker: str  # 对话对象的 wxid
    content: str  # 原始内容
    timestamp: int  # Unix 时间戳（秒）
    extra_info: str = ""  # 额外的 XML/JSON 数据

    # 解析后的字段
    parsed_text: str = ""
    media_path: str = ""
    sender_name: str = ""

    @property
    def time(self) -> datetime:
        return datetime.fromtimestamp(self.timestamp)

    @property
    def time_str(self) -> str:
        return self.time.strftime("%Y-%m-%d %H:%M:%S")


def parse_contacts(db_path: Path) -> dict[str, Contact]:
    """从 MicroMsg.db 解析联系人列表"""
    contacts = {}

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row

    # 尝试不同的表名
    for table in ["Contact", "rcontact", "contact"]:
        try:
            rows = conn.execute(f"SELECT * FROM {table}").fetchall()
            for row in rows:
                cols = row.keys()
                username = _get_field(row, cols, ["UserName", "username"])
                nickname = _get_field(row, cols, ["NickName", "nickname", "conRemark"])
                remark = _get_field(row, cols, ["Remark", "remark", "conRemark"])

                if username:
                    contacts[username] = Contact(
                        username=username,
                        nickname=nickname or "",
                        remark=remark or "",
                        is_group=username.endswith("@chatroom"),
                    )
            if contacts:
                break
        except sqlite3.OperationalError:
            continue

    conn.close()
    return contacts


def parse_messages(db_path: Path) -> list[Message]:
    """从 MSG*.db 解析消息"""
    messages = []
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row

    # 尝试不同的表名和结构
    msg_tables = _find_msg_tables(conn)

    for table in msg_tables:
        try:
            rows = conn.execute(
                f"SELECT * FROM {table} ORDER BY CreateTime ASC"
            ).fetchall()

            for row in rows:
                cols = row.keys()
                msg = _parse_row(row, cols)
                if msg is not None:
                    messages.append(msg)
        except sqlite3.OperationalError:
            continue

    conn.close()
    return messages


def _find_msg_tables(conn: sqlite3.Connection) -> list[str]:
    """查找包含消息的表"""
    cursor = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    )
    all_tables = [row[0] for row in cursor]

    msg_tables = []
    for t in all_tables:
        # 微信消息表的常见命名模式
        if re.match(r"^MSG\d*$", t, re.IGNORECASE):
            msg_tables.append(t)
        elif re.match(r"^Chat_[a-f0-9]+$", t):
            msg_tables.append(t)
        elif t in ("message", "Message"):
            msg_tables.append(t)

    return sorted(msg_tables)


def _get_field(row, cols: list[str], candidates: list[str]) -> str:
    """从多个候选列名中获取值"""
    for name in candidates:
        if name in cols:
            val = row[name]
            return str(val) if val is not None else ""
    return ""


def _parse_row(row, cols: list[str]) -> Message | None:
    """解析一行数据库记录为 Message 对象"""
    msg_type = int(_get_field(row, cols, ["Type", "type", "msgType"]) or 0)
    sub_type = int(_get_field(row, cols, ["SubType", "subType", "sub_type"]) or 0)
    content = _get_field(row, cols, ["StrContent", "strContent", "content", "Content"])
    talker = _get_field(row, cols, ["StrTalker", "strTalker", "talker", "Talker"])
    timestamp = int(_get_field(row, cols, ["CreateTime", "createTime", "create_time"]) or 0)
    is_sender = int(_get_field(row, cols, ["IsSender", "isSender", "is_sender"]) or 0)
    msg_id = int(_get_field(row, cols, ["MsgSvrID", "msgSvrId", "msgId", "localId"]) or 0)
    extra = _get_field(row, cols, ["BytesExtra", "CompressContent", "bytesExtra"])

    if timestamp == 0 or not talker:
        return None

    msg = Message(
        msg_id=msg_id,
        msg_type=msg_type,
        sub_type=sub_type,
        is_sender=bool(is_sender),
        talker=talker,
        content=content,
        timestamp=timestamp,
        extra_info=extra,
    )

    # 解析不同类型的消息
    msg.parsed_text = _format_message(msg)

    return msg


def _format_message(msg: Message) -> str:
    """将消息格式化为可读文本"""
    try:
        match msg.msg_type:
            case MsgType.TEXT:
                return msg.content

            case MsgType.IMAGE:
                return "[图片]"

            case MsgType.VOICE:
                return "[语音]"

            case MsgType.VIDEO:
                return "[视频]"

            case MsgType.EMOJI:
                return _parse_emoji(msg.content)

            case MsgType.LOCATION:
                return _parse_location(msg.content)

            case MsgType.LINK:
                return _parse_link_message(msg)

            case MsgType.VOIP:
                return "[语音/视频通话]"

            case MsgType.SYSTEM:
                return _parse_system_message(msg.content)

            case MsgType.SYSTEM_REVOKE:
                return _parse_system_message(msg.content)

            case _:
                return msg.content or f"[未知消息类型: {msg.msg_type}]"

    except Exception:
        return msg.content or f"[解析失败: type={msg.msg_type}]"


def _parse_emoji(content: str) -> str:
    """解析表情消息"""
    if not content:
        return "[表情]"
    try:
        root = ET.fromstring(content)
        desc = root.get("productid", "")
        return f"[表情: {desc}]" if desc else "[表情]"
    except ET.ParseError:
        return "[表情]"


def _parse_location(content: str) -> str:
    """解析位置消息"""
    if not content:
        return "[位置]"
    try:
        root = ET.fromstring(content)
        location = root.find(".//location")
        if location is not None:
            label = location.get("label", "")
            poiname = location.get("poiname", "")
            name = poiname or label
            return f"[位置: {name}]" if name else "[位置]"
    except ET.ParseError:
        pass
    return "[位置]"


def _parse_link_message(msg: Message) -> str:
    """解析链接类复合消息"""
    content = msg.content
    if not content:
        return "[链接]"

    try:
        root = ET.fromstring(content)
        appmsg = root.find(".//appmsg")
        if appmsg is None:
            return "[链接]"

        msg_type = int(appmsg.findtext("type", "0"))
        title = appmsg.findtext("title", "")
        des = appmsg.findtext("des", "")
        url = appmsg.findtext("url", "")

        match msg_type:
            case LinkSubType.FILE:
                filename = title or "未知文件"
                return f"[文件: {filename}]"

            case LinkSubType.QUOTE:
                # 引用回复
                ref = appmsg.find(".//refermsg")
                ref_text = ""
                if ref is not None:
                    ref_content = ref.findtext("content", "")
                    ref_name = ref.findtext("displayname", "")
                    ref_text = f"\n> {ref_name}: {ref_content}" if ref_name else ""
                reply = title or ""
                return f"{reply}{ref_text}"

            case LinkSubType.MINI_PROGRAM | LinkSubType.MINI_PROGRAM_ALT:
                return f"[小程序: {title}]"

            case LinkSubType.MUSIC:
                return f"[音乐: {title}]"

            case LinkSubType.ARTICLE:
                link_text = f"[链接: {title}]"
                if url:
                    link_text = f"[{title}]({url})"
                return link_text

            case LinkSubType.TRANSFER:
                return f"[转账: {des or title}]"

            case LinkSubType.RED_PACKET:
                return f"[红包: {title}]"

            case LinkSubType.STICKER:
                return "[动画表情]"

            case _:
                if title:
                    if url:
                        return f"[{title}]({url})"
                    return f"[链接: {title}]"
                return "[链接]"

    except ET.ParseError:
        return "[链接]"


def _parse_system_message(content: str) -> str:
    """解析系统消息（撤回、红包领取等）"""
    if not content:
        return "[系统消息]"

    # 去除 XML 标签
    text = re.sub(r"<[^>]+>", "", content).strip()
    return text or "[系统消息]"


def group_messages_by_talker(
    messages: list[Message],
) -> dict[str, list[Message]]:
    """将消息按对话对象分组"""
    groups: dict[str, list[Message]] = {}
    for msg in messages:
        if msg.talker not in groups:
            groups[msg.talker] = []
        groups[msg.talker].append(msg)

    # 每组内按时间排序
    for msgs in groups.values():
        msgs.sort(key=lambda m: m.timestamp)

    return groups
