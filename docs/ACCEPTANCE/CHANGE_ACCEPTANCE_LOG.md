# 验收要求变更记录

## 2026-08-02 · PR #60 · read-only installer directory cleanup recovery

- Product branch: `codex/pr60-cleanup-readonly-dir-623d3c9d`
- Product commit: `pending (local final-closeout cleanup repair)`
- Affected modules: task-scoped acceptance cleanup execution and Windows installer-profile cleanup regression coverage.
- Risk level: P0
- User-visible change: final acceptance cleanup completes when NSIS has left an empty Start Menu directory with the Windows read-only attribute.
- Data and security boundary: the existing exact task-id/root/one-direct-child authorization remains unchanged; reparse points are still not traversed or chmod-followed.

### Automated acceptance

- [x] `python -m pytest -q tests/test_cleanup_acceptance_workspace.py`: `13 passed`; an authorized task root containing a read-only installer directory is fully removed, while unrelated targets remain protected.
- [ ] `python -m pytest -q --tb=short`, Desktop smoke/build, Rust/Tauri, and unified release validation.

### Real-machine acceptance

- [ ] Use the repaired script on the exact partially cleaned `PR60-MEMORY-TRIAL-05376996` root: dry-run authorized; execute completes; old root absent; new `623d3c9d` task root preserved.

### Regression items

- [ ] Only normal directories receive writable attributes immediately before `os.rmdir`; reparse/link handling remains separate.
- [ ] No wildcard, parent-root, neighbor, production, Vault, or unknown-worktree deletion is authorized.

### Out of scope

- No runtime, UI, import, memory, Qdrant, installer, or owner-data behavior change.

## 2026-08-02 · PR #60 · fresh Day 0 generated-scaffold truth recovery

- Product branch: `codex/pr60-vector-snapshot-truth-05376996`
- Product commit: `d82f23517eb537473f141955173aba82d26f1ddc` (integrated local release-validation commit)
- Affected modules: single-Vault retrieval eligibility, fresh memory-gateway bootstrap, and MCP-published empty-store status.
- Risk level: P0
- User-visible change: a newly created LingJi DataRoot no longer reports generated permanent-memory UI scaffolding as owner knowledge, Core Memory, or healthy semantic vectors before any authorized import.
- Data and security boundary: generated dashboards and templates remain available in Obsidian, while only owner/imported knowledge enters the rebuildable lexical and semantic indexes; no real owner content is read by this repair.

### Automated acceptance

- [x] `python -m pytest -q tests/test_vault_layout.py tests/test_semantic_runtime_wiring.py tests/test_permanent_memory_gateway.py` (18 passed): generated permanent-memory UI files exist but are excluded from retrieval, an owner-created System rule remains indexable, and a fresh gateway publishes 0 documents/chunks/vectors with `collection_empty` truth.
- [x] `python -m pytest -q --tb=short` (623 passed, 10 skipped, 3 subtests passed before the acceptance-contract merge; combined tree passed again inside unified release validation): complete Python regression suite.
- [x] `python scripts/check_acceptance_sync.py`: product changes carry the incremental acceptance contract. Final handoff check remains part of the exact committed release tree.
- [x] `npm ci --no-audit --no-fund`, `npm run test:smoke` (22 scripts), and `npm run build` in `desktop/lingji-control`.
- [x] `scripts/validate.ps1 -Mode release` on integrated commit `d82f23517eb537473f141955173aba82d26f1ddc`: all 15 suites passed, including clean install, full Python, Desktop smoke/build, Rust/Tauri, Sidecar, NSIS, and Windows package generation; summary and package metadata both reread the exact commit.

### Real-machine acceptance

- [ ] Build a new Windows Artifact from the merged repair Head, delete only the named task root with the product cleanup utility, and repeat a fresh locked acceptance Day 0.
- [ ] Before any fixture or authorization, authenticated API and packaged UI both report 0 documents, 0 chunks, 0 Core Memory, and 0 vectors; lexical remains available and semantic reports `empty / collection_empty`.
- [ ] After owner-authorized synthetic import, the MCP-owned index transitions to a coherent non-empty state without a second Qdrant owner.

### Regression items

- [x] `00-System/Permanent-Memory.md` and everything under `00-System/Templates` are excluded by the authoritative retrieval eligibility rule.
- [x] `00-System/Rules` and formal knowledge/Core Memory paths remain indexable in regression coverage.
- [x] Permanent-memory dashboard, Base, and template files remain generated for owner operation.

### Out of scope

- No automatic permanent-memory approval, real owner-data read, external AI-client mutation, or second memory/index implementation.

## 2026-08-02 · PR #60 · exact release Git identity recovery

- Product branch: `codex/pr60-validation-git-identity-05376996`
- Product commit: `4e6d25cc63800e290cdea1bc5e41e51a5bc200ec` (validated code commit)
- Affected modules: unified local validation entrypoint, release metadata, and validation regression coverage.
- Risk level: P0
- User-visible change: local Windows release summaries and package metadata identify the exact repair commit and branch instead of `unknown`.
- Data and security boundary: no owner data or runtime path changes; only repository identity collection before validation is affected.

### Automated acceptance

- [x] `python -m pytest -q tests/test_validation_git_identity.py tests/test_acceptance_sync.py tests/test_local_execution_handoff.py` (33 passed): stale PowerShell native exit state cannot hide a successful Git identity read.
- [x] `python -m pytest -q --tb=short`: complete Python suite passed inside unified release validation.
- [x] Desktop smoke/build and Rust/Tauri tests passed inside unified release validation.
- [x] `scripts/validate.ps1 -Mode release`: all 15 suites passed; `latest-summary.json` and `build-metadata.json` both contain exact commit `4e6d25cc63800e290cdea1bc5e41e51a5bc200ec`, never `unknown`.

### Real-machine acceptance

