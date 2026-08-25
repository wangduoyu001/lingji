# CHANGELOG.md — LingJi（灵机）项目变更日志

> Format（格式）: `[ISO 日期] 变更说明（作者或参考）`

## 2026-08-25

### SB-0 Work Fact 部分实现与文档事实对齐

- `master` 已加入 WorkStore 的 work/event/pending 读取方法、Capture bridge 正式 `create_work()` 接线，以及 WorkControlService 的 Store → Projector 适配。
- 已加入四个后端合同测试文件，但当前仓库记录没有证明它们已在要求环境实际运行通过。
- 本次文档治理纠正了 `PROJECT_STATUS.md` 和 `CODE_MAP.md` 对已实现子项的过时描述，并明确剩余阻塞。
- 正式 `create_control_app()` 路由注册、LocalControlService 共享 Store、Python/Desktop DTO 与响应合同、Outcome/NextAction/Memory 投影、端到端测试和主人验收仍未完成。
- Phase 1 仍为 `SECOND BRAIN COMPLETION`，Opportunity Center 继续冻结；最近 M5 仍为 `FAIL / DO NOT MERGE`。

## 2026-07-26

### P2-11B Packaged Python runtime Sidecar manager

- 合并 PR #47，将 packaged Python runtime sidecar manager 纳入 `feature/second-brain-memory`。
- 正式合并提交：`6720d0cd76c8ff9e9bc38ef2df52793c0ab0f4c5`。
- 修复 Windows release gate 未安装测试依赖且未检查 pytest 退出码的问题。
- 新增认证的 `GET /api/runtime/ping` 作为 runtime liveness 探针，避免 `/api/health` 的可选诊断耗时影响 sidecar 生命周期判断。
- 本机验收通过：定向 Python 测试、Desktop smoke、Tauri Rust tests、compileall、sidecar build 与真实 packaged exe `/api/runtime/ping` / `/api/health` / stop acceptance。
- GitHub CI：PR #47 合并前全部检查成功。

### P2-12A Observation-first Desktop UI

- Rebase 并合并 PR #48，base 更新为 `feature/second-brain-memory`。
- 正式合并提交：`7e53fc29fb308b73031b39f9a2a000122653674f`。
- Rebase 无冲突；未对 #48 追加非阻塞重构或扩展修复。
- 本机验收通过：`npm run test:smoke`、`npm run build`、Python full unittest、compileall、Obsidian plugin `node --check`、Tauri Rust tests。
- GitHub CI：PR #48 `unit-tests (3.11)`、`unit-tests (3.12)`、`windows-tests`、`desktop-ui-smoke`、`browser-capture-smoke`、`obsidian-plugin-smoke`、`mcp-smoke-test` 全部成功。
- 新增最终验收报告：`docs/TEST_REPORTS/PR47_PR48_FINAL_ACCEPTANCE_REPORT.md`。

## 2026-07-22

### P2-10A Owner-visible Settings Governance Core

- 合并 PR #33，将设置治理代码底座纳入 `feature/second-brain-memory`。
- 正式合并提交：`325ad6e4a5f9d2c21bc4441039f32a28292b0f1d`。
- 增加 `OwnerSettingsRegistry` 与 `CompleteOwnerSettingsRegistry`，由后端统一提供默认值、推荐值、分组、风险、影响和能力状态。
- `Settings` 中存在的字段成为默认值来源，避免兼容 Registry 的历史字面量与真实配置分叉。
- 增加认证接口 `POST /api/settings/preview` 与 `POST /api/settings/commit`。
- 高风险设置必须先预览性能、存储、费用和隐私影响，再提交明确确认；未经确认返回403。
- 增加跨设置校验：自动转写、OCR、镜头检测必须配置相应 Provider；冷存储必须选择目录。
- 增加能力状态与不可用原因；设置页加载不执行耗时的外部 Obsidian CLI 探测。
- 将 `auto_review_mode`、`auto_review_ai_enabled`、`auto_review_timeout_seconds` 纳入主人可见目录。
- Auto Review 模式只暴露 OFF/SHADOW；错误 ACTIVE 默认值回落 OFF，执行层仍拒绝 ACTIVE。
- Desktop 删除重复 `GROUP_LABELS` 与默认值合同，改为消费后端动态分组和元数据。
- 设置页支持全局搜索、只显示已修改、只看高风险、只看不可用、单项恢复、分组恢复和未保存草稿保护。
- 修复恢复单项默认时覆盖其他未保存草稿的问题。
- 只提交真实 dirty values，手动重新加载前会提示未保存修改。
- 新增 `tests/test_settings_governance.py`、`tests/test_settings_governance_api.py` 与 `settings-governance-smoke.mjs`。
- `tests` workflow #709：SUCCESS。
- `P0 Windows Gate` #102：SUCCESS。
- Python 3.11、Python 3.12、Windows 全量测试、14套 Desktop Smoke、React/Vite Build、Tauri Rust Check、MCP、浏览器采集和 Obsidian Plugin 全部通过。
- Issue #11 按 `completed` 关闭。
- 未修改数据库 Schema，未新增设置文件、数据库或第二套配置系统，未执行 rebase、force push 或 master 修改。
- 完整视觉与信息层级重设计尚未开始；P2-10A 只完成其依赖的稳定代码合同。

