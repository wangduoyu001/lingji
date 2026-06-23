---
title: "Screenpipe"
date: 2026-06-20
github: https://github.com/screenpipe/screenpipe
stars: 19391
category: AI生产力
interest: 2
status: 未试
usable: 待评估
实际用途: 屏幕录制 + AI 分析工具
tags:
  - AI工具
  - GitHub
  - AI项目
  - AI分析
  - 个人助手
  - 屏幕录制
---

# Screenpipe

> ⭐ 19,391 | 📅 2026-06-20 | [GitHub](https://github.com/screenpipe/screenpipe)
>
> 💡 **怎么标记**：改上面 `interest` 数字 → 3=必装 2=想试 1=观望 0=跳过 → 改完按 Ctrl+S 保存

## 干什么
Screenpipe 是一个"AI 记忆眼镜"——它 24/7 录制你的屏幕、麦克风、键盘操作，然后让 AI 能搜索和利用你看过、听过、做过的一切（就像给你装了个"完美记忆芯片"，再也不怕忘事）。没有它之前，你看过的重要网页、听过的会议内容、操作过的软件步骤，一旦关掉就找不回来了。Screenpipe 把这些都记下来，存你电脑上（不上传！），然后用自然语言搜索——说"我昨天看的那个抖音运营文章在哪"，AI 就帮你找出来。它还有自动"Pipe"功能，根据你的行为自动触发 AI 任务（比如自动写日报、会议总结）。

## 能实现什么效果
装了 Screenpipe，你的电脑就变成了"有记忆的 AI"。忘记刚才看过的网页？问 Screenpipe "最近5分钟我看了什么"就行。忘记会议里谁说了什么？Screenpipe 有完整录音和转写。需要写日报但不想手动记？设置 Pipe 自动生成。更厉害的是，它可以接到 Claude Code/WorkBuddy 等 AI 工具，让 AI 了解你的工作上下文——AI 不再是"瞎子"，它知道你最近在看什么、做什么，给出的建议就更精准。YC S26 项目，团队质量有保障。

## 怎么用
1. **找回看过的内容**：问 AI "我昨天看的命理类直播分析在哪" → Screenpipe 搜索屏幕记录 → 直接找到
2. **自动会议记录**：开会时 Screenpipe 自动录制 → 会后自动生成总结和待办事项
3. **AI 有工作上下文**：Claude Code 接入 Screenpipe MCP → AI 知道你最近在做什么 → 建议更精准
4. **自动日报生成**：设定 Pipe → 每天自动总结你的工作行为 → 生成日报
5. **ADHD 助手**：找回丢失的标签页、忘记的对话、找不到的文件

## 运行位置
本地电脑运行，支持 Windows 10/11（你的 Win10 完全支持）、macOS（Intel + Apple Silicon）、Linux（需从源码构建）。有桌面应用（推荐）和 CLI 两种方式。数据完全本地存储在 SQLite 数据库里，不上传任何云端。资源占用：CPU 5-10%、内存 0.5-3GB、磁盘约 20GB/月。

## 需要准备什么
① 桌面版免费下载（screenpi.pe/onboarding），基础功能免费。② 不需要注册账号。③ 不需要 API Key（基础功能）。④ 如果要接 Claude 等云端 AI，需要对应的 API Key。⑤ 最低配置：8GB 内存 + 现代 CPU（你的 16GB 完全够用）。⑥ 不需要显卡。⑦ 桌面应用直接安装就行。⑧ 如果用 MCP 接入 Claude，需要运行 `claude mcp add screenpipe` 一行命令。

## 配合什么软件
最佳搭配：Claude Code/Claude Desktop（通过 MCP 集成）、Cursor（给编程 AI 提供上下文）、OpenClaw/Hermes Agent（官方支持集成）、WorkBuddy（MCP 接入）。独立使用也行，有自带搜索界面。还有 Tauri/Electron/Swift SDK 可以开发自定义集成。

## 客观评价
**优点**：概念很新颖（给 AI 加记忆），完全本地隐私安全，Windows/macOS 都支持，资源占用合理（CPU 5-10%），有 PII 过滤（自动识别并过滤敏感信息如密码），YC 项目团队靠谱，MCP 集成简单一行命令。**缺点**：每月存 20GB 数据磁盘占用不小，录制一切可能让一些人觉得"太监控了"，Pipe 自动化功能还比较基础，Windows OCR 偶尔识别率不如 macOS，隐私 PII 过滤偶有遗漏。**适合谁**：经常忘记看过什么的人、想让 AI 了解工作上下文的人、需要自动会议记录的人、ADHD 人群。**不适合谁**：对隐私极度敏感不想要任何录制的人、磁盘空间紧张的人。**评分：7/10**。理由：AI 记忆概念非常好，但隐私顾虑和磁盘占用是现实问题。

## 未来趋势
① 项目处于**快速增长**阶段（YC S26），功能持续增加。② 6-12 月：PII 过滤更精准、Pipe 自动化更丰富、与更多 AI 工具集成。③ 关注度评分：**4/5**，AI 记忆/上下文是热门方向，Screenpipe 定位独特。

## 更新记录

| 日期 | 变更 | Stars |
|------|------|-------|
| 2026-06-20 | 馍次记录 | 19,391 |

---

*记录时间: 2026-06-20*

---

📂 **同类别工具**：[[_索引_AI生产力工具|查看 AI生产力工具 全部 22 个工具]]

---
## 相关内容

- [[aaif-goose_goose]]
- [[addyosmani_agent-skills]]
- [[affaan-m_ECC]]
- [[Aider-AI_aider]]
- [[anomalyco_opencode]]
