---
title: "Agent Skills (Addy Osmani)"
date: 2026-06-20
github: https://github.com/addyosmani/agent-skills
stars: 63971
category: AI 编程技能
interest: 2
status: 未试
usable: 待评估
实际用途: AI Agent 技能集合（Chrome 团队）
tags:
  - GitHub
  - AI项目
  - AI编程
  - 工程技能
  - 工作流
---

# Agent Skills — Google 工程师的 AI 编程标准流程

> ⭐ 63,971 | 📅 2026-06-20 | [GitHub](https://github.com/addyosmani/agent-skills)
>
> 💡 **怎么标记**：改上面 `interest` 数字 → 3=必装 2=想试 1=观望 0=跳过 → 改完按 Ctrl+S 保存

## 干什么

如果说 Matt Pocock 的技能包是"独立开发者的武林秘籍"，那 Addy Osmani 这套就是"大厂工程团队的 SOP（标准操作流程）"。Addy Osmani 是 Google Chrome 团队的高级工程师，他把大厂软件开发的完整生命周期——从需求定义到代码上线——编码成了 AI 能理解并执行的 24 个技能。

整包的核心是一套"质量门禁"体系：定义需求（`/spec`）→ 制定计划（`/plan`）→ 增量构建（`/build`）→ 测试验证（`/test`）→ 代码审查（`/review`）→ 简化优化（`/code-simplify`）→ 发布上线（`/ship`）。这不是建议，而是强制执行——每个阶段的技能都会要求你拿出证据证明"这一步真的做对了"，不通过就不能进入下一步。

其中最有意思的是"反合理化"机制：每个技能都预设了人类程序员常见的偷懒借口（比如"我稍后再加测试"），并给出了标准反驳——逼着你按正确的方式做。

## 能实现什么效果

装上这套技能后，AI 不再是一个"你可以糊弄的实习生"，而是一个"严格执行 SOP 的质检员"。你想偷懒跳测试？AI 不会让你通过的。你想写一堆过度设计的代码？`/code-simplify` 会让你重构到最简。

对大厂开发者来说，这意味着你可以把 AI 当成一个"自带流程规范的同事"来用——而不是一个"写代码很快但质量没保障"的工具。对个人开发者来说，这是学习大厂工程实践的最佳方式——直接用就行，不用去看各种理论文章。

## 怎么用

- **装到 Claude Code**（推荐）：`/plugin marketplace add addyosmani/agent-skills` → `/plugin install agent-skills@addy-agent-skills`。
- **装到 Cursor**：复制 `SKILL.md` 文件到 `.cursor/rules/` 目录。
- **装到 Gemini CLI**：`gemini skills install https://github.com/addyosmani/agent-skills.git --path skills`。
- **开工写新功能**：先 `/spec` 明确需求 → `/plan` 制定计划 → `/build auto` 让 AI 自己执行所有任务（每步都带测试验证）。
- **代码写完了审查**：`/review` 让 AI 从 5 个维度审查代码质量 → `/code-simplify` 简化冗余。
- **准备发布**：`/ship` 检查发布清单，确保一切就绪。

## 运行位置

- 本地电脑，作为 AI 编程工具的插件/技能包运行
- 支持 Claude Code、Cursor、Gemini CLI、Antigravity、Windsurf、GitHub Copilot 等

## 需要准备什么

- 免费开源（MIT 协议）
- 需要一个支持的 AI 编程工具（Claude Code 推荐）
- 部分安装方式需要 Git
- 不需要额外 API Key（技能本身免费，AI 工具费用自理）
- 电脑配置：普通笔记本就行

## 配合什么软件

- 必须配合 AI 编程工具使用
- 可配合 GitHub 用于代码管理和 CI/CD

## 客观评价

**优点**：大厂工程实践的精华提炼，流程严谨、覆盖全面；"反合理化"设计非常巧妙，直击人类惰性痛点；`/build auto` 模式很实用——一次批准，AI 自己跑完所有任务并提交；Addy Osmani 的背书让这套技能在工程圈有天然信任度；文档质量高，每个技能都有详细说明。

**缺点**：流程偏重，简单需求走完 7 步流程显得杀鸡用牛刀；部分技能（如 "doubt-driven development"）概念较新，理解起来有点绕；依赖 AI 工具严格遵守流程，但 AI 有时候还是会跳过步骤；6 万+ star 里有一定"追星"成分（Addy Osmani 本身就是名人）。

**适合谁**：想要建立工程规范的开发团队、想学习大厂开发流程的个人开发者、做企业级应用的开发者。**不适合**：快速原型开发、简单脚本编写。

**评分 8/10**：大厂工程实践的最佳 AI 化翻译。扣分在于流程偏重，小项目不划算。

## 未来趋势

项目处于**稳定增长期**。随着企业级 AI 编程需求增加，这类"工程流程标准化"技能包会成为刚需。

**关注度 4/5**：工程质量的保障者，大团队和严肃项目的必备。

## 更新记录

| 日期 | 变更 | Stars |
|------|------|-------|
| 2026-06-20 | 首次记录 | 63,971 |

---

*记录时间: 2026-06-20*
