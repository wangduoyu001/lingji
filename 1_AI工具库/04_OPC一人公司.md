---
title: "OPC一人公司"
date: 2026-06-15
---

# OPC 一人公司工具

> 一个人就能用的 AI 工具合集。按场景分类：自动剪辑、运营数据、开发自动化、知识管理、内容生产。

## 📹 自动剪辑

> AI 自动剪辑视频、去重、批量处理，一个人当剪辑团队用。

| 项目    | Stars | 一句话 | 能用吗 |
| ----- | ----- | --- | --- |
| _待收录_ | -     | -   | -   |

## 📊 运营数据

> 自动采集、分析、可视化运营数据，一个人看懂所有数据。

| 项目 | Stars | 一句话 | 能用吗 |
|------|-------|--------|--------|
| _待收录_ | - | - | - |

## 💻 开发自动化

| 项目 | Stars | 一句话 | 能用吗 |
|------|-------|--------|--------|
| [[1_AI工具库/OPC一人公司/snarktank_ralph.md]] | 20K | AI 自动循环写代码 | ❌ 需 Claude Code |
| [[1_AI工具库/OPC一人公司/Fosowl_agenticSeek.md]] | 26K | 完全离线开发 agent | ❌ 显存不够 |

## 🧠 知识管理 & 研究

| 项目 | Stars | 一句话 | 能用吗 |
|------|-------|--------|--------|
| [[1_AI工具库/AI生产力工具/khoj-ai_khoj.md]] | 35K | AI 第二大脑 | ✅ 强烈推荐 |
| [[1_AI工具库/AI生产力工具/assafelovic_gpt-researcher.md]] | 28K | 自动深度研究 | ✅ 强烈推荐 |

## 🖥 日常提效

| 项目 | Stars | 一句话 | 能用吗 |
|------|-------|--------|--------|
| [[1_AI工具库/AI生产力工具/CherryHQ_cherry-studio.md]] | 47K | 一站式 AI 桌面客户端 | ✅ 强烈推荐 |
| [[1_AI工具库/AI Agent框架/crewAIInc_crewAI.md]] | 54K | 多 agent 协作框架 | ⚠️ 可试 |
| [[1_AI工具库/AI Agent框架/Significant-Gravitas_AutoGPT.md]] | 185K | 低代码自动化平台 | ⚠️ 可试 |
| [[1_AI工具库/AI Agent框架/NousResearch_hermes-agent.md]] | 194K | 自我进化 AI 助手 | ⚠️ 显存不够 |

```dataview
TABLE stars AS "⭐ Stars", usable AS "实用度", date AS "日期"
FROM "1_AI工具库"
WHERE for_opc = true
SORT date DESC
```