- [x] Built one local Windows release with PyInstaller 6.21.0 in the task-owned D-drive venv; summary/package identity and installer, portable, manifest, metadata, and Sidecar hashes were independently reread.

### Regression items

- [x] Capture `$LASTEXITCODE` immediately after native Git execution, before any PowerShell pipeline command can change it.
- [x] Git absence or a real nonzero Git exit still returns the explicit fallback.

### Out of scope

- No product runtime, UI, memory, Qdrant, import, owner data, or release publishing change.

## 2026-08-02 · PR #60 · Control-only Qdrant ownership recovery

- Product branch: `feature/unified-ai-memory-connectors`
- Product commit: `pending (second-owner recovery branch)`
- Affected modules: Control API Codex/project runtime wiring and the MCP-owned embedded semantic index boundary.
- Risk level: P0
- User-visible change: opening LingJi’s start and activity views no longer competes with the managed MCP runtime for the embedded vector store.
- Data and security boundary: Control routes retain SQLite/Vault lexical access and only consume the MCP-published vector status; only the MCP process may open embedded Qdrant.

### Automated acceptance

- [x] `python -m pytest -q tests/test_p2_07_integration_wiring.py tests/test_packaged_control_api.py tests/test_mcp_http_auth.py tests/test_mcp_server.py tests/test_assistant_hub_imports.py tests/test_assistant_hub_api.py` (45 passed): verifies the Control project gateway explicitly disables semantic runtime while packaged MCP remains the queue and semantic owner.
- [x] `python -m pytest -q --tb=short` (621 passed, 10 skipped): validates the complete cross-platform suite.
- [x] `python scripts/check_acceptance_sync.py`

### Real-machine acceptance

- [ ] A newly built isolated Artifact starts the Desktop start page, imports one authorized synthetic ChatGPT export, and proves the MCP-published snapshot reaches a coherent post-import vector state without `embedded_store_locked`.

### Regression items

- [ ] `/api/codex/current` must not instantiate a second embedded Qdrant client.
- [ ] Control API must keep reporting the MCP-published snapshot rather than live-opening Qdrant.

### Out of scope

- No real owner data, external AI-client configuration, or automatic Core Memory approval.

## 2026-08-02 · PR #60 · MCP-owned packaged extraction recovery

- Product branch: `feature/unified-ai-memory-connectors`
- Product commit: `pending (qdrant-owner recovery branch)`
- Affected modules: packaged MCP runtime, durable extraction worker, and MCP extraction pipeline.
- Risk level: P0
- User-visible change: authorized imports keep processing automatically while the MCP process remains the single semantic-index owner.
- Data and security boundary: only the MCP process opens the embedded Qdrant path; Control API continues reading the published snapshot.

### Automated acceptance

- [x] `python -m pytest -q tests/test_p2_07_integration_wiring.py tests/test_packaged_control_api.py tests/test_mcp_http_auth.py tests/test_mcp_server.py tests/test_assistant_hub_imports.py tests/test_assistant_hub_api.py` (44 passed): verifies the MCP worker remains in its semantic owner process while the standard MCP server keeps its direct-stdio pipeline contract.
- [x] `python -m pytest -q --tb=short` (620 passed, 10 skipped): verifies the complete cross-platform unit suite after the ownership change.
- [x] `python scripts/check_acceptance_sync.py`

### Real-machine acceptance

- [ ] A new isolated Artifact imports one synthetic export and proves queue completion, a healthy MCP snapshot, and no embedded-store lock.

### Regression items

- [x] Parent Sidecar must not start a second extraction worker.
- [x] Direct stdio MCP retains its existing pipeline construction and skill-registry layout.
- [ ] MCP worker must stop with its owner process and preserve queue completion semantics on the new Artifact.

### Out of scope

- No real owner data, external AI-client configuration, or automatic Core Memory approval.

## 2026-08-02 · PR #60 · autonomous import recovery release

- Product branch: `feature/unified-ai-memory-connectors`
- Product commit: `pending (release-repair branch)`
- Affected modules: packaged Sidecar extraction worker, isolated Assistant Hub environment, and task-scoped cleanup policy.
- Risk level: P0
- User-visible change: an authorized supported export is processed by the packaged runtime instead of remaining indefinitely queued; automatic scans stay within the declared isolated profile.
- Data and security boundary: no real content is read before authorization; empty fixture environments do not inherit owner configuration; cleanup remains limited to one named task root.

### Automated acceptance

- [x] `python -m pytest -q tests/test_packaged_control_api.py tests/test_assistant_hub_imports.py tests/test_assistant_hub_discovery.py tests/test_cleanup_acceptance_workspace.py tests/test_assistant_hub_api.py tests/test_ai_memory_connectors.py tests/test_ai_connector_readiness.py tests/test_executable_resolution.py` (60 passed)
- [x] `python scripts/check_acceptance_sync.py`
- [x] `npm run test:smoke` (22 passed) and `npm run build` in `desktop/lingji-control`

### Real-machine acceptance

- [ ] A newly built isolated Artifact repeats Day 0 with a synthetic export and proves the job leaves `queued` without a second submission.

### Regression items

- [x] An explicitly empty environment never discovers host `CODEX_HOME` or export directories.
- [x] The exact `4161807c` legacy root is allowed only for the `1860fa17` cleanup task; adjacent names remain blocked.

### Out of scope

- No real owner data, external AI-client configuration, or automatic Core Memory approval.

> 每个包含产品代码、运行时、UI、连接器、数据链路、脚本、依赖或发布流程变化的 PR，都必须在本文件顶部追加一条记录。
>
> 记录描述“本次代码变化后，验收必须新增、修改或回归什么”。历史记录不得删除，只能更正明显错误并说明原因。

## 填写模板

