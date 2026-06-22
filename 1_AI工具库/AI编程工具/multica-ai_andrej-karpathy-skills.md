---
title: "Andrej Karpathy Skills"
date: 2026-06-20
github: https://github.com/multica-ai/andrej-karpathy-skills
stars: 179097
category: AI 编程技能
interest: 3
status: 未试
usable: 待评估
实际用途: Karpathy 风格 AI 技能/提示词
tags:
  - AI工具
  - GitHub
  - AI项目
  - AI编程
  - Claude-Code
  - 技能
---

# Karpathy Skills — 让 AI 编程不再"自以为聪明"

> ⭐ 179,097 | 📅 2026-06-20 | [GitHub](https://github.com/multica-ai/andrej-karpathy-skills)
>
> 💡 **怎么标记**：改上面 `interest` 数字 → 3=必装 2=想试 1=观望 0=跳过 → 改完按 Ctrl+S 保存

## 干什么

这项目就一个文件——`CLAUDE.md`。但这个文件能解决 AI 编程里最让人抓狂的一个问题：AI 太"自以为是"了。它经常不问你需求细节就直接开写，喜欢把简单的事情复杂化（10 行能搞定的非要写 100 行），还动不动顺手改掉你没让它动的代码。

这个问题的根源是大模型的工作方式——它倾向于"脑补"你没说的部分，而不是停下来问你。AI 大神 Andrej Karpathy 在 Twitter 上吐槽了这些问题后，有人把 Karpathy 的观点整理成了四条给 AI 的行为准则，放进一个 CLAUDE.md 文件里。你把文件丢到项目根目录，Claude Code 就会自动按这四条准则来行事——变得谨慎、克制、目标明确。

四条准则分别是：**先想再写**（不许瞎猜，不确定就问）、**极简优先**（只写必需代码，不搞过度设计）、**手术式修改**（只改该改的地方，不乱碰别的）、**目标驱动**（定义成功标准，反复验证直到达标）。

## 能实现什么效果

装了这个之后，你会明显感觉 AI 的"废话"和"瞎改"变少了。以前让 AI 改一个按钮颜色，它可能顺手"优化"了整个页面的布局——装了之后它只改按钮颜色，别的不动。

Karpathy 原话的关键洞察是：不要告诉 AI "怎么做"，而是告诉它"做成什么样就行了"——比如不说"加一个表单验证"，而是说"确保用户提交时如果邮箱格式不对就弹红色提示，并写一个测试验证这个行为"——AI 就会自己去循环调试直到测试通过。

实际效果：代码返工减少、PR 更干净（diff 里没有莫名其妙的多余修改）、AI 会主动在不确定的时候问你而不是瞎猜。

## 怎么用

- **给 Claude Code 装上**（推荐方式）：在 Claude Code 里输入 `/plugin marketplace add forrestchang/andrej-karpathy-skills` 然后 `/plugin install andrej-karpathy-skills@karpathy-skills`，一条命令搞定。
- **手动放到项目里**：`curl -o CLAUDE.md https://raw.githubusercontent.com/forrestchang/andrej-karpathy-skills/main/CLAUDE.md`，放到项目根目录就行。
- **给 Cursor 用**：项目里带了 `.cursor/rules/karpathy-guidelines.mdc` 文件，复制到 Cursor 规则目录即可。
- **合并到已有配置**：如果项目里已经有 `CLAUDE.md`，把内容追加进去就行，不冲突。

## 运行位置

- 这不是一个独立软件，而是一个"配置文件"
- 在你的电脑上，任何支持 CLAUDE.md 的 AI 编程工具都能用（Claude Code、Cursor 等）

## 需要准备什么

- 完全免费（MIT 协议）
- 不需要注册、不需要 API Key（它是配置文件，不是软件）
- 需要一个支持 CLAUDE.md 的 AI 编程工具（Claude Code 或 Cursor）
- 没有硬件要求——它不运行任何东西，只是给 AI 的行为规范

## 配合什么软件

- **Claude Code**（原生支持 CLAUDE.md）或 **Cursor**（项目自带适配文件）
- 可以和任何项目搭配使用，不影响现有配置

## 客观评价

**优点**：极简——就一个文件、四条规则，5 分钟看完装好；效果立竿见影——AI 的行为变化非常明显；来自 AI 领域最具影响力的人（Karpathy 是 OpenAI 联合创始人、前特斯拉 AI 总监）的实践经验；免费、无依赖、不占资源。

**缺点**：只对支持 CLAUDE.md 的工具有效（Claude Code 和 Cursor），Codex CLI、Gemini CLI 等工具不支持；规则偏"保守"，对于简单的需求可能会让 AI 显得过于谨慎、问太多问题；本质是"软约束"而非"硬限制"，AI 不一定会严格遵守每一条。

**适合谁**：所有用 Claude Code 或 Cursor 写代码的人。**特别适合**：经常被 AI 过度设计困扰的开发者。**不太适合**：只用 Codex 或 Gemini CLI 的用户（需要等对应工具支持）。

**评分 9/10**：用最简单的方式解决了最普遍的问题。唯一扣分是工具兼容性有限。

## 未来趋势

项目处于**成熟稳定期**，核心内容（四条准则）不会频繁变化。但随着更多 AI 编程工具支持类似机制，这套思路会成为行业标准。

**关注度 5/5**：不是因为技术复杂，而是因为这代表了 AI 编程方法论的重要进化方向。

## 更新记录

| 日期 | 变更 | Stars |
|------|------|-------|
| 2026-06-20 | 首次记录 | 179,097 |

---

*记录时间: 2026-06-20*

---

📂 **同类别工具**：[[_索引_AI编程工具|查看 AI编程工具 全部 24 个工具]]
