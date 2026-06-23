---
title: "ds4 (DwarfStar)"
date: 2026-06-20
github: https://github.com/antirez/ds4
stars: 14737
category: AI 推理引擎
interest: 2
status: 未试
usable: 待评估
实际用途: AI 推理引擎/DSL
tags:
  - AI工具
  - GitHub
  - AI项目
  - DeepSeek
  - 本地AI
  - 推理引擎
---

# ds4 — Redis 作者亲手打造的 DeepSeek 本地推理引擎

> ⭐ 14,737 | 📅 2026-06-20 | [GitHub](https://github.com/antirez/ds4)
>
> 💡 **怎么标记**：改上面 `interest` 数字 → 3=必装 2=想试 1=观望 0=跳过 → 改完按 Ctrl+S 保存

## 干什么

这是 antirez（Redis 数据库的创始人，编程圈公认的大神级人物）用纯 C 语言写的 DeepSeek V4 本地推理引擎。它的目标很纯粹：在你的 MacBook 上以尽可能快的速度、尽可能低的内存占用，本地运行 DeepSeek V4 这个强大的 AI 模型。

antirez 为什么要做这个？因为他不满意现在本地跑大模型的方式——要么太慢、要么太吃内存、要么太复杂。他用自己写 Redis 时练就的"极致性能优化"功力，重新设计了一个专为 DeepSeek V4 优化的推理引擎，让 96GB 内存的 MacBook 就能流畅运行 2bit 量化版，速度达到 M4 Max 上 45-55 tokens/s。

除了推理引擎本身，他还附带做了全套工具链：DwarfStar Server（兼容 OpenAI/Anthropic API 格式的服务端，可以对接 Claude Code、Codex 等 AI 编程工具）、DwarfStar Agent（原生编码 Agent）、GGUF 模型量化工具等。

## 能实现什么效果

把价值几十万的云端大模型服务，搬到你的笔记本电脑上免费、无限量使用。以 DeepSeek V4 Flash 为例，云端 API 要按使用量付费，用了 ds4 后你在 MacBook 上随便用，不花一分钱。

对隐私敏感的人来说，这意味着你的数据和对话永远不会离开你的电脑——没有第三方服务器能看到你在问什么。

还有一个很酷的功能：分布式推理。如果你有两台 Mac Studio，可以把模型拆成两半分在两边跑，获得更大的吞吐量。甚至可以通过互联网连接两台电脑来协同推理（虽然网速会成为瓶颈）。

## 怎么用

- **下载模型**：`./download_model.sh q2-imatrix`（根据你的内存大小选不同量化版本）。
- **编译**：macOS 上 `make`、NVIDIA GPU 上 `make cuda-generic`、DGX Spark 上 `make cuda-spark`。
- **启动服务**：`./ds4-server`，然后就能通过 OpenAI 兼容 API 调用（`http://localhost:8080/v1`）。
- **当 AI 编程后端**：启动服务后，在 Claude Code / Codex CLI / OpenCode 里把 API 地址指向 `http://localhost:8080/v1`，就能用本地 DeepSeek V4 写代码了。
- **用原生 Agent**：`./ds4-agent` 启动一个自带 KV 缓存持久化的本地编码 Agent，比走 API 更快。
- **多机协同**：两台 Mac 各跑一部分模型层，通过局域网协作推理。

## 运行位置

- **本地电脑**：macOS（Metal）、Linux（CUDA）、Windows（通过 WSL）
- 支持 Apple Silicon（M 系列芯片）、NVIDIA GPU、AMD ROCm

## 需要准备什么

- 完全免费开源（MIT 协议）
- 不需要任何 API Key、不需要注册任何账号——完全离线
- 硬件要求较高：推荐 Apple M 系列芯片 + 96GB 以上统一内存（或 NVIDIA GPU + 足够显存）。64GB 内存可以通过 SSD 流式加载勉强跑
- 需要下载模型权重文件（几 GB 到几十 GB，看量化版本）
- 需要 C 编译环境（macOS 上 Xcode 命令行工具即可）

## 配合什么软件

- 独立使用内置的 ds4-server 和 ds4-agent
- 可作为后端配合 Claude Code / Codex CLI / OpenCode / Pi 等 AI 编程工具
- 兼容 OpenAI API 格式，配合任何支持自定义 API 地址的客户端

## 客观评价

**优点**：antirez 出品，代码质量毋庸置疑（Redis 的作者做性能优化的功力是世界顶级）；纯 C 实现，极致轻量高效；M4 Max 上 45-55 tokens/s 的推理速度在本地引擎里算第一梯队；全套工具链（服务端 + Agent + 量化工具）开箱即用；分布式推理功能独特。

**缺点**：目前只支持 DeepSeek V4 系列，不能跑其他模型（但作者在考虑扩展）；硬件要求不低——96GB 内存的 MacBook 不是谁都有的；项目还比较新（2026 年 5 月才发布），社区和文档都还在建设中；纯 C 代码，想贡献代码门槛很高。

**适合谁**：有高性能 Mac（M3/M5 Max 96GB+）的用户、对本地推理有刚需的人、追求极致隐私的用户、想学习推理引擎实现的技术爱好者。**不适合**：硬件不够的用户、只用过 Web 版 ChatGPT 的非技术用户。

**评分 8/10**：技术实力顶尖，但目前受众有限（硬件门槛高）。一旦扩展到支持更多模型（尤其是 Qwen、Gemma 等中文用户常用的），价值会翻倍。

## 未来趋势

项目处于**早期爆发期**——发布一个多月就 1.4 万+ star，antirez 的名人效应加上 DeepSeek V4 的热度推动。本地推理引擎是确定的趋势方向。

6-12 个月内：大概率会扩展支持更多模型（Qwen、Llama 等）、Windows 原生支持、更多社区贡献的优化。

**关注度 5/5**：antirez 的个人品牌 + 技术质量 + 本地推理趋势，即使你现在硬件跑不动也应该关注。

## 更新记录

| 日期 | 变更 | Stars |
|------|------|-------|
| 2026-06-20 | 首次记录 | 14,737 |

---

*记录时间: 2026-06-20*

---

📂 **同类别工具**：[[_索引_AI编程工具|查看 AI编程工具 全部 24 个工具]]

---
## 相关内容

- [[aaif-goose_goose]]
- [[addyosmani_agent-skills]]
- [[affaan-m_ECC]]
- [[Aider-AI_aider]]
- [[anomalyco_opencode]]