```markdown
## YYYY-MM-DD · <PR/任务> · <短标题>

- 产品分支：`<branch>`
- 产品 Commit：`<sha 或 pending>`
- 影响模块：
- 风险等级：P0 / P1 / P2 / P3
- 用户可感知变化：
- 数据或安全边界变化：

### 新增或修改的自动验收

- [ ] `<测试命令或测试文件>`：验证什么

### 新增或修改的真机验收

- [ ] `<步骤>`：预期结果

### 主人肉眼确认

- [ ] `<必须人工观察的行为>`

### 回归项

- [ ] `<历史 Bug 或兼容承诺>`

### 清理与回滚

- 临时数据前缀：
- 覆盖安装或迁移方式：
- 临时备份删除条件：
- 测试数据清理方式：

### 不在范围

- `<本次没有实现且不得宣称已完成的能力>`

### 最终报告

- 报告路径：`docs/TEST_REPORTS/<REPORT>.md`
- 报告分支：`acceptance/<task>-<short-sha>`
```

---

## 2026-08-02 · PR #72 / PR #60 后续 · 自动导入、运行时真相与清理闭环

- 产品分支：`fix/pr60-import-state-cleanup-recovery`
- 产品 Commit：`pending`
- 来源缺陷：`PR60-MEMORY-QUALITY-TRIAL-4161807C / DAY0 FAIL / BLOCKED_POST_CLEANUP`
- 影响模块：AI 助手导入编排、ChatGPT/Codex 导出候选发现、正式采集队列、Codex 三层连接状态、MCP/Qdrant 所有权、向量状态快照、Desktop 状态页、安全清理工具、Day 0 生命周期验收
- 风险等级：P0
- 用户可感知变化：灵机自动发现受支持导出包；发现后只需一次授权即可入队。未发现时只保留一个文件选择动作，选中即入队，不再要求填写路径或二次提交。配置、命令启动、真实客户端验证、全文检索和语义检索分别显示真实证据。
- 数据或安全边界变化：自动候选发现仅扫描受控位置和元数据，不读取正文、不暴露绝对路径；真实文件读取仍需精确授权；MCP 成为 SQLite/Qdrant 唯一实时拥有者；不自动写 Core Memory、不自动重建 Production Qdrant。

### 新增或修改的自动验收

- [ ] `python -m pytest -q tests/test_assistant_hub_imports.py tests/test_assistant_hub_api.py`：验证候选扫描有界、只读元数据、不泄露路径、一次授权入队、无候选时只有一个选择动作、不支持来源没有假按钮。
- [ ] `python -m pytest -q tests/test_ai_memory_connectors.py tests/test_ai_connector_readiness.py`：验证 Codex 配置、命令启动和真实客户端注册三层状态；Access Denied、命令缺失和 MCP 不可见均不得显示 ready。
- [ ] `python -m pytest -q tests/test_vector_truth_contract.py tests/test_memory_owner_lock.py tests/test_memory_statistics.py`：验证 MCP 单一所有权、Windows/POSIX 文件锁、可读诊断元数据、empty/locked/stale/healthy 向量状态和全文/语义检索分离。
- [ ] `python -m pytest -q tests/test_cleanup_acceptance_workspace.py`：合法 dry-run 返回 `DRY_RUN_READY`，显式执行后目标消失；越界、身份不匹配或真实删除失败才返回 `BLOCKED`。
- [ ] `npm run test:smoke`：验证 AI 助手页没有路径输入和二次提交，连接器与 Qdrant 状态使用证据合同。
- [ ] `npm run build`：验证 React/TypeScript 生产构建。
- [ ] `P0 Windows Gate`：验证 Windows Python、Desktop、Rust/Tauri 和启动恢复链。
- [ ] `Windows Desktop Release Baseline`：验证打包 Sidecar、MCP 单一所有权、NSIS、身份与哈希合同。

### 新增或修改的真机验收

- [ ] 首次启动后灵机自动扫描 Downloads、Desktop 和任务导入箱中受支持导出包的元数据；未授权前真实正文读取数保持 0。
- [ ] 发现 ChatGPT/Codex 支持包时，UI 只显示一个“授权并开始导入”动作；授权后立即进入正式采集队列，不再要求填写路径或再次提交。
- [ ] 未发现包但存在正式适配器时，UI 只显示一个文件选择动作；选择完成立即入队，并自动显示处理进度、去重和失败重试。
- [ ] Claude Code、WorkBuddy 等暂无正式历史适配器的来源只解释边界，不展示无效导入按钮。
- [ ] Codex 状态必须分别展示配置、命令启动、真实客户端注册；路径存在但 `Access is denied` 时必须为 `client_launch_blocked`。
- [ ] 只有真实 Codex 命令运行并列出 `lingji-memory` 后才可显示 ready；配置存在不得借用绿色状态。
- [ ] MCP 是嵌入式 Qdrant 唯一进程拥有者；Control API 只读 MCP 发布快照，不得再次打开同一嵌入式目录。
- [ ] `ready + 0 vectors` 必须显示 `empty`，不得显示语义检索可用；目录锁冲突显示 `embedded_store_locked`，并说明全文检索仍可用。
- [ ] 首次 Core/Sidecar/MCP 恢复必须在验收预算内完成，8766 与 8767 同时健康后才算 ready；不得出现第一轮超过 45 秒、后续轮次才恢复的结果。
- [ ] 结束清理先 dry-run，状态必须为 `DRY_RUN_READY`；显式执行后唯一任务根不存在，相邻目录与主人数据不变。

### 主人肉眼确认

- [ ] 主人能在 5 秒内看懂灵机发现了什么、是否读取正文、当前唯一授权动作以及授权后的自动处理范围。
- [ ] 选中文件后不再出现第二个“提交导入”动作。
- [ ] 配置、命令和真实连接不会出现互相矛盾的绿色/红色状态。
- [ ] Qdrant 面板能一眼区分服务、Collection、向量数量、全文检索、语义检索、原因和自动恢复状态。
- [ ] 日常流程不要求主人手动驱动扫描、刷新、重试和进度轮询。

### 强制回归项

