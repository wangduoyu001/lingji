---
title: "Goose"
date: 2026-06-20
github: https://github.com/aaif-goose/goose
stars: 49906
category: AI Agent 桌面应用
interest: 2
status: 未试
usable: 待评估
实际用途: AI Agent 桌面应用框架
tags:
  - AI工具
  - GitHub
  - AI项目
  - AI框架
  - 个人助手
  - 桌面应用
---

# Goose — 电脑上的全能 AI 助手

> ⭐ 49,906 | 📅 2026-06-20 | [GitHub](https://github.com/aaif-goose/goose)
>
> 💡 **怎么标记**：改上面 `interest` 数字 → 3=必装 2=想试 1=观望 0=跳过 → 改完按 Ctrl+S 保存

## 干什么

Goose（鹅）是一个跑在你电脑上的通用 AI Agent。它不像 ChatGPT 那样只能聊天，也不像 Claude Code 那样只能写代码——它能干一切：写代码、查资料、写文章、处理数据、自动化工作流。它有三种形态：桌面 App（像普通软件一样用）、命令行工具（终端里跑）、API（嵌入到你的软件里）。

Goose 的核心卖点是"不挑食"——支持 15+ 个大模型提供商（Anthropic、OpenAI、Google、Ollama、OpenRouter 等），支持 70+ 个 MCP 扩展（通过这些扩展连接你的文件系统、数据库、GitHub、浏览器等），而且全部开源，数据完全在你电脑上。

Goose 最近被捐给了 Linux Foundation 旗下的 Agentic AI Foundation（AAIF），这意味着它有长期的组织保障，不会突然烂尾。

## 能实现什么效果

装了 Goose 之后，你电脑上就多了一个"全能管家"。你告诉它"帮我把这个文件夹里的所有 PDF 转成 Markdown 然后按主题分类"，它会自己调用 PDF 转换工具、读取内容、用 AI 分类、把结果整理好——你不需要手动操作每一个 PDF。

更具体：你可以在写代码时让 Goose 帮你重构、写文档时让 Goose 帮你查资料并整理、做数据分析时让 Goose 帮你处理 Excel——一个工具覆盖了以前需要好几个工具才能完成的事。

因为支持 MCP 协议，Goose 的可扩展性非常强——你给它接上 GitHub MCP，它就能管理你的仓库；接上文件系统 MCP，它就能批量处理文件；接上浏览器 MCP，它就能自动操作网页。

## 怎么用

- **桌面 App**（推荐新手）：去官网下载安装包 → 双击安装 → 打开 → 选一个模型提供商 → 输入 API Key → 开始对话。
- **命令行**：`curl -fsSL https://github.com/aaif-goose/goose/releases/download/stable/download_cli.sh | bash` → 终端里直接和 Goose 对话。
- **配置扩展**：在设置里添加 MCP Server（比如添加 GitHub MCP），Goose 就能获得对应能力。
- **写代码场景**：告诉 Goose "帮我实现一个用户登录功能"→ 它会读你的项目结构 → 写代码 → 运行测试 → 确认通过。
- **数据处理场景**：把 CSV 文件拖给 Goose → "分析这个销售数据，找出增长最快的产品并画个图"→ 它处理数据并生成图表。

## 运行位置

- **桌面 App**：macOS / Linux / Windows 全平台
- **命令行**：macOS / Linux / Windows
- **API 模式**：可以嵌入到你自己的软件里

## 需要准备什么

- 免费开源（Apache 2.0 协议）
- 需要至少一个大模型的 API Key（可以选 Anthropic、OpenAI、Google 等，或者用 Ollama 跑本地模型零费用）
- 桌面 App 安装很简单，双击就行
- 电脑配置：普通笔记本就能跑（如果不用本地模型的话）；如果要本地跑模型需要足够内存
- Rust 编写，性能很好，不占资源

## 配合什么软件

- 独立使用就能完成大部分工作
- 如果要本地模型：配合 Ollama
- 如果要扩展能力：配合 MCP Server（GitHub MCP、Filesystem MCP、Puppeteer MCP 等）
- 如果要自动化发布：配合 GitHub Actions

## 客观评价

**优点**：作为全平台桌面 App 的 AI Agent，体验在同类里算最好的；Rust 编写性能优秀，启动快、内存占用低；MCP 生态支持完善，扩展能力强；Linux Foundation 托管，长期可靠性有保障；一个工具替代了 ChatGPT + Claude Code + 自动化脚本的组合。

**缺点**：作为通用 Agent，"样样通样样松"——写代码不如 Claude Code 专业，写文章不如直接跟 ChatGPT 聊顺畅；配置扩展需要一定的技术能力（不是小白能搞定的）；文档以英文为主；依赖 MCP 生态发展（如果某个平台没有 MCP Server 你就没法接入）。

**适合谁**：需要一个"万能工具"而不是"专用工具"的人、技术爱好者喜欢折腾、日常电脑工作流复杂的人。**不适合**：纯粹写代码的人（用 Claude Code 更好）、纯粹聊天的人（用 ChatGPT 更简单）。

**评分 7/10**：方向正确，体验不错，但还需要更多时间打磨专用场景下的深度。

## 未来趋势

项目处于**成熟增长期**，已进入 Linux Foundation，有稳定治理结构。随着 MCP 生态爆发，Goose 作为 MCP 客户端会持续受益。

6-12 个月内：预计 MCP 扩展生态继续增长、桌面 App 体验进一步打磨、可能加入 Agent 协作能力。

**关注度 4/5**：Linux Foundation 背书 + MCP 生态优势 + 全平台覆盖，基础扎实。

## 更新记录

| 日期 | 变更 | Stars |
|------|------|-------|
| 2026-06-20 | 首次记录 | 49,906 |

---

*记录时间: 2026-06-20*

---

📂 **同类别工具**：[[_索引_AI Agent框架|查看 AI Agent框架 全部 15 个工具]]
