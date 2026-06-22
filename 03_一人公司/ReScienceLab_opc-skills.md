---
title: "ReScienceLab/opc-skills"
date: 2026-06-17
github: https://github.com/ReScienceLab/opc-skills
stars: 930
interest: 1
status: 未试
usable: 待评估
category: OPC一人公司
实际用途: OPC 一人公司技能/工具包
tags:
  - AI工具
  - GitHub
  - AI项目
  - 技能包
  - 一人公司
---

# OPC Skills

> ⭐ 930 | 📅 2026-06-17 | [GitHub](https://github.com/ReScienceLab/opc-skills)
>
> 💡 **怎么标记**：改上面 `interest` 数字 → 3=必装 2=想试 1=观望 0=跳过 → 改完按 Ctrl+S 保存

## 干什么

OPC Skills 是一个"给一人公司（OPC = One-Person Company）量身定做的 AI 技能包合集"——里面包含了 10 个可以直接装进你的 AI 编程助手（Claude Code/Cursor/Codex 等）的"技能模块"，每个模块让 AI 多一项专业能力。通俗地说，就是"给你的 AI 助手装插件"——装完之后，你跟 AI 说"帮我分析一下 Reddit 上对我产品的讨论"，它就能直接去搜、整理、汇报，不用你手动去 Reddit 一个个帖子翻。

它的设计理念是"Agent Skills 标准"——每个技能是一个独立的文件夹，里面有一份 `SKILL.md` 文件（告诉 AI 这个技能是干什么的、什么时候用、怎么用），还可以附带脚本和资源文件。你的 AI 助手会根据需要自动加载对应的技能，就像一个员工自己知道"这个问题该用哪个工具"一样。

这 10 个技能覆盖了一人公司最核心的需求：让产品被找到（SEO/域名/竞品分析）、让设计不用愁（Logo/横幅生成）、让市场调研自动化（Reddit/Twitter/Product Hunt 搜索）、让项目有记忆（会话归档）。对于一个人做项目的人来说，这套技能包相当于"雇了一个小团队"——有人做设计、有人做市场调研、有人做 SEO、有人做归档。

## 能实现什么效果

举个例子：你做了一个 SaaS 产品，想看看 Reddit 上有没有人在讨论类似的产品、或者有没有人抱怨现有产品的痛点（这些痛点就是你的机会）。以前你要自己上 Reddit 搜、一个个帖子看、做笔记，可能要花 1-2 小时。用了 OPC Skills 里的 `reddit` 技能，你跟 AI 说"帮我搜 Reddit 上关于 XX 产品的讨论，整理出用户痛点"，它直接调用 Reddit 公开 API 搜一遍，把相关讨论摘出来、分好类、列出痛点清单，10 分钟搞定。原来要花 1-2 小时的事，现在 10 分钟，而且不会漏掉重要信息。

另一个例子：你要给产品做个 Logo，但请设计师要么贵要么等得久。用了 `logo-creator` 技能，你跟 AI 说"帮我设计一个简约风格的 SaaS 产品 Logo，主色是蓝色"，它调用 AI 图像生成（Gemini 多模态）帮你生成几个方案，还能自动去背、导出成 SVG 格式，直接就能用。虽然可能还是需要人工挑选和调整，但"从零到有一个能用的初稿"这个过程，从"等设计师 3 天"变成了"10 分钟出初稿"。

它的 `seo-geo` 技能也很实用：现在很多人用 ChatGPT、Perplexity 这些 AI 搜索引擎来找产品，传统的 SEO（搜索引擎优化）不够了，还需要做 GEO（生成式引擎优化——让 AI 搜索能找到你）。这个技能帮你分析你的网站在 AI 搜索里有没有被收录、怎么优化，对于靠 AI 搜索带流量的产品来说很值钱。

## 怎么用

- **Claude Code 插件安装（最简单）**：在 Claude Code 里运行 `/plugin marketplace add ReScienceLab/opc-skills` → 然后 `/plugin install reddit@opc-skills`（安装你想要的具体技能） → 安装完直接用，跟 AI 说"帮我搜 Reddit..."它就会自动调用 `reddit` 技能
- **通用安装（支持 16+ 种 AI 工具）**：在终端里运行 `npx skills add ReScienceLab/opc-skills` → 它会自动检测你用的是哪种 AI 工具（Claude Code/Cursor/Windsurf 等）并把技能装到对应目录 → 重启 AI 工具就能用
- **安装单个技能**：如果只想装某一个，运行 `npx skills add ReScienceLab/opc-skills --skill twitter` → 只安装 `twitter` 技能，不装其他的
- **处理技能依赖**：有些技能需要其他技能才能用（比如 `domain-hunter` 需要 `twitter` 和 `reddit`），安装时它会提示你，或者你可以一次性全装：`npx skills add ReScienceLab/opc-skills --skill reddit --skill twitter --skill domain-hunter`
- **浏览所有技能**：打开 [skills.sh/ReScienceLab/opc-skills](https://skills.sh/ReScienceLab/opc-skills) → 查看每个技能的详细说明和用法 → 决定装哪些

## 运行位置

- 🖥️ **本机运行**：Windows/Mac/Linux 都支持，技能装完在你的 AI 工具配置目录里，不需要单独运行
- 🔌 **嵌入 AI 工具**：装完之后，技能在你的 Claude Code/Cursor/Codex 等工具里直接可用，不需要单独打开什么
- 🌐 **在线浏览**：[skills.sh](https://skills.sh/ReScienceLab/opc-skills) 可以在线查看所有技能的说明，不需要安装

## 需要准备什么

- 💰 **要钱吗**：技能包本身开源免费（Apache 2.0 许可证），可以随便用、随便改
- 🔑 **API Key**：大部分技能需要你的 AI 工具有 API Key（比如 Claude Code 需要 Anthropic API Key）。部分技能还需要额外的 API（比如 `twitter` 技能需要 twitterapi.io 的 API Key，`reddit` 技能用的是 Reddit 公开 API，不需要 Key）
- 💻 **电脑配置**：要求很低，能跑你的 AI 编程助手就行
- 📦 **要装什么**：需要先装好一个支持的 AI 工具（Claude Code/Cursor/Windsurf 等 16 种），然后用一行命令装技能，不用额外装别的东西
- 🌐 **网络**：需要能访问技能调用的服务（比如 Reddit/Twitter/Product Hunt 等），国内网络可能需要代理

## 配合什么软件

- **Claude Code**：最主要的支持工具，安装和使用体验最好
- **Cursor**：AI 代码编辑器，也支持
- **Windsurf**：另一个 AI 编程工具，支持
- **Codex**：OpenAI 的编程助手，支持
- **16+ 种 AI 工具**：完整列表在 [github.com/vercel-labs/add-skill](https://github.com/vercel-labs/add-skill#available-agents)，包括 GitHub Copilot、Gemini CLI 等

## 客观评价

**优点**：
- 专为一人公司设计，技能选择很实用（都是一个人做项目最需要的：市场调研、设计、SEO、域名等）
- 安装超级简单，一行命令搞定，支持市面上主流的 AI 编程工具，不用自己折腾适配
- 开源免费，可以自己改技能、自己加新技能，也可以给项目贡献技能
- 有在线文档（DeepWiki）和技能浏览器（skills.sh），查找和学怎么用很方便
- 技能是模块化设计，想用哪个装哪个，不想用的不装，不臃肿

**缺点/坑**：
- 项目还比较新，star 数只有 930，社区还不够大，技能的完善度和稳定性可能不如更成熟的项目
- 部分技能需要额外 API Key（比如 Twitter 技能需要 twitterapi.io 的 Key，这不是免费的），增加了使用成本
- 技能的效果上限取决于底层 AI 模型的能力，有些任务（比如生成很精细的 Logo）可能还是需要人工设计师收尾
- 信息有限：因为项目比较新，网上的教程和评测不多，遇到问题解决可能要多靠自己看代码
- 对不懂怎么配置 API Key 的小白来说，第一步就可能卡住

**适合谁**：正在或打算做一人公司/独立产品的开发者；已经在用 Claude Code/Cursor 等 AI 编程工具的人；需要快速做市场调研、设计初稿、SEO 优化的人。

**不适合谁**：完全不懂技术、连 API Key 是什么都不知道的小白；需求很特殊、这 10 个技能覆盖不到的人；对 AI 生成内容的质量要求很高、不能接受"初稿级别"输出的人。

**评分**：7/10 — 方向很实用（一人公司刚需），安装和使用设计得很好，但项目还新、技能数量有限、部分技能有额外成本，长期价值需要进一步观察。

## 未来趋势

- 📈 **所处阶段**：早期阶段，star 数 930 说明还在起步，但"一人公司 + AI"这个方向本身很热，项目有增长潜力
- 🔮 **6-12 个月走向**：预计技能数量会继续增加（社区可以贡献新技能），覆盖更多一人公司的场景；可能会加入更多"多技能协作"的功能（比如让 `reddit` 和 `twitter` 技能配合做一个完整的竞品舆情分析）；随着一人公司赛道越来越热，这个项目也会受到更多关注
- ⭐ **关注度**：3/5 — 目前关注度还不高，但"一人公司 + AI"是趋势，值得持续观察

## 更新记录

| 日期 | 变更 | Stars |
|------|------|-------|
| 2026-06-17 | 重写为8字段富描述版本 | 930 |
| 2026-06-16 | 首次记录 | 930 |

---

*记录时间: 2026-06-17*

---

📂 **同类别工具**：[[_索引_OPC一人公司|查看 OPC一人公司 全部 6 个工具]]

---
## 相关内容

- [[aaif-goose_goose]]
- [[addyosmani_agent-skills]]
- [[affaan-m_ECC]]
- [[Aider-AI_aider]]
- [[anomalyco_opencode]]
