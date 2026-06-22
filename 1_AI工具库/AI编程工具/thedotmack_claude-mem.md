---
title: "Claude-Mem"
date: 2026-06-21
github: https://github.com/thedotmack/claude-mem
stars: 83452
category: AI编程工具
interest: 3
status: 未试
usable: 待评估
实际用途: Claude 持久记忆插件
tags:
  - AI工具
  - GitHub
  - AI项目
  - AI编程工具
  - Claude-Code
  - AI记忆
---

# Claude-Mem

> ⭐ 83,452 | 📅 2026-06-21 | [GitHub](https://github.com/thedotmack/claude-mem)
>
> 💡 **怎么标记**：改上面 `interest` 数字 → 3=必装 2=想试 1=观望 0=跳过 → 改完按 Ctrl+S 保存

## 干什么
Claude-Mem 是给 Claude Code 加上"记忆力"的插件。你现在用 Claude Code，每次开新会话它就失忆了——之前干了什么、改了什么、踩了什么坑全忘了，你得重新跟它解释一遍项目背景。Claude-Mem 解决的就是这个问题：它自动记录你每次会话里做了什么，然后用 AI 做智能压缩和摘要，下次开新会话时自动注入相关上下文。就像你请了一个助手，每次你跟他聊完天他都会写笔记，下次见面时他已经把你之前说过的重点都复习好了。没它之前，你得在 CLAUDE.md 里手动写项目说明，而且只能写静态信息；有它之后，动态的操作历史、踩坑记录、代码修改原因全都自动保留。

## 能实现什么效果
安装之后，你每次用 Claude Code 干的事——读文件、改代码、跑命令、搜索 bug——都会被自动记录。下次开新会话，相关的上下文（比如"上次你在这个文件改了登录逻辑"、"上次踩坑发现 API 调用要加 timeout"）会自动注入。实测效果：① 跨会话不用重复解释项目背景，省30-50%的沟通时间；② 三层渐进式披露机制，先用50-100 token 看索引，需要细节再取完整记录，token 消耗可控；③ 有 Web 查看器界面（localhost:37777），能可视化浏览所有记忆流；④ 支持中文模式（设置 `CLAUDE_MEM_MODE: code--zh`）。最终产出是持续积累的项目记忆库，让你和 AI 的协作越来越默契。

## 怎么用
1. **日常开发**：安装 Claude-Mem → 正常用 Claude Code → 每次会话自动记录 → 下次自动注入 → 不用每次重新解释项目
2. **踩坑记录**：遇到 bug → Claude Code 解决了 → 自动记到记忆库 → 下次遇到类似问题 → Claude 直接说"上次我们用这个方法解决的"
3. **团队协作**：把记忆库共享给队友 → 队友的 Claude Code 也知道项目上下文 → 新人上手速度加快
4. **回顾项目历史**：打开 Web 查看器 → 浏览所有记忆流 → 搜索关键词 → 看到项目完整的操作时间线

## 运行位置
本地电脑运行（Windows/Mac/Linux）。Worker 服务跑在 localhost:37777，数据存 SQLite + Chroma向量数据库，全部本地。

## 需要准备什么
① 完全免费开源，Apache 2.0 许可证。② 不需要注册账号。③ 需要 Node.js >= 20（Claude Code 本身就需要）。④ 电脑不需要 GPU，普通配置就行，SQLite 和 Chroma 都是轻量级。⑤ 安装只需要一条命令：`npx claude-mem install`，它会自动检查依赖和注册钩子。

## 配合什么软件
专为 Claude Code 设计，也支持 Gemini CLI、OpenCode、Claude Desktop。配合 WorkBuddy 也能用（因为 WorkBuddy 底层也用 Claude Code）。独立使用需要 Node.js 环境。

## 客观评价
优点：① 解决了 Claude Code 最痛的问题——每次会话失忆，这是所有 Claude Code 用户最大的痛点；② 三层渐进式披露设计精巧，先看索引再取细节，token 消耗很省；③ 有 Web 查看器界面，可视化浏览记忆，比纯文本方便；④ 支持中文模式，对中文用户友好；⑤ 跨 Agent 通用，不只 Claude Code，Codex/Gemini/OpenCode 都能用。缺点：① 需要跑一个 Worker 服务在 37777 端口，占资源；② Chroma 向量数据库安装偶尔会出问题；③ 新安装可能需要重启 Claude Code 才生效；④ 记忆注入有时会选到不太相关的内容，需要手动用 `<private>` 标签排除敏感信息。适合：每天用 Claude Code 开发的人、大型项目长期开发的人。不适合：偶尔用一下 Claude Code 的人（记忆积累太少没意义）。我打 **9/10**——解决核心痛点，设计精巧，8万+星说明市场认可度极高，强烈推荐装。

## 未来趋势
① 项目处于快速增长期，每天都在更新；② 6-12个月内可能会推出更多 Agent 支持、更智能的记忆筛选、团队协作功能；③ 关注度 **5/5**——AI 记忆是2026年最关键的基础设施之一，没有记忆的 AI 就像没有硬盘的电脑。

## 更新记录

| 日期 | 变更 | Stars |
|------|------|-------|
| 2026-06-21 | 馮次记录 | 83,452 |

---

*记录时间: 2026-06-21*
