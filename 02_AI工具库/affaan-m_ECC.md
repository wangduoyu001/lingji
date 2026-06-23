---
title: "affaan-m/ECC"
date: 2026-06-17
github: https://github.com/affaan-m/ECC
stars: 217446
interest: 1
status: 未试
usable: 待评估
category: AI编程工具
实际用途: AI 代码编辑/补全工具
tags:
  - AI工具
  - GitHub
  - AI项目
  - Claude
  - 编程工具
  - 代码编辑
---

# ECC (Everything Claude Code)

> ⭐ 212,000 | 📅 2026-06-17 | [GitHub](https://github.com/affaan-m/ECC)
>
> 💡 **怎么标记**：改上面 `interest` 数字 → 3=必装 2=想试 1=观望 0=跳过 → 改完按 Ctrl+S 保存

## 干什么

ECC 全称"Agent Harness Operating System"（代理驾驭操作系统），是一套装在 Claude Code 上面的"超级外挂包"。它不是普通的配置文件合集，而是一个完整的系统，包含 271 个专业技能、67 个专业代理（子 AI）、92 个斜杠命令，以及内存优化、持续学习、安全扫描等能力。

你可以把它理解成给 Claude Code"装了一个完整的软件开发团队"——有代码审查员、架构师、测试工程师、安全审计员，各自负责一块，你下一个指令，它们协作完成任务。比如你说"帮我做用户登录功能"，planner 代理先出设计方案，tdd-guide 代理再按测试驱动开发（先写测试再写代码，一种保证质量的方法）的方式写代码，最后 code-reviewer 代理来检查质量。

这个项目最厉害的地方是"跨平台"——买一次，不光能在 Claude Code 用，还能在 Cursor、OpenCode、Codex、Gemini CLI、GitHub Copilot 等 12 种 AI 编程工具里用，配置可以同步。作者是资深开发者，这个项目经过 10 个月以上日常高强度使用打磨出来的，不是拍脑袋写的。

## 能实现什么效果

装了 ECC 之后，Claude Code 的能力会从"一个程序员助手"升级成"一个软件工厂"。原来你需要手动告诉 Claude Code 每一步怎么做，现在你只需要说"我要做 X 功能"，ECC 的代理们会自动分工：有人做规划、有人写代码、有人审查、有人写测试，最后给你一个可以直接用的功能。

举个例子：你要做一个"用户评论"功能。没有 ECC 时，你要自己想数据库表结构、API 接口、前端组件、测试用例，一个个让 Claude Code 帮你写。有了 ECC，你运行 `/ecc:plan "添加用户评论功能"`，planner 代理会先输出一份完整的实现蓝图（包含数据表设计、API 定义、组件结构），然后 tdd-workflow 技能会让 Claude Code 按"先写测试、再写代码"的方式实现，最后 `/code-review` 命令会让 code-reviewer 代理帮你检查代码质量。整个过程从原来的 2 小时缩短到 20 分钟，而且代码质量更高。

安全方面也很强：内置 AgentShield 安全审计工具，能扫描你的配置文件里有没有泄露的 API 密钥（就像检查代码里有没有把密码明文写进去），还能检测恶意 MCP 服务器配置。对于担心 AI 生成代码有安全漏洞的人，这个功能是刚需。

## 怎么用

- **首次安装**：在 Claude Code 里运行 `/plugin marketplace add https://github.com/affaan-m/ECC` 添加市场，然后 `/plugin install ecc@ecc` 安装。规则文件需要手动复制（因为 Claude Code 插件系统不支持自动分发规则），跟着 README 里的命令执行就行
- **开始新功能**：运行 `/ecc:plan "你的功能描述"` → planner 代理生成实现蓝图 → 自动进入实施阶段
- **代码审查**：写完代码后运行 `/code-review` → code-reviewer 代理检查代码，告诉你哪里有问题、怎么改
- **安全扫描**：运行 `/security-scan` → security-reviewer 代理按 OWASP Top 10（全球通用的 Web 安全漏洞清单）标准审计代码
- **查看所有可用命令**：在 Claude Code 里运行 `/plugin list ecc@ecc` 可以看到所有 92 个命令，也可以打开项目自带的 Dashboard GUI（运行 `npm run dashboard`）可视化浏览所有组件

## 运行位置

- 🖥️ **Windows / Mac / Linux 都支持**，在 Claude Code 终端里运行
- 需要联网（调用 Claude API）
- 也可以用在 Cursor、OpenCode、Codex、Gemini CLI 等其他 AI 编程工具里（ECC 支持 12 种平台）
- Dashboard GUI 用 Python Tkinter 写成，装了 Python 就能跑

## 需要准备什么

- 💰 **要钱吗**：ECC 本身是免费的（MIT 开源协议），但需要 Claude Code 能正常工作——也就是说需要 Anthropic API 或者 Claude Pro/Max 订阅
- 🔑 **API Key**：需要 Anthropic API Key，或者直接用 Claude Pro/Max 登录（ECC 支持订阅登录，不需要单独 API Key）
- 💻 **电脑配置**：要求不高，8GB 内存就够。需要装 Node.js 18 以上版本（运行安装脚本用）
- 📦 **要装什么**：除了 Claude Code 本身，Windows 用户还需要 Git for Windows（提供 bash 环境），因为部分安装脚本用了 Linux 命令
- 🌐 **网络**：需要能访问 GitHub 和 Anthropic 服务器，国内可能需要代理

## 配合什么软件

- **Claude Code**：主要运行环境，ECC 就是为它设计的
- **Cursor / OpenCode / Codex / Gemini CLI**：也支持，ECC 会根据不同平台自动适配
- **VS Code**：可以通过 Claude Code 插件间接使用
- **Dashboard GUI**：可选，用 Python 写成，可以可视化浏览所有技能、代理、命令

## 客观评价

**优点**：
- 功能极其全面，271 个技能覆盖几乎所有主流开发场景（React/Vue/Python/Java/Go 等），不用自己一个个找
- 跨平台支持是最好的，买一次配置，12 种 AI 编程工具都能用，换工具不用重新配置
- 有 Dashboard GUI，可以可视化浏览所有组件，对新手很友好
- 安全功能强，AgentShield 有 1282 个测试、98% 代码覆盖率，不是玩具级的安全检查
- 持续学习系统（v2）能记住你的使用习惯，用得越久越顺手
- MIT 开源协议，完全免费，代码透明

**缺点/坑**：
- 安装有点复杂，插件安装后还要手动复制规则文件，新手可能会卡在这一步
- 271 个技能、67 个代理， information overload（信息过载），新手不知道从哪里开始
- 需要 Claude Code 能正常工作，如果 Claude Code 本身有网络问题，ECC 也用不了
- 部分高级功能（如持续学习、内存优化）需要一定配置，开箱即用度不是 100%
- 项目更新很快（v2.0.0 刚毕业），文档有时跟不上版本，可能遇到命令找不到的情况
- 体积不小，克隆完整仓库 + 依赖需要几百 MB 磁盘空间

**适合谁**：已经在使用 Claude Code / Cursor / OpenCode 等 AI 编程工具、想提升效率的人。特别适合需要经常切换不同 AI 编程工具的人（一套配置到处用）。

**不适合谁**：完全不懂命令行的人（安装需要跑脚本）、不用 Claude Code 等支持的工具的人、只想用最简单 AI 辅助编程不想折腾配置的人。

**评分**：9/10 — 功能最全面的 Claude Code 增强包，就是上手门槛有点高

## 未来趋势

- 📈 **所处阶段**：成熟期（v2.0.0 已毕业为稳定版）。项目增速惊人，日均新增约 1500 Star，是 GitHub AI 工具类增速第一的项目
- 🔮 **6-12 个月走向**：预计会加入更多语言的规则支持（目前已有 12 种语言生态系统），Dashboard GUI 会更强大，可能会出"一键安装包"降低新手安装门槛。Rust 控制平面（ECC 2.0 Alpha）如果成熟，性能会大幅提升
- ⭐ **关注度**：5/5 — 已经超过 21 万 Star，是 GitHub 上最火的 AI 编程工具增强项目，必须关注

## 更新记录

| 日期 | 变更 | Stars |
|------|------|-------|
| 2026-06-17 | 重写为8字段富描述版本 | 212000 |
| 2026-06-18 | Stars 更新 212K → 217K | 217446 |
| 2026-06-16 | 首次记录（stars 数据有误，已修正） | 216000 |

---

*记录时间: 2026-06-18*

---

📂 **同类别工具**：[[_索引_AI编程工具|查看 AI编程工具 全部 24 个工具]]

---
## 相关内容

- [[aaif-goose_goose]]
- [[addyosmani_agent-skills]]
- [[Aider-AI_aider]]
- [[anomalyco_opencode]]
- [[anthropics_claude-code]]
