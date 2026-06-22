---
title: "Headroom"
date: 2026-06-21
github: https://github.com/chopratejas/headroom
stars: 42377
category: AI编程工具
interest: 2
status: 未试
usable: 待评估
实际用途: AI Agent 上下文压缩，减少 Token 消耗
tags:
  - AI工具
  - GitHub
  - AI项目
  - AI框架
  - Token优化
  - 成本节省
---

# Headroom

> ⭐ 42,377 | 📅 2026-06-21 | [GitHub](https://github.com/chopratejas/headroom)
>
> 💡 **怎么标记**：改上面 `interest` 数字 → 3=必装 2=想试 1=观望 0=跳过 → 改完按 Ctrl+S 保存

## 干什么
Headroom 是 AI Agent 的"上下文压缩层"——在所有内容到达大模型之前先压缩一遍，减少 60-95% 的 token 消耗，但回答质量不变。和 RTK 不同的是，RTK 只压缩命令输出，Headroom 压缩一切：工具输出、日志、RAG 搜索结果、文件内容、对话历史，还支持跨 Agent 共享记忆。就像你给 AI 的所有信息先经过一个"压缩秘书"，把冗余去掉、保留核心，AI 看到的是精华版但理解效果一样。没它之前，你用 Claude Code 长时间开发，上下文越来越长，token 消耗越来越多，最后撞到限制被迫开新会话又得重新解释；有它之后，上下文自动压缩，同样预算做更多事，还能跨会话保留关键记忆。

## 能实现什么效果
实测数据：代码搜索100个结果从17765→1408 token（省92%），SRE事故调试从65694→5118（省92%），GitHub Issue分类从54174→14761（省73%）。标准基准测试验证：GSM8K 数学准确率完全不变（0.870→0.870），TruthfulQA 甚至更好（0.530→0.560）。这意味着：① 长会话不用担心撞 token 限制；② API 费用减少60-92%；③ 而且压缩是可逆的——原始内容本地缓存，AI 需要时可以通过 `headroom_retrieve` 取回完整内容。还有 `headroom learn` 功能：自动从失败会话中学教训，写入 CLAUDE.md 或 AGENTS.md。

## 怎么用
1. **包装 Claude Code**：`headroom wrap claude` → 之后所有 Claude Code 交互自动压缩 → token 省60-92% → 回答质量不变
2. **跨 Agent 共享记忆**：Claude Code 和 Codex 共用同一个项目 → Headroom 让两个 Agent 共享存储 → 不用重复解释
3. **学习失败教训**：开发遇到 bug → Headroom 自动分析失败模式 → 写入修正到 CLAUDE.md → 下次不再犯同样的错
4. **MCP 集成**：`headroom mcp install` → 作为 MCP Server 运行 → Claude/Gemini/OpenCode 都能调用压缩功能

## 运行位置
本地电脑运行（Windows/Mac/Linux），Python 3.10+。本地优先设计，数据不出电脑。也有代理模式（Proxy）零代码改动适用任何语言。

## 需要准备什么
① 免费开源，Apache 2.0 许可证。② 不需要注册账号。③ 基础功能不需要 API Key；ML 增强压缩可选装 Kompress-base 模型（本地运行）。④ 电脑需要 Python 3.10+，不需要 GPU（基础压缩），ML 模式需要 GPU。普通配置8GB内存够用。⑤ 安装 `pip install "headroom-ai[all]"` 或 `npm install headroom-ai`。

## 配合什么软件
支持6种 AI Agent：Claude Code（wrap模式）、Codex、Cursor、Aider、Copilot CLI、OpenClaw。还有 Python Library、Node SDK、MCP Server、Proxy 四种集成方式。配合 LangChain、LiteLLM、Vercel AI SDK 等都有适配。

## 客观评价
优点：① 压缩范围比 RTK 更广——不只命令输出，还压缩文件、日志、RAG结果、对话历史；② 实测效果惊人，92% 压缩率但准确率不变甚至更好；③ 可逆压缩（CCR机制），原始内容不丢；④ 跨 Agent 共享记忆，打破不同 AI 工具之间的信息孤岛；⑤ 四种使用模式（Library/Proxy/MCP/Agent Wrap）灵活适配各种场景；⑥ `headroom learn` 自动从失败中学教训很实用。缺点：① 安装依赖较多（尤其 ML 模式），环境配置比 RTK 复杂；② ML 增强压缩需要 GPU，没 GPU 只能用基础压缩（效果打折）；③ 压缩有时对非常专业的术语过度简化；④ 项目还在快速迭代，API 可能变化；⑤ 和 RTK 功能有重叠，需要选一个。适合：长时间用多种 AI 工具开发的人、想跨 Agent 共享上下文的人、token 成本压力大的人。不适合：只用单一 AI 工具短时间使用的人。我打 **8/10**——功能比 RTK 更全面，跨 Agent 记忆是杀手功能，但安装门槛稍高。

## 未来趋势
① 项目处于爆发增长期，每天+3795星，说明市场需求巨大；② 6-12个月内可能会加强更多 Agent 支持、优化 ML 增强压缩、增加团队协作功能；③ 关注度 **5/5**——Token 成本+上下文管理是2026年两大核心痛点，Headroom 同时解决两个。

## 更新记录

| 日期 | 变更 | Stars |
|------|------|-------|
| 2026-06-21 | 馮次记录 | 42,377 |

---

*记录时间: 2026-06-21*

---

📂 **同类别工具**：[[_索引_AI编程工具|查看 AI编程工具 全部 24 个工具]]
