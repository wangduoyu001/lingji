---
title: "garrytan/gstack"
date: 2026-06-17
github: https://github.com/garrytan/gstack
stars: 80000
interest: 1
status: 未试
usable: 待评估
category: AI编程工具
实际用途: AI 编程工具栈/模板
tags:
  - GitHub
  - AI项目
  - AI编程工具
---

# gstack

> ⭐ 80,000 | 📅 2026-06-17 | [GitHub](https://github.com/garrytan/gstack)
>
> 💡 **怎么标记**：改上面 `interest` 数字 → 3=必装 2=想试 1=观望 0=跳过 → 改完按 Ctrl+S 保存

## 干什么

gstack 是 Y Combinator（美国最著名的创业孵化器，相当于国内的创新工场+天使投资）总裁 Garry Tan 开源的 Claude Code 配置包。它的核心思路是：Claude Code 本来只能当"一个程序员"用，但 gstack 给它配了 23 个"角色技能"（CEO、设计师、工程经理、QA 测试、发布工程师、文档工程师等），让一个人用 AI 就能模拟整个软件团队的工作流。

这个项目不是简单的"提示词合集"，而是一套有严格顺序的工作流：思考 → 规划 → 构建 → 评审 → 测试 → 发布 → 复盘。每个阶段的输出会自动流入下一个阶段，就像真实团队里的"需求文档 → 设计稿 → 代码 → 测试 → 上线"流程。Garry Tan 自己在博客里说，2026 年他的代码变更速度是 2013 年的约 810 倍——这就是 gstack 的实战效果。

它还支持 10 种 AI 编程工具（不只能用在 Claude Code），包括 Cursor、Codex、OpenCode、Hermes 等，装一次配置，多个工具都能用。如果你在团队里，还可以用"团队模式"——把 gstack 配置提交到仓库里，团队成员拉代码时自动获得同一套配置，保证大家用同一个"工作流程"。

## 能实现什么效果

装上 gstack 之后，你用 Claude Code 的方式会从"我一步步告诉 AI 做什么"变成"我只需要说idea，AI 按流程自己走完全流程"。原来你要手动做规划、写代码、自己 review、自己写测试、自己写发布文档，现在运行 `/office-hours "我要做一个每日简报应用"`，gstack 会先让你回答 6 个强制性问题（防止你"想不清楚就开干"），然后输出一份设计文档，后面的 `/plan-ceo-review`、`/review`、`/qa`、`/ship` 等命令会自动接力，你只需要在关键节点审批就行。

举个例子：你想做一个"日历每日简报"功能。原来你要自己想：数据从哪来？用什么格式？用户最需要哪 5 个信息？技术架构怎么搭？测试用例怎么写？这些都要你自己想清楚再告诉 AI。有了 gstack，你运行 `/office-hours`，它会挑战你的假设（"你说'每日简报'，但你实际描述的是一个私人幕僚长 AI，这两个范围差很远，你到底要做哪个？"），帮你把模糊的想法变成精确的规格文档，后面的命令按这个文档自动执行，你从"全程指挥"变成了"关键节点审批"，效率提升 5-10 倍。

对于已经有团队的场景，"团队模式"也很有价值：大家用同一套 gstack 配置，AI 生成的代码风格、review 标准、测试要求都是一致的，不会出现"张三的代码有测试，李四的代码没测试"的问题。

## 怎么用

- **首次安装**：在 Claude Code 终端里粘贴一行命令：`git clone --single-branch --depth 1 https://github.com/garrytan/gstack.git ~/.claude/skills/gstack && cd ~/.claude/skills/gstack && ./setup`，然后按提示操作。Windows 用户需要额外装 Bun v1.0+ 和 Node.js
- **团队模式（推荐）**：在仓库里运行 `(cd ~/.claude/skills/gstack && ./setup --team) && ~/.claude/skills/gstack/bin/gstack-team-init required`，然后把变更提交到 Git。团队成员拉代码后自动获得 gstack，不需要每人手动装
- **开始一个新功能**：运行 `/office-hours`，回答 6 个强制性问题 → 获得设计文档 → 运行 `/plan-ceo-review` 做 CEO 视角评审 → 运行 `/plan-eng-review` 做工程视角评审
- **写代码阶段**：设计文档审批通过后，Claude Code 会自动进入实施模式（按 gstack 的规格写代码，不是随便写）。写完后运行 `/review` 做代码审查（会自动修复明显问题，复杂问题会问你）
- **测试和上线下**：运行 `/qa <staging-url>` 做 QA 测试（AI 会打开真实浏览器点击测试）→ 运行 `/ship` 推送代码、跑测试、开 PR → 运行 `/canary` 监控上线后的情况

## 运行位置

- 🖥️ **Windows / Mac / Linux 都支持**，在 Claude Code 终端里运行
- 需要联网（调用 Claude API）
- 也支持 Cursor、Codex、OpenCode、Hermes 等其他 AI 编程工具（安装时加 `--host cursor` 等参数）
- 部分命令（如 `/qa`、`/browse`）需要能打开浏览器（用于自动测试）

## 需要准备什么

- 💰 **要钱吗**：gstack 本身完全免费开源（MIT 协议），但需要 Claude Code 能正常工作——需要 Anthropic API 或者 Claude Pro/Max 订阅
- 🔑 **API Key**：需要 Anthropic API Key，或者直接用 Claude Pro/Max 登录（gstack 支持订阅登录，不需要单独 API Key）
- 💻 **电脑配置**：要求不高，8GB 内存就够。需要装 Node.js 和 Bun v1.0+（Windows 用户必须装，Mac/Linux 安装脚本会自动处理）
- 📦 **要装什么**：Claude Code（必须）、Git（必须）、Bun v1.0+（必须，Windows 用户特别注意）。可选：Playwright（用于 `/browse` 浏览器测试命令）
- 🌐 **网络**：需要能访问 Anthropic 服务器，国内可能需要代理

## 配合什么软件

- **Claude Code**：主要运行环境，gstack 就是为它设计的
- **Cursor / Codex / OpenCode / Hermes**：也支持，安装时指定 `--host` 参数
- **Conductor**（https://conductor.build）：Garry Tan 推荐配合使用的多会话管理工具，可以同时跑 10-15 个并行 Claude Code 会话（每个会话用一个 gstack 工作流），实现"10 个并行冲刺"，效率极高
- **GBrain**：gstack 支持接入 GBrain（AI 代理的持久知识库），可以跨会话记住项目信息
- **Git**：gstack 的 `/ship` 命令会自动提交 Git、开 PR，需要仓库已初始化 Git

## 客观评价

**优点**：
- 作者是 YC 总裁 Garry Tan，他自己每天都在用（不是"开源了就不维护了"的那种项目），实战验证过
- 工作流设计严谨：强制先在 `/office-hours` 里想清楚再动手，防止"AI 跑偏"——这是很多 AI 编程工具的痛点
- 23 个角色技能覆盖完整软件团队工作流，从想法到上线到复盘都有，不是只有"写代码"
- 支持 10 种 AI 编程工具，装一次，多个工具都能用，换工具不浪费
- "团队模式"设计好：配置存在仓库里，团队统一标准，这个在企业场景很有价值
- MIT 开源协议，完全免费，代码透明
- 有安全设计：`/careful` 命令会在执行破坏性操作前警告（比如 `rm -rf`、`DROP TABLE`、force-push），防止 AI 误操作

**缺点/坑**：
- 学习曲线陡：23 个技能，每个技能有自己的使用场景，新手不知道"现在该用哪个命令"
- 需要 Claude Code 能正常工作，如果 Claude Code 本身有网络问题，gstack 也用不了
- 部分高级功能需要额外配置（如 GBrain 集成、Conductor 并行会话），不是开箱即用
- 项目更新很快，可能需要定期跑 `/gstack-upgrade` 更新，跟不上最新版本可能会遇到命令找不到的情况
- Windows 安装比 Mac/Linux 复杂（需要手动装 Bun，而且 Bun 在 Windows 上偶尔有兼容性问题）
- 信息有限：我无法实际使用它，以上评价基于 README，可能有遗漏

**适合谁**：已经在使用 Claude Code / Cursor 等 AI 编程工具、想提升"从想法到上线"全流程效率的人。特别适合一个人做项目、但需要"模拟团队"的独立开发者。

**不适合谁**：完全不懂命令行的人（安装需要跑脚本）、不用 Claude Code 等支持的工具的人、只想"AI 帮我写代码"不需要完整工作流的人。

**评分**：8/10 — 工作流设计最严谨的 Claude Code 增强包，就是学习曲线有点陡

## 未来趋势

- 📈 **所处阶段**：快速增长期。2026 年 3 月开源，3 周就获得 61K Star，目前约 80K Star，是 2026 年 AI 编程工具圈最火的项目之一
- 🔮 **6-12 个月走向**：预计会加入更多角色技能（目前 23 个，可能会扩展到 30+ 个），Conductor 集成会更紧密（让"并行冲刺"更简单），可能会出图形化界面（目前全是命令行）
- ⭐ **关注度**：5/5 — YC 总裁亲自维护，社区热度极高，必须关注

## 更新记录

| 日期 | 变更 | Stars |
|------|------|-------|
| 2026-06-17 | 重写为8字段富描述版本 | 80000 |
| 2026-06-16 | 首次记录（stars 数据有误，已修正） | 111000 |

---

*记录时间: 2026-06-17*
