---
title: "RTK"
date: 2026-06-21
github: https://github.com/rtk-ai/rtk
stars: 64301
category: AI编程工具
interest: 3
status: 未试
usable: 待评估
实际用途: LLM Token 优化工具，减少 60-90% 输出
tags:
  - AI工具
  - GitHub
  - AI项目
  - Token优化
  - 编程工具
  - 成本节省
---

# RTK

> ⭐ 64,301 | 📅 2026-06-21 | [GitHub](https://github.com/rtk-ai/rtk)
>
> 💡 **怎么标记**：改上面 `interest` 数字 → 3=必装 2=想试 1=观望 0=跳过 → 改完按 Ctrl+S 保存

## 干什么
RTK（Rust Token Killer）是一个帮你省钱的小工具——用它之后，AI 编程工具（Claude Code、Cursor、Codex 等）的 token 消耗能减少 60-90%。原理很简单：AI 编程工具执行命令时（比如 `git status`、`ls`、`cat`），命令的原始输出可能几千 token，RTK 把这些输出过滤压缩成几百 token，AI 看到的信息量一样但花费的钱大幅减少。就像你请翻译，原文10000字翻译费10000字的钱；RTK 先把原文压缩成2000字关键信息再翻译，翻译费只剩2000字的钱，但翻译出来的结果质量一样好。

## 能实现什么效果
实测数据（30分钟 Claude Code 会话）：ls/tree 从2000→400 token（省80%），cat/read 从40000→12000（省70%），git diff 从10000→2500（省75%），cargo test/npm test 从25000→2500（省90%），pytest 从8000→800（省90%）。综合下来一个30分钟会话从118000→23900 token，省80%。这意味着：① 如果你用 Claude Code API，原来花100块的现在花20块；② 同样的 token 预算可以做4-5倍的工作量；③ 长会话不容易撞到 token 限制。而且压缩是可逆的——如果命令失败了，RTK 自动保存完整输出让 AI 能看。

## 怎么用
1. **日常 Claude Code 开发**：`rtk init -g` → 重启 Claude Code → 之后所有 Bash 命令自动经过 RTK 压缩 → token 消耗直接减少60-90%
2. **Cursor 开发**：`rtk init -g --agent cursor` → 重启 Cursor → 命令输出自动压缩 → 同样省钱
3. **Codex 开发**：`rtk init -g --codex` → 重启 Codex → 命令输出压缩 → 大幅降低 OpenAI API 成本
4. **查看节省统计**：`rtk gain` → 看你累计省了多少 token → 心里清楚 RTK 帮你省了多少钱

## 运行位置
本地电脑运行。单一 Rust 二进制文件，不需要额外依赖。Linux/macOS 完整支持，Windows 原生不支持 Hook（但支持 CLAUDE.md 注入模式，WSL 完整支持）。

## 需要准备什么
① 完全免费开源，Apache 2.0 许可证。② 不需要注册账号。③ 不需要 API Key。④ 电脑任何配置都行，RTK 是单个 Rust 二进制文件，开销小于10ms。⑤ 安装方式：Homebrew `brew install rtk`（推荐），或从 GitHub Releases 下载预编译二进制，或 `cargo install`。

## 配合什么软件
支持14种 AI 编程工具：Claude Code、GitHub Copilot、Cursor、Gemini CLI、Codex、Windsurf、Cline/Roo Code、OpenCode、Hermes、Kilo Code 等。配合 WorkBuddy 也可以用（Claude Code 模式）。安装后自动适配对应工具。

## 客观评价
优点：① 省钱效果震撼——80%的 token 减少，实打实的成本节省；② 单个 Rust 二进制，安装简单、运行快、开销小于10ms；③ 支持14种主流 AI 编程工具，覆盖面广；④ 命令失败时自动保存完整输出（tee 机制），不丢信息；⑤ 100+ 常用命令全覆盖。缺点：① Windows 原生不支持 Hook 自动重写，只能用 CLAUDE.md 注入模式（效果打折）；② Claude Code 内置工具（Read/Grep/Glob）不经过 Hook，只压缩 Bash 命令的输出；③ 有些压缩可能丢失边缘信息（比如注释里的特殊标记）；④ 开源项目还在快速迭代，偶尔有 bug；⑤ 遥测默认关闭但安装时会提示开启。适合：每天用 AI 编程工具、想省 API 费用的人。不适合：只用免费额度的人（省不省无所谓）。我打 **9/10**——直接省钱60-90%，安装简单无感使用，强烈推荐（尤其你用的是付费 API）。

## 未来趋势
① 项目处于爆发增长期，6.4万星且每天+633星；② 6-12个月内可能会支持更多命令、改进 Windows 原生 Hook 支持、增加更多 AI 工具兼容；③ 关注度 **5/5**——Token 成本是所有 AI 编程工具用户的痛点，RTK 直接解决。

## 更新记录

| 日期 | 变更 | Stars |
|------|------|-------|
| 2026-06-21 | 馮次记录 | 64,301 |

---

*记录时间: 2026-06-21*

---

📂 **同类别工具**：[[_索引_AI编程工具|查看 AI编程工具 全部 24 个工具]]
