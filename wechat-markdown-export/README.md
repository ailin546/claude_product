# 微信聊天记录 Markdown 导出工具

将微信（WeChat）PC/Mac 端的聊天记录导出为 Markdown 文档。

## 功能

- 自动查找微信数据目录（Windows + macOS）
- 自动从微信进程内存提取数据库解密密钥
- 解密 SQLCipher 加密的 SQLite 数据库
- 解析多种消息类型（文字、图片、语音、视频、文件、链接、小程序、引用回复、红包、转账等）
- 按联系人/群聊分目录，按月份分文件导出
- 支持过滤特定联系人
- 可复制相关媒体文件

## 导出格式

```
wechat-export-output/
├── 张三/
│   ├── chat.md              # 完整聊天记录
│   ├── 2025-01.md           # 按月份分割
│   ├── 2025-02.md
│   └── media/               # 媒体文件
├── 工作群/
│   └── chat.md
└── 李四/
    └── chat.md
```

每个 `.md` 文件示例：

```markdown
# 张三

> 时间范围：2024-01-01 ~ 2025-12-31
> 消息数量：1234

---
### 2025-03-15 星期六

**张三** `10:30:15`

今天天气不错

**我** `10:31:02`

是啊，出去走走吧

**张三** `10:32:45`

[图片]

**张三** `10:33:01`

[位置: 中山公园]
```

## 安装

```bash
# 克隆项目
git clone <repo-url>
cd wechat-markdown-export

# 安装依赖
pip install -e .

# macOS/Linux 可能还需要:
pip install pysqlcipher3

# 如果 pysqlcipher3 安装困难，可用纯 Python 解密（需要 cryptography）:
pip install cryptography
```

### 依赖说明

| 依赖 | 平台 | 用途 |
|------|------|------|
| `pysqlcipher3` | 全平台 | SQLCipher 解密（推荐） |
| `cryptography` | 全平台 | 纯 Python 解密（备选） |
| `pymem` | Windows | 从进程内存提取密钥 |

## 使用

### 自动模式（推荐）

确保微信正在运行并已登录，然后：

```bash
# Windows: 需要管理员权限运行终端
# macOS: 可能需要 sudo 或关闭 SIP

wechat-export
```

工具会自动：
1. 查找微信数据目录
2. 从微信进程提取密钥
3. 解密数据库
4. 导出 Markdown

### 手动指定密钥

如果自动提取密钥失败，可以使用其他工具获取密钥后手动指定：

```bash
wechat-export --key 你的64位十六进制密钥
```

### 更多选项

```bash
# 指定数据目录
wechat-export --data-dir "C:\Users\xxx\Documents\WeChat Files\wxid_xxx"

# 指定输出目录
wechat-export -o ./my-export

# 仅导出特定联系人
wechat-export --filter "张三,工作群"

# 设置自己的显示名称
wechat-export --my-name "小明"

# 使用已解密的数据库（跳过解密步骤）
wechat-export --decrypted-dir ./已解密的数据库目录
```

## 获取密钥的替代方法

如果自动提取密钥失败，可以使用以下工具：

| 平台 | 工具 |
|------|------|
| Windows | [Aeron1-bit/PyWxDump](https://github.com/Aeron1-bit/PyWxDump) |
| macOS | [cocohahaha/wechat-decrypt-macos](https://github.com/cocohahaha/wechat-decrypt-macos) |

获取密钥后，使用 `--key` 参数传入。

## 工作原理

```
微信 PC/Mac 端
    │
    ├── 本地 SQLite 数据库（SQLCipher 加密）
    │   ├── MicroMsg.db    → 联系人、群聊信息
    │   ├── MSG0.db        → 消息记录
    │   ├── MSG1.db        → 消息记录（续）
    │   └── ...
    │
    └── FileStorage/       → 图片、语音、视频、文件
```

本工具的流程：
1. **定位** → 自动查找微信数据存储路径
2. **取钥** → 从微信进程内存读取 SQLCipher 解密密钥
3. **解密** → 将加密的 SQLite 数据库解密为明文
4. **解析** → 读取联系人表和消息表，解析不同消息类型
5. **导出** → 按联系人分目录、按日期分段，生成 Markdown 文件

## 支持的消息类型

| 类型 | 导出格式 |
|------|----------|
| 文字 | 原文 |
| 图片 | `[图片]` + 复制文件 |
| 语音 | `[语音]` |
| 视频 | `[视频]` |
| 表情 | `[表情]` |
| 位置 | `[位置: 地点名]` |
| 文件 | `[文件: 文件名]` |
| 链接 | `[标题](URL)` |
| 小程序 | `[小程序: 名称]` |
| 引用回复 | 引用内容 + 回复 |
| 红包 | `[红包: 祝福语]` |
| 转账 | `[转账: 金额]` |
| 语音通话 | `[语音/视频通话]` |
| 系统消息 | *斜体显示* |

## 注意事项

- **Windows** 需要以**管理员权限**运行终端（读取进程内存需要）
- **macOS** 可能需要关闭 SIP 或授予终端调试权限
- 仅能导出**已同步到 PC/Mac 端的消息**，手机端独有的消息无法导出
- 杀毒软件可能会阻止进程内存读取，请添加信任
- 微信版本更新可能影响密钥提取，如遇问题请使用 `--key` 手动指定
- 本工具**仅读取数据，不修改任何微信文件**

## 法律声明

本工具仅供个人备份自己的聊天记录使用。请遵守当地法律法规，不要用于未经授权的数据获取。
