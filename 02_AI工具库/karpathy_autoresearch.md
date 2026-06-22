---
title: "AutoResearch"
date: 2026-06-21
github: https://github.com/karpathy/autoresearch
stars: 87823
category: AI编程工具
interest: 2
status: 未试
usable: 待评估
实际用途: AI 自动化科研实验工具
tags:
  - AI工具
  - GitHub
  - AI项目
  - AI研究
  - 编程工具
---

# AutoResearch

> ⭐ 87,823 | 📅 2026-06-21 | [GitHub](https://github.com/karpathy/autoresearch)
>
> 💡 **怎么标记**：改上面 `interest` 数字 → 3=必装 2=想试 1=观望 0=跳过 → 改完按 Ctrl+S 保存

## 干什么
AutoResearch 是 AI 大神 Karpathy（前特斯拉 AI总监、OpenAI联合创始人）的新项目，核心想法特别酷：让 AI Agent 自己做 AI 研究。你给它一个小型 LLM 训练代码，它自己改代码、跑5分钟训练、看结果有没有变好、保留好的改动、扔掉差的改动，然后继续循环。你睡觉前启动它，早上起来就看到一堆实验记录，模型可能变好了。就像你雇了一个研究生，他不眠不休地做实验，你只用看最终报告。没它之前，调模型超参数你得自己一个一个试，可能试一周都不一定找到最优方案；现在 AI 自己试，一晚上能跑约100次实验。

## 能实现什么效果
启动之后，AI Agent 自动修改 `train.py`（模型架构、超参数、优化器、batch size 都改），每次固定跑5分钟，看验证集指标有没有改善。大约每小时能跑12次实验，睡觉8小时≈100次实验。最终产出是一个经过自动优化的模型和详细的实验日志。如果你想用 Claude Code 或 Codex 来做这个事，直接让 Agent 读 `program.md` 然后开始工作就行。这是"AI 研究自动化"的起点——让 AI 自己做以前人类研究者做的事。

## 怎么用
1. **调参实验**：有个模型想优化 → 启动 AutoResearch → 让 Claude/Codex 读 `program.md` → 睡觉 → 早上看100次实验的结果和最优配置
2. **学习训练原理**：想了解 LLM 训练怎么回事 → 自己手动跑一次 `uv run train.py` → 看训练过程 → 理解 val_bpb 等核心指标
3. **小设备实验**：用 MacBook 或小 GPU → 参考 README 里的调参建议（降低 vocab_size、减小 DEPTH、用 TinyStories 数据集）→ 在小设备上也能跑自动实验
4. **定制研究流程**：修改 `program.md` → 定义你的研究策略 → 让 Agent 按你的思路做实验 → 自己迭代研究方法论

## 运行位置
本地电脑运行，需要 NVIDIA GPU（官方测试用 H100）。有 Mac/Windows/AMD 的 fork 版本可以用。Python 环境，需要 PyTorch。

## 需要准备什么
① 完全免费，MIT 许可证。② 不需要注册账号。③ 不需要 API Key（训练部分），但如果用 Claude/Codex 做 Agent 就需要对应的 API Key。④ 需要 NVIDIA GPU，最好 8GB+ 显存（H100 最佳，RTX 4060 Ti 8GB 可以跑小模型版本）。⑤ 需要装 Python 3.10+、PyTorch、uv（Python项目管理工具）。

## 配合什么软件
配合 Claude Code、Codex CLI 等 AI 编程工具——Agent 的"大脑"就是这些工具。也可以配合 Ollama 本地模型。训练代码基于 Karpathy 的 nanochat 项目。

## 客观评价
优点：① Karpathy 出品，AI 领域最具影响力的人物之一，项目质量有保障；② 概念颠覆性——AI 自己做 AI 研究，这是未来方向；③ 极简设计，只有3个核心文件，容易理解；④ 一晚上100次实验的效率人类做不到。缺点：① 需要 NVIDIA GPU，没 GPU 就跑不了（Mac 有 fork 但效果打折）；② 目前只支持单 GPU，不支持分布式训练；③ 训练5分钟时间预算意味着小设备每次实验跑得慢、总实验次数少；④ val_bpb 指标对不同平台不可比——你跑的结果和 Karpathy 的结果不能直接比较；⑤ Agent 修改代码有时会搞出语法错误，需要人工监督。适合：有 GPU、想玩 AI 研究、对 LLM 训练好奇的人。不适合：没有 GPU 的人、不想折腾环境的人。我打 **7/10**——概念极其酷，Karpathy 加持，但硬件门槛限制了很多人。

## 未来趋势
① 项目处于概念验证阶段，3个月就8.7万星说明关注度极高；② 6-12个月内可能会有更多平台支持（CPU/MPS/AMD）、分布式训练版本、更完善的 program.md 模板；③ 关注度 **5/5**——"AI做AI研究"是2026年最热门的概念之一，这个项目是起点。

## 更新记录

| 日期 | 变更 | Stars |
|------|------|-------|
| 2026-06-21 | 馮次记录 | 87,823 |

---

*记录时间: 2026-06-21*

---

📂 **同类别工具**：[[_索引_AI编程工具|查看 AI编程工具 全部 24 个工具]]

---
## 相关内容

- [[aaif-goose_goose]]
- [[addyosmani_agent-skills]]
- [[affaan-m_ECC]]
- [[Aider-AI_aider]]
- [[anomalyco_opencode]]
