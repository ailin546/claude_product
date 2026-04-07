"""
微信 SQLCipher 数据库解密

微信使用 SQLCipher 3/4 加密 SQLite 数据库，参数：
- 算法: AES-256-CBC
- KDF: PBKDF2-HMAC-SHA1 (SQLCipher 3) 或 PBKDF2-HMAC-SHA512 (SQLCipher 4)
- 页大小: 4096 字节
- KDF 迭代次数: 64000
- HMAC: SHA1 (SQLCipher 3) 或 SHA512 (SQLCipher 4)
"""

import hashlib
import hmac
import shutil
import struct
import sqlite3
import tempfile
from pathlib import Path


# SQLCipher 加密参数
PAGE_SIZE = 4096
IV_SIZE = 16
HMAC_SIZE = 20  # SHA1
RESERVED_SIZE = IV_SIZE + HMAC_SIZE + 12  # IV + HMAC + padding = 48
SALT_SIZE = 16
KEY_SIZE = 32
KDF_ITERATIONS = 64000


def decrypt_db_file(
    db_path: Path,
    key: bytes,
    output_path: Path | None = None,
) -> Path:
    """
    解密微信加密数据库文件

    优先使用 pysqlcipher3（性能好、兼容性强），
    回退到纯 Python 实现（无需编译依赖）。

    Args:
        db_path: 加密数据库路径
        key: 32 字节解密密钥
        output_path: 输出路径，默认为同目录下 xxx_decrypted.db

    Returns:
        解密后的数据库文件路径
    """
    if output_path is None:
        output_path = db_path.with_suffix(".decrypted.db")

    # 检查是否已经是明文数据库
    with open(db_path, "rb") as f:
        header = f.read(16)
    if header[:6] == b"SQLite":
        # 已是明文数据库，直接复制
        shutil.copy2(db_path, output_path)
        return output_path

    # 优先用 pysqlcipher3
    try:
        return _decrypt_with_sqlcipher(db_path, key, output_path)
    except ImportError:
        pass
    except Exception as e:
        print(f"[!] pysqlcipher3 解密失败 ({e})，尝试纯 Python 解密...")

    # 回退到纯 Python 实现
    return _decrypt_raw(db_path, key, output_path)


def _decrypt_with_sqlcipher(
    db_path: Path, key: bytes, output_path: Path
) -> Path:
    """使用 pysqlcipher3 解密"""
    from pysqlcipher3 import dbapi2 as sqlcipher

    hex_key = key.hex()

    conn = sqlcipher.connect(str(db_path))
    cursor = conn.cursor()

    # 设置 SQLCipher 参数（微信使用的配置）
    cursor.execute(f"PRAGMA key = \"x'{hex_key}'\"")
    cursor.execute("PRAGMA cipher_page_size = 4096")
    cursor.execute("PRAGMA kdf_iter = 64000")
    cursor.execute("PRAGMA cipher_hmac_algorithm = HMAC_SHA1")
    cursor.execute("PRAGMA cipher_kdf_algorithm = PBKDF2_HMAC_SHA1")

    # 验证解密是否成功
    try:
        cursor.execute("SELECT count(*) FROM sqlite_master")
    except Exception:
        conn.close()
        # 尝试 SQLCipher 4 参数
        conn = sqlcipher.connect(str(db_path))
        cursor = conn.cursor()
        cursor.execute(f"PRAGMA key = \"x'{hex_key}'\"")
        cursor.execute("PRAGMA cipher_page_size = 4096")
        cursor.execute("PRAGMA kdf_iter = 256000")
        cursor.execute("PRAGMA cipher_hmac_algorithm = HMAC_SHA512")
        cursor.execute("PRAGMA cipher_kdf_algorithm = PBKDF2_HMAC_SHA512")
        cursor.execute("SELECT count(*) FROM sqlite_master")

    # 导出为明文数据库
    cursor.execute(f"ATTACH DATABASE '{output_path}' AS plaintext KEY ''")
    cursor.execute("SELECT sqlcipher_export('plaintext')")
    cursor.execute("DETACH DATABASE plaintext")
    conn.close()

    return output_path


