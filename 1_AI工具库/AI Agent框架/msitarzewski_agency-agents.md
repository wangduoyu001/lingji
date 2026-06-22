---
title: "Agency Agents"
date: 2026-06-20
github: https://github.com/msitarzewski/agency-agents
stars: 114667
category: AI Agent 团队
interest: 2
status: 未试
usable: 待评估
实际用途: AI Agent 团队协作框架
tags:
  - AI工具
  - GitHub
  - AI项目
  - AI-Agent
  - 多Agent协作
  - 一人公司
---

# Agency Agents — 你的"AI 公司"，232 个专家随叫随到

> ⭐ 114,667 | 📅 2026-06-20 | [GitHub](https://github.com/msitarzewski/agency-agents)
>
> 💡 **怎么标记**：改上面 `interest` 数字 → 3=必装 2=想试 1=观望 0=跳过 → 改完按 Ctrl+S 保存

## 干什么

想象你开了一家公司，雇了 232 个不睡觉、不抱怨、随时待命的专业员工——前端工程师、UI 设计师、产品经理、SEO 专家、安全审计师、营销策划……这就是 Agency Agents。它不是让你去学怎么用 AI，而是直接给你配好了一整套"AI 员工"，你用的时候只需要说"激活前端工程师模式"就行。

这些 Agent 不是随便写的通用提示词，而是每个都有详细的"人设"——有独特的语言风格、工作流程、交付标准。比如"前端工程师" Agent 会用 React/Next.js 的思维来写代码，"安全架构师" Agent 会从攻击者的角度审视你的系统。

项目覆盖 16 个部门：工程、设计、市场、销售、产品、安全、游戏开发、GIS 地理信息、财务、学术等，几乎涵盖了做互联网产品需要的所有角色。

## 能实现什么效果

你一个人就是一个公司。想做一个小程序？激活产品经理 Agent 做规划 → 前端工程师写界面 → 后端架构师搭 API → UI 设计师调样式 → 测试工程师检查质量——全部是 AI 来完成，你只需要审核和决策。

对做一人公司的独立开发者来说，这意味着你不需要花钱请设计师、外包写代码、找 SEO 专家——这些角色的 AI 版本虽然不能 100% 替代真人，但已经能覆盖 70-80% 的日常工作。

具体场景：搭一个 SaaS 产品官网，从前端开发到 SEO 优化到文案撰写，一个人借助这套 Agent 团队，一天内可以完成过去需要一周的工作量。

## 怎么用

- **装到 Claude Code**（推荐）：`git clone` 下来 → `./scripts/install.sh --tool claude-code`，所有 Agent 就装好了。然后说"激活前端工程师模式"就行。
- **只装需要的部门**：`./scripts/install.sh --tool claude-code --division engineering,security`（只装工程和安全两个部门的 Agent）。
- **装到 Cursor**：`./scripts/install.sh --tool cursor`，Agent 会变成 Cursor 的规则文件。
- **多工具并行装**：`./scripts/convert.sh` 生成所有工具的适配文件 → `./scripts/install.sh` 交互式选择要装的工具和 Agent。
- **更新**：官方更新后 `./scripts/convert.sh --parallel` 重新生成即可。

## 运行位置

- 本地电脑（macOS / Linux，Windows 需 WSL 或用 Git Bash）
- 在 AI 编程工具里运行，不需要额外服务器

## 需要准备什么

- 免费开源（MIT 协议），商用没问题
- 需要一个 AI 编程工具（Claude Code、Cursor、Gemini CLI、Codex 等 12 种工具任选其一）
- 需要 Git 来克隆仓库
- 需要 bash 环境（macOS/Linux 自带，Windows 需要 Git Bash 或 WSL）
- 不需要额外 API Key——Agent 文件本身是免费的，AI 工具的费用是你自己的

## 配合什么软件

- 必须配合 AI 编程工具使用（Claude Code 推荐，体验最好）
- 可配合 GitHub / Linear 用于项目管理
- 各种 Agent 覆盖不同场景，不需要额外装别的软件

## 客观评价

**优点**：覆盖面之广令人惊叹——232 个 Agent，16 个部门，几乎没有没覆盖到的角色；安装脚本非常成熟，一条命令搞定，支持多种 AI 工具；人设设计有深度，不是"你是一个前端工程师"这种敷衍的提示词；社区翻译版本多（中文、日语、韩语等都有）。

**缺点**：Agent 质量参差不齐，部分冷门领域的 Agent 写得比较浅；232 个 Agent 太多了，选起来眼花缭乱；OpenCode 有限制只能装 119 个；部分 Agent 偏向英语语境，中文场景效果打折扣；需要自己判断什么时候用哪个 Agent，没有智能调度。

**适合谁**：一人公司/独立开发者（这是最完美的目标用户）、想做全栈项目但缺某些技能的开发者、想快速验证产品创意的人。**不适合**：大型团队（Agent 文件太多不好管理）、纯粹的小白（需要会基本的 AI 工具使用）。

**评分 7/10**：量很大，精品率约 60-70%。对 OPC 场景价值极高，但质量不均是个问题。

## 未来趋势

项目处于**快速增长期**，社区活跃，经常有新 Agent 加入。随着 AI Agent 生态成熟，"预制专家角色"会成为标配。

6-12 个月内：预计会加入智能 Agent 推荐（自动判断任务该用哪个 Agent）、更多中文优化、可能推出 Web 管理界面。

**关注度 4/5**：对 OPC 一人公司场景价值巨大，但质量参差不齐需要自己筛选。

## 更新记录

| 日期 | 变更 | Stars |
|------|------|-------|
| 2026-06-20 | 首次记录 | 114,667 |

---

*记录时间: 2026-06-20*