- [ ] 未经主人授权不得读取 ChatGPT、Codex、剧本、Vault 或其他真实正文。
- [ ] 候选扫描不得跟随符号链接，不得扫描未知目录，不得向前端返回绝对路径。
- [ ] 过期候选 ID 必须重新扫描并拒绝，不得继续读取已移动或删除文件。
- [ ] 任意 JSON/ZIP 不得因为后缀相同就成为导入候选。
- [ ] 配置文件存在、可执行文件路径存在、命令能启动和 MCP 注册可见必须分别取证。
- [ ] Control API 与 MCP 不得各自创建嵌入式 Qdrant 客户端并给出独立结论。
- [ ] stale 快照不得宣称语义检索可用。
- [ ] 清理工具不得把合法 dry-run 的待删除清单误判为阻断，也不得放宽到通配符或父目录删除。
- [ ] 候选未批准前 Core Memory 不增加，拒绝项不进入永久记忆。
- [ ] Production 污染保持 0；Stage 1 在新 Day 0 PASS 前保持 NOT_RUN。

### 清理与回滚

- 临时数据前缀：由新的精确 Head Day 0 任务声明。
- 覆盖安装方式：新 Artifact 覆盖安装，不卸载主人数据。
- 运行时锁：任务根 `runtime/memory-owner.lock` 仅作 OS 互斥，`runtime/memory-owner.json` 仅作可读诊断；任务清理时共同删除。
- 测试数据清理：仅删除任务专属 DataRoot、Artifact、安装包、日志、fixture、临时配置和 worktree；先 dry-run，再显式执行。
- 回滚：回退自动导入编排、三层连接合同、MCP 单一所有权和向量快照；不得恢复路径输入、二次提交或多进程 Qdrant 探测。

### 不在范围

- 不自动读取 Codex 原始 Session/JSONL。
- 不新增 Claude Code 或 WorkBuddy 正文导入适配器。
- 不自动下载 Embedding 模型。
- 不自动重建 Production Qdrant。
- 不自动批准永久记忆。
- 不开放远程或公网 MCP。

### 最终报告

- 实施报告：`docs/TEST_REPORTS/PR60_AUTONOMOUS_IMPORT_STATE_COHERENCE_CLEANUP_FIX.md`
- 新 Artifact 和复验任务：精确 Head CI、P0 Windows、Release 和哈希核验通过后更新。

---

## 2026-08-02 · PR #71 / PR #60 后续 · Runtime DataRoot 强绑定与 UI 观察台自治改造

- 产品分支：`fix/pr60-autonomous-runtime-binding`
- 产品 Commit：`pending`
- 来源缺陷：`FAIL_DATA_ROOT_ISOLATION`
- 影响模块：Desktop bootstrap、RuntimeManager、打包 Runtime 身份接口、桌面自动恢复、AI 助手元数据扫描、首页观察台、Day 0 隔离验收
- 风险等级：P0
- 用户可感知变化：灵机主动选择安全非 C 盘、启动和恢复核心、扫描 AI 与来源元数据、刷新模型和硬件状态；UI 主要展示正在做什么、进度、阻塞和授权边界，不再要求主人逐项驱动流程。
- 数据或安全边界变化：Runtime 必须反向证明实际 DataRoot 和 workspace；不匹配或未托管 Runtime 不得显示健康；自动扫描仍只读元数据，读取真实正文、修改外部客户端配置和写入永久记忆仍需主人授权。

### 新增或修改的自动验收

- [ ] `python -m pytest -q tests/test_brain_status_e2e.py tests/test_assistant_hub_api.py tests/test_assistant_hub_discovery.py tests/test_packaged_mcp_runtime.py`：验证鉴权 Runtime ping 返回实际 DataRoot/workspace，并保持发现扫描不读正文。
- [ ] `npm run test:smoke`：验证自动 DataRoot、绑定核验、自动扫描/模型/硬件刷新、UI 观察台语义和授权边界。
- [ ] `npm run build`：验证新增 Autopilot 状态组件与 TypeScript 生产构建。
- [ ] `cargo test`：验证启动契约、精确有效根、锁定绑定、路径归一化和非 C 盘自动候选。
- [ ] `scripts/validate.ps1 -Mode release`：验证完整 Desktop、Sidecar、Tauri、NSIS 和发布合同。

### 新增或修改的真机验收

- [ ] 使用任务专属 `LINGJI_BOOTSTRAP_CONTRACT_FILE` 启动，Desktop 在 Runtime 启动前显示固定任务根、workspace、绑定来源和 binding id。
- [ ] `/api/runtime/ping` 必须返回与启动契约逐字一致的实际 DataRoot 和 workspace。
- [ ] 机器上存在其他有效 bootstrap 或 acceptance Runtime 时，Desktop 必须拒绝复用，不得显示 ready。
- [ ] 无启动契约和旧配置时，灵机自动选择首个可写非 C 盘；仅在没有安全候选时显示手动目录备用入口。
- [ ] 连接后无需主人点击，自动执行 AI 元数据扫描、模型刷新、硬件刷新和状态轮询。
- [ ] 自动扫描只读取安装、路径类型、候选数量和支持状态，不读取聊天、剧本、Vault 或 Session 正文。
- [ ] 读取真实正文、应用外部客户端配置、永久记忆批准/拒绝前必须明确请求主人授权。

### 主人肉眼确认

- [ ] 首页能直接看到灵机当前自动动作、完成项、失败重试项、精确 DataRoot、workspace 和绑定验证结果。
- [ ] 菜单完整保留，但日常按钮表达为“查看进度/查看授权/手动干预”，而不是要求主人按流程逐项操作。
- [ ] AI 助手页默认自动扫描，主人无需点击“扫描我的 AI 软件”。
- [ ] 主人能一眼区分“灵机正在自动处理”和“现在确实需要我授权或决定”。

### 强制回归项

