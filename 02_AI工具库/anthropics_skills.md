---
title: "Anthropic Skills"
date: 2026-06-18
github: https://github.com/anthropics/skills
stars: 152293
category: AI编程工具
interest: 1
status: 未试
usable: 待评估
实际用途: Anthropic AI 编程技能/工具包
tags:
  - AI工具
  - GitHub
  - AI项目
  - Anthropic
  - 编程工具
  - 技能
---

# Anthropic Skills

> ⭐ 152,293 | 📅 2026-06-18 | [GitHub](https://github.com/anthropics/skills)
>
> 💡 **怎么标记**：改上面 `interest` 数字 → 3=必装 2=想试 1=观望 0=跳过 → 改完按 Ctrl+S 保存

## 干什么

Anthropic Skills 是 Anthropic（Claude 的母公司）官方出品的 Agent Skills 仓库。它就像给 Claude Code 装上了一套"专业技能插件包"——让 AI 编程代理不光能写代码，还能做设计、写文档、做测试、创建 PPT、生成 Excel 报表等。以前用 AI 编程，它只会写代码，遇到要生成一个漂亮的 PDF 报表就抓瞎了；有了这些官方 Skills，你能直接说"给我生成一份季度销售分析 PPT"，AI 就能自动调用对应的 Skill 来完成。因为是官方出品，质量和安全性有保障。

## 能实现什么效果

装了 Anthropic Skills 之后，Claude Code 的能力范围大大扩展。比如你在做项目，需要一份项目计划书——以前得自己打开 Word 一个字一个字写，现在在终端里说"根据这个代码仓库生成一份项目计划 PPT"，几分钟后一份排版整齐的 PPT 就出来了。再比如你写完代码需要写测试——说"给这些函数写单元测试，覆盖率达到 90%"，AI 会用专门的 test skill 来生成高质量的测试代码。官方 Skills 覆盖了文档生成、前端设计、数据分析、安全审计等 20+ 个专业领域。

## 怎么用

- **生成 PPT**：在 Claude Code 终端里 → "用 skill 帮我根据 README 生成一个产品介绍 PPT" → 自动生成 pptx 文件
- **代码审计**：写完代码担心有安全问题 → "用 security skill 检查这个仓库的代码安全" → 生成安全审计报告
- **文档生成**：代码写完了 → "用 doc skill 给所有公开 API 生成带示例的文档" → 生成结构化的 Markdown 文档
- **Excel 报表**：需要数据分析 → "用 xlsx skill 把这个 CSV 数据生成图表和分析报告" → 自动生成 Excel
- **前端页面**：需要快速出原型 → "用 frontend skill 根据这段描述生成一个登录页面的 HTML/CSS" → 直接出可用页面

## 运行位置

- **本地电脑**：作为 Claude Code 的插件运行，Windows/Mac/Linux 都支持
- 本质上是 Claude Code 的技能配置文件，Python 脚本驱动

## 需要准备什么

- **费用**：完全免费开放（Anthropic 官方维护）
- **账号**：不需要额外账号
- **API Key**：需要有 Claude API Key（通过 Anthropic 官网申请，按使用量付费）
- **电脑配置**：跟 Claude Code 一样，8GB 内存以上即可
- **软件依赖**：需要先安装 Claude Code，然后安装 Python 运行 Skills

## 配合什么软件

必须配合 Claude Code 使用。部分 Skills 需要 Python 环境。如果用其他 AI 编程工具（Codex、Cursor），不能用这个。

## 客观评价

优点：① 官方出品，质量稳定、更新及时、不会跑路；② 免费开源；③ 覆盖面广——从前端到后端、从文档到安全；④ 安装简单，一条命令搞定。

缺点/坑：① 绑定 Claude Code 生态，不能跨工具使用；② 某些 Skill 依赖 Python 第三方库，可能需要额外安装；③ 社区 Skills 没有（不像 superpowers 那样有社区贡献），全靠官方一家；④ Claude API 费用不低，如果你免费额度用完了，继续用要花钱。

适合谁：Claude Code 重度用户、需要生成文档/PPT/报表的开发者。不适合：用其他 AI 编程工具的人、对 Claude API 费用敏感的用户。

打分：7.5/10。官方品质有保障，但绑定生态是硬伤。扣 2.5 分因为锁死 Claude 生态且缺少社区贡献。

## 未来趋势

① 所处阶段：快速完善期——Skills 从 2025 年底推出后一直在增加新技能；② 6-12 个月：可能会推出社区贡献机制，允许第三方提交 Skills；③ 关注度：4/5，Claude Code 用户必装。

## 更新记录

| 日期 | 变更 | Stars |
|------|------|-------|
| 2026-06-18 | 首次记录 | 152,293 |

---

*记录时间: 2026-06-18*

---

📂 **同类别工具**：[[_索引_AI编程工具|查看 AI编程工具 全部 24 个工具]]

---
## 相关内容

- [[aaif-goose_goose]]
- [[addyosmani_agent-skills]]
- [[affaan-m_ECC]]
- [[Aider-AI_aider]]
- [[anomalyco_opencode]]
