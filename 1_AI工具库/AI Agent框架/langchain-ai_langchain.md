---
title: "LangChain"
date: 2026-06-18
github: https://github.com/langchain-ai/langchain
stars: 139607
category: AI框架
interest: 1
status: 未试
usable: 待评估
实际用途: LLM 应用开发框架
tags:
  - AI工具
  - GitHub
  - AI项目
  - LLM框架
  - Agent框架
---

# LangChain

> ⭐ 139,607 | 📅 2026-06-18 | [GitHub](https://github.com/langchain-ai/langchain)
>
> 💡 **怎么标记**：改上面 `interest` 数字 → 3=必装 2=想试 1=观望 0=跳过 → 改完按 Ctrl+S 保存

## 干什么

LangChain 是 AI 应用开发的"标准工具箱"——几乎所有复杂的 AI 应用底层都在用它。打个比方：如果你要做家具，Dify 是宜家的成品家具（开箱即用），LangChain 就是工具箱+原材料（需要自己动手但自由度极高）。它提供了连接大模型、管理对话记忆、检索数据、调用工具的一整套标准化模块。以前开发者要让 AI 能查数据库、能搜索网页、能记住之前的对话——每个功能都得自己从头写；LangChain 把这些都做成了标准化的"积木块"，开发者只需要拼接就行。它为 Python 和 TypeScript 都提供了完整的 SDK。

## 能实现什么效果

用 LangChain 可以构建任何你能想到的 AI 应用。比如：一个能自动阅读你的邮件、提取待办事项、在日历里安排时间的 AI 秘书；一个能连接公司内部所有数据库、用自然语言查询的 AI 数据分析师；一个能自动阅读论文、提取关键发现、生成综述报告的 AI 研究员。LangChain 的底层抽象让你可以把 AI 的"思考-行动-观察"循环标准化，做出真正自主的多步骤 AI 代理。LangGraph（LangChain 2.0 核心）支持用状态图来编排复杂的多 Agent 协作。

## 怎么用

- **构建 AI Agent**：用 LangChain Python 库 → 定义 Agent 的工具（搜索、计算器、数据库）→ 设置 Agent 的行为规则 → Agent 自动拆解任务并执行
- **RAG 知识库**：加载公司文档 → 用 LangChain 的文档加载器处理 → 设置检索器 → 用户提问时 AI 自动在文档中找到相关内容并回答
- **多 Agent 协作**：用 LangGraph 定义工作流 → 设置"研究员 Agent + 写手 Agent + 审校 Agent"三个角色 → 研究员搜资料 → 写手写文章 → 审校检查质量
- **API 集成**：用 LangChain 连接外部 API → 用户说"帮我查一下明天北京飞上海的航班" → AI 自动调用航班 API 获取数据并整理展示
- **对话记忆**：构建一个有记忆的聊天机器人 → 用户三天前说过喜欢红色 → 三天后推荐产品时自动优先推荐红色款

## 运行位置

- **本地电脑**：作为 Python/TypeScript 库使用，Windows/Mac/Linux 全平台
- **服务器端**：部署到云服务器作为后端服务
- 是一个编程框架/库，不能独立运行，需要开发者写代码

## 需要准备什么

- **费用**：完全免费开源（MIT 协议）
- **账号**：不需要
- **API Key**：需要大模型 API Key（OpenAI/Claude/本地 Ollama 等至少一个）
- **电脑配置**：开发环境 4GB 内存即可；生产环境取决于应用规模
- **软件依赖**：Python 3.9+ 或 Node.js 18+，pip/npm 安装

## 配合什么软件

作为编程库使用，需要配合 IDE（VS Code/PyCharm）和 Python/Node.js 环境。可以连接任何 REST API、数据库、向量数据库。常与 Ollama（本地模型）、OpenAI/Claude API 配合。也常配合 Streamlit 或 Gradio 做前端 Demo。

## 客观评价

优点：① 生态最完整——市面上 AI 开发框架中，LangChain 的集成最多、教程最多、社区最大；② 灵活性极高——从简单脚本到复杂多 Agent 系统都能做；③ Python/TypeScript 双语言支持；④ LangGraph 解决了旧版的架构痛点，多 Agent 编排能力大幅提升。

缺点/坑：① 学习曲线陡——文档虽然多但乱，新手很容易迷失；② 过度抽象——有时为了做一件简单的事，要写很多 boilerplate 代码；③ API 变化快，去年写的代码今年可能跑不通；④ 并非所有场景都需要 LangChain——如果你只是简单调用 API，用原生 SDK 更快。

适合谁：AI 应用开发者、想构建复杂 Agent 的工程师。不适合：想做简单 AI 聊天但不想写代码的人、追求极简的开发者（可能觉得 LangChain 太重）。

打分：7/10。它是最流行的 AI 开发框架，但复杂度也很高。扣 3 分因为学习曲线、API 不稳定性和过度抽象。

## 未来趋势

① 所处阶段：成熟稳定期——已经是 AI 开发的事实标准，但内部仍在快速演进（LangGraph 取代旧 Chains）；② 6-12 个月：LangGraph 会进一步简化，可能推出零代码的 Agent 构建器；③ 关注度：5/5，AI 开发者绕不开的项目。

## 更新记录

| 日期 | 变更 | Stars |
|------|------|-------|
| 2026-06-18 | 首次记录 | 139,607 |

---

*记录时间: 2026-06-18*