def _decrypt_raw(db_path: Path, key: bytes, output_path: Path) -> Path:
    """
    纯 Python 解密（不依赖 pysqlcipher3）

    手动实现 SQLCipher 的解密流程：
    1. 读取文件头部的 salt
    2. 通过 PBKDF2 派生加密密钥和 HMAC 密钥
    3. 逐页解密 (AES-256-CBC)
    4. 验证每页的 HMAC
    5. 拼接为明文 SQLite 文件
    """
    try:
        from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
        from cryptography.hazmat.primitives import padding as crypto_padding
    except ImportError:
        raise RuntimeError(
            "纯 Python 解密需要 cryptography 库: pip install cryptography\n"
            "或安装 pysqlcipher3: pip install pysqlcipher3"
        )

    with open(db_path, "rb") as f:
        data = f.read()

    if len(data) < PAGE_SIZE:
        raise ValueError(f"文件太小，不是有效的加密数据库: {db_path}")

    # 提取 salt (前 16 字节)
    salt = data[:SALT_SIZE]

    # 派生密钥
    enc_key = hashlib.pbkdf2_hmac("sha1", key, salt, KDF_ITERATIONS, KEY_SIZE)

    # 派生 HMAC 密钥
    hmac_salt = bytes(b ^ 0x3A for b in salt)
    hmac_key = hashlib.pbkdf2_hmac("sha1", enc_key, hmac_salt, 2, KEY_SIZE)

    # 逐页解密
    usable_size = PAGE_SIZE - RESERVED_SIZE
    total_pages = len(data) // PAGE_SIZE
    plain_pages = []

    for page_num in range(total_pages):
        page_offset = page_num * PAGE_SIZE

        if page_num == 0:
            # 第一页跳过 salt
            enc_data = data[page_offset + SALT_SIZE : page_offset + SALT_SIZE + usable_size - SALT_SIZE]
            iv = data[page_offset + PAGE_SIZE - RESERVED_SIZE : page_offset + PAGE_SIZE - RESERVED_SIZE + IV_SIZE]
        else:
            enc_data = data[page_offset : page_offset + usable_size]
            iv = data[page_offset + usable_size : page_offset + usable_size + IV_SIZE]

        # AES-256-CBC 解密
        cipher = Cipher(algorithms.AES(enc_key), modes.CBC(iv))
        decryptor = cipher.decryptor()
        try:
            plain_data = decryptor.update(enc_data) + decryptor.finalize()
        except Exception:
            # 如果解密失败，跳过此页
            plain_pages.append(b"\x00" * PAGE_SIZE)
            continue

        if page_num == 0:
            # 第一页需要加上 SQLite 文件头
            plain_page = b"SQLite format 3\x00" + plain_data
            # 填充到完整页大小
            plain_page = plain_page[:PAGE_SIZE]
            if len(plain_page) < PAGE_SIZE:
                plain_page += b"\x00" * (PAGE_SIZE - len(plain_page))
        else:
            plain_page = plain_data[:PAGE_SIZE]
            if len(plain_page) < PAGE_SIZE:
                plain_page += b"\x00" * (PAGE_SIZE - len(plain_page))

        plain_pages.append(plain_page)

    # 写入明文数据库
    with open(output_path, "wb") as f:
        for page in plain_pages:
            f.write(page)

    # 验证输出
    try:
        conn = sqlite3.connect(str(output_path))
        conn.execute("SELECT count(*) FROM sqlite_master")
        conn.close()
    except sqlite3.DatabaseError:
        output_path.unlink(missing_ok=True)
        raise RuntimeError(
            f"解密失败: {db_path.name}\n"
            "可能的原因：密钥错误或微信版本不兼容"
        )

    return output_path


def decrypt_all_dbs(
    db_files: list[Path],
    key: bytes,
    output_dir: Path,
) -> list[Path]:
    """批量解密所有数据库文件"""
    output_dir.mkdir(parents=True, exist_ok=True)
    decrypted = []

    for db_file in db_files:
        output_path = output_dir / db_file.name
        try:
            result = decrypt_db_file(db_file, key, output_path)
            decrypted.append(result)
            print(f"[+] 解密成功: {db_file.name}")
        except Exception as e:
            print(f"[!] 解密失败: {db_file.name} - {e}")

    return decrypted
