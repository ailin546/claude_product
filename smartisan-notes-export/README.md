# 锤子便签 Markdown 导出工具

将锤子便签（Smartisan Notes）中的全部笔记导出为 Markdown 格式文件。

## 功能特点

- 一键导出全部笔记为 `.md` 文件
- 按文件夹分类打包为 ZIP
- 保留笔记修改时间
- 处理同名文件自动编号
- 兼容 `cloud.smartisan.com` 和 `note.smartisan.com`
- 无需后端服务，纯本地读取

## 导出格式

```
smartisan-notes-2026-04-07.zip
├── 工作/
│   ├── 会议纪要.md
│   └── 项目计划.md
├── 生活/
│   └── 购物清单.md
└── 未分类/
    └── 随手记.md
```

每个 `.md` 文件内容：

```markdown
# 笔记标题

> 修改时间：2026/04/07 10:30:00

笔记正文内容...
```

## 使用方式

### 方式一：Chrome 扩展（推荐）

1. 打开 Chrome，进入 `chrome://extensions/`
2. 开启右上角「开发者模式」
3. 点击「加载已解压的扩展程序」
4. 选择本项目的 `smartisan-notes-export` 目录
5. 打开 [cloud.smartisan.com](https://cloud.smartisan.com) 并登录
6. 等待笔记同步完成
7. 点击页面右上角红色「导出 Markdown」按钮

### 方式二：浏览器控制台脚本

适用于不想安装扩展的情况：

1. 打开 [cloud.smartisan.com](https://cloud.smartisan.com) 并登录
2. 等待笔记同步完成
3. 按 `F12` 打开开发者工具 → Console
4. 复制 `src/standalone.js` 的全部内容，粘贴到控制台并回车

## 原理

锤子便签的 Web 端使用 PouchDB 将笔记数据缓存在浏览器的 IndexedDB 中。本工具直接读取这些本地数据库：

| 数据库 | 内容 |
|--------|------|
| `_pouch_folder` | 文件夹信息（名称、ID） |
| `_pouch_note` | 笔记数据（标题、正文、时间、所属文件夹） |

不涉及任何网络请求，不上传任何数据。

## 注意事项

- 必须先登录锤子便签网页版，等待数据同步到浏览器本地
- 如果导出为空，请刷新页面等待同步后重试
- 本工具仅读取数据，不会修改或删除任何笔记

## 致谢

参考了 [reed-soul/smartisan-notes-saver](https://github.com/reed-soul/smartisan-notes-saver) 的实现思路。