### P2-08 Auto Review SHADOW 与 P2-09 Runtime/Desktop Reliability

- 合并 PR #24：修复 Brain Status GPU 假零、复用正式遥测服务、区分未知与真实0，并将 Embedding 默认值对齐为 `bge-m3` 主模型与 `nomic-embed-text` 备用模型。
- 保留 Qdrant Collection 维度保护；维度冲突阻止写入、标记 `rebuild_required`，不自动删除或重建生产 Collection。
- 合并 PR #25：增加 `src/extraction/idempotency.py` 作为 Pipeline 和 Queue 的唯一持久幂等算法来源。
- 文件使用内容 SHA-256，目录使用稳定 Manifest，Payload/Options 使用 canonical JSON；CaptureDeduplicator 继续只负责短窗口去重。
- Codex Work Report 与 Web Capture MCP 工具改为默认先进入持久 SQLite Queue；`process_now` 仍先入队再处理。
- 合并 PR #26：增加统一 Desktop Polling Hook，支持 Abort、无重叠、退避、隐藏暂停、stale、手动刷新和旧数据保留。
- 合并 PR #27：增加确定性 Auto Review Core；OFF/SHADOW 可用，ACTIVE 仅保留枚举并在实现层拒绝。
- Core、删除/遗忘、权限隐私、restricted、跨项目、冲突、证据不足、未验证开发报告和主人编辑保持强制人工审核。
- 合并 PR #28：增加本地 loopback Ollama Reviewer、严格 JSON、模型角色主备回退、8766 SHADOW API、决策查询、Metrics、Feedback 与 Audit Verify。
- 本地 AI 只允许增加风险，不得降低硬规则风险或改变确定性动作；不请求或存储私有思维链。
- 合并 PR #29：Desktop 整理为五组导航，连接栏可折叠，Overview 展示真实状态，增加 Auto Review SHADOW 看板。
- SHADOW 看板没有 approve、reject、delete、execute 或 ACTIVE 控件；人工 Memory Review 继续是唯一主人确认入口。
- 合并 PR #30：增加 P2-08/P2-09 跨模块集成测试和最终集成报告。
- 最终正式功能分支提交：`9efda7a9a976d20596dbdabda5741a5c54180954`。
- `tests` workflow #696：SUCCESS。
- `P0 Windows Gate` #94：SUCCESS。
- Python 3.11、Python 3.12、Windows 全量测试、Desktop Smoke、React/Vite Build、Tauri Rust Check、MCP、浏览器采集和 Obsidian Plugin 全部通过。
- 未修改数据库 Schema；未新增第二套队列、生命周期或审计数据库；未执行 rebase、force push 或 master 修改。
- 2026-07-22，项目主人确认 RTX 4060、Ollama、Qdrant、8766 与 Tauri 本机验收已经完成。
- 本机验收按主人现场确认记录；仓库未附加新的逐项命令、原始日志、耗时或硬件数值，因此不补造未提供的细节。
- P2-08 与 P2-09 状态更新为 `MERGED_AND_VALIDATED`，Issue #23 按 `completed` 关闭。

## 2026-07-21

### P2-06 Obsidian CLI 正式迁移

- 将 Obsidian CLI 单一实现迁入 `src/obsidian/`，按 models、discovery、config、client、service 分层。
- 保留既有 `management.py` 和 `system_ui.py`，未复制第二套 Vault 管理能力。
- 将 `second_brain/obsidian_cli.py` 降为兼容转发，删除约400行重复命令实现。
- 增加 Runtime Settings 的启用、CLI/Vault 路径、Vault 名称、超时和 Dry Run。
- 增加认证的8766 Obsidian状态、配置草稿校验和刷新接口。
- 增加 Tauri Obsidian 页面、官方 Dialog Plugin 路径选择和独立 Smoke Test。
- 状态 API 不返回原始 CLI/Vault 绝对路径；Client 拒绝绝对路径和 `..` 越界。
- Linux Python 3.12：`405 passed, 11 skipped, 0 failed`，10.31秒。
- Windows Python 3.12：`405 passed, 11 skipped, 0 failed`，71.77秒。
- `npm ci`、Obsidian Smoke、全部 Desktop Smoke、Build 和 `cargo check` 通过。
- 已验证实现提交：`4b0ad577eb396030ee6baa5c3bb217e990385475`；最终已验证 HEAD：`6dfa31148585e2cb78c83af52b752550962820c9`。
- 正式合并提交：`5ce10ed8be98784f57e8723ffc27e40e3abaffbc`。
- 未访问生产 Vault、SQLite、Qdrant 或 Ollama；未修改数据库 Schema；未新增监听、手机端或浏览器扩展。