- [ ] HTTP 200 或 Token 匹配不能单独证明 Runtime 身份；实际根和 workspace 必须同时匹配。
- [ ] 锁定启动契约不能在 UI 中被旧 bootstrap 或手动选择覆盖。
- [ ] 端口 8766 已占用时不得静默改绑或接管外部 Runtime。
- [ ] 未托管外部 Runtime 不得被 Desktop 停止，只能拒绝接管并报告。
- [ ] 自动发现不得读取正文、不得跟随符号链接、不得扫描未知目录。
- [ ] 禁止恢复模糊文案“配置存在但尚未激活；全文检索仍可用，后续从向量中心处理”。
- [ ] 候选未批准前 Core Memory 不增加，外部客户端配置未授权前不修改。

### 清理与回滚

- 临时数据前缀：由新的精确 Head Day 0 任务声明。
- 覆盖安装方式：新 Artifact 覆盖安装，不卸载主人数据。
- 启动契约：任务结束后删除任务专属 JSON，恢复原 bootstrap 哈希或原不存在状态。
- 测试数据清理：只删除任务专属 DataRoot、Artifact、安装包、日志、fixture、临时配置和 worktree；共享父目录允许保留。
- 回滚：回退本次启动契约、Runtime身份核验和 Autopilot UI提交；不得恢复“只凭健康端口信任Runtime”的旧行为。

### 不在范围

- 不自动读取 Codex原始 Session/JSONL、ChatGPT正文、剧本或 Obsidian正文。
- 不自动批准永久记忆。
- 不自动修改未经授权的 Codex、Claude Code 或 WorkBuddy配置。
- 不自动下载 Embedding模型或重建 Production Qdrant。

### 最终报告

- 实施报告：`docs/TEST_REPORTS/PR60_AUTONOMOUS_RUNTIME_BINDING_AND_UI_OBSERVABILITY.md`
- 新 Artifact 和复验任务：代码、完整 release 和精确 Head Windows Artifact 全部通过后更新。

---

## 2026-07-30 · PR #60 · AI 助手中心主动引导与真实状态修复

- 产品分支：`feature/unified-ai-memory-connectors`
- 产品 Commit：`pending`
- 来源缺陷：`D0-UX-001`、`D0-CODEX-002`
- 影响模块：AI 助手中心、Codex/Claude 连接状态、历史导入说明、Embedding/Qdrant 状态说明、Desktop Smoke
- 风险等级：P0
- 用户可感知变化：扫描后页面必须主动说明发现了什么、能导入什么、不会读取什么，并只给出一个明确下一步；配置文件存在不得再显示为连接可用。
- 数据或安全边界变化：扫描继续只读元数据；真实正文读取和导入仍需主人确认；不新增自动永久记忆写入，不扫描未知目录。

### 新增或修改的自动验收

- [ ] `python -m pytest -q tests/test_ai_memory_connectors.py`：Codex 配置存在但命令缺失时必须为 BLOCKED，只有真实 CLI 验证后才能 READY。
- [ ] `node desktop/lingji-control/scripts/assistant-memory-connectors-smoke.mjs`：页面必须包含统一准备度、主动导入提示、Embedding/Qdrant 原因和真实连接三段状态。
- [ ] `npm run build`：新状态面板和样式必须通过 TypeScript/React 生产构建。
- [ ] `P0 Windows Gate`：Windows PowerShell、Desktop、Rust/Tauri 和完整 Python 回归通过。

### 新增或修改的真机验收

- [ ] 扫描完成后，顶部只显示一个当前最优先动作，不能让主人自行在扫描、连接、导入、审核之间猜测。
- [ ] 检测到 Codex 目录时，主动显示脱敏目录、候选文件数量、当前支持的 Codex Report JSON，以及“未读取原始 Session 正文”。
- [ ] 主人未确认前不得读取或导入真实正文；点击“暂不处理”后不得创建采集任务。
- [ ] Codex 配置已写入但 `codex` 命令缺失时，统一显示“已阻塞”，并说明配置存在不等于连接可用。
- [ ] Codex 只有配置、命令和真实 MCP 测试全部通过后才能显示绿色“连接可用”。
- [ ] Embedding/Qdrant 不可用时，在同一页面显示配置模型、实际激活状态、最近错误或重建要求，不能只写“后续处理”。
- [ ] 连接、导入和向量异常必须各有明确原因，不允许多个卡片给出互相矛盾的结论。

### 主人肉眼确认

- [ ] Checkpoint A 重测：扫描完成后能在 5 秒内指出下一步，不需要开发者解释。
- [ ] 能一眼区分“发现本地目录”“配置文件已写入”“客户端命令可用”“真实连接测试通过”。
- [ ] 能看懂准备导入的资料类型、来源和安全边界。
- [ ] 能一眼看到 Embedding/Qdrant 为什么不可用，以及全文检索是否仍可用。

### 强制回归项

- [ ] A-01：显式空环境不得继承主人真实 `CODEX_HOME`。
- [ ] 配置冲突继续拒绝覆盖，连接配置继续备份并可回滚。
- [ ] Token 不得出现在 UI、日志、报告或配置预览。
- [ ] 扫描不读取正文、不跟随符号链接、不扫描未知路径。
- [ ] `propose_memory` 仍只生成候选，不自动写 Core Memory。
- [ ] WorkBuddy 无稳定官方配置接口时仍使用复制配置，不伪造自动连接成功。

### 清理与回滚

- 临时数据前缀：`PR60_GUIDED_SETUP_`
- 覆盖安装方式：新 Artifact 直接覆盖旧安装，不卸载主人数据。
- 临时配置副本：连接测试完成并验证回滚后删除。
- 测试数据清理：删除临时 Artifact、日志、截图、fixture、checkpoint、配置副本、worktree 和测试候选；不删除主人授权保留的真实资料。

### 不在范围

