# CHANGELOG.md — LingJi（灵机）项目变更日志

> Format（格式）: `[ISO 日期] 变更说明（作者或参考）`

## 2026-07-21

### P0 Engineering Hygiene 正式合并

- 通过 PR #12 将 `work/p0-engineering-hygiene` 正常合并到 `feature/second-brain-memory`。
- P0 正式 merge commit：`d2a605e463552cb982342bdb2376da8aad1b36b5`。
- 删除 `src/config.py` 中机器专属 `D:/codex/backups/pemis` 默认值，未配置时统一使用 `<storage_path>/backups`。
- Obsidian CLI 改为环境变量、PATH 和平台标准目录探测，补充 `%LOCALAPPDATA%\Programs\Obsidian`。
- Vault 名称改为 `OBSIDIAN_VAULT_NAME -> Vault 目录名 -> 兼容默认值`。
- 建立核心、UI、媒体、MCP、测试依赖所有权。
- 增加 `constraints/python-3.12-windows.txt` 和 `constraints/python-3.13-linux.txt`。
- 新增 `scripts/validate_clean_install.py`，检查依赖归属、精确约束、敏感源、本机路径和前端锁文件。
- 删除启动文件逐字源码比较测试，改为 AST、Settings、main guard 和端口所有权合同测试。
- 增加 Windows 测试专用 Workspace 临时根 Fixture，同时保留生产 `C:\` 系统盘拒绝保护。
- Qdrant 单元测试改为确定性的 in-memory 合同，不依赖生产 Qdrant Server。
- Brain Status API 测试改为 FastAPI 应用级合同，不再通过真实端口和 `nvidia-smi` 超时碰运气。
- 新增 `.github/workflows/p0-windows-gate.yml`，自动执行 Windows Python 3.12 和 Desktop 门禁。
- Windows CI 最终结果：`359 passed, 11 skipped, 0 failed`，持续 63.24 秒。
- Python 依赖安装、`pip check`、clean-install validator、完整 `compileall` 全部通过。
- `npm ci`、Desktop Smoke Test、`npm run build` 全部通过。
- 历史 `306 passed / 19 failed / 13 skipped` 的19项失败全部关闭。
- 未访问生产 Vault、SQLite、Qdrant、Ollama，未修改数据库 Schema，未执行 rebase 或 force push。

### P2-03 → P2-04 正式集成

- 将 `work/p2-04-integrated-validation` 以安全 fast-forward 方式合入正式分支 `feature/second-brain-memory`。
- 合并 P2-03 Structured Read Model（结构化读取模型），建立 Source、Conversation、Message 派生读取模型、权限继承、稳定 ID、幂等写入和只读关联查询。
- 合并 P2-03B Structured Ingestion Wiring（结构化采集接线），将 Adapter、Vault、Memory、Structured Read Model 和 Audit Event 接入正式采集链路。
- 合并 P2-03C Capture Sources Foundation（信息入口基础框架），增加统一 Capture 模型、低功耗策略、两阶段去重、隐私检查和 Codex/Web/Media 结构化回退。
- 合并 P2-04 Memory Inspector Desktop UI（记忆检查器桌面界面），支持 Source、Conversation、Message、Memory、Chunk 和 Vector 真实关系查看。
- 修复 Vector Provider 和 Snapshot 错误路径泄漏，对外只返回稳定摘要。
- 修复 Capture 去重失败污染、Message 独立 Memory Link、嵌套敏感 Metadata 和保留字段覆盖问题。
- 修复 Memory Inspector Query 参数、嵌套状态、Message→Memory、Vector、Citation 和 Chunk Count 合同。
- 恢复 TypeScript 构建门禁，锁定 `tsx 4.23.1`，`tsc -b`、6 套 Smoke Test 和 `npm run build` 全部通过。
- P2-03 → P2-04 最终里程碑门禁：`91 passed, 0 failed, 0 skipped`。
- 遗漏历史回归补充验证：`20 passed, 0 failed`。
- 当时全仓库 pytest 记录为 `306 passed, 19 environment-specific failures, 13 skipped`；这些失败已在同日 P0 Engineering Hygiene 中全部关闭。
- 正式数据和生产 Qdrant、Ollama、Vault、SQLite 均未访问或修改。
- 用户明确暂缓系统监听、剪贴板监听、文件夹监听、手机分享客户端和浏览器插件；下一阶段转向 P2-05 Manual Capture Center（手动信息入口中心）。

## 2026-07-20

### P2 合并与验证

- 合并并验证 P2-01 Vector Center（向量中心）到 `feature/second-brain-memory`。
- 在 Tauri（跨平台桌面应用框架）控制中心增加 Memory Index（记忆索引）、Embedding Provider（向量嵌入提供器）、Qdrant（向量数据库）和 Vector Coverage（向量覆盖率）只读状态页。
- P2-01 本机汇总：5 项 Smoke Test（冒烟测试）通过，`npm run build` 通过。
- 合并并验证 P2-02 Collection Migration（向量集合迁移工具）。
- 增加独立候选 Collection 构建、模型与维度检查、精确向量计数、100% 覆盖率验证、Activation Settings（激活设置）、Rollback Settings（回滚设置）和 Atomic Manifest（原子迁移清单）。
- P2-02 本机汇总：8/8 重点单元测试通过，真实 `bge-m3` 隔离验收覆盖率 100%。
- 正式生产 `bge-m3` Collection 构建和生产模型切换仍未执行。
- 最新本机测试汇总记录为 `223 passed, 0 failed, 8 skipped`。
- 记录测试质量债务：旧 PySide6 桌面测试按依赖跳过；启动文件测试仍需改成 Semantic Startup Contract Test（语义启动合同测试）；测试数量差异尚未核对。
- 新增 `docs/FINAL_P2_MERGE_REPORT.md`。
- 新增 `docs/DOCUMENTATION_MAINTENANCE.md`，建立 Documentation Contract（文档维护合同）、明确更新时间点、状态词、术语解释和低积分执行规则。
- 刷新 `docs/PROJECT_STATUS.md` 和 P2-01/P2-02 测试报告，使文档与正式分支状态一致。

### P1 统一语义记忆

- 完成提交 `9ab3c55074b0e56dac9ac8adccba934627bedd90` 的真实 Windows P1-05 验收。
- 验证 Ollama 0.32.0 与 `bge-m3`，实际密集向量维度为 1024。
- 验证 Qdrant in-memory（内存模式）和 temporary embedded disk（临时嵌入式磁盘模式），覆盖率为 2/2。
- 验证 `/api/memory/status`、`/api/vector/status`、`/api/vector/coverage` 和 `/api/brain/status` 真实数据。
- P1-05 原始全仓库结果记录为 `244 passed, 2 known pre-existing failures, 9 optional skips`。
- 增加 `docs/TEST_REPORTS/P1_05_LOCAL_ACCEPTANCE_SUMMARY.md`。
- 将兼容层 Ollama Embedding（向量嵌入）行为迁移到 `src/model_center/embedding.py`。
- 将 Qdrant 搜索、索引和诊断能力迁移到 `src/retrieval/qdrant_provider.py`。
- 增加 `MemoryIndexCoordinator`，实现 lexical-first（词法优先）和 semantic-degraded-safe（语义降级安全）同步。
- 将 Embedding、Qdrant、HybridRetriever 和 MemoryIndexCoordinator 接入正式 MemoryGateway 运行链路。
- 增加 `MemoryStatisticsService` 与 Workspace（工作区）状态快照。
- 在 8766 Local Control API（本地控制接口）增加认证状态接口。
- 修复 Brain Status 未知数量被显示成假零的问题。
- 将 MCP 写入文档接入统一词法与向量索引流程。
- 增加 Production/Acceptance Workspace（生产与验收工作区）隔离合同。

### 工具与兼容层

- 修复 `conftest.py` 环境变量转义。
- 增加 Obsidian CLI（命令行接口）抽象层。
- 增加 LingJi Tools 统一工具服务层。
- 增加 E2E（端到端）Brain Status 验收测试。
- 增加相关单元测试和测试报告。

## 2026-07-19

- 增加 Obsidian CLI 集成测试，包括编码、超时、Dry Run（试运行）和安全检查。
- 增加 LingJiTools 服务层及单元测试。
- 增加工具服务和 Obsidian CLI 审计文档。

## 2026-07-16

- 增加原生 PySide6 Windows 桌面控制台，当前已降为 Compatibility UI（兼容界面）。
- 增加 Production/Acceptance 双 Workspace 隔离。
- 增加桌面验收自动化。
- 增加独立 API 和 Watcher（监听器）启动控制。
- 桌面默认使用 Acceptance Workspace；无请求头 API 保持 Production 行为。
- Second Brain 开发前创建升级备份。

## 2026-07-15

- 在 `feature/second-brain-memory` 上增加隔离的 Second Brain 记忆服务。
- 增加 Embedded Qdrant（嵌入式向量数据库），无需 Docker。
- 增加 Source、Conversation、Message、Memory 和 Knowledge Document 的 SQLite Schema（数据库结构）。
- 增加 `127.0.0.1:8765` FastAPI（接口服务）健康和记忆接口。
- 增加有边界的三目录 Watcher。
- 增加 Ollama Embedding，`bge-m3` 为主模型，`nomic-embed-text` 为备用模型。
- 增加 `AGENTS.md` 和磁盘安全规则。
- 从上游 `lingji.git` master 分支建立初始 Worktree（独立工作树）。
