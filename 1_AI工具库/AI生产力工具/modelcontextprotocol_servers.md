---
title: "MCP Servers"
date: 2026-06-18
github: https://github.com/modelcontextprotocol/servers
stars: 87406
category: MCP生态
interest: 1
status: 未试
usable: 待评估
实际用途: MCP 协议官方服务器集合
tags:
  - AI工具
  - GitHub
  - AI项目
  - MCP
  - AI工具
---

# MCP Servers

> ⭐ 87,406 | 📅 2026-06-18 | [GitHub](https://github.com/modelcontextprotocol/servers)
>
> 💡 **怎么标记**：改上面 `interest` 数字 → 3=必装 2=想试 1=观望 0=跳过 → 改完按 Ctrl+S 保存

## 干什么

MCP Servers 是 AI 世界的"万能转接头"——它用一套标准协议让 AI 能连接和控制各种外部工具。MCP（Model Context Protocol，模型上下文协议）就像是 AI 的 USB 接口：不管你插什么设备（数据库、文件系统、浏览器、搜索引擎），AI 都能用同一套方式跟它们交互。以前想让 AI 查你的数据库，得专门写一段代码去对接；现在只要装一个对应的 MCP Server，AI 就能直接查、直接改。这个仓库是官方维护的参考实现集合，包含了连接文件系统、GitHub、PostgreSQL、Slack、Google 地图等几十种工具的现成 Server。

## 能实现什么效果

装了 MCP Server 之后，你的 AI 编程代理（Claude Code/Codex 等）的能力会发生质变。以前 AI 只能分析你给的代码，现在它可以直接：查你的 GitHub Issues 然后修复指定的 bug；读取你的数据库然后生成数据报表；调用搜索引擎查最新的技术文档然后回答问题；操作你的浏览器自动完成网页上的重复操作。它把 AI 从一个"只会聊天的脑袋"变成了一个"有手有脚能用工具的身体"。2026 年 MCP 已经移交给 Linux Foundation 治理，成为行业标准。

## 怎么用

- **代码管理**：安装 GitHub MCP Server → 在 Claude Code 里说"帮我看看这个仓库最新的 5 个 PR，总结一下改了什么" → AI 自动调用 GitHub API
- **数据查询**：安装 PostgreSQL MCP Server → "查一下上个月的销售数据，哪些产品利润率低于 10%" → AI 自动写 SQL 并执行
- **文件操作**：安装 Filesystem MCP Server → "帮我把 Downloads 文件夹里所有的 PDF 文件移动到文档/Pdf/目录" → AI 自动操作文件系统
- **网页搜索**：安装 Brave Search MCP Server → "搜索 2026 年最新的 TypeScript 5.0 特性，总结给我" → AI 自动联网搜索
- **浏览器自动化**：安装 Puppeteer MCP Server → "帮我登录这个网站，把订单历史导出为 CSV" → AI 自动操控浏览器

## 运行位置

- **本地电脑**：跟 AI 编程工具同一台电脑上运行（Node.js/Python）
- 本质上是后台服务，由 AI 编程代理调用
- TypeScript 和 Python 都有官方实现

## 需要准备什么

- **费用**：完全免费开源
- **账号**：安装 MCP Server 本身不需要；但某些 Server 需要对应的服务账号（比如 GitHub Server 需要 GitHub token）
- **API Key**：取决于使用的 Server 类型——GitHub Server 需要 GitHub Token，数据库 Server 不需要
- **电脑配置**：几乎不消耗资源（只是中间层转发），任何能跑 Node.js/Python 的电脑都行
- **软件依赖**：Node.js 或 Python，以及对应的 AI 编程工具（Claude Code/Codex CLI 等）

## 配合什么软件

必须配合支持 MCP 协议的 AI 工具（Claude Code、Codex CLI、Cline、Cursor、Gemini CLI 等）。不能独立使用。每个 MCP Server 需要对应它在操作的"东西"（如数据库、GitHub 账号）。

## 客观评价

优点：① MCP 正在成为 AI 工具互联的行业标准——2026 年几乎所有主流 AI 工具都支持了 MCP；② 官方维护，Server 质量可靠；③ 极大扩展 AI 代理的能力边界；④ 社区贡献活跃，新的 Server 每天都在增加。

缺点/坑：① 概念对新手来说比较抽象——"什么是协议""什么是 Server""什么是 Client"搞明白要花时间；② 配置比较繁琐——每个 Server 都需要单独配置，Token/密码管理容易混乱；③ 安全性需要注意——给了 AI 数据库权限，如果它"理解错"了你的意图，可能误操作；④ MCP 协议还在快速演进，偶尔有兼容性问题。

适合谁：AI 编程代理的重度用户、想把 AI 接入公司内部系统的开发者。不适合：只用 AI 聊天不用 AI 编程的人、对安全和权限管理不敏感的用户。

打分：8/10。MCP 是 2026 年最重要的 AI 基础设施之一，但体验还不够"开箱即用"。扣 2 分因为配置繁琐和安全风险。

## 未来趋势

① 所处阶段：快速标准化——2026 年移交 Linux Foundation 后成为行业标准；② 6-12 个月：会出现官方 MCP 管理面板，一键安装和配置各种 Server；③ 关注度：5/5，AI Agent 时代的基础设施。

## 更新记录

| 日期 | 变更 | Stars |
|------|------|-------|
| 2026-06-18 | 首次记录 | 87,406 |

---

*记录时间: 2026-06-18*
