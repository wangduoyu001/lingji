---
title: "Chrome DevTools MCP"
date: 2026-06-21
github: https://github.com/ChromeDevTools/chrome-devtools-mcp
stars: 44093
category: MCP生态
interest: 2
status: 未试
usable: 待评估
实际用途: Chrome 开发者工具 MCP 接口
tags:
  - AI工具
  - GitHub
  - AI项目
  - MCP
  - 调试工具
  - 浏览器自动化
---

# Chrome DevTools MCP

> ⭐ 44,093 | 📅 2026-06-21 | [GitHub](https://github.com/ChromeDevTools/chrome-devtools-mcp)
>
> 💡 **怎么标记**：改上面 `interest` 数字 → 3=必装 2=想试 1=观望 0=跳过 → 改完按 Ctrl+S 保存

## 干什么
Chrome DevTools MCP 是 Google Chrome DevTools 团队官方出的 MCP Server，让 AI 编程助手（Claude、Cursor、Copilot 等）能直接操控和检查 Chrome 浏览器。就像你给 AI 配了一双能看网页的眼睛和一双能点鼠标的手——AI 不只能写代码了，还能打开浏览器、点击按钮、截图查看页面效果、分析性能、调试网络请求。没它之前，AI 写完前端代码你得自己打开浏览器看效果、手动测试、自己查 console 错误；有它之后，AI 自己打开浏览器看页面、自己截图检查、自己调试错误，你只要说"帮我检查这个页面的性能"就行了。

## 能实现什么效果
AI 助手通过 MCP 协议连接 Chrome，能做：① 自动操作浏览器（点击、输入、导航、截图）——让 AI 自己测试前端功能；② 性能追踪和分析——AI 录制性能 trace、提取优化建议、结合真实用户体验数据；③ 调试网络请求——AI 查看哪些请求慢、哪些返回了错误；④ 检查 Console 错误——AI 看到页面报什么错、在哪报的（支持源码映射）；⑤ 内存分析——AI 查看内存泄漏、大对象。还有47个工具覆盖输入自动化、导航、性能、网络、调试、内存等全方位能力。这意味着：前端开发的测试调试时间从手动30分钟→AI自动5分钟。

## 怎么用
1. **前端测试**：让 Claude Code 写完前端代码 → 通过 Chrome DevTools MCP 打开浏览器 → AI 自己点击按钮测试 → 截图看效果 → 发现问题自动修改
2. **性能优化**：告诉 AI "帮我检查这个页面的性能" → AI 自动录制 trace → 分析瓶颈 → 给出具体优化建议（比如"图片太大，压缩到200KB以下"）
3. **调试 bug**：页面有 bug → AI 通过 MCP 查看 Console 错误 → 看网络请求 → 定位问题 → 修改代码 → 再次测试
4. **移动端调试**：连接 Android 上的 Chrome → AI 远程调试 → 检查移动端显示问题

## 运行位置
本地电脑运行（Windows/Mac/Linux），需要 Chrome 浏览器。作为 MCP Server 运行，AI 工具通过 MCP 协议连接。Node.js 环境。

## 需要准备什么
① 完全免费开源，Apache 2.0 许可证。② 不需要注册账号。③ 不需要 API Key。④ 需要 Chrome 浏览器（稳定版）和 Node.js LTS。⑤ 安装方式：在 MCP 配置中添加 `npx -y chrome-devtools-mcp@latest`，或 `npm install chrome-devtools-mcp`。

## 配合什么软件
配合任何支持 MCP 的 AI 工具：Claude Code、VS Code Copilot、Cursor、Gemini CLI、JetBrains AI、Windsurf 等。有20+ MCP 客户端的详细配置指南。也提供独立 CLI 模式，不需要 MCP 也能用。

## 客观评价
优点：① Chrome DevTools 官方团队出品，不是第三方模拟，是真正的 DevTools 能力；② 47个工具覆盖全面，从点击到内存分析都有；③ 性能追踪结合 CrUX 真实用户数据，优化建议不只是理论；④ 支持20+ MCP 客户端，兼容性极好；⑤ 有轻量模式（slim+headless），3个工具就够了，适合简单场景。缺点：① 只支持 Google Chrome，Edge/Brave 等其他 Chromium 浏览器不保证能用；② 使用统计默认开启，需要手动关闭；③ 浏览器内容会暴露给 MCP 客户端，有隐私风险（不要在银行网站上用）；④ 需要 Chrome 144+ 才能用自动连接功能；⑤ 并发多代理操作同一浏览器需要特殊配置。适合：做前端开发的人、需要 AI 自动测试网页的人、做性能优化的人。不适合：不做前端开发的人、担心隐私的人。我打 **8/10**——官方出品质量有保障，功能全面，但只支持 Chrome 是限制。

## 未来趋势
① 项目处于快速增长期，4.4万星，Chrome官方背书；② 6-12个月内可能会支持更多浏览器、增加更多调试工具、改善隐私机制；③ 关注度 **4/5**——MCP+浏览器是2026年重要基础设施。

## 更新记录

| 日期 | 变更 | Stars |
|------|------|-------|
| 2026-06-21 | 馮次记录 | 44,093 |

---

*记录时间: 2026-06-21*

---

📂 **同类别工具**：[[_索引_AI生产力工具|查看 AI生产力工具 全部 22 个工具]]