### P2-05 Manual Capture Center 集成验证

- 按 `P2-05B -> P2-05A -> P2-05C` 顺序合入 `work/p2-05-integrated-validation`。
- 增加手动文本、网页、支持文件、媒体、ChatGPT Export 和 Codex Report 入口。
- 增加持久化 Capture Mode、Queue 分页、取消、重试、暂停和恢复。
- 增加脱敏 CaptureJob DTO、稳定错误码和 Capture Audit Event。
- 增加 Tauri Capture Center、官方 Dialog Plugin、任务操作和 Memory Inspector 跳转。
- 真实生成并锁定 npm 与 Cargo 依赖文件。
- 将临时 `_api_core.py` 和 `_queue_core.py` 折回正式模块并删除。
- 修复 Windows SQLite 测试连接泄漏、Windows Vault 路径跨平台解析和 CPU 平台模拟测试。
- Windows Python 3.12 最终全仓结果：`398 passed, 11 skipped, 0 failed`，持续79.40秒。
- `npm ci`、Capture Smoke、7项 Desktop Smoke、TypeScript/Vite Build 和 `cargo check` 全部通过。
- 已验证集成树：`1bf95b8d16a9daea52b60518f0e920a0c0bd50db`。
- 正式合并提交：`c77e78c0f71339264d54fc083dbc5cfabcfaa173`。
- 未访问生产 Vault、SQLite、Qdrant 或 Ollama；未修改数据库 Schema；未开发监听、手机端或浏览器插件。

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
- Windows CI 最终结果：`359 passed, 11 skipped, 0 failed`，持续63.24秒。
- Python 依赖安装、`pip check`、clean-install validator、完整 `compileall` 全部通过。
- `npm ci`、Desktop Smoke Test、`npm run build` 全部通过。
- 历史 `306 passed / 19 failed / 13 skipped` 的19项失败全部关闭。
- 新增 `docs/TEST_REPORTS/P0_FINAL_VALIDATION_REPORT.md`，以 post-fix Windows CI 结果作为最终验收权威。
- 通用 `.github/workflows/tests.yml` 改为安装测试/MCP依赖、使用 pytest、执行完整 compileall，并将 Desktop CI 收口为 `npm ci + test:smoke + build`。
- 关闭 P0 Issue #9，并将 P2-05A、P2-05B、P2-05C 三条分支移动到同一正式基线。
- 未访问生产 Vault、SQLite、Qdrant、Ollama，未修改数据库 Schema，未执行 force push。

### P2-03 → P2-04 正式集成

- 将 `work/p2-04-integrated-validation` 以安全 fast-forward 方式合入正式分支 `feature/second-brain-memory`。
- 合并 P2-03 Structured Read Model，建立 Source、Conversation、Message 派生读取模型、权限继承、稳定 ID、幂等写入和只读关联查询。
- 合并 P2-03B Structured Ingestion Wiring，将 Adapter、Vault、Memory、Structured Read Model 和 Audit Event 接入正式采集链路。
- 合并 P2-03C Capture Sources Foundation，增加统一 Capture 模型、低功耗策略、两阶段去重、隐私检查和 Codex/Web/Media 结构化回退。
- 合并 P2-04 Memory Inspector Desktop UI，支持 Source、Conversation、Message、Memory、Chunk 和 Vector 真实关系查看。
- 修复 Vector Provider 和 Snapshot 错误路径泄漏，对外只返回稳定摘要。
- 修复 Capture 去重失败污染、Message 独立 Memory Link、嵌套敏感 Metadata 和保留字段覆盖问题。
- 修复 Memory Inspector Query 参数、嵌套状态、Message→Memory、Vector、Citation 和 Chunk Count 合同。
- 恢复 TypeScript 构建门禁，锁定 `tsx 4.23.1`，`tsc -b`、6套 Smoke Test 和 `npm run build` 全部通过。
- P2-03 → P2-04 最终里程碑门禁：`91 passed, 0 failed, 0 skipped`。
- 遗漏历史回归补充验证：`20 passed, 0 failed`。
- 当时全仓库 pytest 记录为 `306 passed, 19 environment-specific failures, 13 skipped`；这些失败已在同日 P0 Engineering Hygiene 中全部关闭。
- 正式数据和生产 Qdrant、Ollama、Vault、SQLite 均未访问或修改。
- 用户明确暂缓系统监听、剪贴板监听、文件夹监听、手机分享客户端和浏览器插件；下一阶段转向 P2-05 Manual Capture Center。

