# LingJi（灵机）项目上下文

> 更新日期：2026-07-20
> 当前开发分支：`feature/second-brain-memory`

## 项目定位

LingJi 是一个本地优先的个人 AI 第二大脑与机会决策系统，由两部分组成：

1. **PEMIS v6**：负责内容采集、索引、机会分析、调度与安全降级。
2. **Second Brain**：负责 AI 对话、Codex 任务、Obsidian 知识的结构化存储、记忆蒸馏与检索。

当前工作目录为 `D:\codex\lingji-second-brain`。旧版项目目录 `C:\Users\Administrator\Documents\New project-ai` 仅作历史保留，不允许本分支写入运行数据或修改文件。

## 当前阶段

当前处于 **Local Alpha 前验收阶段**：

- 文档体系已建立。
- Python、API、UI 构建和硬件检测已通过真机验收。
- Second Brain、SQLite、嵌入式 Qdrant、Ollama 模型检测和桌面控制台已实现。
- 下一步优先处理已知轻微问题、桌面打包和记忆闭环体验，不应无计划扩展数据入口。

最新实际状态以 `docs/PROJECT_STATUS.md`、`docs/ROADMAP.md` 和最新测试报告为准。

## 开发前必读顺序

1. `AGENTS.md`
2. `docs/PROJECT_STATUS.md`
3. `docs/ARCHITECTURE.md`
4. `docs/DEVELOPMENT_RULES.md`
5. 与本次任务相关的模块、调研和测试文档

## 核心技术栈

- Python、FastAPI、SQLite
- Embedded Qdrant（可重建向量索引）
- Ollama（本地模型与嵌入模型）
- PySide6（Second Brain 原生桌面界面）
- React、Vite、Tauri（控制中心桌面端）
- Obsidian（正式知识入口与人工管理界面）

## 核心设计原则

- SQLite 保存结构化事实；Qdrant 仅作为可重建的向量检索层。
- Obsidian 内容属于用户正式知识，不得自动蒸馏为个人记忆。
- AI 对话与 Codex 任务可以进入自动记忆流程。
- 监听范围必须有明确白名单，禁止扫描整块磁盘。
- 所有模型、缓存、数据库、日志和临时数据优先放在 D 盘。
- 优先复用现有模块，用最少代码完成需求。
- 开发前先阅读项目，再查官方文档和优秀实现，最后确定方案。
- 不得用大规模重构代替小范围修复。

## 主要目录

| 路径 | 作用 |
|---|---|
| `src/` | PEMIS v6 核心逻辑 |
| `second_brain/` | 第二大脑服务、连接器、记忆与检索 |
| `desktop/` | 控制中心前端与桌面配置 |
| `tests/` | 单元、集成、UI 与验收测试 |
| `scripts/` | 启动、停止、环境和验收脚本 |
| `docs/` | 架构、状态、规则、调研和测试记录 |
| `data/` | 本地运行数据，通常不提交 Git |

## 开发与验收要求

每次开发必须：

1. 检查当前分支、最新提交和工作区状态。
2. 阅读相关代码、测试与文档。
3. 对新增技术先查官方文档和可靠项目。
4. 以最小改动完成任务，并补充相应测试。
5. 保持已有测试不减少，禁止通过删除测试获得通过。
6. 更新 `docs/PROJECT_STATUS.md`、`docs/CHANGELOG.md` 或对应开发记录。
7. 只提交本任务相关文件，不提交 `node_modules`、缓存、密钥、数据库或临时文件。
8. 在真实本地环境完成测试后再宣布验收通过。

## 禁止事项

- 禁止修改旧版项目目录。
- 禁止提交 `.env`、API Key、Token、个人聊天原文和真实数据库。
- 禁止未经批准扩大监听范围或自动发布内容。
- 禁止把未经用户确认的建议写成长期事实或正式决策。
- 禁止编造已实现功能、测试结果、硬件状态或模型兼容性。