- 不新增 Claude Code 历史导入。
- 不新增 WorkBuddy 历史导入。
- 不自动读取 Codex 原始 Session、JSONL 或 Markdown 正文。
- 不在本次修复中自动安装 Embedding 模型或静默重建 Production Qdrant Collection。
- 不改变远程/public MCP 边界。

### 最终报告

- 缺陷记录：`docs/TEST_REPORTS/PR60_ASSISTANT_HUB_GUIDED_FLOW_PLAN.md`
- 实施报告：`docs/TEST_REPORTS/PR60_ASSISTANT_HUB_GUIDED_FLOW_IMPLEMENTATION.md`
- 新 Artifact 和复验任务：代码 CI 与 Release 通过后更新 `LOCAL_EXECUTION_TASK.md`。

---

## 2026-08-01 · PR #60 后续 · 代码发布验证临时目录安全清理修复

- 产品分支：`fix/cleanup-code-validation-workspace`
- 产品 Commit：`pending`
- 来源阻塞：`PR60-CODE-RELEASE-VALIDATION-A90A18A6 / BLOCKED_POST_CLEANUP`
- 影响模块：本机任务治理、安全清理工具、代码发布链结果回执
- 风险等级：P1
- 用户可感知变化：不需要重跑已通过的 15 套 release 验证；修复后只补做安全清理、最终回执和远程复读。
- 数据或安全边界变化：不触碰产品 Runtime、UI、Vault、数据库、Qdrant、真实资料或用户 AI 配置；仍只允许删除任务 ID 推导出的精确临时目录。

### 新增或修改的自动验收

- [x] `python -m pytest -q tests/test_cleanup_acceptance_workspace.py`：本地隔离验证 `10 passed`。
- [ ] GitHub `tests`：验证 Python 3.11、3.12、Windows 和完整仓库回归。
- [ ] `acceptance-doc-sync`：验证脚本变化已同步本记录。

### 新增或修改的真机验收

- [ ] 使用 `PR60-CODE-RELEASE-VALIDATION-A90A18A6` 对 `D:\codex\LingJiValidation\PR60-CODE-a90a18a6` 先 dry-run。
- [ ] dry-run 清单必须只包含该任务创建的 product、report、release、日志、缓存和证据目录。
- [ ] 显式 `--execute` 后目标目录必须不存在，相邻目录和主人数据保持不变。
- [ ] 更新原报告与结果回执为最终 `PASS`，再次 push 并远程复读。

### 主人肉眼确认

- [x] 不需要主人参与；本任务不安装、不启动 UI、不读取真实数据。

### 回归项

- [ ] 不允许通配符删除。
- [ ] 不允许删除清理根目录本身。
- [ ] 不允许删除根目录外或非直接子目录。
- [ ] 任务类型、PR号和 8 位 Commit 身份必须与目录名精确匹配。
- [ ] 旧 `D69874AF` 记忆质量任务仍能清理两个明确登记的 `1c514877` 历史目录。
- [ ] 不跟随符号链接或 Windows reparse point。

### 清理与回滚

- 当前清理根：`D:\codex\LingJiValidation`
- 当前目标：`PR60-CODE-a90a18a6`
- 安全入口：`scripts/cleanup_acceptance_workspace.py`
- 回滚：回退本次策略和测试；不得恢复宽泛白名单或手工强删。

### 不在范围

- 不重跑产品代码、Desktop、Rust/Tauri 或 Windows release 验证。
- 不生成或安装正式 GitHub Artifact。
- 不解决 PR #60 与 master 的后续合并冲突。
- 不进入 Day 0、UI 或真实数据验收。

### 最终报告

- 修复报告：`docs/TEST_REPORTS/PR60_CODE_VALIDATION_CLEANUP_POLICY_FIX.md`
- 原验证报告：`docs/TEST_REPORTS/PR60_CODE_RELEASE_VALIDATION_a90a18a6.md`
- 原报告分支：`acceptance/pr60-code-release-validation-a90a18a6`

---

## 2026-07-31 · PR #60 · d69874af 引导修复复验与真实数据记忆质量试运行

- 产品分支：`feature/unified-ai-memory-connectors`
- 产品 Commit：`d69874afd8def42a40c4a5cc5e678a71921d44b5`
- 固定 Artifact：`lingji-windows-0.1.0-d69874af`
- Artifact ID：`8762312712`
- Artifact ZIP SHA256：`6bf1f591502617c400ce482f6beb0d5e430a172cd036137bb4a39cae2cbf4cb4`
- 安装器 SHA256：`d62867b7b7c90bee8273b3cf5720f53099c266897ce95d0e42224deae31bf262`
- 影响模块：首次使用引导、AI 软件与历史目录发现、Codex 连接状态机、Embedding/Qdrant 诊断、Day 0、真实数据试运行、报告提交和本地清理
- 风险等级：P0
- 用户可感知变化：页面必须给出唯一当前动作，主动解释扫描结果和可导入范围，不再同时显示“配置正常”和“命令不存在”，向量问题必须展示具体原因与处理入口。
- 数据或安全边界变化：Day 0 未 PASS 禁止读取真实资料；历史目录只读取元数据，读取内容前必须获得主人授权；Production 保持只读和物理隔离。

### 已通过的自动验收

- [x] `acceptance-doc-sync #43`
- [x] `local-execution-handoff #35`
- [x] `tests #1138`
- [x] `P0 Windows Gate #258`
- [x] `Windows Desktop Release Baseline #142`
- [x] 旧模糊文案“已设置，等待测试”回归断言。
- [x] 配置文件、客户端命令和真实连接三个状态分离。

### 新增或修改的真机验收

