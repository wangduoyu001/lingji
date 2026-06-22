---
title: "google-gemini/gemini-cli"
date: 2026-06-17
github: https://github.com/google-gemini/gemini-cli
stars: 105000
interest: 1
status: 未试
usable: 待评估
category: AI编程工具
实际用途: Google Gemini 命令行工具
tags:
  - GitHub
  - AI项目
  - AI编程工具
---

# Gemini CLI

> ⭐ 105,000 | 📅 2026-06-17 | [GitHub](https://github.com/google-gemini/gemini-cli)
>
> 💡 **怎么标记**：改上面 `interest` 数字 → 3=必装 2=想试 1=观望 0=跳过 → 改完按 Ctrl+S 保存

## 干什么

Gemini CLI 是 Google 官方出的终端 AI 编程助手。它和 Claude Code、Codex CLI 是同一类产品，但有个杀手锏：用个人 Google 账号登录就能免费用，而且额度很大方——每分钟 60 次请求、每天 1000 次请求，对个人开发者来说基本用不完。你可以把它想象成"Google 雇了个程序员帮你写代码，还不要你钱"。

它最厉害的地方是 1M token 的上下文窗口（能一口气读几万行代码）。什么概念呢？Claude Code 最多能读几万行，GPT-4 最多能读一两万行，Gemini CLI 能读整个中型项目——所有文件一次性全塞进去，它都能记住。你不用再担心"项目太大它理解不了"。

它是 Google 官方出品，用的是 Gemini 系列模型（目前最强的是 Gemini 2.5 Pro，支持推理能力）。开源（Apache 2.0），代码完全透明。除了免费额度，还支持 API Key 和 Vertex AI（企业版），可以根据需要选择。

## 能实现什么效果

举个例子：你接手了一个跑了三年的老项目，代码堆了几万行，文档几乎没有，你完全不知道从哪下手。以前你要花好几天时间一行行读代码、画架构图、写注释。用 Gemini CLI，你在项目目录运行 `gemini`，然后说"帮我分析这个项目的架构，画出主要的模块关系，并找出最可能出bug的三个地方"——因为它有 1M token 上下文，它能一口气读完整个项目，给出完整分析。原本要花几天的事，半小时就搞定了。

另一个例子：你要做一个新功能，但不确定最好的实现方式。你把需求告诉 Gemini CLI，它不仅能写代码，还能用 Google Search 联网搜索（内置功能）最新的最佳实践、查官方文档、看别的开发者踩过的坑，然后给你一个综合考虑了性能、可维护性、安全性的方案。相当于身边有个会 Google 搜索的高级架构师。

它还能做自动化脚本。比如你希望每次提交代码前，自动让 AI 审查一遍改动、跑测试、更新文档。用 Gemini CLI 的"非交互模式"（headless mode），写个简单的 shell 脚本就能实现，完全不用手动操作。

## 怎么用

- **快速开始**：打开终端进入项目目录 → 运行 `gemini` → 选择"Sign in with Google"登录 → 直接开始对话 ✓（最推荐，免费额度够用）
- **分析整个项目**：进入项目目录 → 运行 `gemini` → 说"分析这个项目，告诉我主要功能和架构" → 它会读所有文件 → 给出详细分析
- **写新代码**：运行 `gemini` → 说"用 Python 写一个爬虫，抓取豆瓣电影 Top250 的数据并保存为 CSV" → 它生成完整代码 → 你试运行 → 有问题继续对话修改
- **自动化脚本**：运行 `gemini -p "运行测试并修复所有失败的用例"` → 它会非交互式地执行任务，适合写在 shell 脚本里自动跑
- **GitHub 集成**：在 GitHub 仓库里 at 它（`@gemini-cli`）→ 它会自动审查 PR、给 issue 打标签、回答技术问题

## 运行位置

- 🖥️ **Windows / Mac / Linux 都可以**：在终端（命令行）里运行
- 需要联网（要调用 Google 的 Gemini API）
- 不是网页版，是装在本地的命令行工具
- 支持 VS Code 集成（有配套扩展）
- 可以在 GitHub Actions 里用（自动化代码审查）

## 需要准备什么

- 💰 **要钱吗**：个人用户基本不用钱！用 Google 账号登录就能享受免费额度（每分钟 60 次、每天 1000 次请求），对个人开发者来说完全够用。如果用量特别大，可以付费升级或者用 Google Cloud 的付费计划
- 🔑 **API Key 或登录**：推荐用 Google 账号直接登录（OAuth），不用管 API Key，最省事。也可以配置 Gemini API Key（从 aistudio.google.com/apikey 获取）或者 Vertex AI（企业用户）
- 💻 **电脑配置**：要求很低，普通办公电脑就行。有 8GB 内存就够了。不需要显卡（AI 运算在云端）
- 📦 **要装什么**：
  - 最简单：运行 `npx @google/gemini-cli`（不用安装，直接跑）
  - 全局安装：`npm install -g @google/gemini-cli`
  - Mac/Linux：`brew install gemini-cli`
  - Windows（Scoop）：`scoop install gemini-cli`
  - Windows（Chocolatey）：`choco install gemini-cli`
- 🌐 **网络**：需要能访问 Google 的服务器。国内网络可能需要代理才能连上（这是最大的门槛）

## 配合什么软件

- **终端**：主要配合终端使用（Windows 的 PowerShell 或 CMD、Mac 的 Terminal、Linux 的 Bash）
- **VS Code**：有配套扩展，可以在 VS Code 里用（更方便看 diff）
- **Git**：强烈建议项目用 Git 管理（这样 Gemini CLI 改错了可以一键回退）
- **GitHub Actions**：可以集成到 CI/CD 流程里，自动审查 PR、自动给 issue 打标签
- **Google Search**：内置 Google Search 接地功能（grounding），能联网查最新信息
- **MCP 服务器**：支持 Model Context Protocol，可以接入各种外部工具（数据库、API、云服务等）

## 客观评价

**优点**：
- 免费额度非常大方，个人开发者基本不用花钱（这是最大优势）
- 1M token 上下文窗口是目前市面上最大的之一，能读整个代码库
- Google 官方出品，质量有保障，模型能力强（Gemini 2.5 Pro 的推理能力很强）
- 内置 Google Search 接地功能，能联网查最新信息，别的 CLI 工具大多没有
- 开源（Apache 2.0），代码透明
- 支持非交互模式（headless），适合脚本和自动化
- 有 GitHub Actions 集成，适合团队使用

**缺点/坑**：
- 对网络有要求，国内直连 Google 服务器需要代理，这是最大门槛
- Gemini 模型在代码生成上还不如 Claude 3.5/3.7 那么"懂人话"，偶尔需要多对话几次才能得到想要的结果
- 免费额度虽然大，但也有上限，超了要付费（不过个人用很难超）
- 终端界面对不熟悉命令行的用户有一定学习成本
- 社区和生态还不如 Claude Code 和 Cline 那么成熟（毕竟出来得晚一点）

**适合谁**：有一定编程基础、能搞定网络代理、希望免费用强大 AI 编程助手的人。特别适合学生、个人开发者、小团队。

**不适合谁**：完全不知道什么是终端的人、网络环境无法访问 Google 且搞不定代理的人。

**评分**：8/10 — 免费额度大方、上下文窗口大，但网络要求和模型理解力稍逊于 Claude Code

## 未来趋势

- 📈 **所处阶段**：爆发增长期。Google 在大力推广，stars 数正在快速追赶 Claude Code 和 Cline
- 🔮 **6-12 个月走向**：免费额度可能会调整（目前太慷慨了，Google 可能撑不住），但应该会保留一定的免费额度。可能会加入更多 Google 生态的集成（比如直接对接 Google Cloud 服务）。VS Code 集成会更完善，可能会出独立桌面应用
- ⭐ **关注度**：5/5 — Google 官方出品 + 免费额度，必须关注

## 更新记录

| 日期 | 变更 | Stars |
|------|------|-------|
| 2026-06-17 | 重写为8字段富描述版本 | 105000 |
| 2026-06-16 | 首次记录 | 105000 |

---

*记录时间: 2026-06-17*
