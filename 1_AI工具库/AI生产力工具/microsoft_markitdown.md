---
title: "MarkItDown"
date: 2026-06-21
github: https://github.com/microsoft/markitdown
stars: 156672
category: AI生产力工具
interest: 2
status: 未试
usable: 待评估
实际用途: 文档转 Markdown 工具（PDF/Word/Excel）
tags:
  - GitHub
  - AI项目
  - AI生产力工具
  - 文档处理
---

# MarkItDown

> ⭐ 156,672 | 📅 2026-06-21 | [GitHub](https://github.com/microsoft/markitdown)
>
> 💡 **怎么标记**：改上面 `interest` 数字 → 3=必装 2=想试 1=观望 0=跳过 → 改完按 Ctrl+S 保存

## 干什么
MarkItDown 是微软 AutoGen 团队做的"文档翻译机"，专门把 PDF、Word、Excel、PPT、HTML 这些乱七八糟的文件格式统统变成干净的 Markdown 文本。就像你请了一个秘书，把各种花里胡哨的文件全部整理成纯文本笔记，方便你（或者 AI）后续阅读和处理。没它之前，你要处理不同格式的文档得装一堆软件，PDF 要 Adobe、Word 要 Office、Excel 要看表格软件，现在一个工具搞定所有。最关键的是——输出的 Markdown 正好是大模型最喜欢的格式，因为 GPT-4o、Claude 这些 AI 天生就"说" Markdown，token 消耗最少、理解最准确。

## 能实现什么效果
用了之后，你丢一个 50 页的 PDF 或者一个嵌满图表的 Excel 给它，几分钟就吐出一份结构清晰的 Markdown 文本，标题、列表、表格、链接全部保留。这意味着你可以：① 把老板发来的合同 PDF 直接转成文本扔给 AI 分析关键条款，省了你自己逐页翻阅的时间；② 把客户发来的报价单 Excel 转成文本让 AI 对比不同方案，不用你手动抄数据；③ 批量把公司文档库里的 Word 文件全部转成 AI 可读格式，构建知识库。原来干这些事可能要半天，现在几分钟。产出的是 Markdown 文本，可以直接喂给 ChatGPT/Claude/Dify 等任何 AI 工具做后续分析。

## 怎么用
1. **分析合同**：收到 PDF 合同 → `markitdown contract.pdf > contract.md` → 把 Markdown 扔给 Claude，让它帮你提炼关键条款和风险点
2. **处理报表**：月底收到 Excel 财务报表 → 转成 Markdown → 让 AI 自动生成摘要和趋势分析，省了你自己看数据的功夫
3. **构建知识库**：把公司文档库里的 Word/PPT 全部批量转成 Markdown → 导入到 RAGFlow 或 Dify 知识库 → AI 可以随时回答公司相关问题
4. **网页内容提取**：想把某个网页内容保存给 AI 用 → `markitdown https://example.com` → 直接得到干净的文本，比手动复制粘贴省事得多

## 运行位置
本地电脑运行（Windows/Mac/Linux 都支持）。也有 Docker 版本，适合服务器部署。Python 环境，不需要浏览器。

## 需要准备什么
① **免费开源**，MIT 许可证，不要钱。② 不需要注册账号。③ 不需要 API Key（基础功能），但如果要用 Azure Document Intelligence 增强功能，需要 Azure 账号和 API Key。④ 电脑只需要 Python 3.10+，没有显卡要求，内存够跑 Python 就行。⑤ 需要装 Python 和 pip，然后 `pip install 'markitdown[all]'` 一条命令安装所有依赖。

## 配合什么软件
配合 Claude Code、ChatGPT、Dify、RAGFlow 等 AI 工具最合适——转出来的 Markdown 正好是这些工具的输入格式。也可以配合 Ollama 本地模型做离线文档分析。独立使用也行，就是纯文件转换工具。

## 客观评价
优点：① 微软出品，质量有保障，AutoGen 团队维护，更新频繁；② 支持格式最全面，PDF/Word/Excel/PPT/HTML/图片/音频/视频全覆盖；③ 输出 Markdown 格式对 AI 最友好，token 效率高；④ 插件系统可以扩展。缺点：① 复杂排版（比如多栏报纸、图文混排）的 PDF 转换质量有限，结构会丢失一些；② 基础功能的 OCR 能力一般，扫描版 PDF 需要配 Azure 服务才好用；③ 图片里的文字提取要额外装 OCR 插件；④ Windows 下有些依赖包安装可能会遇到兼容问题。适合：经常需要把各种文档丢给 AI 分析的人、搭建知识库的人、做数据提取的人。不适合：需要高保真人类阅读文档转换的人（它明确说了输出是面向文本分析工具的）。我打 **8/10**——功能强大覆盖面广，微软背书可靠性高，但 OCR 和复杂排版是短板。

## 未来趋势
① 项目处于快速增长期，15 万+星说明市场需求巨大，微软持续投入资源；② 6-12个月内可能会加强图片 OCR 和扫描版 PDF 处理能力，集成更多 Azure 服务；③ 关注度 **5/5**——文档→AI 是2026年基础设施级别的能力，几乎每个 AI 应用都需要。

## 更新记录

| 日期 | 变更 | Stars |
|------|------|-------|
| 2026-06-21 | 首次记录 | 156,672 |

---

*记录时间: 2026-06-21*
