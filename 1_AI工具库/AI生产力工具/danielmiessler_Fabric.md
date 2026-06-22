---
title: "Fabric"
date: 2026-06-20
github: https://github.com/danielmiessler/Fabric
stars: 42486
category: AI生产力
interest: 2
status: 未试
usable: 待评估
实际用途: AI 提示词和模式集合框架
tags:
  - AI工具
  - GitHub
  - AI项目
  - AI生产力
  - 提示词框架
---

# Fabric

> ⭐ 42,486 | 📅 2026-06-20 | [GitHub](https://github.com/danielmiessler/Fabric)
>
> 💡 **怎么标记**：改上面 `interest` 数字 → 3=必装 2=想试 1=观望 0=跳过 → 改完按 Ctrl+S 保存

## 干什么
Fabric 是一个"AI 提示词工具箱"——它把几百个精心设计的 AI 提示词（叫 Patterns）按实际任务分类整理好，你直接选一个 Pattern 就能用 AI 干活，不用每次都自己想怎么写提示词（就像有个菜谱大全，想做菜直接翻菜谱照做，不用自己发明做法）。没有它之前，每次让 AI 干新活都得自己琢磨怎么写提示词，写不好 AI 就给烂结果，浪费大量时间试错。Fabric 的 Patterns 是社区众包的，每个都经过验证，覆盖了从总结文章、分析视频、写文案到审计代码等几十种常见任务。一句话就能调用：`fabric -p summarize`，AI 就按最佳模式帮你干活。

## 能实现什么效果
用了 Fabric，你让 AI 干活的效率直接翻倍。想总结一个 YouTube 视频？`fabric -y "视频URL" -p extract_wisdom`，10秒出精华摘要。想让 AI 按你的风格写文章？选个 Pattern，AI 就按预设结构输出。想分析一篇文章值不值得读？`fabric -p analyze_claims`，AI 直接告诉你文章的核心论点和可信度。对于做直播运营的你来说，Fabric 可以帮你快速总结竞品直播内容、分析话术质量、改写文案风格、生成社交媒体内容，每次都是高质量输出，不用反复调试提示词。

## 怎么用
1. **总结视频/直播内容**：`fabric -y "直播录像URL" --stream -p extract_wisdom` → AI 提取精华内容
2. **按你的风格写文案**：`fabric -p write_essay --stream` → 输入想法 → AI 按预设结构写作
3. **分析话术质量**：把话术文本传给 `fabric -p analyze_claims` → AI 评估核心论点和说服力
4. **改写文档**：`fabric -p improve_writing` → 输入原文 → AI 改写得更专业
5. **批量处理**：配合 Pipes 串联多个 Pattern → 自动"总结→分析→改写→输出"一条龙

## 运行位置
本地电脑运行，支持 Windows、macOS、Linux。还可以用 Docker 运行。有 REST API 模式可以当服务器用（`fabric --serve`），其他工具就能通过网络调用。纯命令行工具，没有图形界面。

## 需要准备什么
① 完全免费开源（MIT 许可证）。② 不需要注册账号。③ 需要 AI 提供商的 API Key（OpenAI/Claude/Gemini/Ollama 等任选一个），用 Ollama 的话完全免费。④ 安装很简单：Windows 用 `winget install danielmiessler.Fabric` 或 PowerShell 一行命令；macOS 用 Homebrew。⑤ 不需要显卡（除非用 Ollama 本地模型）。⑥ 内存 4GB 起步就够。⑦ 需要终端/命令行环境。

## 配合什么软件
最佳搭配：Ollama（免费本地模型后端）、yt-dlp + FFmpeg（处理视频/音频内容）、Jina AI（处理网页内容）。也可以独立使用，纯命令行就行。支持 20+ AI 提供商随便切换。

## 客观评价
**优点**：Patterns 设计精良（社区众包+验证，质量很高），使用极其简单（一行命令就行），覆盖场景广泛（总结/分析/写作/编程等几十种），开源免费，支持多种 AI 后端随便切换，有 yt-dlp 集成直接处理视频。**缺点**：纯命令行没有图形界面（对非技术用户不太友好），Patterns 数量太多偶尔有质量参差，需要终端操作习惯，REST API 模式配置稍复杂。**适合谁**：经常让 AI 干各种任务但不想每次调提示词的人、有命令行使用习惯的人、需要批量处理内容的人。**不适合谁**：完全不想用命令行的人、只需要简单聊天不需要模式化任务的人。**评分：7/10**。理由：提示词工具箱概念很好、质量高，但命令行门槛对非技术用户偏高。

## 未来趋势
① 项目处于**成熟稳定**阶段，核心功能完善，社区持续贡献新 Patterns。② 6-12 月：可能出图形界面或 Web UI、Patterns 数量继续增长、与更多 AI 工具集成。③ 关注度评分：**3/5**，提示词框架有刚需但不是最热赛道。

## 更新记录

| 日期 | 变更 | Stars |
|------|------|-------|
| 2026-06-20 | 馍次记录 | 42,486 |

---

*记录时间: 2026-06-20*

---

📂 **同类别工具**：[[_索引_AI生产力工具|查看 AI生产力工具 全部 22 个工具]]
