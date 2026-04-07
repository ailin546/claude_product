"""
微信聊天记录 Markdown 导出 - CLI 入口

用法:
    # 自动模式（检测数据路径 + 提取密钥 + 导出）
    wechat-export

    # 手动指定密钥
    wechat-export --key YOUR_HEX_KEY

    # 手动指定数据目录
    wechat-export --data-dir "C:\\Users\\xxx\\Documents\\WeChat Files\\wxid_xxx"

    # 指定输出目录
    wechat-export -o ./my-wechat-export

    # 仅导出特定联系人
    wechat-export --filter "张三,李四"

    # 使用已解密的数据库
    wechat-export --decrypted-dir ./decrypted_dbs
"""

import argparse
import sys
import tempfile
from pathlib import Path

from .platform import WeChatDataPaths, find_wechat_data, find_db_files
from .key_extract import extract_key, parse_hex_key
from .decrypt import decrypt_all_dbs
from .parser import parse_contacts, parse_messages, group_messages_by_talker
from .exporter import export_to_markdown


def main():
    parser = argparse.ArgumentParser(
        description="微信聊天记录 Markdown 导出工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  wechat-export                           # 自动检测并导出
  wechat-export --key abc123...           # 手动指定密钥
  wechat-export --data-dir /path/to/data  # 手动指定数据目录
  wechat-export --filter "张三,群聊名"    # 仅导出指定联系人/群聊
  wechat-export --decrypted-dir ./dbs     # 使用已解密的数据库
        """,
    )
    parser.add_argument(
        "-o", "--output",
        type=Path,
        default=Path("./wechat-export-output"),
        help="输出目录 (默认: ./wechat-export-output)",
    )
    parser.add_argument(
        "--key",
        type=str,
        help="数据库解密密钥 (64 位十六进制字符串)",
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        help="微信数据目录路径 (包含 Msg/ 子目录)",
    )
    parser.add_argument(
        "--decrypted-dir",
        type=Path,
        help="已解密的数据库目录 (跳过解密步骤)",
    )
    parser.add_argument(
        "--filter",
        type=str,
        help="仅导出指定联系人/群聊，逗号分隔",
    )
    parser.add_argument(
        "--my-name",
        type=str,
        default="我",
        help="自己的显示名称 (默认: 我)",
    )
    parser.add_argument(
        "--no-monthly",
        action="store_true",
        help="不按月份分割文件",
    )

    args = parser.parse_args()

    print("=" * 50)
    print("  微信聊天记录 Markdown 导出工具")
    print("=" * 50)
    print()

    try:
        _run(args)
    except KeyboardInterrupt:
        print("\n[!] 用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n[错误] {e}")
        sys.exit(1)


def _run(args: argparse.Namespace):
    # ---- Step 1: 确定数据库文件 ----
    if args.decrypted_dir:
        # 直接使用已解密的数据库
        print(f"[1/4] 使用已解密数据库: {args.decrypted_dir}")
        db_files = list(args.decrypted_dir.glob("*.db"))
        if not db_files:
            raise RuntimeError(f"目录中未找到 .db 文件: {args.decrypted_dir}")
        decrypted_dbs = db_files
        data_paths = None
    else:
        # 查找微信数据
        data_paths = _resolve_data_paths(args)

        # 查找数据库文件
        db_files = find_db_files(data_paths)
        if not db_files:
            raise RuntimeError(
                f"未找到数据库文件: {data_paths.msg_dir}\n"
                "请确保微信已同步聊天记录到本地"
            )
        print(f"    找到 {len(db_files)} 个数据库文件")

        # ---- Step 2: 解密数据库 ----
        print("\n[2/4] 解密数据库...")
        key = _resolve_key(args)
        print(f"    密钥: {key[:4].hex()}...{key[-4:].hex()}")

        tmp_dir = Path(tempfile.mkdtemp(prefix="wechat_export_"))
        decrypted_dbs = decrypt_all_dbs(db_files, key, tmp_dir)

        if not decrypted_dbs:
            raise RuntimeError("所有数据库解密失败")
        print(f"    成功解密 {len(decrypted_dbs)} 个数据库")

    # ---- Step 3: 解析消息 ----
    print("\n[3/4] 解析消息...")

    # 解析联系人
    contacts = {}
    for db in decrypted_dbs:
        try:
            c = parse_contacts(db)
            contacts.update(c)
        except Exception:
            pass
    print(f"    联系人: {len(contacts)} 个")

    # 解析消息
    all_messages = []
    for db in decrypted_dbs:
        try:
            msgs = parse_messages(db)
            all_messages.extend(msgs)
        except Exception as e:
            print(f"    [!] 解析失败 {db.name}: {e}")
    print(f"    消息总数: {len(all_messages)}")

    if not all_messages:
        raise RuntimeError("未解析到任何消息")

    # 按对话分组
    grouped = group_messages_by_talker(all_messages)
    print(f"    对话数: {len(grouped)}")

    # 过滤
    if args.filter:
        filter_names = set(n.strip() for n in args.filter.split(","))
        filtered = {}
        for talker, msgs in grouped.items():
            contact = contacts.get(talker)
            name = contact.display_name if contact else talker
            if name in filter_names or talker in filter_names:
                filtered[talker] = msgs
        if not filtered:
            print(f"    [!] 未找到匹配的联系人: {args.filter}")
            print(f"    可用联系人: {', '.join(c.display_name for c in contacts.values() if c.display_name)[:200]}")
            return
        grouped = filtered
        print(f"    过滤后: {len(grouped)} 个对话")

    # ---- Step 4: 导出 Markdown ----
    print(f"\n[4/4] 导出 Markdown 到: {args.output}")

    media_dir = data_paths.image_dir if data_paths else None
    stats = export_to_markdown(
        messages_by_talker=grouped,
        contacts=contacts,
        output_dir=args.output,
        my_name=args.my_name,
        media_source_dir=media_dir,
    )

    # 打印统计
    print(f"\n{'=' * 50}")
    print(f"  导出完成！")
    print(f"{'=' * 50}")
    print(f"  对话数: {len(stats)}")
    print(f"  消息总数: {sum(stats.values())}")
    print(f"  输出目录: {args.output.resolve()}")
    print()

    # 按消息数排序显示前 20 个
    sorted_stats = sorted(stats.items(), key=lambda x: x[1], reverse=True)
    print("  消息最多的对话:")
    for name, count in sorted_stats[:20]:
        print(f"    {name}: {count} 条")

    if len(sorted_stats) > 20:
        print(f"    ... 还有 {len(sorted_stats) - 20} 个对话")
    print()


def _resolve_data_paths(args: argparse.Namespace) -> WeChatDataPaths:
    """确定微信数据路径"""
    print("[1/4] 查找微信数据...")

    if args.data_dir:
        data_dir = args.data_dir
        if not data_dir.exists():
            raise RuntimeError(f"指定的目录不存在: {data_dir}")

        # 如果指定的是包含多个账号的父目录，扫描子目录
        from .platform import _detect_account_paths

        paths = _detect_account_paths(data_dir, data_dir.name)
        if paths is not None:
            return paths

        # 扫描子目录寻找账号
        sub_results = []
        for entry in data_dir.iterdir():
            if not entry.is_dir():
                continue
            if entry.name.lower() in ("all_users", "all users", "applet", "wmpf", "backup"):
                continue
            sub = _detect_account_paths(entry, entry.name)
            if sub is not None:
                sub_results.append(sub)

        if len(sub_results) == 1:
            return sub_results[0]
        if len(sub_results) > 1:
            print(f"    找到 {len(sub_results)} 个微信账号:")
            for i, p in enumerate(sub_results):
                print(f"      [{i + 1}] {p.wxid} ({p.base_dir})")
            while True:
                try:
                    choice = input(f"\n    请选择账号 [1-{len(sub_results)}]: ").strip()
                    idx = int(choice) - 1
                    if 0 <= idx < len(sub_results):
                        return sub_results[idx]
                except (ValueError, EOFError):
                    pass
                print("    无效选择，请重试")

        # 兜底：当作直接包含 db 文件的目录
        return WeChatDataPaths(
            wxid=data_dir.name,
            base_dir=data_dir,
            msg_dir=data_dir,
            contact_db=None,
            image_dir=data_dir / "FileStorage" / "Image",
            voice_dir=data_dir / "FileStorage" / "Voice",
            video_dir=data_dir / "FileStorage" / "Video",
            file_dir=data_dir / "FileStorage" / "File",
            avatar_dir=data_dir / "FileStorage" / "General" / "Data",
        )

    # 自动查找
    all_paths = find_wechat_data()
    if not all_paths:
        raise RuntimeError(
            "未找到微信数据目录。\n\n"
            "可能的原因:\n"
            "1. 微信未安装或从未登录\n"
            "2. 数据存储在非默认路径\n\n"
            "请使用 --data-dir 手动指定路径"
        )

    if len(all_paths) == 1:
        paths = all_paths[0]
        print(f"    找到微信账号: {paths.wxid}")
        print(f"    数据目录: {paths.base_dir}")
        return paths

    # 多个账号，让用户选择
    print(f"    找到 {len(all_paths)} 个微信账号:")
    for i, p in enumerate(all_paths):
        print(f"      [{i + 1}] {p.wxid} ({p.base_dir})")

    while True:
        try:
            choice = input(f"\n    请选择账号 [1-{len(all_paths)}]: ").strip()
            idx = int(choice) - 1
            if 0 <= idx < len(all_paths):
                return all_paths[idx]
        except (ValueError, EOFError):
            pass
        print("    无效选择，请重试")


def _resolve_key(args: argparse.Namespace) -> bytes:
    """确定解密密钥"""
    if args.key:
        return parse_hex_key(args.key)

    print("    自动提取密钥（需要微信正在运行）...")
    return extract_key()


if __name__ == "__main__":
    main()
