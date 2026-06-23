---
title: "openai/codex"
date: 2026-06-17
github: https://github.com/openai/codex
stars: 91400
interest: 1
status: 未试
usable: 待评估
category: AI编程工具
实际用途: 终端 AI 编程助手，替代 Cursor/GitHub Copilot
tags:
  - AI工具
  - GitHub
  - AI项目
  - AI编程
  - Codex
  - 编程工具
---

# Codex CLI

> ⭐ 91,400 | 📅 2026-06-17 | [GitHub](https://github.com/openai/codex)
>
> 💡 **怎么标记**：改上面 `interest` 数字 → 3=必装 2=想试 1=观望 0=跳过 → 改完按 Ctrl+S 保存

## 干什么

Codex CLI 是 OpenAI 官方出的终端编程助手。它不像那些需要在网页上复制粘贴代码的 AI 工具——它是直接跑在你电脑终端里的真家伙，能读你的项目文件、直接帮你写代码、改代码、运行命令。你可以把它想象成"一个会编程的 OpenAI 员工坐在你旁边"，你说话，它干活。

它最厉害的地方是轻量快速。和 Claude Code 比起来，Codex CLI 用的是 Rust 写的核心，速度更快、占用内存更少，启动几乎是秒开。对小项目或者快速改几行代码来说，它比那些"大家伙"更顺手。

它是 OpenAI 官方出品，不是第三方山寨货，安全性和兼容性有保障。除了终端版，它还有 VS Code 插件版、桌面应用版（运行 `codex app` 就能启动），甚至还有云端版（chatgpt.com/codex），你可以根据喜好选。

## 能实现什么效果

举个例子：你想给网站加一个"回到顶部"的按钮。以前你要打开编辑器、找到对应的 HTML/CSS/JS 文件、逐个修改、然后测试。用 Codex CLI，你只在终端里说一句话："帮我加一个回到顶部的按钮，点击后平滑滚动到页面顶部"——它会在几秒内找出需要改的文件、生成完整代码、甚至帮你运行测试看有没有报错。原本要花 20 分钟的事，2 分钟搞定。

另一个例子：你在用一个开源项目，文档写得不清楚，你看不懂某个配置项是干嘛的。把那个配置文件丢给 Codex CLI，它能读出配置项的含义、给出推荐值、甚至帮你把配置改成最适合你项目的设置。相当于身边有个 OpenAI 的工程师帮你读代码。

它还能帮你写测试用例、生成项目文档、重构烂代码。比如你有一堆写了好几年都没人敢动的旧代码，让它"帮我给这段代码写单元测试并确保覆盖率超过 80%"，它会逐个函数分析、生成测试、跑测试、报结果。

## 怎么用

- **快速改代码**：打开终端进入项目目录 → 运行 `codex` → 说"把所有的 console.log 改成合适的日志库调用" → 审查改动 → 保存 ✓
- **调试报错**：复制终端里的报错信息 → 丢给 Codex CLI → 它会分析是哪个文件的哪一行、为什么报错、怎么修 → 确认后执行修复
- **生成新功能**：告诉它你要什么（比如"加一个导出 Excel 的功能"） → 它生成代码 → 你试运行 → 有问题继续对话修改
- **代码审查**：把同事的 PR diff 复制过来 → 让它"帮我审查这些改动，找出潜在 bug" → 得到详细审查意见
- **项目文档**：说"帮我给这个项目生成一个 README，包括安装步骤和使用示例" → 自动生成完整文档

## 运行位置

- 🖥️ **Windows / Mac / Linux 都可以**：在终端（命令行）里运行
- 需要联网（要调用 OpenAI 的云端 AI 才能工作）
- 不是网页版，是装在本地的命令行工具
- 也可以用 VS Code 插件版，在编辑器里直接用
- 桌面应用版（运行 `codex app` 或访问 chatgpt.com/codex?app-landing-page=true）

## 需要准备什么

- 💰 **要钱吗**：有两种用法。① 用 ChatGPT 账号登录（Plus/Pro/Business 计划包含 Codex 使用额度），这是最省事的。② 用 API Key 按量付费，写代码量不大的话一个月几十块。先去 platform.openai.com 注册，生成 API Key
- 🔑 **API Key 或登录**：可以用 ChatGPT 账号直接登录（推荐），也可以配置 OpenAI API Key。登录方式选"Sign in with ChatGPT"，按提示操作就行
- 💻 **电脑配置**：要求很低，普通办公电脑就行。有 8GB 内存就够了。不需要显卡（AI 运算在云端）
- 📦 **要装什么**：Windows 用户运行 `powershell -ExecutionPolicy ByPass -c "irm https://chatgpt.com/codex/install.ps1 | iex"`，Mac/Linux 用户运行 `curl -fsSL https://chatgpt.com/codex/install.sh | sh`。也可以 `npm install -g @openai/codex` 或 `brew install --cask codex`
- 🌐 **网络**：需要能访问 OpenAI 的服务器。国内网络可能需要代理才能连上

## 配合什么软件

- **终端**：必须配合终端使用（Windows 的 PowerShell 或 CMD、Mac 的 Terminal、Linux 的 Bash）
- **VS Code**：有官方插件，可以在 VS Code 里用，不用切到终端。去 chatgpt.com/codex/ide 安装
- **Git**：强烈建议项目用 Git 管理（这样 Codex CLI 改错了可以一键回退）
- **ChatGPT**：可以用同一个 ChatGPT 账号，在网页版和 CLI 之间无缝切换

## 客观评价

**优点**：
- OpenAI 官方出品，质量有保障，更新及时，不用担心跑路
- 轻量快速，Rust 核心让启动和运行速度都比同类工具快
- 多种使用方式：终端 CLI、VS Code 插件、桌面应用、云端版，覆盖面广
- 可以用 ChatGPT 账号直接登录，不用单独管理 API Key 和余额
- 开源（Apache 2.0 许可证），代码透明

**缺点/坑**：
- 对网络有要求，国内直连 OpenAI 服务器可能很慢或连不上，需要搞定代理
- API 按量付费的话，改大型项目可能烧钱（虽然 ChatGPT Plus 用户有包含额度）
- 功能上还比不上 Claude Code 那么"懂项目"，复杂项目的理解能力稍弱
- 终端版对不熟悉命令行的用户有一定学习成本
- Windows 安装需要执行 PowerShell 脚本，可能被系统安全策略拦截

**适合谁**：已经熟悉终端操作、想要一个轻量快速的 AI 编程助手的人。如果你是 ChatGPT Plus 用户，这个工具几乎是白送的，强烈建议试试。

**不适合谁**：完全不知道什么是终端的人、网络环境无法访问 OpenAI 服务器且搞不定代理的人。

**评分**：7.5/10 — 轻量快速，官方背书，但网络要求和功能深度稍逊于 Claude Code

## 未来趋势

- 📈 **所处阶段**：快速增长期。OpenAI 官方在大力推广，功能在快速迭代
- 🔮 **6-12 个月走向**：大概率会和 VS Code 更深度集成，可能加入类似 Claude Code 的"理解整个项目"的能力。桌面应用版可能会加入更多可视化功能。免费额度可能会调整（目前 Plus 用户包含使用额度）
- ⭐ **关注度**：4/5 — OpenAI 官方出品，值得关注，但竞争激烈（Claude Code 目前更受欢迎）

## 更新记录

---

*记录时间: 2026-06-17*

---

📂 **同类别工具**：[[_索引_AI编程工具|查看 AI编程工具 全部 24 个工具]]

---
## 相关内容

- [[aaif-goose_goose]]
- [[addyosmani_agent-skills]]
- [[affaan-m_ECC]]
- [[Aider-AI_aider]]
- [[anomalyco_opencode]]