- [ ] 开始前使用 `scripts/cleanup_acceptance_workspace.py` 清理旧任务专用临时目录；脚本必须先 dry-run，再显式 `--execute`，且只能操作任务单允许的精确目录。
- [ ] Day 0 在任何真实数据导入前完成：固定 Artifact、覆盖安装、Runtime、8766/8767、MCP 鉴权、真实 Codex 调用、候选边界、A-01、三轮 Core 重启和 Windows 重启。
- [ ] 页面始终只有一个明确主要动作；扫描完成后主动说明发现的软件和历史目录元数据。
- [ ] 发现历史目录后主动询问是否查看或导入，明确说明当前支持与不支持的格式。
- [ ] 配置文件存在、`codex` 命令可用和真实 MCP 连接必须分别显示；缺少命令时不得显示 ready。
- [ ] Embedding/Qdrant 必须显示配置模型、激活模型、缺失模型、最近错误、Qdrant 状态、是否需要重建和当前可执行入口。
- [ ] 主人明确授权后，Stage 1 只导入 1 部剧本、1 份 Codex 报告、少量 ChatGPT 历史和 1 个明确 Obsidian 目录。
- [ ] Stage 1 无 P0/P1 后才逐步扩展到最多 10 部授权剧本和其他授权资料。
- [ ] 至少执行 20 道质量题：精确事实不少于 8、跨文档比较不少于 4、来源核验不少于 4、负面边界不少于 4。

### 主人肉眼确认

- [ ] Checkpoint A：安装和首次打开，无黑窗，首页正常，唯一下一步清楚，状态文案能区分。
- [ ] Checkpoint B：Codex 能看到 LingJi 工具、真实调用成功、返回内容正确。
- [ ] Checkpoint C：主人亲自批准一个测试候选、拒绝一个测试候选，页面可理解。
- [ ] Checkpoint D：Windows 重启后无黑窗，灵机恢复且页面可操作。
- [ ] Checkpoint E：主人至少抽查 10 道质量题，确认答案与来源评分。

### 强制回归项

- [ ] Day 0 未 PASS 时禁止导入真实资料。
- [ ] 未经主人授权不得读取或导入任何真实目录内容。
- [ ] 剧本人物、剧情和台词不得进入主人个人事实。
- [ ] 不存在的问题必须承认未知，不得拿相似资料冒充。
- [ ] 候选未批准前 Core Memory 不增加，拒绝候选不进入永久记忆。
- [ ] A-01 隔离不得读取或修改主人真实 `CODEX_HOME`。
- [ ] 覆盖安装和连接器回滚不得破坏主人数据或配置。
- [ ] Windows 重启后 Runtime、MCP、Workspace、DataRoot 和 Vault 恢复。
- [ ] 开始前和结束后临时目录必须清理；清理失败时只能 BLOCKED，不得绕过安全策略。

### 质量阈值

```text
quality_score >= 90%
source_accuracy >= 95%
false_positive_rate <= 5%
Codex MCP 真实调用成功率 >= 95%
重复正式内容 = 0
Production 污染 = 0
人工审核链成功率 = 100%
Windows 重启后恢复 = 100%
```

### 清理与回滚

- 当前临时数据前缀：`PR60_MEMORY_TRIAL_D69874AF_`
- 当前临时根目录：`D:\codex\LingJiAcceptance\PR60-MEMORY-TRIAL-d69874af`
- 必须清理的历史临时目录：`D:\codex\LingJiAcceptance\PR60-MEMORY-TRIAL-1c514877`、`D:\codex\LingJiAcceptance\PR60-1c514877`
- 安全清理入口：`python scripts/cleanup_acceptance_workspace.py --task-id PR60-MEMORY-QUALITY-TRIAL-D69874AF --target <精确目录>`；确认 dry-run 后追加 `--execute`。
- 清理工具拒绝验收根目录本身、根目录外路径、非白名单目录和不匹配任务身份；不跟随符号链接或 Windows reparse point。
- 覆盖安装方式：固定安装器直接覆盖，不卸载。
- 临时配置副本：每个客户端最多一个，哈希验证后删除。
- 主人授权的真实资料是否保留由主人选择，Codex不得擅自删除。
- 报告第一次远程确认后清理，更新结果回执，再次 push 和远程复读。

### 不在范围

- Codex 原始 Session / JSONL 自动导入。
- Claude Code 和 WorkBuddy 历史导入。
- 自动下载 Embedding 模型。
- 自动重建 Production Qdrant。
- 自动批准永久记忆。
- 远程或公网 MCP。

### 最终报告

- 专项协议：`docs/ACCEPTANCE/MEMORY_QUALITY_TRIAL.md`
- 任务单：`docs/ACCEPTANCE/LOCAL_EXECUTION_TASK.md`
- 报告路径：`docs/TEST_REPORTS/PR60_MEMORY_QUALITY_TRIAL_d69874af.md`
- 报告分支：`acceptance/pr60-memory-quality-trial-d69874af`
- 产品 PR 必须保持 Draft 且不得合并，直到 Day 0、Stage 1、质量指标、主人检查点、远程提交和清理全部满足 PASS。

---

## 2026-07-30 · PR #60 · 1c514877 首轮试运行（历史失败，禁止重跑）

- 产品分支：`feature/unified-ai-memory-connectors`
- 产品 Commit：`1c5148779624910f1c6072d95d6c6f6822f631e6`
- 固定 Artifact：`lingji-windows-0.1.0-1c514877`
- Artifact ID：`8723868744`
- 状态：历史 `FAIL / BLOCKED_SUBMISSION`，已被 2026-07-31 的 d69874af 条目取代。
- 已知缺陷：`D0-UX-001` 页面缺少统一引导；`D0-CODEX-002` 配置状态和命令状态矛盾；`BLOCKED_POST_CLEANUP` 旧临时目录未清理。
- 历史报告：`docs/TEST_REPORTS/PR60_MEMORY_QUALITY_TRIAL_1c514877.md`
- 历史报告分支：`acceptance/pr60-memory-quality-trial-1c514877`
- 当前不得再按该产品 Commit、Artifact 或报告路径执行。

---

## 2026-07-30 · 本机任务信箱与结果回执硬门禁

