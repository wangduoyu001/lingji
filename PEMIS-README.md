# PEMIS v4 - AI Memory OS / Opportunity Dashboard

## 这是什么？

PEMIS v4 是一个赚钱机会发现系统（Opportunity OS），功能包括：
- **机会发现** — 扫描外网热点 + GitHub 开源项目，自动生成赚钱机会
- **机会评分 (MoneyScore)** — 按需求强度/变现清晰度/竞争/成本综合排序
- **变现路径** — 每个机会生成 3 条路径（快速/中期/长期）
- **语义搜索** — 用自然语言搜索历史机会（bge-m3 + Qdrant）
- **Obsidian Dashboard** — 在 Obsidian 内通过 Dataview 表格查看

## 系统架构

Obsidian Vault -> Snapshot Layer -> Embedding Pipeline -> Qdrant Vector DB -> API

## 快速开始

### 启动系统
双击桌面 **"Start PEMIS AI Memory OS"** 快捷方式，或运行:
  cd D:\codex\obsidian-qdrant-memory && scripts\start.bat

### 打开 Obsidian Vault
1. 打开 Obsidian => 管理仓库 => 打开本地仓库
2. 选择: D:\codex\obsidian-qdrant-memory\vault\
3. 安装 Dataview 社区插件
4. 打开 PEMIS/dashboard/main.md 查看机会看板

## 核心 API
- 语义搜索: POST /v1/search {"query": "赚钱机会", "top_k": 5}
- 系统状态: GET /v1/status
- 获取原文: POST /v1/context {"file": "PEMIS/opportunities/opp_xxx.md"}
- 创建快照: POST /v1/snapshot
- 机会扫描: POST /v1/opportunity/scan
- API文档: http://localhost:8000/docs
- Qdrant管理: http://localhost:6333/dashboard

## 目录
vault/PEMIS/dashboard/main.md = 看板入口
vault/PEMIS/opportunities/   = 赚钱机会 (102个)
vault/PEMIS/status/          = 系统状态

## 定时任务
机会扫描每4h / 蒸馏每24h / 完整性检查每24h

## 系统状态
NORMAL=全开 / DEGRADED=降级 / SAFE_MODE=仅查询 / RECOVERY_MODE=恢复中

## 硬件: RTX 4060 Ti (8GB)