## 2026-07-20

### P2 合并与验证

- 合并并验证 P2-01 Vector Center 到 `feature/second-brain-memory`。
- 在 Tauri 控制中心增加 Memory Index、Embedding Provider、Qdrant 和 Vector Coverage 只读状态页。
- P2-01 本机汇总：5项 Smoke Test 通过，`npm run build` 通过。
- 合并并验证 P2-02 Collection Migration。
- 增加独立候选 Collection 构建、模型与维度检查、精确向量计数、100%覆盖率验证、Activation Settings、Rollback Settings 和 Atomic Manifest。
- P2-02 本机汇总：8/8重点单元测试通过，真实 `bge-m3` 隔离验收覆盖率100%。
- 正式生产 `bge-m3` Collection 构建和生产模型切换仍未执行。
- 最新本机测试汇总记录为 `223 passed, 0 failed, 8 skipped`。
- 记录测试质量债务：旧 PySide6 桌面测试按依赖跳过；启动文件测试仍需改成 Semantic Startup Contract Test；测试数量差异尚未核对。
- 新增 `docs/FINAL_P2_MERGE_REPORT.md`。
- 新增 `docs/DOCUMENTATION_MAINTENANCE.md`，建立 Documentation Contract、明确更新时间点、状态词、术语解释和低积分执行规则。
- 刷新 `docs/PROJECT_STATUS.md` 和 P2-01/P2-02 测试报告，使文档与正式分支状态一致。

### P1 统一语义记忆

- 完成提交 `9ab3c55074b0e56dac9ac8adccba934627bedd90` 的真实 Windows P1-05 验收。
- 验证 Ollama 0.32.0 与 `bge-m3`，实际密集向量维度为1024。
- 验证 Qdrant in-memory 和 temporary embedded disk，覆盖率为2/2。
- 验证 `/api/memory/status`、`/api/vector/status`、`/api/vector/coverage` 和 `/api/brain/status` 真实数据。
- P1-05 原始全仓库结果记录为 `244 passed, 2 known pre-existing failures, 9 optional skips`。
- 增加 `docs/TEST_REPORTS/P1_05_LOCAL_ACCEPTANCE_SUMMARY.md`。
- 将兼容层 Ollama Embedding 行为迁移到 `src/model_center/embedding.py`。
- 将 Qdrant 搜索、索引和诊断能力迁移到 `src/retrieval/qdrant_provider.py`。
- 增加 `MemoryIndexCoordinator`，实现 lexical-first 和 semantic-degraded-safe 同步。
- 将 Embedding、Qdrant、HybridRetriever 和 MemoryIndexCoordinator 接入正式 MemoryGateway 运行链路。
- 增加 `MemoryStatisticsService` 与 Workspace 状态快照。
- 在8766 Local Control API增加认证状态接口。
- 修复 Brain Status 未知数量被显示成假零的问题。
- 将 MCP 写入文档接入统一词法与向量索引流程。
- 增加 Production/Acceptance Workspace 隔离合同。

### 工具与兼容层

- 修复 `conftest.py` 环境变量转义。
- 增加 Obsidian CLI 抽象层。
- 增加 LingJi Tools 统一工具服务层。
- 增加 E2E Brain Status 验收测试。
- 增加相关单元测试和测试报告。

## 2026-07-19

- 增加 Obsidian CLI 集成测试，包括编码、超时、Dry Run 和安全检查。
- 增加 LingJiTools 服务层及单元测试。
- 增加工具服务和 Obsidian CLI 审计文档。

## 2026-07-16

- 增加原生 PySide6 Windows 桌面控制台，当前已降为 Compatibility UI。
- 增加 Production/Acceptance 双 Workspace 隔离。
- 增加桌面验收自动化。
- 增加独立 API 和 Watcher 启动控制。
- 桌面默认使用 Acceptance Workspace；无请求头 API 保持 Production 行为。
- Second Brain 开发前创建升级备份。

## 2026-07-15

- 在 `feature/second-brain-memory` 上增加隔离的 Second Brain 记忆服务。
- 增加 Embedded Qdrant，无需 Docker。
- 增加 Source、Conversation、Message、Memory 和 Knowledge Document 的 SQLite Schema。
- 增加 `127.0.0.1:8765` FastAPI 健康和记忆接口。
- 增加有边界的三目录 Watcher。
- 增加 Ollama Embedding，`bge-m3` 为主模型，`nomic-embed-text` 为备用模型。
- 增加 `AGENTS.md` 和磁盘安全规则。
- 从上游 `lingji.git` master 分支建立初始 Worktree。