- 产品分支：`master`
- 产品 Commit：`governance-only`
- 影响模块：仓库治理、Codex 本机执行交接、报告提交、远程复读、本地垃圾清理、GitHub Actions
- 风险等级：P1
- 用户可感知变化：用户只需告诉 Codex 去看任务单，或告诉 ChatGPT Codex 已完成；不再复制长指令、解释 Git、上传报告或排查分支。
- 数据或安全边界变化：不改变产品数据；明确禁止清理主人 DataRoot、Vault、正式记忆和用户 AI 配置，只清理本轮临时验收垃圾。

### 新增或修改的自动验收

- [x] `python scripts/check_local_execution_handoff.py`：校验任务单、结果回执、身份一致性、开始/结束清理、远程确认和报告 Commit 字段。
- [x] `python -m pytest -q tests/test_local_execution_handoff.py`：覆盖 PENDING、COMPLETED、远程确认缺失、清理失败、身份不一致和阻塞提交。
- [x] `local-execution-handoff` Workflow：在 `master`、开发分支和 `acceptance/**` 报告分支执行；报告分支结果不是 `COMPLETED` 时失败。

### 新增或修改的真机验收

- [x] Codex 只读取 `docs/ACCEPTANCE/LOCAL_EXECUTION_TASK.md` 中 `status: ACTIVE` 的任务，不从聊天或本机残留推断。
- [x] 每次开始前整体清理上一轮临时验收目录、Artifact、日志、截图、fixture、checkpoint、临时配置副本和 worktree，再释放 8766/8767。
- [x] 报告 push 后使用 `git ls-remote` 和 GitHub API 重新读取远程分支、Commit、报告、结果回执和 PR 评论。
- [x] 第一次远程确认后清理本轮本地垃圾，更新结果回执，再次 push 和远程复读。

### 主人肉眼确认

- [x] 用户只负责下达“去看任务单干活”或“Codex 已完成”，不负责 Git、上传、报告路径和清理操作。

### 回归项

- [x] 禁止把本机生成报告误写成已经上传。
- [x] 禁止 `git push` 命令执行后未复读远程就宣布完成。
- [x] 禁止长期堆积旧验收目录、重复安装包、日志、截图、fixture、checkpoint、配置副本和 worktree。
- [x] 禁止清理主人正式数据或其他任务数据。

### 清理与回滚

- 临时数据前缀：由 `LOCAL_EXECUTION_TASK.md` 每个任务单独声明。
- 覆盖安装或迁移方式：本次为治理变更，不涉及产品安装。
- 临时备份删除条件：远程报告第一次确认后删除；只保留哈希。
- 测试数据清理方式：本机任务结束时删除任务单指定临时根目录和带任务前缀的数据。

### 不在范围

- 不改变 LingJi 产品 Runtime、UI、数据库、记忆或连接器功能。
- 不代替具体任务的真机验收标准。
- 不要求用户学习 Git 或参与报告提交。

### 最终报告

- 规则权威：`docs/ACCEPTANCE/LOCAL_EXECUTION_TASK.md` 与 `docs/ACCEPTANCE/LOCAL_EXECUTION_RESULT.md`
- 自动门禁：`.github/workflows/local-execution-handoff.yml`

---

## 2026-07-29 · PR #60 · P0-A 与统一 AI 记忆连接器重新真机验收（历史方案）

- 产品分支：`feature/unified-ai-memory-connectors`
- 产品 Commit：`1c5148779624910f1c6072d95d6c6f6822f631e6`
- 固定 Artifact：`lingji-windows-0.1.0-1c514877`
- Artifact ID：`8723868744`
- 状态：被后续真实数据试运行方案取代，保留为历史记录。
- 已通过自动验收：`tests #1081`、`P0 Windows Gate #240`、`Windows Desktop Release Baseline #129`、A-01 回归。
- 原计划报告：`docs/TEST_REPORTS/PR60_OWNER_CODEX_FULL_REACCEPTANCE_1c514877.md`
- 原计划分支：`acceptance/pr60-owner-1c514877`
- 当前不得再按该旧路径执行。

---

## 2026-07-29 · PR #62 · 建立统一 Codex 验收权威

- 产品分支：`docs/acceptance-governance`
- 治理实现与门禁验证基线：`e43da870bc755321f5bd0db4a40aca31df91124d`
- 影响模块：仓库治理、Codex 执行入口、CI 文档同步门禁
- 风险等级：P1
- 用户可感知变化：Codex 拉取代码后可直接从仓库读取当前验收指令，不再依赖聊天中复制的旧指令。
- 数据或安全边界变化：没有产品数据变更；新增规则要求临时证据和配置副本在报告提交后清理。

### 新增或修改的自动验收

- [x] `python scripts/check_acceptance_sync.py`
- [x] `python -m pytest -q tests/test_acceptance_sync.py`
- [x] GitHub Workflow `acceptance-doc-sync #1`
- [x] GitHub Workflow `tests #1082`
- [x] GitHub Workflow `P0 Windows Gate #241`

### 新增或修改的真机验收

- [x] Codex 从仓库读取验收权威，不依赖聊天历史。
- [x] 代码变化后必须同步验收标准。
- [x] 报告提交后清理临时 Artifact、日志、截图、fixture 和配置副本。

### 主人肉眼确认

- [x] 主人明确要求仓库成为验收指令权威。

### 回归项

- [x] 不允许代码变更后遗漏验收标准更新。
- [x] 不允许为了补报告移动已打包产品 Head。
- [x] 不允许长期堆积重复验收垃圾。

### 清理与回滚

- 临时数据前缀：`ACCEPTANCE_GOVERNANCE_`
- 不涉及产品安装或正式数据。

### 不在范围

- 不改变 LingJi 产品功能。
- 不替代模块测试报告。
- 不自动合并产品 PR。

### 最终报告

- 报告路径：`docs/TEST_REPORTS/ACCEPTANCE_GOVERNANCE_IMPLEMENTATION.md`
- 治理 PR：`#62`
