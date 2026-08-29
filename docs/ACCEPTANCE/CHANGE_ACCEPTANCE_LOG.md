# 验收要求变更记录

## 2026-08-29 · Task 8E · Owner-facing plain UI repair Round 5

- 本轮仅修复 Round4 终审指出的两个契约问题，不增加功能：scheduler 对
  `ScanRun` 的 `queued/reused` 缺失值继续保留为未知，只有已完成且实际测量的扫描
  才写入/显示真实计数；内部进度计算使用局部安全回退，不向事件、Work Fact 或
  API 投影伪造 `0`。
- Local Control API 的 action、list、summary、detail 共用正式 scan projector；
  所有有 `scan_id` 的响应稳定派生同一个 `automatic-memory:<scan_id>` `work_id`，
  并保留非接管结果的 `complete/errors/next_action`，避免过期或不支持来源被误报为
  中性成功快照。
- TDD/验证：I1/I2 最小 RED 后 GREEN；直接后端 `69 passed, 1 warning`，Round5
  专项 `17 passed, 1 warning`，Task2–5 affected `184 passed, 3 warnings`；packaged
  contract（显式兼容 event watcher 环境）`2 passed, 1 warning, 291.19s`；Desktop
  rendered E2E、23-script smoke、build（92 modules）均 PASS。
- `compileall` 与 diff-check PASS；本轮没有启动/安装 live App，没有访问或修改
  Acceptance/Production/Vault/主人数据。Mac 默认安全 periodic fallback 未改变；
  packaged 首次在系统 Python 缺少可选 MCP 依赖时停止，安装仓库声明的测试依赖后重跑通过。
- 产品/测试提交：`ca6b8ea40cf6d95974639af213ca6ee41e08bdee`。报告沿用
  `.superpowers/sdd/2026-08-29-task8e-owner-plain-ui/task-report.md`，文档提交另行记录。

## 2026-08-29 · Task 8E · Owner-facing plain UI repair Round 4

- 本轮承接 Round3 的正式计数证据缺口：扫描数据库新增 `queued_count`/`reused_count` 可空字段，旧表增量迁移且旧行保持 `NULL`；只有完整扫描实际测量完成时才原子写入计数，明确空扫描写入真实 `0`，暂停、失败、崩溃恢复、未测量和 legacy 行保持未知。
- `ScanRun`、StateDB、scheduler、snapshot runner、Local Control API 使用同一 presence 语义；列表、摘要、详情和动作响应统一通过同一 scan DTO projector。旧兼容调用传入无 presence 标记的默认 `0` 不得伪装为真实测量值；同秒更新时间以数据库插入顺序稳定排序。
- rendered fixture 改为从统一 scan DTO 形状生成缺失、明确 `0`、正数和未完成状态，并验证 Home/列表/详情的计数存在性一致；不改变 watcher 策略、队列架构、永久记忆权威或任何 live/Acceptance/Production/Vault 数据。
- TDD/自动验收：后端 focused 先复现 legacy 默认 `0` 与同秒 latest 排序问题，再修复至 `47 passed, 1 warning`；Owner rendered E2E PASS；Desktop `test:smoke`（23 scripts）PASS；`npm run build` PASS（92 modules）；Task2–5 相关回归 `183 passed, 3 warnings`；宽仓库回归仍保留既有 22 项质量评测/环境基线失败，不归因于本轮。
- 本轮不启动/打包/安装 App，不访问 live 8766/8767、Acceptance/Production/Vault 或主人数据；主人观察仍待根代理在新 Artifact 上执行，状态保持 `READY_FOR_OWNER_EXPERIENCE`。报告沿用 `.superpowers/sdd/2026-08-29-task8e-owner-plain-ui/task-report.md`。

## 2026-08-29 · Task 8E · Owner-facing plain UI repair Round 3

- 独立复审仅剩 completed scan detail 的计数证据边界：`ScanRun` 模型对未由 StateDB 提供的 `queued/reused` 等字段会默认填充 0，不能在 Desktop 详情中当作真实测量值。本轮只在 Desktop DTO/API adapter 统一摘要与详情的计数判定，不改 backend、数据模型、队列、自动化、API 动作或 live。
- 新增 `scanCountValue` 证据归一化：正数可作为真实值；0 只有 DTO 明确带 `counts_present` 字段时才显示；缺字段或 legacy/model 默认 0 显示“检查结果尚未获得”。同一 helper 用于 Home 摘要与检查详情，明确真实 0 仍显示 0。
- rendered fixture 覆盖 completed 缺字段、legacy/default 0、明确 0 与明确正数，并保留 running 详情未知计数断言；测试先取得 RED，再以最小实现 GREEN。
- 自动验收：`npm run test:e2e:memory`、Desktop `npm run test:smoke`（23 scripts）、`npm run build`、Task8E backend focused、compileall、diff-check、acceptance sync、local handoff。未启动/打包/安装 App，未操作 live、Acceptance/Production/Vault 或主人数据；主人观察仍为 `READY_FOR_OWNER_EXPERIENCE`。报告沿用 `.superpowers/sdd/2026-08-29-task8e-owner-plain-ui/task-report.md`。

## 2026-08-29 · Task 8E · Owner-facing plain UI repair Round 2

- 独立复审剩余 I1–I3：accepted/retrying 工作状态未知、真实 Claude `consent_required + 空路径` 被误计可连接、scan detail 的 model 默认计数 0 伪装为真实结果。本轮只改 Desktop owner-facing 展示与合成 rendered fixture，不改 backend、数据模型、队列、自动化或 live。
- Current Work 覆盖 queued/accepted/running/retrying/pending/completed/success/failed/cancelled 的中文状态；未知值仍中性未知。Claude 只有存在路径或已授权证据才计入可连接来源，真实可授权路径不受影响。
- scan detail 对 running/failed 等非终态的计数默认 0 显示“检查结果尚未获得”，completed 的 backend 明确 0 仍显示 0；缺字段不生成数值。新增 fixture 覆盖真实形状。
- TDD：先新增 rendered RED，再最小 GREEN；最终运行 focused E2E、Desktop 23-script smoke、build、Task8E backend focused、compile、diff-check、acceptance sync、local handoff，全部通过。报告继续写入 `.superpowers/sdd/2026-08-29-task8e-owner-plain-ui/task-report.md`。
- 范围边界：不启动/打包/安装 App，不操作 Acceptance/Production/Vault/主人数据；主人真机观察仍待根代理授权，保持 `READY_FOR_OWNER_EXPERIENCE`。

## 2026-08-29 · Task 8E · Owner-facing plain UI repair Round 1

- 独立 review 发现 I1–I5/M1：空工作未知状态、真实扫描 DTO 缺计数/错误详情语义、pending stale/error 误报无需处理、Claude-only/零可用来源误称可接入、来源 kind 泄漏英文、侧栏 raw error/development/commit/version 普通态泄漏。本轮仅修复 Desktop owner-facing 展示和合成 Playwright fixture，不改 backend、数据模型、队列、自动化或动作 API。
- 普通态现在将 `work: null` 显示为“目前空闲”；完成/进行中/失败检查分别显示真实状态，缺计数不补默认 0；pending 读取失败或过期显示“待办状态暂时无法确认，正在重试”，只有新鲜成功空列表显示无需处理；Claude-only/零可用显示“暂时没有可连接的记录来源。”。
- 已知来源统一为“Codex聊天记录”“ChatGPT导出记录”“其他AI聊天投递箱”，未知来源统一为“其他聊天来源”；侧栏普通态只显示“运行正常/需要检查”，内部错误、development、commit、version、工作区路径移入折叠运行详情。
- 变更专测：先以新增 rendered 断言取得真实 RED，再 GREEN；fixture 覆盖 work:null、summary 缺计数、scan running/failed、pending error、Claude-only/零来源、known+unknown source name、sidebar raw error 隐藏，并保留真实按钮动作、advanced 入口和 900px 检查。
- 本轮边界：不 live、不打包、不安装、不访问 Acceptance/Production/Vault/主人数据；主人观察仍需根代理授权，状态为 `READY_FOR_OWNER_EXPERIENCE`。报告沿用 `.superpowers/sdd/2026-08-29-task8e-owner-plain-ui/task-report.md`。

## 2026-08-29 · Task 8E · Owner-facing plain UI repair

- 主人反馈最终候选“仍然看不懂”。本轮只简化 Desktop 普通首屏、记忆来源、活动记录、需要我处理和主导航文案；不改 backend、数据模型、队列、自动化或永久记忆权威。普通页面只回答灵机是否正常、正在记住什么、最近检查结果与时间、主人是否需要处理。
- 普通页面隐藏 source/work/internal status、英文技术标签、原始 JSON 与开发字段堆叠；技术 ID、事件和 JSON 仅保留在折叠详情。来源文案使用“Obsidian 长期记忆区”和“Claude 暂不支持自动导入旧记录”，来源动作使用“现在检查”“停止记忆”“查看这次检查”。
- 定期检查文案继续读取 API 真实 interval，显示“打开灵机时会检查，之后每15分钟自动检查一次”；interval 缺失/非法显示“检查时间尚未获得”，不伪造 0 或固定时长。失败、空态和主人待办使用可理解的中文下一步。
- 自动验收：现有 Playwright owner fixture rendered/behavior smoke 覆盖 0 来源、1 来源、检查失败/重试、主人待办/解决，验证授权、检查、停止记忆、重试、解决待办真实后端动作，且确认普通页面隐藏技术标签/ID/JSON；另跑 Desktop 23-script smoke、build、相关 backend focused、compileall、diff-check、acceptance sync、local handoff。
- 真机/产品边界：不打包、不安装、不关闭或操作当前 live app，不访问 Acceptance root、Production、Vault 或主人数据；本轮仅合成 fixture 和本地构建验证。主人确认前只允许报告 `READY_FOR_OWNER_EXPERIENCE`。
- 清理/回滚：仅回滚本轮产品/测试与 docs/report 提交，不触碰主人配置、正式记忆、Vault、raw、memory 或 Qdrant。报告路径：`.superpowers/sdd/2026-08-29-task8e-owner-plain-ui/task-report.md`。

## 2026-08-29 · Task 8E · Safe polling fallback Repair Round 2

- 本轮修复最终 I1 与 M1：平台 policy 仅将规范化 `darwin` 判为 Darwin periodic，规范化
  `windows`/`win32`/`linux` 保持 event；`macOS`、`darwin-arm64`、`unknown`、空值和显式
  `None` 等未知/畸形值一律 fail-closed 到 periodic。未注入平台时使用 `platform.system()`，
  其返回值经过同一 policy 合同；显式设置仍优先。
- API/runtime/UI 只在 reconciliation interval 为 finite 且大于 0 时提供数字及分钟文案；
  0、负数、NaN、Infinity、缺失均提供 unknown/“尚未获得”，不得输出误导性的 at-most 文案。
- 自动验收：平台合法/未知负向矩阵、60/900/1800 和非法 interval 的 API/UI executable
  contract、runtime/API parity；继续运行 fallback 静止两个旧周期、pause/resume/restart、
  revoke、backend focused、Desktop 23-script smoke/build、compileall、diff-check、acceptance
  sync、local handoff。
- 边界：不 live、不打包、不安装，不访问 Acceptance root、Production、Vault 或主人数据；30 秒
  事件 SLA 与 Phase 1 自动接管门禁仍为 `BLOCKED`。
- 本轮 product/tests commit：`be73008407b3540eeb8bbcbd040ddc69faf4adc7`；docs/report commit
  在最终验证后单独记录。

## 2026-08-29 · Task 8E · Safe polling fallback

- 基线：`c70ce6b165213151ca02baf34ff11e2217a21c82`。本轮只为 macOS 正式 runtime
  禁用不可靠的 `watchfiles` event scan，保留启动增量扫描、15 分钟 reconciliation、每日
  integrity、手动立即扫描、授权与 revoke；不新增 deletion invalidation、read-model seam、
  第二队列/数据库或普通 Obsidian 读取。
- 自动验收：RED 必须证明安全基线授权空 Obsidian 在真实 macOS backend 下会产生 event scan；
  GREEN 必须证明 fallback 禁用 event watcher 后两个旧周期内增量扫描为 0、startup
  reconciliation=1、manual=1，缩短 interval 的 scheduled reconciliation 能发现变化，revoke
  后不再扫描，source UI 文案与 periodic 模式一致；另跑 backend focused、Desktop 23-script
  smoke/build、compileall、diff-check、acceptance sync、local handoff。
- 真机/产品边界：不打包、不安装、不启动 live app、不使用 Acceptance root 或主人数据；明确记录
  fallback 不满足 30 秒事件 SLA，只满足最迟 15 分钟自动核对，Phase1 自动接管门禁仍为
  `BLOCKED`，等待根代理授权的真机观察。
- 清理/回滚：测试只用 pytest `tmp_path`/synthetic fixture；回滚本轮产品/测试提交和本条文档
  提交，不触碰 Production、Vault、raw、memory、Qdrant、主人配置。

## 2026-08-29 · Task 8E · Safe polling fallback Repair Round 1

- 本轮修复审查 I1/I2 与 M1–M3：safe polling 默认只对 Darwin/macOS 生效，Windows/非 Mac
  保持 event watcher；平台判定集中于可注入 policy，显式设置可覆盖默认。Runtime/API 必须
  暴露真实 reconciliation interval 与最大变化发现延迟，UI 根据字段渲染，字段缺失不得伪造
  15 分钟；已有 startup/manual/reconciliation/integrity/revoke/pause/resume/restart 保持。
- 自动验收：默认 Darwin periodic、Windows event、显式覆盖和 runtime/API mode/interval parity；
  60/900/1800 秒 UI 文案分别显示 1/15/30 分钟，缺失显示“尚未获得”；fallback 静止两个旧
  周期无 event scan，scheduled reconciliation 仍发现变化，pause/resume/restart 恢复，revoke
  停止扫描；UI helper 执行式 DTO 合同加最小 wiring 检查；另跑 backend focused、Desktop
  23-script smoke/build、compileall、diff-check、acceptance sync、local handoff。
- 结果边界：本轮仍不满足 30 秒事件 SLA，只满足按配置周期的自动核对；Phase 1 自动接管门禁
  继续 `BLOCKED`。不打包、不安装、不启动 live app、不访问 Acceptance root、Production、Vault
  或主人数据。

## 2026-08-29 · Task 8E · Mac experience repair candidate

- 基线：`ffc2d8851dc91b5f09b14d31a34c1e6988358933`；唯一要求源为 `.superpowers/sdd/2026-08-29-task8e-mac-experience-repair/task-1-brief.md` 与 `task-1-observations.md`。本轮只修复来源计数、普通首屏/任务行降噪、真实分页、watcher 空事件、SHADOW 错误展示、Obsidian 终态和 Vector/Memory 状态语义，不改变 Task7、检索质量、模型能力或永久数据权威。
- 自动验收：每项独立 RED→GREEN；Desktop smoke/build；watcher/scheduler/runtime 相关 focused 回归；`compileall`、`git diff --check`、acceptance sync、local handoff。watcher 空事件连续注入不得新增 scan、reconciliation event 或 Work Fact；真实变更/手动扫描/启动 reconciliation 仍各保留审计事实；分页以 `pagination.total/has_more` 为准；结构化错误、普通投喂行和 Vector 降级文案保持可理解且不伪报成功。Repair Round 1 另以可执行 contract smoke 覆盖真实 review_service 顶层 DTO 归一化、`ApiError`/嵌套 detail 错误和 disabled/degraded/unavailable 语义矩阵；suite mock fetch 必须恢复原生实现。
- 真机验收（由根代理另行授权执行）：从修复提交构建并覆盖安装 arm64 `/Applications/灵机.app`，隔离 Acceptance root 验证授权撤销、空监听、普通首页/分页/SHADOW/文本投喂/Obsidian 未配置/Vector 降级，以及重启/停止/恢复；deep strict codesign；Production/Vault/真实聊天变化为 0；UI 保持打开，主人确认前仅 `READY_FOR_OWNER_EXPERIENCE`。
- 主人观察：检查普通首屏不展开 Work Fact 原始 JSON，普通文本投喂行不显示 adapter JSON，`configuration_required` 提供中文下一步，空列表下一页 disabled，Memory healthy + embedding unavailable 明确显示记忆可用、向量待配置/降级，错误不显示 `[object Object]`。
- 清理/回滚：自动测试只使用 pytest `tmp_path`/synthetic fixture；不安装 Ollama，不关闭 `/Applications/灵机.app`，不清理 Task8E Acceptance 数据，不访问 Production/Vault/真实聊天。回滚本轮产品/测试提交和本条 docs 提交即可，不触碰主人配置、Vault、raw、memory 或 Qdrant。

## 2026-08-28 · Task 7M-Reset · Runtime Evidence Composition

- 本轮只重置 Task7 measurement composition：corruption 必须经过正式
  SourceRegistry/scan/Snapshot/SQLiteExtractionQueue/ExtractionWorker/WorkStore/read-model
  组合；ContextPack baseline 必须来自正式选择前只读 observation seam；MCP 必须严格比较
  有序完整身份、scope/lifecycle/mode 与 bounds；scale admission 必须校验同一 run identity、
  fixture hashes、verdict、measured quality 与 readiness 一致性。
- Production/Vault sentinel 继续 nullable/`NOT_MEASURED`；scale 只依赖功能质量，不要求
  owner/Mac/Windows。当前质量 CLI 仍必须诚实返回 `FAIL`（MCP `0/100`、baseline
  `NOT_MEASURED` 等），本轮不运行 100k、release、Artifact、live 服务、Production/Vault
  或主人验收。
- RED/GREEN、命令和未关闭项记录在
  `.superpowers/sdd/2026-08-27-phase1-product-landing/task-7m-reset-report.md`；该记录
  不代表 Task7、Task8 或 Phase1 已接受，须由全新独立审查确认 Critical/Important 均为 0。

## 2026-08-28 · Task 7E-CI Repair 1 · Windows PowerShell entry evidence

- 本轮只补齐 Task7E release entry 的真实 Windows 执行证据，不修改
  `.github/workflows/**`、4R2/100k、retrieval、产品数据或本机服务。由于仓库
  workflow 文件不可由当前 OAuth token 推送，复用既有 `p0-windows-gate.yml`
  的依赖安装后 full pytest 路径，由 `tests/test_00_task4_reset_validation_guard.py`
  在发现真实 `pwsh`/`powershell(.exe)` 时调用
  `scripts/run_powershell_validation.py --mode release --entry-only --hook`。
- Windows 运行必须真实进入 `scripts/validate.ps1`，返回非零并包含
  `BLOCKED_4R2_REQUIRED`；hook 规范化后必须严格为 `preflight` 一项，证明
  `scale-env=0`、`scale-command=0`。Windows 平台不得因缺少 runtime 而返回；
  无 PowerShell 的本机仅允许得到 `BLOCKED_POWERSHELL_RUNTIME_UNAVAILABLE`。
- `--entry-only` 仍是测试专用双重 opt-in（参数、环境标记和 hook 同时存在），
  默认 release/full 行为不改变。远程 run、PowerShell 测试 marker 和
  `git ls-remote` 复读结果记录在
  `.superpowers/sdd/2026-08-27-phase1-product-landing/task-7e-report.md`。

## 2026-08-28 · Task 7E-CI Repair 1 · remote result

- 分支 `codex/phase1-automatic-memory` 已复读为
  `e145dbe4b6642723d0e63821dcb137af83a5fe1b`；workflow
  [`33153622216`](https://github.com/wangduoyu001/lingji/actions/runs/33153622216)
  的 Windows Python job `98791162437` 真实执行了重命名后的 guard 测试。
- pytest artifact 中出现唯一明确 marker：
  `TASK7E_REAL_POWERSHELL_RELEASE_ENTRY PASS events=preflight scale-env=0 scale-command=0`。
  该测试通过真实 PowerShell 进入 `scripts/validate.ps1`，非零返回并命中
  `BLOCKED_4R2_REQUIRED`；scale-env/scale-command 均未发生。此前无 runtime 的本机
  结果仍为 `BLOCKED_POWERSHELL_RUNTIME_UNAVAILABLE`。
- Workflow 总体 `failure` 不得改写：Python full suite 约 35% 处有既有 Windows
  测试失败；Desktop smoke 失败于 `Navigation is missing 主动投喂`。Task7E entry
  证据单独结论为 `EXECUTABLE_ENTRY_EVIDENCE_PASS`，不代表 P0、release、4R2、100k、
  Mac、Artifact 或 Phase 1 通过。详见上述 Task7E 报告。

## 2026-08-28 · Task 6V · packaged automatic-memory closeout

- Task6R 产品 HEAD `684398e2b56447203ff6b77b4e93cae2c07b38f2` 已修复
  terminal `snapshot-owned` temporary cleanup；Task6R focused `6 passed`。
  Task6V 仅修改现有 integration/acceptance harness 与 E2E 测试等待，不改
  `src/`、Desktop 产品、数据库、队列、API、检索或数据权威。
- Packaged gate `./.venv/bin/pytest -q tests/integration/test_automatic_memory_packaged_flow.py --tb=short -x`
  从独立临时 roots 连续两次 GREEN：`2 passed, 1 warning, 294.47s` 与
  `2 passed, 1 warning, 295.59s`。每次覆盖十场景、30%/70% 真实 crash/restart、
  原 scan `20/20`、transient=0、raw 64hex hash、自然 identity/status parity、
  fallback=false、queued/duplicates=0、PID/child/port/log cleanup、Gateway/
  Hybrid/MCP/ContextPack lexical degradation、revoke/expiry current/history/as_of/
  version 与 heartbeat instance/generation。
- Task6Q/H/S/A、Task6L/M/P/R、automatic-memory runtime/scheduler/snapshot/resume/
  source/watcher/adapter/Control/MCP/context/Work Fact 与 Task4 reset focused
  matrix：`376 passed, 3 warnings`。Desktop build、runtime/source/repair/Work Fact/
  memory-review smokes 与 rendered E2E 通过；compileall、diff-check、acceptance
  sync、local handoff 通过。E2E 仅将 `networkidle` 改为 DOM load + 既有 heading
  readiness，因认证轮询使 network-idle 不具确定性。
- 当前自动化 disposition：`AUTOMATED_ACCEPTED / READY_FOR_TASK7`。仍不得宣称
  release、Artifact、live 8766/8767、Production/Vault 或 owner acceptance；
  `LOCAL_EXECUTION_TASK.md` 保持 `IDLE`。

## 2026-08-28 · Task 6Q · Trusted lifecycle projection correctness

- Task6P final review 的唯一 Important 已复现并收口：callback lifecycle projection 不再从
  payload/result/error 的显式 lease 敏感键值收集 replacement。移除
  `_lease_material_from_explicit_keys()` 旁路；单一 `_notify_lifecycle()` projection API
  仅接收内部 claim 调用链显式传入的 trusted material。
- trusted material 仅接受当前 queue claim 的 32 位小写 hex lease token 及其对应 64 位
  SHA-256 fingerprint，最多 2 项且格式/关联严格校验；direct execute 无 claim，trusted list
  为空，只递归移除 allowlist 敏感键，不替换普通正文。cycle/depth/node/string fail-closed
  边界保持不变。
- RED 覆盖恶意 short/long/合法形状但不受信的 payload lease 值、nested/list/tuple、direct
  execute、可信 internal token 及普通 token 文本；产品/测试 commit `de412d5`。Task6P
  历史 `FAIL / BLOCKED_AT_REPAIR_CAP` 保留，Task6 仍 `IN_PROGRESS / NOT_ACCEPTED`，Task6V
  packaged 30/70、live/Artifact/Production/Vault/owner acceptance 仍未执行。
- 本轮回归要求：Task6P/L/M、pipeline/queue/worker/runtime、Control/MCP、Work Fact、
  structured 矩阵；Desktop static/source/build/rendered；compileall、diff-check、acceptance
  sync、local handoff。任何 full/release 或 rendered 环境失败须如实记录，不得改写历史结论。

## 2026-08-28 · Task 6P · Repair Round 1 final independent review

- 独立终审报告：`.superpowers/sdd/2026-08-27-phase1-product-landing/task-6p-final-review.md`；审查 tree `33f6ffa407badda2531228a651aea6762dd4cfac`、repair product/tests `924ac0c433a5d1029cce456cec1e6f24ef7dc7ba`，结论 `FAIL / BLOCKED_AT_REPAIR_CAP`，Critical=0、Important=1、Minor=0。Task6P 保持 `NOT_ACCEPTED`，Task6 保持 `IN_PROGRESS / NOT_ACCEPTED`。
- Fresh focused `10 passed`；affected backend matrix `266 passed, 7 warnings`；完整无筛选 pytest `1359 passed, 11 skipped, 7 failed`。两项既有 `structured_evidence_lexical` 的 `SimpleNamespace` 缺 `vault_path` failure 在 repair tree 与 base `d61acdf` 均独立复现，未通过 deselect 掩盖；其余 full-suite failures 均为既有无关边界。
- Desktop `test:memory-sources-repair`、`test:memory-sources`、build、rendered `test:e2e:memory`、compileall、diff-check、acceptance sync、local handoff 均 PASS。未执行 live 8766/8767、Artifact、release、Production/Vault 或主人验收。
- I1：`_lease_material_from_explicit_keys()` 收集任意显式 lease-key 字符串，未限制值的格式、大小或数量，随后 callback projection 对 job/result/error 做全局替换；攻击者提供 `lease_token: "a"` 会把普通正文 `a cat...` 过度替换。该 Important 违反 ordinary text 保持与合理 bounded material 边界；Repair Round 1 已用尽，故 `BLOCKED_AT_REPAIR_CAP`。Task6L/M blocked 历史、Task6V packaged 30/70 及 live/Artifact/Production/Vault/owner 边界不改写。

## 2026-08-28 · Task 6P · Queue persistence lease-material redaction

- 本轮是全新有界 Task6P，不改写 Task6M `FAIL / BLOCKED_AT_REPAIR_CAP` 或
  Task6L `FAIL / BLOCKED_AT_REPAIR_CAP` 历史，不增加功能、数据库、队列、ledger、API、UI、
  检索或记忆事实源；`LOCAL_EXECUTION_TASK.md` 保持 `IDLE`，不启动 live 8766/8767、Artifact、
  Production、Vault 或主人数据。
- 现有 `src/extraction/queue.py` 的单一递归 scrubber 作为持久化与 ordinary projection 边界：
  仅移除明确 lease 键/别名，精确替换本次已知 token/fingerprint；mapping/list/tuple 循环、深度、
  节点和超长字符串有界，未知对象继续遵循既有 JSON serializer 边界，不调用 `repr()`。complete/fail/
  cancel-running 在同一事务读取当前 token 与 durable fingerprint，先 scrub result/error 再清 current
  lease；enqueue/force/enqueue-authorized payload/options 复用同一边界。ownership receipt、private
  worker seam、Task6L durable fingerprint 保持。
- Extraction pipeline 的 complete/fail/process summary、lifecycle callback 与错误日志复用同一
  known-material scrub，避免在 queue 写入已脱敏后由 MCP/process_pending/log 再次泄漏。
- RED：新增 Task6P 用例在旧实现真实 `3 failed`；GREEN：`tests/test_task6p_queue_persistence_redaction.py`
  目标覆盖 terminal complete/fail、retrying error、payload/options、cancel-running、循环/深度/节点
  边界与普通含 `token` 文本。Task6L/queue/worker/runtime/Control/MCP/structured/work 及 Desktop
  矩阵须在产品与文档提交后复读；未执行 live/Artifact/release/owner acceptance。
- 报告：`.superpowers/sdd/2026-08-27-phase1-product-landing/task-6p-report.md`；Task6 仍
  `IN_PROGRESS / NOT_ACCEPTED`，Task6V packaged 30/70、live/Artifact/Production/Vault/owner
  acceptance 仍待后续。

## 2026-08-28 · Task 6P · Independent review disposition

- 独立审查报告：`.superpowers/sdd/2026-08-27-phase1-product-landing/task-6p-review.md`；审查
  HEAD `815a3bb5c0d245f6f33a984e7349e927b0090418`，产品/测试
  `19525638ba3f33223fac005aa258f33dd2eb6091`。结论 `FAIL /
  REPAIR_ROUND_1_AUTHORIZED`，Critical=0、Important=1、Minor=0。
- Fresh Task6P focused `5 passed`；expanded backend `279 passed, 3 warnings`；Desktop
  source/rendered/build、compile、acceptance sync、local handoff 通过。I1：pipeline
  lifecycle callbacks 仍接收带 plaintext `lease_token` 的内部 claimed job；direct
  `execute` callback 仍透传显式嵌套 lease key。仅授权最多一轮 bounded lifecycle
  projection repair，保留内部 worker lease seam 与 ordinary chat text 行为。
- Task6P 保持 `NOT_ACCEPTED`，Task6 保持 `IN_PROGRESS / NOT_ACCEPTED`；Task6L/M 历史
  disposition、Task6V packaged 30/70、live/Artifact/Production/Vault/owner acceptance
  均不改写或提前宣称。

## 2026-08-28 · Task 6L · Durable Lease Ownership Receipt

- 本轮是 Task6M `FAIL / BLOCKED_AT_REPAIR_CAP` 之后的新有界架构任务，不改写
  Task6M 历史、不增加用户功能，不新增数据库/队列/ledger/API/UI/检索/记忆事实源。
  `LOCAL_EXECUTION_TASK.md` 保持 `IDLE`；不启动 live 8766/8767、Artifact、
  Production、Vault 或主人数据。
- 在现有 `extraction_jobs` 做向后兼容的 nullable
  `last_claim_lease_fingerprint` migration。claim 与现有随机 lease token 同事务写入
  SHA-256 指纹；complete/fail/release/release_stale 仅清 current lease，保留最近 claim
  指纹；retry/force re-enqueue 的新 generation 清理旧指纹，防旧 lease 授权新 marker。
- v1 marker 删除须同时证明 job id、marker lease hash、durable last-claim fingerprint
  与同目录 content-addressed raw hard-link identity；running 还须 current lease 匹配。
  terminal/queued/retrying/dead/expired 的 WRONG lease、NULL fingerprint、旧 generation
  和 foreign marker 均保留；legacy UUID marker 继续使用 Task6M 的严格 raw proof。
- root exists/is_dir/is_symlink、iterdir、lstat、raw hash/open、queue read、unlink 等
  reconcile 边界异常 catch `Exception` 并 fail closed；receipt 仅允许通用错误码，不含
  exception string、path、marker、job、lease 或 token。pipeline/worker/runtime 继续通过
  既有 cleanup_pending/cleanup_error 可重试；service/MCP/public queue DTO 不暴露 lease
  token 或 fingerprint。
- RED：`tests/test_task6l_durable_lease_receipt.py` 首轮 `8 failed`；GREEN：Task6L
  focused `11 passed`。Required backend regression：Task6L/6M/runtime、queue/worker/
  snapshot/resume/scheduler/Task6H/Task6S/structured/work 共 `218 passed, 2 warnings`。
  Desktop `npm run test:memory-sources-repair`、`test:memory-sources`、`build` 与
  rendered `test:e2e:memory` 均 PASS；compileall、diff-check、acceptance sync、local
  handoff 需在文档同步后复核。
- 失败/限制：未执行 packaged 30/70（延期 Task6V）、release、live、Artifact、真实
  8766/8767、Production/Vault、主人观察；Task6 保持 `IN_PROGRESS / NOT_ACCEPTED`。
  产品/测试 commits `4fd2386`, `382091b`；报告 `.superpowers/sdd/2026-08-27-phase1-product-landing/task-6l-report.md`。

## 2026-08-28 · Task 6L · Independent review

- Review report：`.superpowers/sdd/2026-08-27-phase1-product-landing/task-6l-review.md`，审查
  HEAD `880bd8c1beeddfda0b0c76752038ca7da521adfe`、产品/测试 `4fd2386`、`382091b`。
  结论 `FAIL / NEEDS_FIXES`，Critical=0、Important=1、Minor=0；Task6L
  `NOT_ACCEPTED`，Task6M 历史 `FAIL / BLOCKED_AT_REPAIR_CAP` 不变，Task6 仍
  `IN_PROGRESS / NOT_ACCEPTED`。
- I1：普通低层 queue `get/list` 与等价 raw reads 仍暴露 plaintext `lease_token` 和
  `last_claim_lease_fingerprint`；Control/Capture/MCP DTO 已脱敏但不能替代普通 queue
  read 边界。仅授权一轮有界 Repair Round 1，要求保留 worker 内部 lease 行为且补 direct
  queue/API/MCP 回归，不新增第二 DB/queue/fact source。
- Fresh evidence：Task6L focused `11 passed`；受影响 backend `218 passed, 2 warnings`；
  Desktop static/build/rendered、compile、diff-check、acceptance sync、local handoff 均
  PASS。未执行 live/Artifact/release/8766/8767/Production/Vault/owner；
  `LOCAL_EXECUTION_TASK.md` 保持 `IDLE`。

## 2026-08-28 · Task 6L · Repair Round 1 — public lease projection boundary

- Review record：`9edb9eab98b5abf58999b0e16d09ece729c2e45e`（审查产品 baseline
  `880bd8c1beeddfda0b0c76752038ca7da521adfe`），结论 `FAIL / NEEDS_FIXES` 仅含
  I1。Task6L 仍 `NOT_ACCEPTED`；Task6M 历史 `FAIL / BLOCKED_AT_REPAIR_CAP` 不改写，
  Task6 仍 `IN_PROGRESS / NOT_ACCEPTED`。本轮只修改 queue/public projection 边界，
  不新增数据库、队列、ledger、API、UI、检索或记忆事实源。
- RED：新增 ordinary `queue.get()`/equivalent read assertion 在旧代码真实暴露
  `lease_token`；GREEN：产品/测试 commit `2daac07` 引入私有
  `_get_claimed_job_internal()` 当前 lease seam，并令普通 `get/list/list_page/`
  `get_by_idempotency_key`、完成/失败/释放/取消返回及 Control/MCP DTO 递归移除 lease
  token/fingerprint（含 nested result/error 值遮蔽）。`ownership_receipt()` 仍是 durable
  fingerprint 的唯一 ownership predicate；worker claim/heartbeat/complete/fail 流程保持。
- 验证：repair focused queue/MCP/capture `34 passed`；required backend matrix
  `219 passed, 2 warnings`；Desktop `test:memory-sources-repair`、`test:memory-sources`、
  `build`、rendered `test:e2e:memory` PASS；compileall 与 `git diff --check` PASS。
  `LOCAL_EXECUTION_TASK.md` 保持 `IDLE`，未启动 live/Artifact/Production/Vault。

## 2026-08-28 · Task 6C Repair Round 1 · blocked cleanup receipt

- Fresh review `3fd8059da4ed10b8a1fcd0581793bd0fb2d177ee` 要求 I1–I6 修复。
  已执行 packaged `-x`，首个真实失败发生在 crash/recovery matrix：原 sidecar
  被真实 PID kill、recovery scan 完成 `20/20`、runtime pause 且 recovery
  sidecar stop 后，`storage/raw/.automatic-memory-<random>.json` marker 仍为
  `2,640,287` bytes，terminal/stop inventory 非空。
- 这是现有产品 cleanup seam 缺陷：`ConsistentSnapshot` 只回收
  `.snapshot-owned-*`，不回收该 automatic-memory marker。harness 不能直接
  unlink 来掩盖真实进程清理问题；未授权产品修改，故 Task6 保持
  `IN_PROGRESS / NOT_ACCEPTED`，先前 `PASS_AUTOMATED / READY_FOR_TASK7` 仅为
  历史状态，已被当前 blocker supersede。
- 本轮未提交未验证的 497 行 harness 改动，测试恢复到已知
  `6eb469fefafe0a33e6ac65f765c7663741883811`。报告
  `.superpowers/sdd/2026-08-27-phase1-product-landing/task-6c-report.md` 已补充
  blocker；不宣称 release、Artifact、live、Production/Vault、owner PASS。

## 2026-08-28 · Phase 1 Product Landing · Task 6C Deterministic Crash-Recovery Receipt

- 本轮是 Task6 最终独立 bounded Acceptance gate，基线为 Task6H accepted
  head `c1cd4453e407afc160e509c9fb1e165845577872`；测试提交
  `6eb469fefafe0a33e6ac65f765c7663741883811`。先保留真实 RED：旧 packaged
  crash matrix `1 failed, 1 passed, 1 warning`，终态 identity `2 != 1`，诊断为
  crashed scan 与后续 audit scan 混淆、dummy PID 和 restart 后 unconditional
  manual POST race，不据此归因产品重复。
- 允许范围仅为随机 loopback 临时 Acceptance roots、真实
  `run_packaged_control_api.py` sidecar、持久 StateDB/queue/raw/structured/read
  model 与现有 retrieval；30%/70% 各 20+ 文件，按持久 progress/total 与真实
  sidecar PID kill，restart 优先等待 `run_on_start` lease recovery，manual
  POST 仅作 bounded fallback 且必须复用原 scan_id。终态立即 pause runtime 以
  隔离正常周期 audit；不改 production default、DB lease、schema、API、
  scheduler/job system、retrieval/promotion/UI。
- GREEN：两次 fresh 完整 packaged 命令均 `2 passed, 1 warning`（265.89s、
  266.73s），每次执行十场景与双 crash roots；Task6H/S/A 及
  scheduler/checkpoint/lease/cron/startup recovery `155 passed, 2 warnings`。
  Desktop build、runtime/source/work-fact/memory-review smokes、rendered E2E、
  compileall、diff-check、acceptance sync、local handoff 均通过。
- 四个 raw receipts：round1 30% `src-9d075cefb0ab4a3186bc869835794c23` /
  `scan-a5d21ae042164427a7dccbcddd72e37a`，PID `45100→45102`，barrier
  `6/20`；round1 70% `src-6b6131db26f5466aacf9a40f30a08ebc` /
  `scan-57b23a1429744ff89fe68bcf14c642f4`，PID `45108→45110`，barrier
  `14/20`；round2 30% `src-7403e7ca55304e309e9c5c296c73d898` /
  `scan-ca34a2632b1b420997343ea4463e0fd4`，PID `45117→45119`，barrier
  `6/20`；round2 70% `src-0342722c0e984a27b948eebce89e3460` /
  `scan-7eace87d949042b3b598c92b2f002686`，PID `45132→45134`，barrier
  `14/20`。四者均 fallback `false`、terminal `completed 20/20`、jobs `20`、
  duplicates `0`，逻辑 identity/raw hash parity、Work Fact、queued `0`、
  cleanup receipt 均通过。
- Task6 authority 更新为 `PASS_AUTOMATED / READY_FOR_TASK7`；唯一详细报告为
  `docs/TEST_REPORTS/PHASE1_AUTOMATION_UI_GATE.md`，Task6C SDD 仅作交接引用：
  `.superpowers/sdd/2026-08-27-phase1-product-landing/task-6c-report.md`。
  `LOCAL_EXECUTION_TASK.md` 保持 `IDLE`。本条不构成 release、Artifact、live
  8766/8767、Production/Vault、owner 或主人验收；fresh security review
  仍需执行，且本 gate 不再授权 repair。

## 2026-08-28 · Phase 1 Product Landing · Task 6H Repair Round 1 (final)

- 独立审查 `8daf700f4dd5dbea90e32305a67c764420b147d7` 保留 Task6H I2：active Work Fact heartbeat touch/write 失败曾被吞掉并继续报告 running；本轮是 Task6H 唯一授权修复，不修改 packaged crash 30/70 matrix、scan identity harness 或其他 Task6 产品边界，之后不再修复。
- heartbeat callback 现在按 source/work 隔离尝试刷新所有 running scan；任一失败都会在同一现有 `automatic_memory_heartbeats` 行写入 `degraded`、UTC timestamp、reason 与 last_error，调度线程和扫描继续运行；下一次全量刷新成功后自动恢复 running 并清除错误。idle 无 active Work Fact 不误报，事件表不增长。
- Runtime/API/UI 继续使用同一真实 heartbeat 来源；DTO 携带 timestamp、instance、generation、state、last_error，来源页对 degraded、stopped、paused、running、unknown 分别显示检查/已停止/已暂停/持续更新/尚未获得，不把未知状态伪装成健康运行。
- RED：新增 active touch failure 首次为 `running` 而非 `degraded`；GREEN：Task6H focused `8 passed`，覆盖错误持久化、恢复、source 隔离与原有 idle/pause/stop/restart/clock-jump/cadence。Task6 仍 `IN_PROGRESS / NOT_ACCEPTED`；crash 30/70 为外部 Task6 阻塞，不归入本轮产品修复。
- 未执行 live 8766/8767、Artifact、Production/Vault、主人数据或 owner acceptance；报告 `.superpowers/sdd/2026-08-27-phase1-product-landing/task-6h-report.md`。

## 2026-08-28 · Phase 1 Product Landing · Task 6H · durable runtime heartbeat

- 本轮是独立 bounded observability closeout，不修复 Task6S、不启动 live/Artifact/Production/Vault，`LOCAL_EXECUTION_TASK.md` 保持 `IDLE`。在既有 `StateDatabase` 内增加可重建 `automatic_memory_heartbeats` 表；每个 AutomaticMemoryScheduler 实例以 `instance_id + generation` 写入一行，状态包含 `running/paused/stopping/degraded/stopped`、UTC `heartbeat_at`、`reason` 与 `last_error`。
- 复用既有 Cron scheduler thread 的 heartbeat callback，默认 cadence 5 秒以内；heartbeat wake-up 不执行 reconciliation/claim，原有 poll cadence 保持独立。active scan 仅无事件地刷新现有 Work Fact `work_items.updated_at`，idle 不创建 Work Fact/event rows。
- `/api/automatic-memory/runtime` 扩展 `scheduler_heartbeat_at/age/reason/instance/generation/state/last_error`，age 由 UTC timestamp 实算；未来时钟、超过 10 秒、读写失败或调度线程不再刷新均 fail-closed 为 degraded，旧实例行不会被新实例复用。pause 继续 heartbeat，stop 写入 stopped 并停止更新。
- RED：新增 Task6H heartbeat matrix 在缺少 heartbeat cadence 参数/来源时 `3 failed`；GREEN：`tests/test_task6h_heartbeat.py` `6 passed`，覆盖 idle refresh、pause/stop、实例重启隔离、clock jump/DB write failure recovery、active Work Fact 无 event growth 与 reconciliation claim cadence 边界。Task2 lifecycle/API regression `50 passed, 1 warning`，control API/packaged `21 passed, 6 warnings`。
-  measured evidence：focused idle heartbeat age `<=1s`（test cadence `0.1s`），同一 instance row 无增长；heartbeat `0.05s` cadence 下 0.25s 仅 `1` 次 claim（阈值 `<=2`），证明未以 heartbeat 频率执行 reconciliation；active Work Fact 事件数保持不变。报告 `.superpowers/sdd/2026-08-27-phase1-product-landing/task-6h-report.md`。
- Task6 仍为 `IN_PROGRESS / NOT_ACCEPTED`，待 packaged crash 30/70、现有 lexical/semantic scenario、双轮完整证据与独立 fresh review；本轮不宣称 release、Artifact、主人验收或 Production/Vault 验收。

## 2026-08-28 · Phase 1 Product Landing · Task 6A Repair Round 1 (final authorized repair)

- 独立审查 `9ed229461165b748066b9cba3d2ed169af43db56` 保留两个 Important：cleanup retry 必须按 watcher/Cron/source ownership 精确清理并重试 Cron；scheduler `start` 必须与 stop/retry 共用 lifecycle serialization。此轮是 Task 6A 唯一批准 Repair Round 1；之后不再修复，若新审查仍有 Critical/Important 则 `BLOCKED_AT_REPAIR_CAP`。
- 仅修改 `src/automatic_memory/scheduler.py` 与直接生命周期测试 `tests/test_automatic_memory_scheduler.py`。内部错误 ownership 只服务既有 `source_cleanup_errors` 投影，不改变状态/API family；无新轮询、队列、服务、数据模型、promotion、discovery、adapter、snapshot consumer、Work Fact、UI 或 retrieval/vector。
- RED：真实线程化 Cron 首次 cleanup 失败并保持 alive 时，retry 未再次调用 Cron.stop 且无条件清空其他 source error；真实 watcher stop event 未释放时，start 提前返回，复现 `_running=true` 而 Cron 已 stopped。有效行为 RED 为 `2 failed, 1 passed`（测试 setup 修正后的记录）。GREEN：Task6A repair seams `3 passed`；Task2 broader matrix `171 passed, 6 warnings`。
- Truthfulness：Cron 仍活或 cleanup 抛错时保留 degraded/cleanup_pending；只有对应 watcher/Cron owner 被确认释放才清除其错误；start/stop/retry/revoke/shutdown 同一 `_stop_lock` 串行，避免双 watcher/旧 generation 交叉。
- 未执行 live 8766/8767、Sidecar、Artifact、Production/Vault、主人数据或 owner acceptance；`LOCAL_EXECUTION_TASK.md` 仍为 `IDLE`。报告 `.superpowers/sdd/2026-08-27-phase1-product-landing/task-6a-report.md`，产品/测试 commit `efde650e77a4ecda7f7266aefe48b29b9e8712de`。
- Task 5B final review commit `bd2ff43` 已记为 `ACCEPTED_FOR_TASK6` / `ACCEPT_FOR_TASK6`（reviewed product head `8136374`，Critical=0，Important=0，Minor=3 non-blocking）；不改变 Task 6A、Task 6 或 release 的未完成状态。

## 2026-08-28 · Phase 1 Product Landing · Task 6A Lifecycle Closeout

- 本次是 Task 2 final disposition 批准的独立 bounded lifecycle closeout，目标仅关闭 watcher 在 stop/revoke 时迟到退出后残留 scheduler cleanup error 的唯一阻塞；不是 Task 2 Repair Round 3，不新增功能或第二套生命周期/队列/服务。
- 允许产品修改严格限制为现有 `src/automatic_memory/scheduler.py`、`src/automatic_memory/watcher.py`、`src/automatic_memory/source_registry.py` 中证明必要的 cleanup ownership；测试仅补充真实线程/event seam 的 lifecycle 回归；不得修改 discovery、adapter、snapshot consumer、Work Fact、UI、promotion、retrieval/vector、数据模型或 API family。
- RED 必须真实复现：首次 stop/revoke 的 bounded cleanup 观察到 watcher 仍存活并报告 `degraded/cleanup_pending`；线程随后自然退出；第二次 stop/retry/reconcile 清除 stale scheduler cleanup error，并使 runtime、registry、scheduler 对同一 source 一致收敛到 stopped（或当前权威等价终态）。仍存活时不得伪装 stopped；重复 stop/retry 必须幂等且不得创建第二 watcher。
- 自动/集成边界：覆盖迟到自然退出、第二次 cleanup、并发 retry/stop、revoke、scheduler shutdown、process-exit boundary 以及 truthful 状态/心跳/错误原因；使用真实 watcher thread 与 `threading.Event` seam，不以 mock return-value 自证；promotion forbidden background seams 必须保持未调用。
- 失败/清理边界：仅使用 pytest `tmp_path` 与测试线程；不启动 live 8766/8767、Sidecar、Artifact，不访问 Production/Vault/主人数据；每次测试释放事件并等待受管线程退出，验证无 LingJi owned watcher/worker/scheduler 残留；失败保持最小证据，不降低断言或隐藏已知基线。
- 计划验证：Task 6A focused lifecycle tests、Task 2 runtime/scheduler/watcher/packaged composition 回归、Task 3 admission/runtime、Task 4/5 API contract、packaged composition smoke、`compileall`、`git diff --check`、acceptance sync、local handoff；不得宣称 Task 6 或 release 完成。

## 2026-08-28 · Phase 1 Product Landing · Task 5B Repair Round 1 follow-up · list error/empty distinction

- 在最终 I1 修复中增加 Memory Review `listError` 分支：初次候选请求失败且没有旧数据时显示明确错误，不显示“没有待审核记忆”空态；保留既有错误提示与可重试刷新入口。未变更 backend/API；该补丁后的 Memory Review smoke、全 UI smokes、build、rendered E2E、compile/diff/handoff 均通过。

## 2026-08-28 · Phase 1 Product Landing · Task 5B Repair Round 1 · Memory Review loading/provenance evidence

- 审查基线：Task 5B 终审 `9272e60fc5fa4b485831e101f5f1a66573f1498d`。本轮仅修复 I1（候选列表/详情 pending 时诚实 loading、错误/空态区分、迟到详情响应不可覆盖较新选择）与 I2（rendered fixture/DTO 严格对齐现有 `MemoryReviewService._read_candidate()` payload）；不修改 backend、Task4 首页、记忆算法、向量或真实环境。
- RED：延迟 candidates 请求后 `npm run test:e2e:memory` 因缺少“正在读取候选记忆…”失败（1 failed）。GREEN：Memory Review list/detail loading、AbortController/request-id 保护、真实 `relative_path/source_refs/created_at` 与缺失字段“尚未获得”映射的 rendered E2E、build、focused smokes 通过。
- fixture 删除 `source_name/source_session_id/source_message_id/conversation_title/message_excerpt/provenance_at/current_state/history_state/proposal_reason/affected_agents` 等 mock-only 字段；未新增 API。审查 Minor M1/M2/M3 为证据覆盖不足，本轮按最小边界保留披露，未修改。
- 仍未执行 live 8766、Sidecar、Artifact、Production/Vault、主人数据或主人验收；`LOCAL_EXECUTION_TASK.md` 保持 `IDLE`。

## 2026-08-28 · Phase 1 Product Landing · Task 5B · Owner workflow UI

- 基线：Task 5A final review `289d663b619e20df0b5dcd933cc97f11c92679f0` / `ACCEPT_FOR_5B`。本轮仅修改 Desktop Activity、Attention、Memory Review/Inspector、Capture 导航、Context Pack 复制反馈、Work Fact TypeScript DTO 与 fake-server smokes；复用认证 Work API 和既有记忆接口，不新增后端/API、状态源、记忆/RAG/向量能力。
- RED：新增真实 fake-8766 rendered flow 首次运行在 Activity history 文案处超时；基线 Activity 仍请求 `/api/work/current`。GREEN：Desktop build、Task 5B work-fact/memory-review smokes 与 rendered E2E 全部通过；报告见 `.superpowers/sdd/2026-08-27-phase1-product-landing/task-5b-report.md`。
- 渲染场景覆盖 Work History 中文摘要和折叠技术详情、pending resolve 后真实退出列表与失败可见、可读 provenance 和 Inspector 入口、legacy Capture 隐藏、900px 无横向裁切。Task 4 source/repair/runtime/inspector/observation smokes 及 Task 5A backend/Work Fact 回归保持通过。
- 未执行 live 8766、Sidecar、Artifact、Production/Vault、主人数据或主人验收；`LOCAL_EXECUTION_TASK.md` 继续保持 `IDLE`。兼容 `/capture` 路由未删除。

## 2026-08-28 · Phase 1 Product Landing · Task 5A · Owner Work API foundation

- 基线：`7d4e4e1bbeeaf24f5000bac2944a1e6c3502bc48`。本轮仅扩展既有 `WorkStore`、`WorkProjector`、`WorkControlService` 与认证 8766 Work Fact 路由：历史分页、稳定时间线投影和 pending action resolve；不得新增任务状态源/API、修改 UI、记忆/RAG/向量、Task 2/3 runtime、Artifact、真实 8766、Production/Vault 或主人数据。
- RED 必须先由 `tests/test_work_control_api.py` 与 `tests/test_task8_work_fact.py` 覆盖分页边界、重启持久化、时间线顺序/身份、resolve 成功/重放/不存在/非法和 current/history/pending 一致性；GREEN 需运行对应 focused backend matrix、`py_compile`、`git diff --check`、acceptance sync 与 local handoff。
- API 成功只代表真实持久事实已读取或变更；未知数量、时间、来源和下一执行者保持 `null`/“尚未获得”，不得用静态或聚合猜测填充。所有新增路由必须沿用现有认证依赖并复用 `WorkStore`。
- 本轮完成后由独立 Luna 审查；最多一次修复。未执行真实服务、发布版或主人验收，不得宣称产品发布完成。

### Repair Round 1（独立审查 `522d41ba42534ea9c00992acf20e6980ad28b454` 后）

- 仅修复两项 Important：resolve 在同一既有 WorkStore 事务中标记 action 并按 `work_id/action_id/actor=owner` 清理过期主人下一步；来源摘要使用已有工作标题作为可读来源并保留精确 `source_id` 次要诊断，无来源保持 null。并发/重放/重启和不同来源差异均有真实 SQLite 测试。
- RED：`tests/test_work_control_api.py` 修复前 3 个行为测试失败；GREEN：聚焦 Task 5A 矩阵 40 passed、2 warnings；Work/Task8/Capture/automatic-memory Work Fact 回归 102 passed、2 warnings。
- 产品/测试提交：`5e71cda68edfb86eac99804bc66fbfb6540bcb9c`。本轮为最后一次授权修复，不扩大到 UI、记忆/RAG/向量、Task 2/3、Artifact、真实 8766、Production/Vault 或主人数据。

## 2026-08-28 · Phase 1 Product Landing · Task 4C · Home fact closure

- 基准/触发审查：Task 4 final independent review `f3d70084e8dfb8a07e2fe46f7e1008e11cdf7c2d`；本轮是独立的 bounded follow-up，不是 Repair Round 3。仅修改 Home DTO/UI 与既有静态/渲染测试，不改后端/API、队列、CurrentWorkPanel、其他页面、检索/向量、发布或本机任务。
- RED：`observation-first-ui-smoke.mjs` 因旧的 `后台自动运行` 断言失败；`npm run test:e2e:memory` 因 Home 缺少 `本次更新` 失败。GREEN：产品/测试提交 `4aa0b7841dab76fed5c784008c2449808e3648f2` 后，Home 渲染 fake backend 的 `本次新增=1`、`本次更新=2`、`本次跳过=3`、`本次失败=0`，字段缺失时更新/跳过均显示 `尚未获得`，缺少 `queue.running` 时显示 `尚未获得`。
- 计划验证：`npm run build`、`npm run test:memory-sources`、`npm run test:memory-sources-repair`、`npm run test:work-fact`、`npm run test:runtime`、`npm run test:inspector`、`npm exec -- tsx scripts/observation-first-ui-smoke.mjs` 与 `npm run test:e2e:memory`；不得把未执行的真实 8766/Artifact/主人验收写成通过。
- 既有 smoke 的 `codex-workspace-smoke` 基线失败保持原样并单独披露；`LOCAL_EXECUTION_TASK.md` 为 `IDLE`，不启动服务、不访问 Production/Vault、不进行发布或主人验收。本条只证明确定性 UI/build/E2E。

## 2026-08-27 · Phase 1 Product Landing · Task 4 · Chinese automatic-memory source onboarding

- 基线：`8f94a1e`（当前 `codex/phase1-automatic-memory`）；本轮仅修改 Desktop UI、UI DTO/API 投影、既有 observation smoke、package scripts 与 deterministic tests。后端/API、数据库、队列、检索、promotion、Task 2/3 代码均未修改。
- 用户可感知变化：运行观察区新增“记忆来源”；首次成功连接后，若没有已授权来源且后端发现可行动来源，只在本次 App 会话导航一次到来源页。来源页合并 discovered/sources/scans，并将 `available` 显示为“已发现”，只有完成终态扫描才显示“已接管”；过期授权、降级、失败、撤销、不支持和 consent_required 均给出中文下一步。授权严格提交后端需要的 `grant_id/source_kinds/roots/granted_at/owner_confirmed/kind/root`，Generic Inbox/ChatGPT 使用 Tauri 文件夹选择器，不提供自由路径输入。Home 投影发现、授权/当前、活动、本次新增/复用/失败（后端缺少时为“尚未获得”）和记忆状态，技术细节仍留在高级诊断。
- 自动验收：先执行真实 RED `npm exec -- tsx scripts/automatic-memory-sources-smoke.mjs`，因 `memorySourcesApi.ts` 尚不存在而失败（`ERR_MODULE_NOT_FOUND`）；实现后 `npm run test:memory-sources` PASS。该 smoke 运行 DTO 合并、canonical source、所有九种 UI 状态、未知计数、过期授权、action payload、终态证据与无提前成功断言，不是源码 grep。
- 渲染验收：`npm run test:e2e:memory` 使用本地 fake 8766-like HTTP server、Vite 与已安装系统 Chrome，覆盖一次性 onboarding、文件夹选择授权、扫描中进度且无终态成功、完成、失败和重试；PASS。未下载浏览器、未启动真实 8766/Sidecar、未访问 Production/Vault、未执行 Artifact 或主人验收。`npm run build`、`npm run test:work-fact`、`npm run test:runtime`、`npm run test:inspector` PASS。
- 既有 smoke：`npm run test:smoke` 在新增来源 smoke 与 observation smoke 均通过，但既有 `codex-workspace-smoke.mjs` 仍因基线 `CurrentWorkPanel.tsx` 缺少“当前项目”文案而失败；本轮未修改该 Task 3/Work Fact 页面，不将该失败改写为通过。
- 真机/主人确认：`LOCAL_EXECUTION_TASK.md` 仍为 `IDLE`；按规则不启动打包版、8766、Artifact，不接触主人数据。真实 UI、窄窗口主人观察和发布验收待根代理安排；本条不构成产品验收或合并结论。
- 清理/回滚：fake server/Vite/Chrome 测试进程在 finally 退出；测试只使用临时 fixture 状态。回滚本轮产品/tests 提交与本条文档提交，不触碰正式 Vault、raw、memory、Qdrant 或主人设置。

### Task 4 Repair Round 1（独立审查 44b00d3 后）

- 基线/审查：原产品 `2dc03e6`；独立审查 `44b00d3`；修复产品/tests 提交：`5201d6ba2a152713610297769acd73b10e88b28f`。本轮只修改 Desktop onboarding/source UI、polling 请求所有权与 deterministic UI tests；后端/API、Task 2/3、Production/Vault 未修改。
- RED：repair smoke 在 helper 导出尚未实现时为 `ERR_MODULE_NOT_FOUND`；rendered fake-server flow 在 revoked 状态找不到重授权按钮而超时。GREEN：`npm run build`、`npm run test:memory-sources-repair`、`npm run test:e2e:memory`、原 source/work-fact/runtime/inspector smoke 均 PASS。
- 覆盖：成功读取后一次性 onboarding、失败读取有界自动重试且不发生陈旧导航；同 kind 不同 root 与 stale authorization 被拒绝；撤销来源显示真实重新授权；九种状态及 offline/expired/unsupported/paused/failed action gating；post-action fresh snapshot 优先展示；旧轮询请求不得清除新请求；fake server 拒绝缺失/错误 `X-LingJi-Token`，生产 client 使用认证 token。
- 既有完整 smoke：新增 repair smoke、UI/观察检查通过后，保留在既有 `codex-workspace-smoke.mjs` 的 `CurrentWorkPanel.tsx` 缺少“当前项目”断言失败；本轮未修改该无关基线。
- 本轮仍不执行 Artifact、真实 8766、真实 UI/主人观察、Production/Vault；`LOCAL_EXECUTION_TASK.md` 保持 `IDLE`。证据 artifact 提交：`33757d8cda435fbb01ba10b0b82f12e5cdd6faf8`；metadata-only 提交：`3564abaee0da59408c0b97f1cc02487a0b0e5f84`。

### Task 4 Repair Round 2（审查 d5f902a 后，最终产品修复）

- 基线/审查：Round 1 产品 `5201d6b`、Round 1 最终报告 `ac73e26`、本轮审查 `d5f902a`；最终修复产品/tests 提交：`b45b1dd7bf860510473f49388b8424d62de9f787`。本轮仅修复 onboarding 长时重试/断连重置、真实 rendered outage/recovery 与 late-navigation race、paused owner copy、polling late-error identity guard；无后端/API/Task 2/3/CurrentWorkPanel/Artifact/Production/Vault 变更。
- RED：七次临时 source failure 令旧六次预算停在 Overview（`locator.waitFor: Timeout 10000ms exceeded`）；移除 outage Notice 的暂时性 RED 为 `locator.waitFor: Timeout 30000ms exceeded`；I4 repair smoke 在 helper 导出前为缺少 `canPublishRequest` 的 SyntaxError。GREEN：长重试自动恢复、延迟响应导航 race、保留快照的 outage/offline/retry/recovery、paused `已暂停`/`继续扫描`、late ordinary error guard 均由 rendered/repair smoke 通过。
- 自动验收：`npm run build`、`npm run test:memory-sources`、`npm run test:memory-sources-repair`、`npm run test:e2e:memory`、`npm run test:work-fact`、`npm run test:runtime`、`npm run test:inspector`、`observation-first-ui-smoke.mjs` PASS；完整 smoke 在不变的 `codex-workspace-smoke.mjs` `CurrentWorkPanel.tsx` 缺少“当前项目”断言处失败，未修改或弱化该基线。
- 证据边界：rendered harness 使用本地 fake 8766-like server 与已安装系统 Chrome，显式验证 token、离线恢复、九态动作/下一步、授权/扫描终态；不宣称真实 8766、打包版、Artifact、主人观察或 Production/Vault 验收。`LOCAL_EXECUTION_TASK.md` 保持 `IDLE`。
- Round 2 证据 artifact 提交：`963dde9e1985e4f7bc8379d24ef7fe8814c3b193`；metadata-only 提交：`9024cd477e571a0c6fb42e656aa8afaaab5c37d3`。

## 2026-08-27 · Phase 1 Automatic Memory · Task 2 · Packaged runtime composition

- 基线：`5510b4f27b8fd0567f4fd89a7f5ba2f65635bb77`；产品范围为一个 packaged Python 进程内的 `AutomaticMemoryRuntime` 组合、既有 Extraction Worker/Scheduler/Watcher/Checkpoint 生命周期、认证 8766 runtime status 读取和 exact-instance shutdown 接线。
- 约束：runtime/service/worker 共享 canonical `lingji_state.db` 路径与同一个 extraction queue wrapper；不得创建第二逻辑 DB、队列、daemon、端口或调用 `AutoMemoryPromotionService.evaluate/promote/submit/reconcile_incomplete_projections/rebuild_derived_projections`。scheduler heartbeat 当前无可信空闲来源，status 必须 `null` 并说明 unavailable；snapshot consumer、adapter dispatch、terminal extraction 与 Work Fact 留给 Task 3。
- 自动验收：新增 runtime lifecycle、canonical path、认证 status route 与 promotion-seam sentinel 测试；RED 先记录占位实现导致 `3 failed, 14 passed`（随后 GREEN 目标为 runtime + packaged tests 全部通过）。计划回归 `tests/test_automatic_memory_scheduler.py`、相关 control tests、`npm run test:runtime`、`py_compile`、`git diff --check`、acceptance sync 和 local handoff。
- 真机/主人确认：`LOCAL_EXECUTION_TASK.md` 仍为 `IDLE`；本条不启动 Artifact、服务、UI，不访问 Production/Vault，不构成发布验收或合并结论。
- 清理/回滚：测试只使用 pytest 临时目录和 synthetic SQLite；回滚本轮产品/tests 与文档提交，不触碰正式 Vault、raw、memory、Qdrant 或主人配置。
- 增量修复：`c415f5aff067d8f13bc5898f639581142634e2dd` 保证 scheduler stop 抛错时仍停止 worker 并标记 runtime stopped；对应 lifecycle 回归保持通过。
- Repair Round 1：产品提交 `bc34b9da3427906810a46e32fcccd6d5efe4f680` 修复 partial-start cleanup、stop timeout/异常的 `degraded + cleanup_pending` 重试语义、动态授权 source attach、watcher/worker 存活线程可观测性与 never-started pause 状态；新增真实 pipeline/StateDB/service/runtime/worker/scheduler packaged composition 正常与 startup-failure 测试。变更仍不覆盖 Task 3 consumer/discovery/Work Fact/UI/promotion/Artifact/Production/Vault。

## 2026-08-27 · Phase 1 Automatic Memory · Task 0 · Owner-review quarantine repair round 1

- 基线：Task 0 产品/tests `03b959a34e548630c621c14e53f5055b18850e0e`、文档 `9bba461754c7e6e3e12fe28e36feb33974ad08b0`；本轮产品/tests 提交为 `1330fff4cbe40944cdc8727d45addb74e967611f`。先复现两项 Critical：旧 `status=error` decision 会无确认自动恢复 active；无 durable owner approval 的 preparing+linked saga 会被 reconcile 激活。修复仅在既有 recovery seams 增加持久 owner-confirmed 证据门槛；无证据 in-flight saga 使用现有 rollback 语义退出 current，不猜测确认。并检查已有 decision/recovered result、`promote`/`submit` aliases 与 rebuild activation seam；不修改 recovery matrix。
- 风险等级：P0。`evaluate()` 的旧 error/recovered/active 结果无 owner-confirmed evidence 时不再返回 active 或触发恢复；`reconcile_incomplete_projections()` 仅在 durable owner approval 存在时激活 preparing projection；`rebuild_derived_projections()` 不重建无 owner evidence 的 active promotion。明确 `approve(..., owner_confirmed=True)` 仍可激活。
- 自动验收：新增真实 SQLite RED 两项为 `2 failed`（旧 error auto-recovery、无 owner evidence reconcile activation）；修复后 promotion/task4 transaction 为 `99 passed`，promotion/source/memory/lifecycle/timeline scoped regressions 为 `126 passed, 2 warnings`。Recovery matrix 保持未修改；其中原有 link-commit restart activation 断言因 quarantine 预期失败 `1 failed, 14 passed`，不为本轮修复测试而改写。
- 诚实性边界：frozen `quality_gate.py`/runner/e2e 的 automatic-activation assertions 因 quarantine 预期阻塞；本轮不越界修改它们，交由主计划 Task 1 做权威契约重置，不能声称 quality path 不受影响。针对 `tests/evaluation/test_automatic_memory_end_to_end.py::test_real_promotion_uses_opaque_memory_ids_and_scans_all_temporary_sqlite_values` 的 targeted run 仍因预期无自动 link 而失败。
- Fixture hashes 保持 corpus `bc1812fe6444402762d01fed82f6836889868da89101318beee399b90d58de94`、questions `338f5051c43902af1ef1358aebeb356ef1d409284a1aac1d6c289625f75d3612`；`py_compile`、`git diff --check`、acceptance sync 与 local handoff 在文档提交后复读。
- 真机/主人确认：`LOCAL_EXECUTION_TASK.md` 为 `IDLE`；不启动 Artifact、服务或 UI，不读取 Production/Vault，不执行主人观察；本条不构成产品发布验收或合并结论。
- 清理/回滚：仅 pytest `tmp_path` synthetic SQLite；无永久测试数据。回滚本轮产品/tests 提交与本条文档提交，不触碰正式 Vault、raw、memory、Qdrant 或用户配置。完整报告：`.superpowers/sdd/2026-08-27-owner-review-quarantine/task-0-report.md`（ignored）。

## 2026-08-27 · Phase 1 Automatic Memory · Task 0 · Owner-review-only promotion quarantine

- 基准：`5763bc94fc19f93ea2d4f6b280eba14bb2ba5317`；本轮仅在 `src/auto_review/promotion.py` 的 `evaluate(...)` 状态边界隔离自动激活，并更新对应 promotion regressions。Automatic archival and candidate generation continue; automatic activation is quarantined; owner approval is required until a future independently approved recovery gate exists. 不修改 recovery matrix、检索/向量、runner、质量阈值、fixtures、Desktop、自动扫描、Extraction、Artifact、Production 或 Vault。
- 风险等级：P0。完全满足自动激活条件的候选只能产生 `pending_owner_review` 与稳定 reason `automatic_activation_quarantined`，仅写候选/决定审计；不得写 preparing/terminal/rollback/repair、派生 projection 或 message-memory link。既有 `approve(..., owner_confirmed=True)`、拒绝、哈希和 provenance fail-closed 行为保持不变。
- 自动验收：RED 新增隔离测试首次运行 `1 failed`（当前实现返回 `active`）；GREEN promotion/task4 transaction 回归为 `95 passed`。完整 focused regressions、fixture hashes、`py_compile`、acceptance sync、local handoff 与 `git diff --check` 在文档提交前完成并记录于任务报告。
- 真机/主人确认：`LOCAL_EXECUTION_TASK.md` 为 `IDLE`；不启动 Artifact、服务或 UI，不读取 Production/Vault，不执行主人观察；本条不构成产品发布验收或合并结论。
- 清理/回滚：仅 pytest `tmp_path` synthetic SQLite；无永久测试数据。回滚本轮产品/测试提交与本条文档提交，不触碰正式 Vault、raw、memory、Qdrant 或用户配置。完整报告：`.superpowers/sdd/2026-08-27-owner-review-quarantine/task-0-report.md`（ignored）。

## 2026-08-27 · Phase 1 Automatic Memory · Task 0 · Promotion boundary final repair round 2

- 基准：`650f79f4658cf495e42daea37b9de1d3cd801ca4`；产品提交：`b909565f1a44709a6d1e6cd922adaf2908b91642`；本轮仅关闭 Task 5 Repair Round 2 的六项 promotion boundary finding：canonical message 重复 fail-closed、promotion payload 严格 schema、typed provenance 稳定错误、普通 promotion audit 脱敏、direct prepare 证据/metadata 校验，以及 post-commit/recovery 状态保护。不得修改 `quality_gate.py`、runner/CLI、Task 6/4R2、冻结 evaluator/fixtures/questions/thresholds、retrieval ranking/query/filter、Desktop、Artifact、Production、Vault 或本机任务单激活。
- 风险等级：P0。派生投影仍只允许 `preparing → active`，所有消息 link 使用 canonical identity/hash；StateDB/MemoryDB/SourceReadModel 保持可重建与跨库 saga 语义，不新增事实源。
- 自动验收：真实 RED `./.venv/bin/python -m pytest -q tests/test_task4_reset_promotion_transaction.py` 为 `6 failed, 42 passed`（无 collection error）；GREEN 同命令 `48 passed`。变更相关回归 `tests/test_auto_memory_promotion.py tests/test_source_read_model.py tests/test_memory_retrieval.py tests/test_memory_lifecycle.py tests/test_task7_timeline_retrieval.py` 为 `71 passed, 2 warnings`；扩展 promotion/source/memory/lifecycle/timeline 回归为 `154 passed, 2 warnings`；fixture hashes 未修改；`py_compile` 与 `git diff --check` PASS。验收同步与本机 handoff 需在文档提交后复读。
- 真机/主人确认：`LOCAL_EXECUTION_TASK.md` 为 `IDLE`；不启动 Artifact、服务或 UI，不读取 Production/Vault，不执行主人观察；本条不构成产品验收或合并结论。
- 清理/回滚：仅 pytest `tmp_path` synthetic SQLite；无永久测试数据。回滚本轮产品与文档提交，不触碰正式 Vault、raw、memory、Qdrant 或用户配置。完整报告：`.superpowers/sdd/2026-08-27-phase1-product-landing/task-0-report.md`（ignored）。

## 2026-08-27 · Phase 1 Automatic Memory · Task 4R-Reset Task 5 · Promotion provenance visibility atomicity

- 基线：`c0a812efa440cf416821afc30643f2655729dd44`；Repair 1 基线：`263ca2df2beb720b046897cf3c6960731567a34e`；产品提交：`055c4637f2d1c8e7283cdeb39161c23f7e5ef042`，Repair 1 产品提交：`b5d7a482787c47137ea8f12458939f100098e524`。影响范围为既有 StateDB、共享 `lingji_memory.db`、SourceReadModel、Temporal 与 promotion audit；不接触 Production/Vault、runner/CLI/frozen evaluator、Task6/4R2/100k、retrieval ranking、Desktop/UI 或 Artifact。
- 风险等级：P0。派生投影只允许 `preparing → active`，消息 provenance 使用 exact identity/hash，links 采用单事务 batch 与 durable decision owner；StateDB stable event/lease 为 additive migration，跨 StateDB/MemoryDB 仍是可恢复 saga，不宣称跨库 ACID。
- 自动验收：初始 promotion suite 的真实 RED 为 `3 failed`；Repair 1 针对 C1–C3/I1–I5 的新增行为测试在未改产品基线取得真实 `7 failed, 0 collection errors`，修复后 repair suite `42 passed`；focused promotion/context `84 passed`，Task1–4/reset combined `274 passed`，source/memory/lifecycle/timeline `39 passed`。Fixture hashes、`py_compile`、`git diff --check`、acceptance sync 与 local handoff PASS。
- 真机/主人确认：`LOCAL_EXECUTION_TASK.md` 为 `IDLE`，不启动 Artifact、服务、UI，不读取 Production/Vault，不执行主人观察；因此本条不构成验收或合并结论。
- 清理/回滚：仅 pytest `tmp_path` synthetic SQLite；无永久测试数据。回滚本轮产品提交 `b5d7a482787c47137ea8f12458939f100098e524` 与本条文档/报告提交，不触碰正式 Vault、raw、memory、Qdrant 或用户配置。完整证据：`docs/TEST_REPORTS/PHASE1_TASK4R_RESET_PROMOTION.md`；忽略报告：`.superpowers/sdd/2026-08-26-task4r-reset/task-5-repair-1-report.md`。

## 2026-08-27 · Phase 1 Automatic Memory · Task 4R-Reset Task 4 · Repair round 2

- 基准：`00191f13641753ecac511240fe8fc715140a44c0`；本轮仅修复 Task 4 Repair 1 review 的 child/root snapshot races、same-size second-pass mutation、reason hostile-input 与 FD ownership 缺口。
- 风险等级：P0。保持 primitives-only；不得修改 runner/CLI/e2e/history、AcceptanceRoots、cleanup inventory、Task 5/6、Task4R2、release/100k、Production/Vault、冻结 evaluator/fixtures/retrieval。
- 自动验收：先复现 Repair 1 C1/I1/I2/I3/M2 RED；focused adversarial count 必须超过 70，随后执行 frozen gate、Task 1–3 regressions、当前 e2e/historical visibility、fixture hashes、diff/acceptance/local-handoff。
- 清理/回滚：仅测试自有临时 roots；ignored 报告写 `.superpowers/sdd/2026-08-26-task4r-reset/task-4-repair-2-report.md`，不得 force-add。
- Repair round 3 基准：`4654926e546c1bb23bd30826f6ca59b33f2e8bf1`；仅收敛 anchored helper 单次 FD ownership、root 初始/最终 fstat 稳定错误、EvaluationReport hostile/malformed fail-closed 与 writer stream-stage 异常，并补充 snapshot-point 文档/对抗测试；不得修改 runner/CLI、Task 5/6/4R2、release/100k、Production/Vault、冻结 evaluator/fixtures/retrieval。
- Repair round 3 自动验收：focused adversarial matrix 必须保持超过 70 collected，并覆盖 close double、root fstat、hostile report、fdopen/write/flush/close/replace/cleanup/parent-close、snapshot next-capture/diff；随后执行 frozen gate、Task 1–3 regressions、当前 e2e/historical visibility、fixture hashes、diff/acceptance/local-handoff。
- Repair round 3 清理/回滚：仅测试自有临时 roots；ignored 报告写 `.superpowers/sdd/2026-08-26-task4r-reset/task-4-repair-3-report.md`，不得 force-add。
- Repair round 4 基准：`9b2c9d2d3dc5f4944443385fb3bc51950545f9c0`；仅修复 admission identity 与首个 anchored root FD 绑定、exact/guarded readiness 和逐次 gate verdict 校验、late publication RuntimeError 稳定化；不得修改 `quality_gate.py`、runner/CLI、Task 5/6、4R2、Production/Vault、冻结 evaluator/fixtures/retrieval。
- Repair round 4 自动验收：先复现 admission replacement、hostile readiness/verdict、late fsync/cleanup 的真实 RED；focused adversarial matrix、frozen gate、Task 1–3 regressions、当前 e2e/historical visibility、fixture hashes、diff/acceptance/local-handoff 均需复核。
- Repair round 4 清理/回滚：仅测试自有临时 roots；ignored 报告写 `.superpowers/sdd/2026-08-26-task4r-reset/task-4-repair-4-report.md`，不得 force-add。

## 2026-08-27 · Phase 1 Automatic Memory · Task 4R-Reset Task 4 · Repair round 1

- 基准：`6c475b99ffe112ce5845f01a036a5e00ef583020`；本轮仅修复 Task 4 independent review 的 C1/C2/I1–I5：POSIX anchored dir-fd sentinel/writer、无安全平台 fail-closed、双哈希内容竞态、EvaluationReport 结构校验、directory fsync 错误传播、序列化稳定错误与 reason allowlist。
- 风险等级：P0。不得修改 `run_quality_gate` return/lifecycle、CLI、e2e/historical callers、AcceptanceRoots、cleanup inventory、Task 5/6、Task4R2、release/100k、Production/Vault、冻结 evaluator/fixtures/retrieval。
- 自动验收：先复现所有 C1/C2/I1–I5 真实 RED；扩展 focused adversarial matrix，随后运行 frozen gate、Task 1–3 primitive regression、当前 e2e/historical visibility、fixture hashes、cumulative diff/acceptance/local-handoff。
- 清理/回滚：仅测试自有临时 roots；ignored 报告写 `.superpowers/sdd/2026-08-26-task4r-reset/task-4-repair-1-report.md`；不 force-add，不接触主人数据。

## 2026-08-27 · Phase 1 Automatic Memory · Task 4R-Reset Task 4 · Readiness envelope and protected-tree gate eligibility

- 基准：`55fdd044809b262c59b68d7d37b02d7239978db8`；本轮仅实现四态质量证据 readiness、冻结 evaluator 的 fail-closed envelope finalizer、测试根限定的 ProtectedTreeSentinel 与低层原子 JSON writer。
- 风险等级：P0。不得修改 `run_quality_gate` 公共返回/lifecycle、e2e/historical callers、AcceptanceRoots、cleanup inventory、Task 5/6、Task4R2、release/100k、Production/Vault、冻结 evaluator/fixtures/retrieval。
- 自动验收：先取得 `tests/evaluation/test_task4_reset_readiness.py` 真实 RED；GREEN 覆盖 state truth table、gate-call eligibility、sentinel root/symlink/race/mutation contract、atomic writer fsync/replace/failure cleanup；随后执行 brief focused/regression/visibility checks、fixture hashes、diff/acceptance/local-handoff。
- 清理/回滚：仅测试自有临时 roots；ignored 报告写入 `.superpowers/sdd/2026-08-26-task4r-reset/task-4-report.md`；不接触主人 Production/Vault 或真实任务单。

## 2026-08-27 · Phase 1 Automatic Memory · Task 4R-Reset Task 3 · Repair round 4

- 基准：`e42fd0b0a4825bc39263b344b2ad43c36f768b3d`；产品提交：`bea44958440a5a556d9ae2a6229db54bd80a4c7f`；仅修复 independent review I9/I10：批次 opaque ID 碰撞 fail-before-persist 与全存储 scanner 的 raw/decoded/物理 body 边界。
- 风险等级：P0。批次先预计算一对一 opaque memory ID→fact bridge，碰撞或重复 fact 在任何 candidate/document/link/event 持久化前 hard fail；不得进入 Task 4–6、4R2、MCP parity、100k、Artifact、Production、Vault 或 retrieval 调参。
- 自动验收：直接覆盖相同生产身份碰撞、嵌套 `content`/`text` evaluator metadata、Unicode escaped fact/citation、已知 plain body marker 与 metadata/event marker；真实 runner 仍扫描三份临时 SQLite 的每张表/每列/每值并正向验证非空晋级链。
- 证据：RED `2 failed, 41 passed, 1 warning`；GREEN focused `47 passed, 1 warning`；brief regression `58 passed, 1 warning`；历史 rejected Task4R1 pair `5 failed, 10 passed, 1 warning`，保留并延期。
- 清理/回滚：仅测试临时 SQLite/raw/vault；报告继续由 `.superpowers/` 忽略；不接触主人数据。产品 commit：`bea44958440a5a556d9ae2a6229db54bd80a4c7f`；正式文档 commit 随本条目提交。

## 2026-08-27 · Phase 1 Automatic Memory · Task 4R-Reset Task 3 · Repair round 3

- 基准：`e3d96d67a179a7ef746452611c86f21dedb17659`；产品提交：`b2e2bfa`（完整 SHA 由提交记录复读）；仅修复 independent review I8 的 quality-runner 身份污染与真实临时存储快照测试缺口。
- 风险等级：P0。真实 promotion path 使用由 source/conversation/message/content hash 生产身份输入生成的 opaque memory ID；仅在内存桥中映射回 frozen fact ID。不得进入 Task 4–6、4R2、MCP parity、100k、Artifact、Production、Vault 或 retrieval 调参。
- 自动验收：全表全列扫描 SourceReadModel/MemoryDatabase/StateDatabase 临时 SQLite，拒绝 frozen fact/citation、fixture/evaluator keys 与 expected/forbidden labels；正向证明派生文档、message-memory links、active promotion event 和 opaque→fact registry bridge 非空。
- 证据：RED `1 failed, 32 passed, 1 warning`；GREEN focused `33 passed, 1 warning`；brief regression `58 passed, 1 warning`；历史 rejected Task4R1 pair `5 failed, 10 passed, 1 warning`，保留并延期。
- 清理/回滚：仅测试临时 SQLite/raw/vault；报告继续由 `.superpowers/` 忽略；不接触主人数据。产品 commit：`b2e2bfa`；正式文档 commit 随本条目提交。

## 2026-08-27 · Phase 1 Automatic Memory · Task 4R-Reset Task 3 · Repair round 2

- 基准：`7175a37c0446e04be91ab950e0f8a680ed12c9b9`；仅修复 independent review I6/I7 与 M2 存储快照测试缺口。
- 风险等级：P0。不得进入 Task 4–6、4R2、MCP parity、100k、Artifact、Production、Vault、冻结文件/evaluator 或 retrieval 调参。
- 自动验收：selector 未知 fact/citation 在评分前抛出并阻断报告；所有 persisted internal/external/corpus composite 表示必须三字段 exact string、非空且无周围空白，partial/malformed fail-closed；真实临时 SourceReadModel/MemoryDatabase/StateDatabase import/promotion 快照不得出现 fixture/evaluator labels 或 fixture 生命周期覆写。
- 证据：RED focused `7 failed, 25 passed, 1 warning`（修正快照分页测试后额外暴露既有 fixture supersession 写入）；GREEN focused `32 passed, 1 warning`；brief regression `58 passed, 1 warning`；历史 rejected Task4R1 callers 仍单独延期。

## 2026-08-27 · Phase 1 Automatic Memory · Task 4R-Reset Task 3 · Repair round 1

- 基准：`6f8ddb00df11610316a798faee11e26a052c6463`；仅修复 Task 3 independent review 的 I1–I5 与明确纳入的 canonical whitespace Minor。
- 风险等级：P0。不得进入 Task 4 readiness、Task 5 promotion state machine、Task 6 runner reset、4R2、MCP parity、100k、Artifact、Production、Vault 或 retrieval tuning。
- 自动验收：raw citation 五字段强制且逐项相等；composite 表示冲突和 link 冲突 fail-closed；每个真实 Gateway pack 每问只 selector 一次；citation ID 按 corpus citation 集保留；补齐 adversarial/limit/order/>200/snapshot/expectation-mutation 测试；canonical kind/ID 拒绝周围 whitespace。
- 证据：RED focused `5 failed, 19 passed`；GREEN focused `25 passed, 1 warning`；brief regression `58 passed, 1 warning`；历史 rejected Task4R1 callers `5 failed, 10 passed, 1 warning`，保留并延期 Task 6。

## 2026-08-27 · Phase 1 Automatic Memory · Task 4R-Reset Task 3 · Typed ContextPack section identity

- 基准：`24a0920414508e29cabda262bd68e120c9c880fe`；本轮仅新增内存态 typed evidence identity registry/selector，并接入真实 quality Gateway pack。
- 风险等级：P0。不得修改冻结 evaluator/fixtures/questions/thresholds、Task 3 retrieval ranking/query/filter、Task 4 readiness、Task 5 promotion、Task 6 runner reset、4R2、100k、Artifact、Production、Vault 或真实本机任务单。
- 自动验收：先保留 typed registry/selector 的真实 RED；GREEN 覆盖四类 section 的 canonical identity、raw hash/provenance、duplicate/contradiction fail-closed、distinct-fact limit/enrichment、mutation isolation、registry map freezing；随后运行 brief 指定 focused 与 Gateway/ContextPack/MCP 回归、fixture hash、diff/acceptance/local-handoff 检查。
- 清理/回滚：仅使用 pytest 临时目录与内存映射；不得写入主人 Vault/Production 数据。回滚本轮两个提交，不 amend/rebase 既有任务。

## 2026-08-27 · Phase 1 Automatic Memory · Task 4R-Reset Task 2 · Repair round 1

- 基准：`5839fc329a7790da0256809723509c8c5a59407c`; 仅修复 Task 2 composite external identity binding、空内部主键防误就绪、分页完整性和 145-row replay stability。
- 风险等级：P0。不得修改 Task 3 selector/registry、Task 4 readiness、Task 5 promotion、Task 6 runner reset、4R2、retrieval、100k、Artifact、Production、Vault 或本机任务单。
- 自动验收：补充同 raw message ID 跨 source/conversation、composite binding ambiguity、空 source/conversation/message primary ID、pagination total/offset/limit/drift/non-progress 和同批次 replay/no-row-growth 测试；先保留真实 RED，再运行 focused/Task 1 regression。
- 清理/回滚：仅使用测试临时 SQLite/storage/vault；不接触主人数据。repair 追加两个提交，不 amend/rebase 既有 `9a942d3`/`5839fc3`。
- Repair 证据：RED `8 failed, 22 passed`；GREEN focused `30 passed`；Task 1 regression `64 passed`；145-row replay 保持七项 `145`、stable `0`、groups `5`，source/conversation/message counts 与 primary IDs 不增长/不变化。

## 2026-08-27 · Phase 1 Automatic Memory · Task 4R-Reset Task 2 · Stable import audit and intentional dedup groups

- 基准：`597df6711f5e0584fccd6991065177f111bc3746`; 本轮只处理批次范围内的稳定导入审计、内容哈希意图组和 quality harness 的只读匹配/fixture 元数据移除。
- 风险等级：P0。不得修改冻结 evaluator、fixtures、questions、thresholds、retrieval/selector、readiness、promotion policy、runner reset、4R2、100k、Artifact、Production、Vault 或本机任务单。
- 自动验收：新增 `tests/evaluation/test_task4_reset_import_audit.py`，更新 `tests/evaluation/test_automatic_memory_gate_integrity.py`；覆盖缺失/额外/复合外部键重复、来源/会话主键重复、顺序与字段逐项匹配、批次泄漏、确定性内容组、空批次和只读快照。
- 必须先保留真实 RED，再执行 focused GREEN；随后回归 Task 1 ingestion-order/source-model/structured-ingestion/capture 测试、fixture SHA、`git diff --check`、acceptance sync 与 local handoff。
- 真机/规模/Artifact/Production/Vault/主人验收仍为 `NOT_MEASURED`；临时 SQLite/raw/vault 仅由测试创建并清理。回滚仅回退本轮代码/测试与文档提交，不触碰主人数据。
- 本轮证据：focused `20 passed`；Task 1 regression `64 passed`；Generic History `145/145`、七项匹配各 `145`、stable duplicates `0`、intentional groups `5`；历史 rejected caller incompatibilities 保留并转 Task 6。

## 2026-08-27 · Phase 1 Automatic Memory · Task 4R-Reset Task 1 · Repair round 1

- 基准：`75b691b9b2f9ce2d65023db87b25fab7018d9f2b`; repair 仅处理 independent review I1/I2/I3 与 root R4。
- 真实 RED：`./.venv/bin/python -m pytest -q tests/test_task4_reset_ingestion_order.py tests/test_source_read_model.py tests/test_structured_ingestion.py tests/test_capture_service.py` — `11 failed, 53 passed`。失败覆盖 v1 migration DDL 残留、fresh v2 marker、CaptureService 直接 sink double kwargs、非法 ordinal start、text/float/bool-like 存储 ordinal 与缺失 leading ordinal。
- 产品 repair commit：`f105bbf7fb1a96a078ccbbf71f440d3d6b1e5e68` (`fix: harden ingestion migration and validation`)。
- GREEN：同一 focused 命令 `64 passed in 0.59s`；此前 Task 1 focused assertions 全部保留。
- 回归：`tests/test_source_service.py tests/test_automatic_memory_adapters.py tests/test_automatic_memory_resume.py tests/test_extraction_idempotency.py` — `111 passed, 2 warnings in 7.20s`；仅既有 ZIP duplicate-member 与 Pydantic deprecation warnings。
- repair 限制：未执行 Tasks 2–6、Task 4R2、100k、Artifact、Desktop、Production、Vault 或物理验收；本机任务仍 `IDLE`。须由独立复审与 root 复核后再判断 Task 1。

## 2026-08-27 · Phase 1 Automatic Memory · Task 4R-Reset Task 1 · SourceReadModel ingestion-order contract

- 基准：`ec268045004647ae1187abe747e70f2e37bdce9f`; 产品范围仅为 SourceReadModel v1→v2 additive migration, typed identities, batch-scoped ingestion ordinals, StructuredReadModelSink propagation and dedicated ingestion read API.
- 风险等级：P0。不得修改冻结 evaluator/fixtures/thresholds、retrieval ranking/query/filters、Task 4R2、100k、Artifact、Desktop、Production、Vault 或主人验收。
- 自动验收：新增 `tests/test_task4_reset_ingestion_order.py`，并修改 SourceReadModel/structured sink tests for migration, exact order, replay/no-duplicate, pagination validation, safe item shape and typed identity case sensitivity.
- RED captured before product implementation：`./.venv/bin/python -m pytest -q tests/test_task4_reset_ingestion_order.py tests/test_source_read_model.py tests/test_structured_ingestion.py` — collection failed with missing `ExternalMessageKey` export from `src.sources`, caused by absent Task 1 API; existing source test also expects v2 and cannot pass on v1.
- Required GREEN/regressions after implementation：focused command above; `tests/test_source_service.py`, `tests/test_automatic_memory_adapters.py`, `tests/test_automatic_memory_resume.py`, `tests/test_extraction_idempotency.py`; fixture hashes; `git diff --check`; acceptance sync and local handoff checks.
- Cleanup/rollback：tests use temporary SQLite only; no Production/Vault/raw fixture writes. Roll back the two Task 1 commits without touching owner data. Physical acceptance remains `NOT_MEASURED`; `LOCAL_EXECUTION_TASK.md` remains `IDLE`.

## 2026-08-26 · Phase 1 Automatic Memory · Task 4R1 final repair round 5

- 产品 Commit：`5be8d92997a3945dd7d83732a0350cac340c5320`；本条记录与报告随独立 docs commit 写入。
- 影响模块：`quality_gate.py` Gateway identity/readiness and sentinel envelope；`quality_evidence.py` persisted-order/hash audit；`promotion.py` per-call PromotionEvidence and post-link attachment；round-5 integrity/e2e tests.
- 风险等级：P0。不得修改冻结 fixtures、Task 2 evaluator/scorer/thresholds、Task 3 retrieval、4R2、Artifact、Production/Vault 或主人验收。
- 真实 RED：`./.venv/bin/python -m pytest -q tests/evaluation/test_task4r1_round5_final_red.py` — `6 failed, 1 warning` on base `338641a`.
- 新增 GREEN：`./.venv/bin/python -m pytest -q tests/evaluation/test_task4r1_round5_final_red.py tests/evaluation/test_task4r1_takeover_red.py tests/evaluation/test_automatic_memory_gate_integrity.py tests/evaluation/test_automatic_memory_end_to_end.py tests/test_auto_memory_promotion.py` — `63 passed, 1 warning`。
- Gateway-vs-selector 观测：`gateway_calls=200`（100 direct + 100 MCP）、`gateway_empty=200`、`gateway_items=0`；selector `100` 次、`0` 条选出，根因是 Gateway 真空结果而非 selector 丢失。
- Sentinel unavailable：配置的 `vault` 根缺失时记录 `missing protected root: vault`，`production_pollution=null`、`available=false`、`unchanged=null`；不得把不可用证据写成数值零，且不调用任何 acceptance gate。
- 4R2 的 MCP parity、degradation/Qdrant、corruption isolation、context baseline、scale 与主人/Mac/reboot 证据全部 `NOT_MEASURED`；`functional_status=NOT_EVALUATED`、`phase_status=NOT_EVALUATED`。
- 固定 fixture SHA 保持：corpus `bc1812fe6444402762d01fed82f6836889868da89101318beee399b90d58de94`；questions `338f5051c43902af1ef1358aebeb356ef1d409284a1aac1d6c289625f75d3612`。
- 必须回归：round-5 RED/GREEN、takeover RED/GREEN、integrity/e2e/promotion、fixture hashes、`git diff --check`、`scripts/check_acceptance_sync.py`、`scripts/check_local_execution_handoff.py`。

## 2026-08-26 · Phase 1 Automatic Memory · Task 4R1 takeover round 4

- 产品 Commit：`8743356`；本条报告 Commit：`cf4f220`。
- 影响模块：`quality_evidence.py` import/sentinel/readiness value objects；`quality_gate.py` pre-query identity selection and fail-closed evidence validation；`promotion.py` source provenance resolution and compensating unlink; `read_model.py` message provenance resolution and link removal.
- 风险等级：P0。不得修改冻结 fixtures、Task 2 evaluator/scorer/thresholds 或 Task 3 retrieval；不得执行 4R2、Artifact、Production/Vault 或主人验收。
- 真实 RED：`./.venv/bin/python -m pytest -q tests/evaluation/test_task4r1_takeover_red.py` — baseline `7 targeted defects failed, 2 baseline safety checks passed`; failures cover adapter projection audit, pre-query identity map, generic provenance, multi-link rollback, unreadable sentinel, readiness isolation and runner sentinel/readiness integration. The rejected initial draft remains `TDD_ORDER_NOT_MET`.
- 新增 GREEN：同一 RED 文件 `9 passed, 1 warning`；focused integrity/e2e/promotion suite `57 passed, 1 warning`.
- 历史运行质量门结果已由 round-5 更正：配置的 `vault` 根缺失时 sentinel 证据不可用，Production pollution 应记录为 `null` 而非数值 `0`；4R1 未测 MCP/degradation/context baseline/scale，envelope 为 `functional_status=NOT_EVALUATED`、`phase_status=NOT_EVALUATED`，不运行 acceptance gate。
- 固定 fixture SHA：corpus `bc1812fe6444402762d01fed82f6836889868da89101318beee399b90d58de94`；questions `338f5051c43902af1ef1358aebeb356ef1d409284a1aac1d6c289625f75d3612`。
- 必须回归：takeover RED/GREEN、`tests/evaluation/test_automatic_memory_gate_integrity.py`、`tests/evaluation/test_automatic_memory_end_to_end.py`、`tests/test_auto_memory_promotion.py`、fixture hashes、`git diff --check`、`scripts/check_acceptance_sync.py`、`scripts/check_local_execution_handoff.py`。


## 2026-08-26 · Phase 1 Task 4 · Automatic memory quality and scale gate

- 产品 Commit：`fe13550485f044562a8be919c8df33bd916be461`；本条报告 Commit：`27fc74e`。
- 新增真实 100-question quality gate、FastMCP 调用、opt-in 100k scale command；默认 focused 不执行 100k，release 必须设置 `LINGJI_RUN_100K=1`。
- 实测功能状态：`FAIL`（事实召回 18.87%、引用准确率 18.87%；其余主要完整性/安全指标通过）。完整阶段状态仍为 `BLOCKED`。
- 不得修改冻结 corpus/questions、阈值或检索排序来消除失败；Task 3 检索修复需另行立项。

> 每个包含产品代码、运行时、UI、连接器、数据链路、脚本、依赖或发布流程变化的 PR，都必须在本文件顶部追加一条记录。
>
> 记录描述“本次代码变化后，验收必须新增、修改或回归什么”。历史记录不得删除，只能更正明显错误并说明原因。

## 2026-08-26 · Phase 1 Automatic Memory · Task 7 final why scope repair · project/type isolation

- 产品分支：`codex/phase1-automatic-memory`
- 产品 Commit：`4bb5d1ae89806345ff6090bb2103e5e9439d3bf6`
- 影响模块：per-result why exclusion matching
- 风险等级：P0
- 用户可感知变化：相同 conflict key 在不同项目、memory type 或 privacy 下不会交叉出现在彼此的 why 排除列表；省略项目过滤时仍保持每条结果的项目边界。
- 数据或安全边界变化：只收窄解释候选；既有 current/history 数据和权限边界不变。

### 新增或修改的自动验收

- [x] `tests/test_task7_timeline_retrieval.py`：15 passed，新增跨项目共享 conflict key 的 per-result 隔离回归。
- [x] Task 7 相关检索/Gateway/MCP/Project Context 回归：89 passed，2 warnings（既有依赖弃用警告）。
- [x] 涉及文件 `py_compile`、`git diff --check`：PASS。
- [ ] Task 1–6 回归、`scripts/check_acceptance_sync.py`、`scripts/check_local_execution_handoff.py`：根代理在双提交后复读。
- [ ] Qdrant unavailable、真实 Production Vault、主人 UI/M5 真机验收：仍不在本轮范围。

### 回滚

- 回滚：回退产品 Commit `4bb5d1ae89806345ff6090bb2103e5e9439d3bf6` 与本条文档提交；不触碰 Vault、原始聊天证据、Qdrant 正式数据或主人配置。

## 2026-08-26 · Phase 1 Automatic Memory · Task 7 final narrow repair · semantic post-filter closure

- 产品分支：`codex/phase1-automatic-memory`
- 产品 Commit：`3c42cf476fcf91f7f2930fd7b8ca383d7557a5c5`
- 影响模块：unified HybridRetriever lexical/semantic/history post-filter
- 风险等级：P0
- 用户可感知变化：语义候选和 why 排除候选现在对 memory type 与 privacy 缺失/不匹配 fail-closed，不能绕过检索范围泄漏决策或私密内容。
- 数据或安全边界变化：不改变数据存储；继续复用 Memory DB 权威记录与既有 Gateway/MCP 权限边界。

### 新增或修改的自动验收

- [x] `tests/test_task7_timeline_retrieval.py`：14 passed，新增 semantic-only decision/private 泄漏阻断。
- [x] Task 7 相关检索/Gateway/MCP/Project Context 回归：88 passed，2 warnings（既有依赖弃用警告）。
- [x] 涉及文件 `py_compile`、`git diff --check`：PASS。
- [ ] Task 1–6 回归、`scripts/check_acceptance_sync.py`、`scripts/check_local_execution_handoff.py`：根代理在双提交后复读。
- [ ] Qdrant unavailable、真实 Production Vault、主人 UI/M5 真机验收：仍不在本轮范围。

### 回滚

- 回滚：回退产品 Commit `3c42cf476fcf91f7f2930fd7b8ca383d7557a5c5` 与本条文档提交；不触碰 Vault、原始聊天证据、Qdrant 正式数据或主人配置。

## 2026-08-26 · Phase 1 Automatic Memory · Task 7 repair round 3 · why scope isolation

- 产品分支：`codex/phase1-automatic-memory`
- 产品 Commit：`2b8ca4eb9724f3f75b23d797a109847b3c42f4c8`
- 影响模块：why lexical/semantic candidate scope, project/tag/agent filtering, short-Chinese history fallback memory-type filtering
- 风险等级：P0
- 用户可感知变化：`why` 的排除候选现在复用完整检索范围；跨项目、未授权 Agent、标签或 memory type 不匹配的证据不会出现在解释中，也不会泄露来源引用。
- 数据或安全边界变化：只收窄解释候选，不改变历史证据保存或 current 检索语义；不新增事实源。

### 新增或修改的自动验收

- [x] `tests/test_task7_timeline_retrieval.py`：13 passed，新增 Project/Memory Type scope 与短中文 history fallback 隔离回归。
- [x] Task 7 相关检索/Gateway/MCP/Project Context 回归：87 passed，2 warnings（既有依赖弃用警告）。
- [x] 涉及文件 `py_compile`、`git diff --check`：PASS。
- [ ] Task 1–6 回归、`scripts/check_acceptance_sync.py`、`scripts/check_local_execution_handoff.py`：根代理在双提交后复读。
- [ ] Qdrant unavailable、真实 Production Vault、主人 UI/M5 真机验收：仍不在本轮范围。

### 回滚

- 回滚：回退产品 Commit `2b8ca4eb9724f3f75b23d797a109847b3c42f4c8` 与本条文档提交；不触碰 Vault、原始聊天证据、Qdrant 正式数据或主人配置。

## 2026-08-26 · Phase 1 Automatic Memory · Task 7 repair round 1 · temporal and why hardening

- 产品分支：`codex/phase1-automatic-memory`
- 产品 Commit：`f045cdfe3a124de7ea4ed3fa61b41c24ffa00a55`
- 影响模块：timezone-aware temporal parsing, stable current cache identity, bounded why exclusions, explicit authority-conflict handling, project refresh interval closure
- 风险等级：P0
- 用户可感知变化：无时区查询和记忆有效期不再被猜测为 UTC；默认 current cache 不因每次读取时间变化而产生伪造新键；`why` 现在展示同一查询候选集中被状态/时间/权威规则排除的记忆及引用；项目替代会在新决定生效时刻关闭旧决定区间。
- 数据或安全边界变化：保持历史证据和原始正文不删除；当前输出仍只允许安全候选，why 解释有数量上限且不改变当前检索可见性。

### 新增或修改的自动验收

- [x] `tests/test_task7_timeline_retrieval.py`：12 passed，新增 per-result why 排除隔离、显式冲突主题与无关结果回归、非法 temporal mode fail-closed。
- [x] Task 7 相关检索/Gateway/MCP/Project Context 回归：86 passed，2 warnings（既有依赖弃用警告）。
- [x] 涉及文件 `py_compile`、`git diff --check`：PASS。
- [ ] Task 1–6 回归、`scripts/check_acceptance_sync.py`、`scripts/check_local_execution_handoff.py`：根代理在双提交后复读。
- [ ] Qdrant unavailable、真实 Production Vault、主人 UI/M5 真机验收：仍不在本轮范围。

### 回滚

- 回滚：回退产品 Commit `f045cdfe3a124de7ea4ed3fa61b41c24ffa00a55` 及其前置 Task 7 修复提交与本条文档提交；不触碰 Vault、原始聊天证据、Qdrant 正式数据或主人配置。

## 2026-08-26 · Phase 1 Automatic Memory · Task 7 · unified timeline retrieval

- 产品分支：`codex/phase1-automatic-memory`
- 产品 Commit：`344bef7ff1b88c23c0979b113a354bc3148bda6e`
- 影响模块：统一 temporal query contract、MemoryDatabase lexical、Qdrant semantic payload/filter boundary、hybrid post-filter、Core/ContextPack、MemoryGateway、Project Context、MCP
- 风险等级：P0
- 用户可感知变化：检索入口统一支持 `current`、`as_of`、`history`、`why`；当前结果排除被替代/失效/归档内容，历史可按时间找回，`why` 提供权威级别、来源引用、有效期和替代原因。时区偏移和损坏时间元数据按规范化瞬时处理并 fail-closed；语义结果经过同一 SQLite 权威记录复核，不能绕过当前过滤。
- 数据或安全边界变化：保留原始证据和历史记录；项目刷新只在可重建 Memory DB 中写替代/失效链接，不删除 Vault/原始证据；不新增 gateway、retriever、temporal database 或事实源。

### 新增或修改的自动验收

- [x] `tests/test_task7_timeline_retrieval.py`：8 passed，覆盖 current/history/as_of/why、半开区间边界、时区偏移、损坏时间 fail-closed、幂等项目刷新、Gateway/ContextPack 模式传播、语义 stale-only 泄漏阻断、显式冲突键下的权威排序与无关同项目记录保留。
- [x] Task 7 相关检索/Gateway/MCP/Project Context 回归：80 passed，2 warnings（既有依赖弃用警告）。
- [x] Task 1–6 回归：241 passed，3 warnings（既有 zip duplicate、Pydantic、依赖弃用警告）。
- [x] 涉及文件 `py_compile`、`git diff --check`：PASS。
- [ ] `scripts/check_acceptance_sync.py`、`scripts/check_local_execution_handoff.py`：根代理在文档提交后复读。
- [ ] Qdrant unavailable、真实 Production Vault、主人 UI/M5 真机验收：仍不在本轮范围。

### 回归与回滚

- [x] 既有 privacy/project/agent-scope、Core、ContextPack、MCP 和 Qdrant/semantic wiring 回归保持通过。
- [x] SQLite 只作为可重建 lexical/read model；Qdrant 仍为可重建 semantic projection，当前状态由 Memory DB temporal predicate 最终裁决。
- 回滚：回退产品 Commit `344bef7ff1b88c23c0979b113a354bc3148bda6e` 及其前置 Task 7 产品提交与本条文档提交；不触碰 Vault、原始聊天证据、Qdrant 正式数据或主人配置。

## 2026-08-26 · Phase 1 Automatic Memory · Task 6 final repair · candidate-owned evidence self-reference

- 产品分支：`codex/phase1-automatic-memory`
- 产品 Commit：`2663a4cf40c267767036c1e18a90df0f8bd10036`
- 影响模块：derived-memory evidence resolver and candidate promotion policy
- 风险等级：P0
- 用户可感知变化：候选自身 ID、内容哈希、决定/晋级 ID 即使被伪装成既有 evidence event，也不会被当作可验证来源；该候选保持主人审核状态。

### 新增或修改的自动验收

- [x] 预置 `evidence_recorded(entity_id=candidate_id)` 的自引用回归：保持 `pending_owner_review` 并返回 `evidence_reference_unverifiable`。
- [ ] Task 6 focused、Task 1–5 回归、`py_compile`、`git diff --check`、acceptance sync、local handoff：根代理在双提交后复读。

### 回滚

- 回滚：回退 `2663a4cf40c267767036c1e18a90df0f8bd10036` 与对应文档提交；不触碰 Vault、原始证据或主人配置。

## 2026-08-26 · Phase 1 Automatic Memory · Task 6 repair round 1 · fail-closed promotion and replay

- 产品分支：`codex/phase1-automatic-memory`
- 产品 Commit：`939407fc47b4f374bb52de146348180e808a395a`
- 影响模块：promotion risk/confidence policy, existing StateDatabase evidence resolution, derived projection replay and recovery idempotency
- 风险等级：P0
- 用户可感知变化：所有高风险 memory type、非有限/非数值置信度、无法从既有来源/证据事件验证的引用均停留在主人审核；伪造 content hash 被拒绝。清空可重建索引后可从既有候选/决定事件恢复当前派生记忆，失败重试不会重复激活或恢复审计。
- 数据或安全边界变化：证据验证只读取既有 StateDatabase/source read model，不创建第二事实源；重建只恢复 active derived projection，不写 Vault/Core/原始证据。

### 新增或修改的自动验收

- [x] `tests/test_auto_memory_promotion.py`：41 passed，覆盖高风险类型矩阵、bool/字符串/NaN/Infinity 置信度、不可验证证据、真实性哈希、失败后成功恢复幂等和事件重放重建。
- [ ] Task 6 focused、auto-review、memory/retrieval/lifecycle 与 Task 1–5 回归、`py_compile`、`git diff --check`、acceptance sync、local handoff：根代理在双提交后复读。
- [ ] Qdrant/真实 Production Vault/主人 UI 与 M5 真机验收：仍不在本轮范围。

### 回滚

- 回滚：回退 `939407fc47b4f374bb52de146348180e808a395a` 与对应文档提交；不触碰 Vault、原始聊天证据或主人配置。

## 2026-08-26 · Phase 1 Automatic Memory · Task 6 · safe derived-memory promotion

- 产品分支：`codex/phase1-automatic-memory`
- 产品 Commit：`63ee78fb4bcbb7034926356026907fa0c6fd12e0`
- 影响模块：`src/auto_review/promotion.py`, automatic-review candidate provenance, rebuildable `MemoryDatabase` derived projection
- 风险等级：P0
- 用户可感知变化：聊天证据先保存为带来源、置信度、权威、提取器版本和风险标记的候选；只有 `confidence >= 0.90`、有直接用户/当前权威项目证据、可验证来源且无冲突/高风险时，才自动进入可重建 current projection。Core、身份、秘密、权限、医疗/法律/金融/安全及不可逆内容必须主人明确确认。
- 数据或安全边界变化：自动激活只写可重建 `lingji_memory.db` 派生投影，不写 Obsidian Vault、Core Memory 或正式知识；决定和审核事件追加写入既有 `StateDatabase`。主人审批/拒绝使用 expected content hash 防止过期操作；失败投影保持 `error`，不假报激活，原始证据保留。

### 新增或修改的自动验收

- [x] `tests/test_auto_memory_promotion.py`：覆盖阈值、证据、冲突/重复、高风险类别、持久化来源链、幂等、版本重算、主人 hash 确认和投影失败。
- [x] `tests/test_auto_review_core.py` 与相关 memory lifecycle/retrieval 回归不得回归（focused 40 passed）。
- [ ] Task 1–5 focused 回归、涉及文件 `py_compile`、`git diff --check`、`scripts/check_acceptance_sync.py`、`scripts/check_local_execution_handoff.py` 全部 PASS；由根代理在产品/文档双提交后复读。
- [ ] Qdrant/真实 Production Vault/主人 UI 与 M5 真机验收：由根代理另行执行；本任务不读取真实 Vault、不宣称 Phase 1 完成。

### 回滚

- 回滚：回退 Task 6 产品 Commit；只删除可重建派生索引和测试临时数据，不触碰 Vault、原始聊天证据、主人配置或第三方 AI 软件。

## 2026-08-26 · Phase 1 Automatic Memory · Task 5 final closeout · Qdrant retry truth and raw TOCTOU

- 产品分支：`codex/phase1-automatic-memory`
- 产品 Commit：`2fb0d7a4b2a81b1248bf1d81b783e2b26ee30e10`
- 影响模块：Obsidian managed-derived migration, Qdrant deletion retry state, raw ownership/hash/symlink validation
- 风险等级：P0
- 用户可感知变化：Qdrant 删除失败会持续显示 `planned/pending_rebuild`，重复执行会重试并在成功前不假报完成；raw copy 在 backup/unlink 前重新验证路径、regular-file、symlink、ownership 和内容哈希。
- 数据或安全边界变化：TOCTOU mismatch、symlink substitution、ownership change 或 hash change 均保留 raw source；审计保存 pending vector IDs 与真实错误，不删除 Vault 或非授权 raw。

### 新增或修改的自动验收

- [x] Qdrant flaky provider：首次/重复失败保持 `planned + pending_rebuild=true`，成功重试后才 `applied + pending_rebuild=false`，审计 pending IDs 清空。
- [x] Raw symlink substitution 与 changed-hash：两者均返回 planned/error 且源文件或 symlink 保留，外部目标不变。
- [x] `./.venv/bin/python -m pytest -q tests/test_automatic_memory_obsidian.py tests/test_obsidian_memory_scope.py tests/test_obsidian_memory_migration.py tests/test_obsidian_service.py tests/test_vault_layout.py tests/test_memory_retrieval.py tests/test_incremental_index_sync.py`：31 passed。
- [x] Task 1–4 回归：`./.venv/bin/python -m pytest -q tests/test_automatic_memory_source_registry.py tests/test_automatic_memory_snapshot.py tests/test_automatic_memory_resume.py tests/test_automatic_memory_watcher.py tests/test_automatic_memory_scheduler.py tests/test_state_db_scheduler.py`：重跑 108 passed（首次有 1 个既有 scheduler timing flake，重跑通过）。
- [x] Direct import、涉及文件 `py_compile`、`git diff --check`：全部 PASS。
- [x] `scripts/check_acceptance_sync.py`、`scripts/check_local_execution_handoff.py`：全部 PASS。

### 回滚

- 回滚：回退 `2fb0d7a4b2a81b1248bf1d81b783e2b26ee30e10`；不触碰 Vault、Production 数据或主人配置。

## 2026-08-26 · Phase 1 Automatic Memory · Task 5 repair round 9 · import/symlink/move-out hardening

- 产品分支：`codex/phase1-automatic-memory`
- 产品 Commit：`d39372b4e791d514ff5a8c1b2858de4e2cf47278`
- 影响模块：Obsidian package exports, fail-closed scope path handling, scoped incremental lexical synchronization
- 风险等级：P0
- 用户可感知变化：直接导入 `MemoryDatabase` 不再触发 Obsidian migration import cycle；通过 `..` 或外部路径的 symlink 在 canonicalize 前即被拒绝；授权 Obsidian 文件删除或移出 scope 后退出 current lexical retrieval，同时保留非 Vault/chat 投影。
- 数据或安全边界变化：migration exports are lazy-only; scoped sync records an internal rebuildable scope reason and never uses it to retire non-Vault sources.

### 新增或修改的自动验收

- [x] Direct smoke: `./.venv/bin/python -c "from src.retrieval.memory_db import MemoryDatabase; print(MemoryDatabase.__name__)"`：`MemoryDatabase`。
- [x] `./.venv/bin/python -m pytest -q tests/test_automatic_memory_obsidian.py tests/test_obsidian_memory_scope.py tests/test_incremental_index_sync.py`：10 passed，含 import cycle、dotdot symlink、move-out/stale lexical 与 non-Vault 保留。
- [x] `./.venv/bin/python -m pytest -q tests/test_automatic_memory_obsidian.py tests/test_obsidian_memory_scope.py tests/test_obsidian_memory_migration.py tests/test_obsidian_service.py tests/test_vault_layout.py tests/test_memory_retrieval.py tests/test_incremental_index_sync.py`：29 passed。
- [x] Task 1–4 全回归：`./.venv/bin/python -m pytest -q tests/test_automatic_memory_source_registry.py tests/test_automatic_memory_snapshot.py tests/test_automatic_memory_resume.py tests/test_automatic_memory_watcher.py tests/test_automatic_memory_scheduler.py tests/test_state_db_scheduler.py`：108 passed。
- [x] 完整涉及文件 `py_compile`、`git diff --check`、`scripts/check_acceptance_sync.py`、`scripts/check_local_execution_handoff.py`：全部 PASS。

### 回归与回滚

- [x] `src.obsidian` migration classes remain publicly importable through lazy `__getattr__`; retrieval imports do not load migration eagerly.
- [x] Vault canonicalization handles macOS `/var` → `/private/var` aliases without weakening lexical symlink checks.
- 回滚：回退 `d39372b4e791d514ff5a8c1b2858de4e2cf47278`；不触碰 Vault、Production 数据或主人配置。

## 2026-08-26 · Phase 1 Automatic Memory · Task 5 · Obsidian scope isolation and derived migration

- 产品分支：`codex/phase1-automatic-memory`
- 产品 Commit：`e98b724266b3f1d89ffeaa283ef8656a00c70f1c`
- 影响模块：`src/obsidian/memory_scope.py`, `src/obsidian/memory_migration.py`, Obsidian discovery/service, Vault memory entry points, incremental lexical sync
- 风险等级：P0
- 用户可感知变化：普通旧 Obsidian Markdown 不再进入自动记忆投影；仅 `_LingJi/Memory Inbox`, `_LingJi/Memory Library` 或 `lingji_memory: true` 参与，`false` 最高优先级。修改/移入/移出使用同一 fail-closed scope 并刷新可重建 lexical/Qdrant 投影。
- 数据或安全边界变化：迁移仅清理 LingJi 自己的可重建 Memory DB/Qdrant/raw 投影，写入无正文审计标记；dry-run manifest 可校验和回滚。绝不写入、移动或删除 Vault；非 Vault/非 Obsidian raw 与 owner-confirmed/Core 记录保留。

### 新增或修改的自动验收

- [x] `./.venv/bin/python -m pytest -q tests/test_automatic_memory_obsidian.py tests/test_obsidian_service.py tests/test_vault_layout.py tests/test_memory_retrieval.py tests/test_incremental_index_sync.py`：18 passed，Task 5 focused 与 Obsidian/retrieval 回归。
- [x] `./.venv/bin/python -m pytest -q tests/test_obsidian_memory_scope.py tests/test_obsidian_memory_migration.py`：scope、frontmatter/symlink fail-closed、manifest checksum、Vault hash/mtime/权限不变、managed raw ownership、idempotent apply/rollback、Core 保留。
- [x] `./.venv/bin/python -m pytest -q tests/test_automatic_memory_source_registry.py tests/test_automatic_memory_snapshot.py tests/test_automatic_memory_resume.py tests/test_automatic_memory_watcher.py tests/test_automatic_memory_scheduler.py tests/test_state_db_scheduler.py`：108 passed，Task 1–4 回归。
- [x] `./.venv/bin/python -m py_compile src/obsidian/memory_scope.py src/obsidian/memory_migration.py src/obsidian/discovery.py src/obsidian/service.py src/indexer/index.py src/retrieval/incremental_sync.py src/retrieval/memory_db.py src/memory/vault_layout.py`、`git diff --check`。
- [ ] Qdrant unavailable、真实 Production Vault、主人 UI/真机验收：需根代理在最终工作树执行；代码真实返回 `pending_rebuild`/错误，不假报成功。

### 回归与回滚

- [x] `VaultLayout.should_index()` 兼容语义保持不变；普通 PEMIS 索引仍可用，自动记忆入口改用独立 scope。
- [x] scoped incremental sync 不删除 chat/file/media 等非 Vault 投影；raw 仅接受 dedicated Obsidian root、显式 manifest 或 per-file Obsidian marker。
- 回滚：回退 Task 5 代码提交；不触碰 Production Vault 或主人配置。

## 2026-08-26 · Phase 1 Automatic Memory · Task 4 修复轮 4 · runner contract and terminal lease cleanup

- 产品分支：`codex/phase1-automatic-memory`
- 产品 Commit：`b8808014062aafa0374e291ba694f276515cf5ab`
- 影响模块：automatic-memory scheduler runner invocation、scan terminal transitions and scheduler lease cleanup
- 风险等级：P0
- 用户可感知变化：真实 `SnapshotJobRunner.run(scan_id, crash_at=...)` 可由 scheduler 正确调用，不会把 source id 当作 crash control；来源失效、撤销、暂停、完成、失败路径都会清理 scheduler lease，授权恢复后 retry/reconcile 可立即继续。
- 数据或安全边界变化：继续复用既有 `automatic_memory_scans` 和 `StateDatabase`；不新增数据库、队列或事实源。通用二参 runner 仍按既有 `(scan_id, source_id)` 契约注入，SnapshotJobRunner 按参数名识别其 `crash_at` 控制参数。

### 新增或修改的自动验收

- [x] `./.venv/bin/python -m pytest -q tests/test_automatic_memory_watcher.py tests/test_automatic_memory_scheduler.py tests/test_state_db_scheduler.py`：37 passed，含真实 SnapshotJobRunner scheduler 集成、paused 兼容路径、失效/撤销终态 scheduler lease 清理与恢复执行。
- [x] `./.venv/bin/python -m pytest -q tests/test_automatic_memory_source_registry.py tests/test_automatic_memory_control_api.py tests/test_automatic_memory_snapshot.py tests/test_automatic_memory_resume.py tests/test_automatic_memory_adapters.py tests/test_extraction_idempotency.py tests/test_extraction_queue.py tests/test_extraction_worker.py`：137 passed，3 warnings（Task 1–3 与 queue/worker 回归）。
- [x] `./.venv/bin/python -m py_compile src/automatic_memory/watcher.py src/automatic_memory/scheduler.py src/scheduler/cron.py src/storage/state_db.py src/config.py`、`git diff --check`。
- [ ] `./.venv/bin/python scripts/check_acceptance_sync.py`、`./.venv/bin/python scripts/check_local_execution_handoff.py`：由根代理在文档提交后复读执行。

### 回归项与边界

- [x] 保持 Task4 前序跨实例 single-flight、scheduler lease heartbeat/过期恢复、direct revoke 快速停止、listener/watcher generation 隔离、普通二参/三参/可变参 runner 注入、SnapshotJobRunner paused resume、授权/symlink 安全。
- [x] 终态清理覆盖 `unsupported`、`degraded`、`expired` trigger、`revoke -> cancelled`、`pause -> paused`、`complete -> completed` 和 `failed` 路径；旧数据库 trigger 会在初始化时重建以应用最新清理逻辑。

### 清理与回滚

- 临时数据前缀：`PHASE1_AUTOMATIC_MEMORY_TASK4_FIX4_`
- 测试仅使用 pytest 临时目录、脱敏 SourceRecord 和临时 SQLite/raw；无真实聊天、Vault、凭据或持久 Artifact。
- 回滚：回滚产品 Commit `b8808014062aafa0374e291ba694f276515cf5ab`，不触碰主人数据。

### 最终报告

- 报告路径：本地调度报告继续由 `.superpowers/` 忽略；正式证据为本条目与测试输出。
- 报告分支：`codex/phase1-automatic-memory`

## 2026-08-26 · Phase 1 Automatic Memory · Task 4 修复轮 3 · cross-instance lease and lifecycle races

- 产品分支：`codex/phase1-automatic-memory`
- 产品 Commit：`a9d5c680b6b5c0424aa83e98d6b5b39d3fe68049`
- 影响模块：automatic-memory scan scheduler lease、source lifecycle terminalization、watcher generation and non-blocking revoke
- 风险等级：P0
- 用户可感知变化：共享 `StateDatabase` 的多个 scheduler 只允许一个 scan runner；scheduler lease 支持 heartbeat 与过期恢复；来源在运行中进入 `unsupported`、`degraded` 或 `expired` 时不会遗留 `running` scan；旧 watcher/listener 的迟到清理或回调不会影响新生命周期，撤销通知不再等待阻塞 watcher。
- 数据或安全边界变化：复用既有 `automatic_memory_scans` 与 `StateDatabase`，不新增数据库、队列或事实源；SnapshotJobRunner 的既有 scan lease/终态保持兼容。

### 新增或修改的自动验收

- [x] `./.venv/bin/python -m pytest -q tests/test_automatic_memory_watcher.py tests/test_automatic_memory_scheduler.py tests/test_state_db_scheduler.py`：30 passed，覆盖跨实例 single-flight、scheduler lease、来源中途终态化、watcher generation、非阻塞 revoke、listener generation 与既有 Cron 回归。
- [x] `./.venv/bin/python -m pytest -q tests/test_automatic_memory_source_registry.py tests/test_automatic_memory_control_api.py tests/test_automatic_memory_snapshot.py tests/test_automatic_memory_resume.py tests/test_automatic_memory_adapters.py tests/test_extraction_idempotency.py tests/test_extraction_queue.py tests/test_extraction_worker.py`：137 passed，3 warnings（Task 1–3 与 queue/worker 回归）。
- [x] `./.venv/bin/python -m py_compile src/automatic_memory/watcher.py src/automatic_memory/scheduler.py src/scheduler/cron.py src/storage/state_db.py src/config.py`、`git diff --check`。
- [ ] `./.venv/bin/python scripts/check_acceptance_sync.py`、`./.venv/bin/python scripts/check_local_execution_handoff.py`：由根代理在文档提交后复读执行。

### 回归项与边界

- [x] 保持 backend 异常审计、single-flight、direct revoke 立即停止、failed retry、`None` fail-closed、scheduler_jobs lease/DB claim、普通 Cron、5/900/86400、授权/symlink 安全。
- [x] 修复轮 3 不把 focused 与 Task 1–3 回归合计为一条；两条命令分别记录为 30 passed 与 137 passed。

### 清理与回滚

- 临时数据前缀：`PHASE1_AUTOMATIC_MEMORY_TASK4_FIX3_`
- 测试仅使用 pytest 临时目录和脱敏 SourceRecord；无真实聊天、Vault、凭据或持久 Artifact。
- 回滚：回滚产品 Commit `a9d5c680b6b5c0424aa83e98d6b5b39d3fe68049`，不触碰主人数据。

### 最终报告

- 报告路径：本地调度报告继续由 `.superpowers/` 忽略；正式证据为本条目与测试输出。
- 报告分支：`codex/phase1-automatic-memory`

## 2026-08-26 · Phase 1 Automatic Memory · Task 4 · watcher and persistent reconciliation

- 产品分支：`codex/phase1-automatic-memory`
- 产品 Commit：`c6d9ebecd6007c5b61f5d09aa5c1a9c85aa25194`
- 影响模块：`watchfiles==1.2.0` observation、existing `CronScheduler` lifecycle、automatic-memory source scan status and reconciliation events
- 风险等级：P0
- 用户可感知变化：已授权来源在启动时增量处理；文件事件经 5 秒防抖后进入现有授权快照/Extraction Queue 入口；事件丢失由 15 分钟 reconciliation 和每日 integrity 任务补偿；Desktop 后续可读取真实扫描报告、错误和下一步。
- 数据或安全边界变化：监听器仅观察授权 root，不读取第三方凭据、Cookie、Token、私有数据库或进程；不写入第三方目录，不新增队列、数据库或并行调度器。暂停、撤销、unsupported 和单来源故障均阻止新工作并保留审计事实。

### 新增或修改的自动验收

- [x] 修复轮 1 RED 后运行 `./.venv/bin/python -m pytest -q tests/test_automatic_memory_watcher.py tests/test_automatic_memory_scheduler.py tests/test_state_db_scheduler.py`：25 passed，覆盖 backend 创建/迭代异常、5 秒防抖、重复事件抑制、路径越界、单源 watcher 停止、暂停/撤销隔离、同源 single-flight、非完整报告落库、持久 start/stop/pause/resume、事件静默后的 reconciliation、每日 integrity、running scan 重启复用。
- [x] `./.venv/bin/python -m pytest -q tests/test_automatic_memory_source_registry.py tests/test_automatic_memory_control_api.py tests/test_automatic_memory_snapshot.py tests/test_automatic_memory_resume.py tests/test_automatic_memory_adapters.py tests/test_extraction_idempotency.py tests/test_extraction_queue.py tests/test_extraction_worker.py`：137 passed，Task 1–3 与 queue/worker 回归；另含 3 个既有 warning（FastAPI/httpx、测试 ZIP duplicate、Pydantic Config）。
- [x] `./.venv/bin/python -m py_compile src/automatic_memory/watcher.py src/automatic_memory/scheduler.py src/scheduler/cron.py src/storage/state_db.py src/config.py`、`git diff --check`。
- [ ] `./.venv/bin/python scripts/check_acceptance_sync.py`、`./.venv/bin/python scripts/check_local_execution_handoff.py`：由根代理在文档提交后复读执行。

### 回归项与边界

- [x] `watchfiles==1.2.0` 的 MIT provenance 已记录在 `.research/local-ai-memory-architecture/FINDINGS.md`；监听事件只是低延迟提示，持久 scheduler reconciliation 才是完整性来源。
- [x] Cron job 的 `run_on_start` 在重启时重新置为 due；已有 running/paused scan 通过现有 `SourceRegistry.start_scan` 复用，不创建重复 scan；单来源失败不会阻塞其他来源。
- [x] 所有扫描回调继续由调用方注入现有 Task 2 `SnapshotJobRunner`/queue；Task 4 不 claim/execute `automatic_memory_snapshot`，不触碰 Obsidian 正文、Vault 或真实本机任务单。
- [x] 修复轮 1：watch backend 的创建/迭代异常调用持久错误回调；同源 reconciliation 以 Future single-flight 合并并发触发；撤销/过期/unsupported 停止该源 watcher、禁用该源 Cron，global resume 不会重新启用；不完整报告将 scan 标为 `failed` 并保存错误。
- [x] 修复轮 1：现有 `scheduler_jobs` 增加兼容性 lease/heartbeat 字段；SQLite 原子 claim 回收 stale `running` job，两个 Cron 实例不能同时执行同一 due job；普通 Cron job 继续使用原有表和模式门禁。
- [x] 修复轮 2：revoke 与 reconcile 完成提交使用 SQLite 授权条件原子化，撤销先提交时 scan 保持 `cancelled`；SourceRegistry 生命周期 listener 让 direct revoke/unsupported 立即停止 watcher 和 source jobs，scheduler stop 会解绑旧 listener。
- [x] 修复轮 2：failed scan 下次触发自动调用既有 `retry_scan`；runner 返回 `None` 或不支持结果会失败落库；若 runner 自身已通过现有 lease 完成 scan，scheduler 会复用其已持久化的 `completed` 状态。

### 清理与回滚

- 临时数据前缀：`PHASE1_AUTOMATIC_MEMORY_TASK4_`
- 测试仅使用 pytest 临时目录和脱敏 SourceRecord；无真实聊天、Vault、凭据或持久 Artifact。
- 回滚：回滚产品 Commit `c6d9ebecd6007c5b61f5d09aa5c1a9c85aa25194`，不触碰主人数据。

### 最终报告

- 报告路径：本地调度报告继续由 `.superpowers/` 忽略；正式证据为本条目与测试输出。
- 报告分支：`codex/phase1-automatic-memory`

## 2026-08-26 · Phase 1 Automatic Memory · Task 3 · fail-closed source adapters

- 产品分支：`codex/phase1-automatic-memory`
- 产品 Commit：`2b987e4ac13401e92104ad70ca54d1c185ad6a71`
- 影响模块：官方 ChatGPT 导出、版本化 Codex transcript、Generic AI History Inbox、Claude Desktop capability boundary、Extraction Adapter Registry
- 风险等级：P0
- 用户可感知变化：只接受官方 ChatGPT ZIP/JSON、明确版本的 Codex JSONL 与主人选定并带 History Inbox 标记的 JSON/JSONL/Markdown；Claude Desktop 在无官方导出时准确显示 `unsupported` 或 `consent_required`。
- 数据或安全边界变化：未知、损坏、恶意或未标记格式 fail-closed 并留下安全审计原因；不读取浏览器 profile、Cookie、Token、认证配置、私有数据库、Claude opaque storage，不扫描任意目录，不联网，不新增队列/数据库/原始事实源。

### 新增或修改的自动验收

- [ ] `./.venv/bin/python -m pytest -q tests/test_automatic_memory_adapters.py`：覆盖 ChatGPT 官方结构、重复/损坏记录、整批 fail-closed、根目录/重复 ZIP 成员、全成员大小/压缩比、异常编码、conversation/message ID；Codex schema v1、未知 schema 正式 Pipeline 队列审计（含 `codex` 兼容 source type）、敏感祖先/symlink/授权 root、重复 ID 与 timezone/order；Generic History Inbox JSON/JSONL/Markdown、重复 ID、边界与 scoped external_id；Claude capability、默认 bootstrap 注册与 Registry approved boundary。
- [ ] `./.venv/bin/python -m pytest -q tests/test_chatgpt_importer.py tests/test_structured_ingestion.py tests/test_capture_adapters.py tests/test_codex_writeback.py tests/test_mcp_extraction_submission.py tests/test_extraction_idempotency.py tests/test_extraction_queue.py tests/test_extraction_hardening.py tests/test_extraction_worker.py tests/test_automatic_memory_source_registry.py tests/test_automatic_memory_control_api.py`：Task 1/2 与既有 Extraction/旧 Codex adapter 回归。
- [ ] `./.venv/bin/python -m py_compile src/extraction/adapters/chatgpt.py src/extraction/adapters/codex.py src/extraction/adapters/generic_ai_history.py src/extraction/adapters/claude_desktop.py src/extraction/registry.py`、`git diff --check`、`./.venv/bin/python scripts/check_acceptance_sync.py`、`./.venv/bin/python scripts/check_local_execution_handoff.py`。

### 回归项与边界

- [ ] 所有 adapter 继续复用 `ExtractionAdapter`、`ExtractionRequest`、`ExtractionBatch`、现有 raw snapshot/Extraction Queue；通用 pipeline 不 claim/execute `automatic_memory_snapshot`。
- [ ] 未知输入只进入明确失败/审计原因，不猜测、不生成消息；不修改 Production/Vault，不创建 ACTIVE 本机任务或 Artifact。
- [ ] 修复轮验证：不得通过 conversation 静默去重、跳过损坏消息、放宽路径敏感组件、移除授权 root、降低时间/ID校验或绕过旧 adapter 回归。
- [ ] 修复轮 2：ChatGPT 预解析校验 metadata object 与 ZIP 全成员安全后才读取 root；单会话 normalize 失败时整批拒绝且错误不泄漏本地路径；Codex 未知 schema 通过正式 enqueue/process 记录具体 reason；Claude 只暴露 capability、不读取 opaque storage。
- [ ] 修复轮 3：ChatGPT 对 ZIP 全成员（含目录）执行兼容的成员数上限，并预验证 title/current_node/parent、metadata model 与附件字段类型；`source_type=codex` 的显式 schema JSON 不再回退到旧工作报告 adapter，未知 schema 通过正式队列失败审计，旧无 schema JSON 工作报告保持兼容。

### 清理与回滚

- 临时数据前缀：`PHASE1_AUTOMATIC_MEMORY_TASK3_`
- fixture 仅为脱敏结构样例，无真实聊天、密钥或个人数据；pytest 临时路径结束后自动清理。
- 回滚：回滚 Task 3 产品 Commit，不触碰主人数据、Production Vault 或历史验收 Artifact。

### 最终报告

- 报告路径：本地调度报告继续由 `.superpowers/` 忽略；正式证据为本条目与测试输出。
- 报告分支：`codex/phase1-automatic-memory`

## 2026-08-26 · Phase 1 Automatic Memory · Task 2 fix round 9 · terminal snapshot cleanup precedence and owner-token admission

- 产品分支：`codex/phase1-automatic-memory`
- 产品 Commits：`b979b66f14d6e64e40049ee6f7258c259bfceb30`（终态清理优先级）、`ccde4be`（owner token 创建端校验）
- 影响模块：snapshot staging cleanup terminal-state and lease ownership decision
- 风险等级：P1
- 用户可感知变化：合法 owned snapshot temp 在 scan 明确进入 completed/cancelled/failed/paused 终态时可确定性回收，即使当前 lease_id 为 NULL；running temp 只有编码 lease 与当前 lease 匹配且 expiry 明确过期时才可回收。
- 数据或安全边界变化：scan 缺失、查询异常、字段异常、未知状态、NULL/非法 expiry、mismatched lease、malformed 或超长 owned token 均 fail-closed 保留；普通 legacy `.snapshot-*.tmp` 仍按 24 小时策略处理。

### 新增或修改的自动验收

- [x] RED：新增的 `test_owned_temp_creation_rejects_untrusted_owner_tokens` 在修复前 4/4 失败；任意路径分隔符、Unicode、超长或空 owner 均可创建 staging，随后清理解析器只能 fail-closed 保留。
- [x] GREEN：`./.venv/bin/python -m pytest -q tests/test_automatic_memory_snapshot.py tests/test_automatic_memory_resume.py tests/test_extraction_queue.py tests/test_extraction_worker.py`：80 passed，覆盖终态 NULL lease 回收、running mismatch/NULL expiry 保留、unknown/overlong/malformed owned 保留、legacy 24h、跨来源 active temp、protected snapshot job、lease/crash/idempotency 和 owner token 创建边界。
- [x] `./.venv/bin/python -m pytest -q tests/test_automatic_memory_source_registry.py tests/test_automatic_memory_control_api.py tests/test_extraction_idempotency.py tests/test_extraction_queue.py tests/test_extraction_hardening.py tests/test_extraction_worker.py tests/test_structured_ingestion.py`：47 passed，Task 1/extraction/queue/worker 回归（含 1 个既有 FastAPI deprecation warning；更正历史 round 8 条目误写的 104）。
- [x] `./.venv/bin/python -m py_compile src/automatic_memory/snapshot.py src/automatic_memory/checkpoint.py src/extraction/pipeline.py src/extraction/queue.py src/extraction/sink.py src/storage/state_db.py`、`git diff --check`、`./.venv/bin/python scripts/check_acceptance_sync.py`、`./.venv/bin/python scripts/check_local_execution_handoff.py`。

### 回归项与边界

- [x] 保持 non-UTC/invalid expiry fail-closed、unknown/overlong owned 保留、普通 legacy `.snapshot-*.tmp` 24 小时策略、活跃跨来源保护、protected snapshot job 边界、lease/crash/idempotency、source/raw 不改动；创建端拒绝不满足同一安全 token 语法的 owner，避免生成不可清理 owned staging。
- [ ] 不扩展 Task 3 或其他架构；不新增数据库、队列、raw archive、watcher、适配器或消费者。
- [ ] Full-suite 既有 Desktop assertion mismatch 与缺少 `python` executable 的 `test_second_brain` baseline failures 不修改、不掩盖；内部 SDD 报告继续 ignored。

### 清理与回滚

- 临时数据前缀：`PHASE1_AUTOMATIC_MEMORY_TASK2_FIX9_`
- 本轮 pytest 临时授权 root、SQLite、raw、queue 与 crash marker 自动清理；未创建持久 debug 目录或日志。
- 回滚：回滚产品 Commit `b979b66f14d6e64e40049ee6f7258c259bfceb30`，不触碰主人数据。

### 最终报告

- 报告路径：本地调度报告继续由 `.superpowers/` 忽略；正式证据为本条目与测试命令输出。
- 报告分支：`codex/phase1-automatic-memory`

## 2026-08-26 · Phase 1 Automatic Memory · Task 2 fix round 8 · unknown owned snapshot retention

- 产品分支：`codex/phase1-automatic-memory`
- 产品 Commit：`78979cbf3852b22a9a8152f35f115eae3adf3f18`
- 影响模块：snapshot staging cleanup parsing and unknown owned-file retention
- 风险等级：P1
- 用户可感知变化：合法但无法关联到现有 scan 的 owned snapshot 临时文件不再因 24 小时 age 策略被删除；超长或异常 scan/lease/token 文件名按 unknown owned 保留。普通 legacy `.snapshot-*.tmp` 仍按 24 小时阈值清理。
- 数据或安全边界变化：只有明确找到 scan 且状态为 completed/cancelled/failed/paused，或当前 running lease 已明确过期时，owned staging 才允许回收；scan 查询异常、缺失或 owner 编码不可信均 fail-closed 保留。

### 新增或修改的自动验收

- [ ] `./.venv/bin/python -m pytest -q tests/test_automatic_memory_snapshot.py tests/test_automatic_memory_resume.py tests/test_extraction_queue.py tests/test_extraction_worker.py`：71 passed，覆盖不存在 scan 的有效编码 stale owned temp 保留、超长 token stale owned temp 保留、malformed/异常 DB、lease expiry、legacy 24h 与既有 Task 2 lease/crash/idempotency 边界。
- [ ] `./.venv/bin/python -m pytest -q tests/test_automatic_memory_source_registry.py tests/test_automatic_memory_control_api.py tests/test_extraction_idempotency.py tests/test_extraction_queue.py tests/test_extraction_hardening.py tests/test_extraction_worker.py tests/test_structured_ingestion.py`：47 passed，Task 1/extraction/queue/worker 回归（含 1 个既有 FastAPI deprecation warning；原记录的 104 为计数错误，已按真实命令输出更正）。
- [ ] `./.venv/bin/python -m py_compile src/automatic_memory/snapshot.py src/automatic_memory/checkpoint.py src/extraction/pipeline.py src/extraction/queue.py src/extraction/sink.py src/storage/state_db.py`、`git diff --check`、`./.venv/bin/python scripts/check_acceptance_sync.py`、`./.venv/bin/python scripts/check_local_execution_handoff.py`。

### 回归项与边界

- [ ] 保持普通 legacy `.snapshot-*.tmp` 24 小时策略、活跃跨来源保护、protected snapshot job 边界、lease/crash/idempotency 行为不变。
- [ ] 不扩展 Task 3 或其他架构；不新增数据库、队列、raw archive、watcher、适配器或消费者。
- [ ] Full-suite 既有 Desktop assertion mismatch 与缺少 `python` executable 的 `test_second_brain` baseline failures 不修改、不掩盖；内部 SDD 报告继续 ignored。

### 清理与回滚

- 临时数据前缀：`PHASE1_AUTOMATIC_MEMORY_TASK2_FIX8_`
- 本轮调试临时目录 `.tmp-debug-19294/` 已清理；pytest 临时授权 root、SQLite、raw、queue 与 crash marker 自动清理。
- 回滚：回滚产品 Commit `78979cbf3852b22a9a8152f35f115eae3adf3f18`，不触碰主人数据。

### 最终报告

- 报告路径：本地调度报告继续由 `.superpowers/` 忽略；正式证据为本条目与测试命令输出。
- 报告分支：`codex/phase1-automatic-memory`

## 2026-08-26 · Phase 1 Automatic Memory · Task 2 fix round 7 · fail-closed lease expiry cleanup

- 产品分支：`codex/phase1-automatic-memory`
- 产品 Commit：`f0b639206f3274ade7ae115c2758c21006e69196`
- 影响模块：snapshot staging cleanup lease-expiry parsing and fail-closed ownership handling
- 风险等级：P1
- 用户可感知变化：owned snapshot temp 清理不再依赖时间字符串排序；带 offset、`Z` 和 UTC 的明确过期 lease 才会回收，naive/非法/查询异常均保守保留。格式异常的 `.snapshot-owned-*` 不会因 24 小时策略被误删；普通 legacy `.snapshot-*.tmp` 仍按 24 小时阈值处理。
- 数据或安全边界变化：`lease_expires_at` 使用 `datetime.fromisoformat` 后统一转换 UTC；无法证明 owner、scan、lease 或 expiry 的 owned temp 保留，避免误删活跃复制中的潜在敏感 staging。

### 新增或修改的自动验收

- [ ] `./.venv/bin/python -m pytest -q tests/test_automatic_memory_snapshot.py tests/test_automatic_memory_resume.py tests/test_extraction_queue.py tests/test_extraction_worker.py`：69 passed，覆盖 offset/`Z`/UTC/naive/非法 expiry、malformed owned temp、StateDatabase 异常 fail-closed、活跃跨来源 temp 和 legacy 24 小时清理。
- [ ] `./.venv/bin/python -m pytest -q tests/test_automatic_memory_source_registry.py tests/test_automatic_memory_control_api.py tests/test_extraction_idempotency.py tests/test_extraction_queue.py tests/test_extraction_hardening.py tests/test_extraction_worker.py tests/test_structured_ingestion.py`：47 passed，Task 1/queue/extraction 回归。
- [ ] `./.venv/bin/python -m py_compile src/automatic_memory/snapshot.py src/automatic_memory/checkpoint.py src/extraction/pipeline.py src/extraction/queue.py src/extraction/sink.py src/storage/state_db.py`、`git diff --check`、`./.venv/bin/python scripts/check_acceptance_sync.py`、`./.venv/bin/python scripts/check_local_execution_handoff.py`。

### 回归项与边界

- [ ] Full-suite：632 passed，11 skipped；仅保留既有 Desktop assertion mismatch 与缺少 `python` executable 的 `test_second_brain` baseline failures，未修改或掩盖。
- [ ] 保持 Task 2 收缩边界：不恢复 generic pipeline 的 snapshot claim/execute，不实现 Task 3 专用 consumer、staging/outbox、下游 visibility transaction。

### 清理与回滚

- 临时数据前缀：`PHASE1_AUTOMATIC_MEMORY_TASK2_FIX7_`
- malformed/unknown/活跃 owned temp 保留；合法 expired owner temp 确定性回收；普通 legacy temp 仅按 24 小时阈值回收；不删除 raw 正式对象、其他组件 temp 或第三方文件。
- 回滚：回滚产品 Commit `f0b639206f3274ade7ae115c2758c21006e69196`，不触碰主人数据。

### 最终报告

- 报告路径：本地调度报告继续由 `.superpowers/` 忽略；正式证据为本条目与测试命令输出。
- 报告分支：`codex/phase1-automatic-memory`

## 2026-08-26 · Phase 1 Automatic Memory · Task 2 fix round 6 · lease-owned snapshot staging cleanup

- 产品分支：`codex/phase1-automatic-memory`
- 产品 Commit(s)：`a16d10c392ecc8c7ba2080c5ae3c3d6ab64791fa`, `58ae897111d4ee665e0a8cf1ba2e11c6e8694c58`
- 影响模块：existing snapshot staging cleanup and Task 2 concurrency/recovery tests
- 风险等级：P1
- 用户可感知变化：一个活跃 runner 的 snapshot temp 不会被另一个来源/runner 构造时误删；不同来源可并行完成且 raw/queue exactly-once 保持。
- 数据或安全边界变化：owned temp 文件名绑定 `scan_id + lease_id`，清理以现有 state DB lease/status/expiry 为权威；未知 fresh temp 默认保留，legacy stale temp 仅按 24 小时安全阈值回收。正式 raw 对象、其他组件 temp 与第三方文件不受影响。

### 新增或修改的自动验收

- [ ] `pytest -q tests/test_automatic_memory_snapshot.py tests/test_automatic_memory_resume.py tests/test_extraction_queue.py tests/test_extraction_worker.py`：58 passed，覆盖活跃 temp 跨实例保留、expired/dead/legacy-null lease 回收策略、unknown fresh/legacy stale、不同来源真实并发、revoke/异常清理、generic snapshot claim/execute 隔离。
- [ ] `pytest -q tests/test_automatic_memory_source_registry.py tests/test_automatic_memory_control_api.py tests/test_extraction_idempotency.py tests/test_extraction_queue.py tests/test_extraction_hardening.py tests/test_extraction_worker.py tests/test_structured_ingestion.py`：47 passed。
- [ ] `py_compile`、`git diff --check`、`python scripts/check_acceptance_sync.py`、`python scripts/check_local_execution_handoff.py`。

### 回归项与边界

- [ ] Full-suite：622 passed，11 skipped；仅保留既有 Desktop assertion mismatch 与缺少 `python` executable 的 `test_second_brain` baseline failures。
- [ ] 保持 Task 2 收缩边界：不恢复 generic pipeline 的 snapshot claim/execute，不实现 Task 3 专用 consumer、staging/outbox、下游 visibility transaction。

### 清理与回滚

- 临时数据前缀：`PHASE1_AUTOMATIC_MEMORY_TASK2_FIX6_`
- 未知 fresh/活跃 temp 不删除；成功、失败、revoke、lease loss 的本轮 temp 由 capture 确定性清理；SIGKILL 遗留按 lease/年龄策略处理。
- 回滚：回滚产品 Commit(s) `a16d10c392ecc8c7ba2080c5ae3c3d6ab64791fa`、`58ae897111d4ee665e0a8cf1ba2e11c6e8694c58` 及其父实现提交，不触碰主人数据。

### 最终报告

- 报告路径：本地调度报告继续由 `.superpowers/` 忽略；正式证据为本条目与测试命令输出。
- 报告分支：`codex/phase1-automatic-memory`

## 2026-08-26 · Phase 1 Automatic Memory · Task 2 fix round 5 · protected snapshot admission boundary

- 产品分支：`codex/phase1-automatic-memory`
- 产品 Commit：`b0bc0cc2b15112b0cae203dee3af445fca2b33b7`
- 影响模块：existing extraction queue claim policy/pipeline boundary, short snapshot raw/queue authorization checks, secure snapshot source opening, raw sink validation, Task 2 race/recovery tests
- 风险等级：P0
- 用户可感知变化：通用 ExtractionPipeline 不会执行或 claim 内部 `automatic_memory_snapshot` 作业；普通 job 保持原行为。快照作业仍由 Task 2 runner 负责授权快照、content-addressed raw 和 existing queue admission。
- 数据或安全边界变化：移除包围文件/Vault/索引 callback 的长 SQLite 事务；raw commit 与 queue admission 各自使用短授权检查。revoke 仍在现有 `lingji_state.db` 原子取消 snapshot queued/retrying/running jobs；raw 与 queue 之间的孤儿 raw evidence 通过 scan 状态错误记录保留、但不进入 current retrieval。lease/heartbeat/manifest/no-follow race 修复保持。

### 新增或修改的自动验收

- [ ] `pytest -q tests/test_automatic_memory_snapshot.py tests/test_automatic_memory_resume.py tests/test_extraction_queue.py tests/test_extraction_worker.py`：54 passed，覆盖内部 snapshot 不 claim/不 execute、revoke cancel、短 TTL、心跳生命周期、no-follow source/raw race、双 runner 最终 completed 与强杀恢复。
- [ ] `pytest -q tests/test_automatic_memory_source_registry.py tests/test_automatic_memory_control_api.py tests/test_extraction_idempotency.py tests/test_extraction_queue.py tests/test_extraction_hardening.py tests/test_extraction_worker.py tests/test_structured_ingestion.py`：47 passed，Task 1/queue/extraction/pipeline 回归。
- [ ] `py_compile`、`git diff --check`、`python scripts/check_acceptance_sync.py`、`python scripts/check_local_execution_handoff.py`。

### 新增或修改的真机验收

- [ ] 本轮不启动 Artifact；保持 `LOCAL_EXECUTION_TASK.md` 为 `IDLE`。

### 回归项

- [ ] Full-suite baseline limitation 保持原样：Desktop integration assertion mismatch 与 `python` executable unavailable 的 `test_second_brain` 在 `d12c1fb` 和当前树均复现；不修改、不掩盖。
- [ ] Task 3 待办：专用 snapshot parser/consumer、可恢复 staging/outbox、下游可见性事务；通用 ExtractionPipeline 禁止绕过此边界。Task 2 不实现 adapter、watcher、聊天解析、Obsidian 正文或 tombstone/reconcile。

### 清理与回滚

- 临时数据前缀：`PHASE1_AUTOMATIC_MEMORY_TASK2_FIX5_`
- 覆盖安装或迁移方式：不安装、不启动；pytest 临时数据库/raw/queue/marker 自动清理。
- 冲突清理：不保留 `.conflict` 正文副本；仅在现有 scan `last_error` 保留无正文 hash/path 诊断。
- 回滚：回滚产品 Commit `b0bc0cc2b15112b0cae203dee3af445fca2b33b7` 及其父实现提交，不触碰主人数据。

### 最终报告

- 报告路径：本地调度报告继续由 `.superpowers/` 忽略；正式证据为本条目与测试命令输出。
- 报告分支：`codex/phase1-automatic-memory`

## 2026-08-26 · Phase 1 Automatic Memory · Task 2 fix round 3 · revoke-safe downstream and lease hardening

- 产品分支：`codex/phase1-automatic-memory`
- 产品 Commit：`1c55fd7822de6cc90dfea23736aced6b309b7a8d`
- 影响模块：existing StateDatabase lease/revoke/manifest, extraction queue/pipeline, raw sink, Task 2 process/concurrency tests
- 风险等级：P0
- 用户可感知变化：来源撤销在同一 `lingji_state.db` 事务内取消 snapshot queued/retrying/running jobs；worker 在执行、索引和结构化写入前复核授权，撤销来源不会完成下游结果。
- 数据或安全边界变化：SnapshotJobRunner 拒绝 state/queue 不同 SQLite 文件（含别名校验）；lease 使用 TTL/heartbeat、进程实例 UUID 与线程元数据，长复制期间续租；raw 已有对象通过 no-follow descriptor 校验，冲突删除临时正文，仅记录 expected/actual hash 与目标路径诊断；manifest 提供 retired scan 清理 API。

### 新增或修改的自动验收

- [ ] `pytest -q tests/test_automatic_memory_snapshot.py tests/test_automatic_memory_resume.py tests/test_extraction_worker.py`：撤销 admission 后取消队列、跨进程双 runner、同库边界、短 TTL 慢复制、旧 NULL lease、inode=0、冲突隐私诊断与强杀恢复。
- [ ] `pytest -q tests/test_automatic_memory_source_registry.py tests/test_automatic_memory_control_api.py tests/test_extraction_idempotency.py tests/test_extraction_queue.py tests/test_extraction_hardening.py tests/test_extraction_worker.py`：Task 1/queue/extraction 回归。
- [ ] `py_compile`、`git diff --check`、`python scripts/check_acceptance_sync.py`、`python scripts/check_local_execution_handoff.py`。

### 新增或修改的真机验收

- [ ] 本轮不启动 Artifact；保持 `LOCAL_EXECUTION_TASK.md` 为 `IDLE`。

### 回归项

- [ ] Full-suite 仍有两项 baseline limitation（Desktop integration assertion mismatch；`python` executable unavailable in `test_second_brain`），在 `d12c1fb` 与当前树均复现，不修改、不掩盖。
- [ ] 不实现 Task 3 adapter、watcher、聊天解析、Obsidian 正文或 tombstone/reconcile。

### 清理与回滚

- 临时数据前缀：`PHASE1_AUTOMATIC_MEMORY_TASK2_FIX3_`
- 覆盖安装或迁移方式：不安装、不启动；pytest 临时数据库/raw/queue/marker 自动清理。
- 冲突清理：不保留 `.conflict` 正文副本；仅在现有 scan `last_error` 保留无正文 hash/path 诊断。
- 回滚：回滚 `1c55fd7822de6cc90dfea23736aced6b309b7a8d` 及其父实现提交与本条文档提交，不触碰主人数据。

### 最终报告

- 报告路径：本地调度报告继续由 `.superpowers/` 忽略；正式证据为本条目与测试命令输出。
- 报告分支：`codex/phase1-automatic-memory`

## 2026-08-26 · Phase 1 Automatic Memory · Task 2 fix round 2 · revoke-safe atomic admission

- 产品分支：`codex/phase1-automatic-memory`
- 产品 Commit：`3c890e1d0986707b802e3b0c629c8f99cef87c34`
- 影响模块：StateDatabase lease TTL/revocation, incremental scan manifest, atomic raw/queue admission, Task 2 concurrency tests
- 风险等级：P0
- 用户可感知变化：撤销、并发和进程中断不会把未获授权文件继续推进到 raw/queue；恢复只复核增量 per-path sentinel，不重写完整 manifest。
- 数据或安全边界变化：revoke 原子取消 scan 并清理 lease；raw commit 使用原子 no-overwrite hard-link；queue admission 与 revoke 共用现有 state DB SQLite writer lock；lease 由不可预测 UUID、owner 元数据和明确 TTL/heartbeat 共同约束。

### 新增或修改的自动验收

- [ ] `pytest -q tests/test_automatic_memory_snapshot.py tests/test_automatic_memory_resume.py`：撤销 mid-copy/raw/queue 竞态、取消态不转 failed、TTL/死线程/心跳、多进程 raw 收敛、symlink/损坏 raw、per-path 2000 项 manifest、立即 lease 强杀、30%/70% queue-before-checkpoint 强杀。
- [ ] `pytest -q tests/test_automatic_memory_source_registry.py tests/test_automatic_memory_control_api.py tests/test_extraction_idempotency.py tests/test_extraction_queue.py tests/test_extraction_hardening.py tests/test_extraction_worker.py tests/test_chatgpt_importer.py tests/test_structured_ingestion.py tests/test_capture_control.py`：Task 1/extraction 回归。
- [ ] `py_compile`、`git diff --check`、`python scripts/check_acceptance_sync.py`、`python scripts/check_local_execution_handoff.py`。

### 新增或修改的真机验收

- [ ] 本轮不启动 Artifact；保持 `LOCAL_EXECUTION_TASK.md` 为 `IDLE`。

### 主人肉眼确认

- [ ] 不适用；Task 2 不修改 Desktop 或正式 Vault 正文。

### 回归项

- [ ] 保持现有 StateDatabase/source registry、extraction queue/sink/idempotency 行为。
- [ ] Full-suite 两项 baseline limitation（Desktop integration assertion mismatch；`python` executable unavailable in `test_second_brain`）保持原样，不修改、不掩盖。
- [ ] 不实现 Task 3 adapter、watcher、聊天解析、Obsidian 正文或 tombstone/reconcile。

### 清理与回滚

- 临时数据前缀：`PHASE1_AUTOMATIC_MEMORY_TASK2_FIX2_`
- 覆盖安装或迁移方式：不安装、不启动；pytest 临时数据库/raw/queue/marker 自动清理。
- 临时备份删除条件：无。
- 测试数据清理方式：仅清理本轮 pytest 临时目录和 conflict diagnostic 文件。
- 回滚：回滚 fix round 2 实现与文档提交，不触碰主人数据。

### 最终报告

- 报告路径：本地调度报告继续由 `.superpowers/` 忽略；正式证据为本条目与测试命令输出。
- 报告分支：`codex/phase1-automatic-memory`

## 2026-08-26 · Phase 1 Automatic Memory · Task 2 fix round 1 · lease-safe recovery

- 产品分支：`codex/phase1-automatic-memory`
- 产品 Commit：`2ee5fbf7e7dac74f95e8ed7220261aee36ef51b1`
- 影响模块：existing StateDatabase scan leases/checkpoints, snapshot runner recovery, content-addressed raw sink, Task 2 focused tests
- 风险等级：P0
- 用户可感知变化：扫描在并发、进程中断和重启后只由当前 lease owner 推进，并会复核 cursor 之前文件的持久 sentinel。
- 数据或安全边界变化：checkpoint/progress/finalize/release 均按 lease ownership 条件更新；旧 lease 不能覆盖或清理新 lease；损坏或目录 raw 冲突显式失败并保留临时诊断文件。

### 新增或修改的自动验收

- [ ] `pytest -q tests/test_automatic_memory_snapshot.py tests/test_automatic_memory_resume.py`：17 项，含线程/多进程 lease 竞争、旧 lease 隔离、早期 sentinel/新增早期路径、raw 冲突、30%/70% 子进程强杀后重启收敛及 queue-before-checkpoint 中断。
- [ ] `pytest -q tests/test_automatic_memory_source_registry.py tests/test_automatic_memory_control_api.py tests/test_extraction_idempotency.py tests/test_extraction_queue.py tests/test_extraction_hardening.py tests/test_extraction_worker.py tests/test_chatgpt_importer.py tests/test_structured_ingestion.py tests/test_capture_control.py`：Task 1 与 extraction 回归。
- [ ] `py_compile`、`git diff --check`、`python scripts/check_acceptance_sync.py`、`python scripts/check_local_execution_handoff.py`。

### 新增或修改的真机验收

- [ ] 本轮不启动 Artifact；保持 `LOCAL_EXECUTION_TASK.md` 为 `IDLE`。

### 主人肉眼确认

- [ ] 不适用；Task 2 不修改 Desktop 或正式 Vault 正文。

### 回归项

- [ ] 既有 `StateDatabase`/source registry 状态和 extraction queue/sink/idempotency 回归保持通过。
- [ ] Full-suite 两项既有失败（Desktop integration assertion mismatch；`python` executable unavailable in `test_second_brain`）已在基线 `d12c1fb` 与当前 HEAD 复现，记录为 baseline limitation，不修改、不掩盖。
- [ ] 不新增数据库、队列、raw archive、watcher、聊天解析或 Task 3 适配器。

### 清理与回滚

- 临时数据前缀：`PHASE1_AUTOMATIC_MEMORY_TASK2_FIX1_`
- 覆盖安装或迁移方式：不安装、不启动；pytest 临时目录和子进程自动清理。
- 临时备份删除条件：无。
- 测试数据清理方式：只清理 pytest 临时授权 root、SQLite、raw、queue 与 crash marker。
- 回滚：回滚本 fix round 提交，不触碰主人数据。

### 不在范围

- 不解析聊天、不实现 watcher、不写 Obsidian 正文、不改变 Task 3 代码。

### 最终报告

- 报告路径：本地调度报告仍保留于 gitignored `.superpowers/sdd/2026-08-26-phase1-automatic-memory/task-2-report.md`；正式验收证据为本条目。
- 报告分支：`codex/phase1-automatic-memory`

## 2026-08-26 · Phase 1 Automatic Memory · Task 2 · consistent snapshot and resume

- 产品分支：`codex/phase1-automatic-memory`
- 产品 Commit：`pending`
- 影响模块：automatic-memory snapshot/checkpoint、extraction raw sink/idempotency/queue
- 风险等级：P0
- 用户可感知变化：授权来源文件可以以一致快照进入现有 raw/queue 流程，并在受控中断后从最后确认项目恢复。
- 数据或安全边界变化：仅允许 active owner-authorized source root 内的普通文件；拒绝 symlink、目录、root escape、revoked/expired source；raw 使用 content address；不修改源文件。

### 新增或修改的自动验收

- [ ] `pytest -q tests/test_automatic_memory_snapshot.py tests/test_automatic_memory_resume.py`：stat-before/copy/stat-after、重试、路径边界、raw/queue 幂等、lease/checkpoint、30%/70% resume。
- [ ] `pytest -q tests/test_automatic_memory_source_registry.py tests/test_extraction_idempotency.py tests/test_extraction_queue.py tests/test_extraction_hardening.py`：Task 1 与 extraction 回归。
- [ ] `python scripts/check_acceptance_sync.py`、`python scripts/check_local_execution_handoff.py`、diff/compile/secret/absolute-path scans。

### 新增或修改的真机验收

- [ ] 本任务不启动 Artifact；保持 `LOCAL_EXECUTION_TASK.md` 为 `IDLE`。

### 主人肉眼确认

- [ ] 不适用；Task 2 不修改 Desktop 或正式 Vault 正文。

### 回归项

- [ ] 现有 `VaultExtractionSink`、`SQLiteExtractionQueue` 和 canonical extraction idempotency 行为保持兼容。
- [ ] 不创建第二 state DB、queue 或 raw archive；不读取真实聊天、Vault 或第三方 AI 目录。

### 清理与回滚

- 临时数据前缀：`PHASE1_AUTOMATIC_MEMORY_TASK2_`
- 覆盖安装或迁移方式：不安装、不启动；pytest 临时目录自动清理。
- 临时备份删除条件：无。
- 测试数据清理方式：仅 pytest 临时授权 root、SQLite、raw 与 queue。
- 回滚：回滚本 Task 2 提交，不触碰主人数据。

### 不在范围

- 不解析聊天、不实现 watcher、不写 Obsidian 正文、不实现全目录发现。

### 最终报告

- 报告路径：`.superpowers/sdd/2026-08-26-phase1-automatic-memory/task-2-report.md`
- 报告分支：`codex/phase1-automatic-memory`

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

## 2026-08-26 · Phase 1 Automatic Memory · Task 0 contract and plan封板（pending implementation）

- 产品分支：`codex/phase1-automatic-memory`
- 产品 Commit：`pending — Task 0 docs-only baseline d12c1fb837257e83835a7cdb899bb29a9c675c3d`
- 影响模块：自动化第二大脑授权、官方 AI 记录导入、raw/provenance、Extraction Queue、时态 derived memory、RAG/ContextPack/MCP、Obsidian scope、Desktop Work Fact、macOS M5-first acceptance
- 风险等级：P0
- 用户可感知变化：本条目只封板后续开发和验收契约；Task 0 不改变产品运行行为。后续阶段必须让主人看见发现、接管、执行、结果、失败、下一动作与证据。
- 数据或安全边界变化：后续输入必须由一次中文主人授权和精确 allowlist 限定；禁止 Cookie、Token、凭证、浏览器资料、私有 DB、进程注入、应用目录写入、全盘扫描和网络上传。ChatGPT 只用官方导出，Codex schema-detect/fail-closed，Claude opaque storage 显示 `unsupported`/`consent_required`。

### 新增或修改的自动验收

- [ ] Task 1：`tests/test_automatic_memory_source_registry.py` 使用真实临时 SQLite 验证一次中文授权、精确 root allowlist、持久 source/scan 状态、cursor/progress/error/recovery 与 revoke；不得读取聊天正文。
- [ ] Task 1：`tests/test_automatic_memory_control_api.py` 使用真实 FastAPI app 验证 8766 现有 token 鉴权、authorize/revoke/scan/pause/retry/sources/scans 路由及未授权 401；未知状态不得伪造成 completed/0。
- [ ] Task 1 fix round 1：过期 grant 在持久 read/list/start/pause/retry 路径变为 `expired` 并拒绝扫描；revoke 在同一 SQLite 事务取消 running/paused/failed scan；register/start 的重复与并发调用保持单一 source/active scan，scope 冲突返回明确 4xx。
- [ ] Task 1 fix round 2：active grant 下 failed scan 允许 pause 并保留 recovery token/error；expired/revoked failed scan 与 cancelled scan 仍拒绝恢复。
- [ ] Task 1–2：授权 scope、根目录边界、客户端 capability 和拒绝原因。
- [ ] Task 3：ChatGPT 官方导出 ZIP、raw snapshot、message identity、幂等和 malformed export failure。
- [ ] Task 4：`watchfiles==1.2.0`、5 秒防抖、30 秒入队、15 分钟 reconciliation、每日完整性。
- [ ] Task 5–6：Codex schema fail-closed；Claude 不读取 opaque storage 并显示准确 unsupported/consent 状态。
- [ ] Task 7–9：SHA-256 raw/provenance、append-only audit、Obsidian allowlist、时态 validity、current filter、derived confidence `>= 0.90`。
- [ ] Task 10：ContextPack `<= 12000` 字符、citation、统一 MemoryGateway、MCP 与 Desktop 同一 Work Fact ID。
- [ ] Task 11：`quality_score >= 90%`、`source_accuracy >= 95%`、`false_positive_rate <= 5%`、Codex MCP `>= 95%`、duplicate formal content `0`、Production pollution `0`、owner review `100%`、reboot recovery `100%`。

### 新增或修改的真机验收

- [ ] Task 1：不启动 Artifact；仅确认代码路径只注册现有认证 8766 app，`LOCAL_EXECUTION_TASK.md` 保持 `IDLE`，并以临时 SQLite 重启后复读 registry/scan 状态。
- [ ] 仅在产生新产品 Commit 和同 SHA Artifact 后执行；Task 0 不下载、不安装、不启动 Artifact。
- [ ] macOS M5 first：覆盖安装、授权、发现、导入、Work/Memory/ContextPack/MCP、三轮 Core 重启、一次 macOS 重启、主人观察、清理和远程复读完成后，才进入 Windows。
- [ ] Production 与 Acceptance 的 Vault、raw、SQLite、Qdrant、日志和设置物理隔离；普通 Obsidian 文档不读不索引。

### 主人肉眼确认

- [ ] 首页、Work、Attention、Capture、Memory 能显示同一真实事实链；主人能理解系统接管了什么、做了什么、结果是什么、下一步由谁执行。
- [ ] unsupported、consent_required、degraded、unknown、failure 和空状态不伪造为成功、健康或零工作。

### 回归项

- [ ] Task 1：现有 StateDatabase/control API focused 回归通过；不新增数据库、8765 路由、客户端正文读取或未认证 8766 路由。
- [ ] 保持 `LOCAL_EXECUTION_TASK.md` 为 `IDLE`；不得创建本阶段真机任务或重跑淘汰 Artifact。
- [ ] 保持 Obsidian Vault + Git 为正式正文权威；derived current memory 不等于 Core/正式永久正文。
- [ ] Current retrieval 排除 `superseded`、`invalidated`、`archived`；历史记录仍可审计。
- [ ] Opportunity Center 保持冻结；不引入 Mem0、OpenMemory、Letta、Zep/Graphiti 或 LlamaIndex 第二系统。

### 清理与回滚

- Task 1：测试使用 pytest 临时目录和临时 SQLite，测试结束自动清理；失败仅回滚本提交，不触碰 Production/Vault。
- 临时数据前缀：`PHASE1_AUTOMATIC_MEMORY_`
- 覆盖安装或迁移方式：未来验收直接覆盖安装；Task 0 不安装。
- 临时备份删除条件：报告远程第一次确认后删除；只保留脱敏哈希。
- 测试数据清理方式：只清理本阶段明确 allowlist 的 Acceptance fixture、raw、日志、截图、checkpoint 和配置副本，不触碰 Production/Vault。
- 回滚：回退 Task 0 文档提交；不得激活本机任务或改变历史失败结论。

### 不在范围

- Task 0 不修改产品代码、测试代码、依赖、Runtime、Desktop、数据库、Qdrant、Vault 或正式记忆。
- 不创建 `ACTIVE` 本机任务，不生成 Artifact，不进行真实客户端调用，不进入 Windows 验收。
- 不把任何计划入口、能力矩阵或文档契约写成已实现产品能力。

### 最终报告

- 报告路径：`logs/sdd/task-0-report.md`
- 执行计划：`docs/superpowers/plans/2026-08-26-phase1-automatic-memory.md`
- 报告分支：`codex/phase1-automatic-memory`

## 2026-08-26 · Phase 1 Automatic Memory · Task 0 fix round 1 · dependency and entry-point repair（pending implementation）

- 产品分支：`codex/phase1-automatic-memory`
- 产品 Commit：`pending — documentation repair on d59658e52bbf75fc8e6fd26f6625610f7360793e`
- 影响模块：自动记忆计划依赖顺序、source registry/scan API、consistent snapshot/resume、adapter registry、scheduler lifecycle、Obsidian migration、temporal all-path filter、Work Fact/8766/Desktop、RAG/evaluation、macOS/Windows acceptance
- 风险等级：P0
- 用户可感知变化：本轮不改变产品行为；修复计划后，任何自动记忆能力都必须先有可恢复证据链和真实 Work Fact，再进入 RAG、Desktop 或平台验收。
- 数据或安全边界变化：source root、scan cursor/progress/error/recovery、stat-before/copy/stat-after、content hash、lease/retry 和 crash recovery 必须持久化；不读取秘密、私有 DB、opaque storage、进程或全盘路径。

### 新增或修改的自动验收

- [ ] Task 1–2：持久 registry、授权/扫描 8766 鉴权、cursor/progress/error/recovery、consistent snapshot、source sentinel、30%/70% crash resume、重复 raw/job 为 0。
- [ ] Task 3–4：ChatGPT/Codex/Claude/generic JSON/JSONL/Markdown adapters；watchfiles 5 秒防抖、15 分钟 reconciliation、每日完整性和 scheduler 生命周期。
- [ ] Task 5–8：Obsidian dry-run manifest/managed-derived rollback；derived promotion；lexical/Qdrant/hybrid/Core/ContextPack/MemoryGateway/MCP temporal modes；Work Fact/TS DTO/8766/Desktop smoke。
- [ ] Task 9：现有 `src/retrieval/context_pack.py` RAG 扩展、12,000 字符和 citations；独立 100 问评测与阈值 gate。
- [ ] Task 10–11：macOS M5 owner acceptance first，随后 PowerShell 5.1 Windows parity；不得把重启或主人观察写成 pytest/validate 自动 PASS。

### 回归项

- [ ] 不创建 `src/gateway/memory.py` 或 `src/automatic_memory/context_pack.py`；只扩展真实 `src/gateway/memory_gateway.py` 与 `src/retrieval/context_pack.py`。
- [ ] `LOCAL_EXECUTION_TASK.md` 保持 `IDLE`；Task 10 完成后由主代理另发 ACTIVE 本机任务。
- [ ] Opportunity Center 保持冻结；不引入第二记忆系统或新的永久事实源。

### 最终报告

- 报告路径：`logs/sdd/task-0-report.md`
- 执行计划：`docs/superpowers/plans/2026-08-26-phase1-automatic-memory.md`
- 报告分支：`codex/phase1-automatic-memory`

---

## 2026-08-25 · 文档事实审计 · 对齐 SB-0 实际进度并降级历史快照

- 产品分支：`codex/docs-project-truth-audit`
- 审计基线：`ced1128e50d3b3758585573042ea6bcc6f315384`
- 产品代码变化：无
- 影响模块：项目状态、代码导航、文档治理、历史实施/验收文档标识、PEMIS 生成快照标识
- 风险等级：P2
- 用户可感知变化：开发者和主人不再把已经修复的 SB-0 子项误判为尚未开始，也不会把旧模块报告、旧 M5 研究或 2026-06 PEMIS 快照误判为当前产品状态。
- 数据或安全边界变化：无；不修改 Runtime、API、Desktop、Vault、数据库、Qdrant、Credential、正式记忆、Artifact 或主人数据。

### 新增或修改的自动验收

- [x] `python3 scripts/check_acceptance_sync.py`：确认纯文档变更没有遗漏产品变化验收记录。
- [x] `python3 scripts/check_local_execution_handoff.py`：确认当前任务仍为 `IDLE`，最近结果仍为 `COMPLETED / FAIL`。
- [x] `git diff --check`：确认 Markdown 无空白错误。
- [x] 全量受跟踪文档本地链接扫描：确认当前权威没有缺失的相对链接。
- [x] 当前状态引用扫描：确认当前治理文档不再引用已删除的 `docs/AI_CONTEXT.md` 或 `UNIFIED_MEMORY_DEVELOPMENT_ROADMAP.md`。

### 新增或修改的真机验收

- [x] 不需要。本任务不安装、不启动 UI、不运行 Sidecar、不访问真实数据，也不改变产品行为。

### 主人肉眼确认

- [x] 不需要产品 UI 肉眼确认；最终向主人提供非技术化的“能做什么 / 缺什么 / 卡点”说明。

### 回归项

- [x] 保持 `PHASE 1 — SECOND BRAIN COMPLETION`，不得提前进入 Opportunity Center。
- [x] 保持最近 M5 `FAIL / DO NOT MERGE`，不得把 SB-0 部分实现写成 Phase 1 PASS。
- [x] 保持 `LOCAL_EXECUTION_TASK.md` 为 `IDLE`，不得激活或重跑旧 Artifact。
- [x] 保留 `docs/TEST_REPORTS/**`、验收结果回执、哈希与失败证据，不改写历史结论。
- [x] Work Fact 必须继续明确：正式 8766 路由、LocalControlService 共享接入、Desktop DTO/响应合同、Outcome/NextAction、端到端与真实验收仍未完成。

### 清理与回滚

- 临时数据前缀：无
- 覆盖安装或迁移方式：不适用
- 临时备份删除条件：不适用
- 测试数据清理方式：不创建产品测试数据
- 回滚：回退本次文档提交；不得恢复错误的当前进度或把历史快照提升为当前权威。

### 不在范围

- 不注册 `/api/work/*`。
- 不修改 Work Fact、Capture、Memory 或 Desktop 合同。
- 不执行 focused/full/release 产品门禁。
- 不创建新产品 Commit、Artifact、ACTIVE 本机任务或主人验收结论。
- 不删除 120 个 PEMIS opportunity 生成记录或任何历史测试/验收报告。

### 最终报告

- 报告路径：`docs/TEST_REPORTS/DOCUMENTATION_TRUTH_AUDIT_20260825.md`
- 执行计划：`docs/superpowers/plans/2026-08-25-documentation-truth-audit.md`
- 报告分支：不适用；本次不是 Artifact 真机验收报告分支

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
## 2026-08-26 · Phase 1 Automatic Memory · Task 8 · Work Fact 与真实 Desktop

- 产品分支：`codex/phase1-automatic-memory`
- 影响模块：`src/work/`, authenticated `127.0.0.1:8766` work read routes, Python↔TypeScript Work Fact contract, formal Desktop observation pages
- 风险等级：P0
- 用户可感知变化：Home、Activity、Attention、Capture 与 Memory 必须读取同一可重启 Work Fact 链，展示真实事件、结果、失败、下一动作和真实主人待办；不能通过静态聚合状态猜测成功或待确认。
- 数据或安全边界变化：继续只使用 `lingji_state.db` 和认证 8766 Local Control API；不新增数据库、队列、事实源，不读取 SQLite 的 UI，不触碰 Vault 或第三方 AI 软件。

### 新增或修改的自动验收

- [ ] WorkStore 重启持久化、不可变事件、稳定 ID 幂等、时间排序与 limit。
- [ ] Capture → Work → Event → Outcome/Failure → Memory candidate 或 PendingAction 成功、失败、重试、主人确认路径。
- [ ] 8766 `/api/work/current`、`/api/work/pending-actions`、`/api/work/timeline/{id}` 认证、404/503、统一 DTO。
- [ ] Desktop TypeScript contract、真实 API polling、loading/empty/stale/401/503/error 状态和跨页同一 work_id。
- [ ] Task8 focused/regression、Node real smoke、py_compile/compileall/diff-check、acceptance sync、local handoff。
- [x] 兼容回归：无 `state_db` 的历史 Control Stub 不会因 Work routes 初始化而崩溃；正式 `LocalControlService` 仍只复用既有 `lingji_state.db` 注册 Work routes。
- [x] UI 真实性回归：首页待办提示不再由健康/队列聚合猜测，只有真实 `PendingAction` 才进入 Attention；当前工作卡对 loading/stale/401/503 公开真实状态。
- [x] Repair round 1：真实 `ExtractionPipeline` 队列完成、最终失败、重试和直接 execute 均回写同一 Work Fact；回调异常不改变队列状态，失败重试不提前制造主人待办，终态失败才记录 Failure/failed outcome/PendingAction，重复回调幂等。
- [x] 增加回调异常回归：生命周期 callback 抛错时队列仍保持真实 completed/failed 状态，Work Fact 不假报丢失。
- [x] Repair round 2：WorkStore/Projector 从现有 `extraction_jobs` completed/failed 终态重放 Work Fact，覆盖 callback 崩溃窗口；事件与 owner action 按稳定 ID 幂等，重试成功 resolve 旧待办，retrying 不创建主人待办，原因脱敏。
- [x] 恢复语义回归：历史 Failure 保留审计，但重试成功后的 current Work Fact 不再投影旧 Failure。
- [x] Repair round 3：重复 Capture 复用原始 queue payload.capture_id 对应的 Work；相同 dedup key 不创建孤立 Work，完成后只产生一条 outcome/terminal event；缺少 canonical capture_id 时 fail-closed。
- [x] Repair round 4：CaptureWorkBridge、CaptureControlService 与 terminal replay 的 NextAction 使用稳定 `next:<work_id>:<phase>` ID；completed/failed/retrying 重放不改变 action_id。
- [x] Repair round 5：duplicate job 缺少 canonical `payload.capture_id` 时严格不创建、不回退绑定 `result.capture_id` 对应 Work；保留单一 queue，普通新 Capture 行为不变。

### 真机与主人确认

- [ ] 真实发布版逐页点击 Overview / Activity / Attention / Capture / Memory，确认可读事实与同一 ID。
- [ ] 主人确认前不得声明 Phase 1 或 Task8 真机验收完成。

### 回滚

- 回滚产品 Commit 与本条文档提交；不触碰 Vault、原始聊天证据、正式记忆、Qdrant 或主人配置。

## 2026-08-26 · Phase 1 Automatic Memory · Remaining Work Replan

- 产品分支：`codex/phase1-automatic-memory`
- 执行计划：`docs/superpowers/plans/2026-08-26-phase1-automatic-memory-followup.md`
- 风险等级：P0
- 用户可感知变化：先消除“工作已完成但仍要求主人处理”的事实冲突，再用固定 100 问评测约束 RAG，最后进入真实 Mac M5 发布版验收；Windows 只能在 Mac PASS 后开始。
- 数据与安全边界：继续复用既有 State DB、Memory DB、Qdrant、Extraction Queue、MemoryGateway、8766 和 Desktop；不读取第三方凭证/内部数据库，不触碰普通 Obsidian 文档，不新增云端上传。

### 增量自动验收

- [ ] Work Fact 状态转换矩阵覆盖 callback/replay/restart/重复/乱序；失败后立即成功在任何 read/replay 前未解决主人待办数为 0。
- [ ] 100 问 synthetic golden corpus 数量和分类固定，未执行、重复 ID、非有限评分、缺证据和阈值边界均 fail closed。
- [ ] current/as_of/history/why、project/privacy/agent scope、citation、dedup 与 12,000 字符在 ContextPack、MemoryGateway、MCP 语义一致。
- [ ] 质量门禁：有效事实召回 `>= 90%`、引用准确 `>= 95%`、自动激活准确 `>= 95%`、Core/高风险错误晋级 `0`、current 旧决定泄漏 `0`、重复记录 `0`、ContextPack 缩减 `>= 90%`。
- [ ] Mac M5 10 万消息热态检索 P95 `<= 3s`、空闲五分钟 CPU `<= 3%`、Work Fact 心跳 `<= 10s`、Production pollution `0`、第三方可归因修改 `0`。
- [ ] 同一代码树只运行一次 `release`（其包含 full）；acceptance sync、local handoff、真实 UI 全控件、远程两次复读均通过。

### 顺序与阻断

- [ ] Task 1 Work Fact 收口独立审查通过前，不调度 RAG。
- [ ] 固定 100 问评测集审查通过前，不允许为通过指标调整问题或预期答案。
- [ ] `LOCAL_EXECUTION_TASK.md` 为 IDLE 时不得安装、启动或重跑 Artifact；产品 HEAD、同 SHA Artifact 和哈希锁定后才创建新 ACTIVE 任务。
- [ ] 主人明确确认 Mac PASS 前，不关闭验收 UI、不宣布 Phase 1 PASS、不开始 Windows。
- [ ] Windows 主机不可用时结论为 BLOCKED，不以 Mac/CI 结果冒充 Windows PASS。

### 回滚

- 每个任务仅回滚自身产品/测试/文档提交；不触碰 Vault、原始聊天证据、正式记忆、Qdrant、主人设置或第三方软件。

## 2026-08-26 · Phase 1 Automatic Memory · Task 1 follow-up · Work Fact terminal transition closeout

- 产品分支：`codex/phase1-automatic-memory`
- 产品 Commit：`2f833aa` (`fix: unify work fact terminal transitions`)
- 影响模块：`src/work/store.py`, `src/work/capture_bridge.py`, `src/control/capture.py`, Extraction Work Fact lifecycle tests
- 风险等级：P0
- 用户可感知变化：失败→重试→成功、实时 callback 与 crash replay 现在经过同一个原子 Work Fact 状态转换；成功写入时立即解决旧 `owner-failure:<work_id>`，不会在 projector/restart/reconciliation 前短暂显示“已完成”与“仍需主人处理”。
- 数据或安全边界变化：继续只使用既有 `lingji_state.db`、Extraction Queue 和认证 8766 Work Fact；仅使用 synthetic `tmp_path` 测试，不读取或修改 Production/Vault/第三方 AI 数据。

### 新增或修改的自动验收

- [x] `./.venv/bin/python -m pytest -q tests/test_task8_work_transition_matrix.py`：RED 首轮 `12 failed`（`AttributeError: WorkStore.apply_extraction_transition` 缺失），GREEN `12 passed`。
- [x] `./.venv/bin/python -m pytest -q tests/test_capture_work_bridge.py tests/test_task8_extraction_work_lifecycle.py tests/test_task8_work_fact.py tests/test_work_control_api.py tests/test_work_control_service.py tests/test_task8_work_transition_matrix.py`：`29 passed, 2 existing warnings`。
- [x] `./.venv/bin/python -m py_compile src/work/store.py src/work/capture_bridge.py src/control/capture.py tests/test_task8_work_transition_matrix.py tests/test_task8_extraction_work_lifecycle.py`：PASS。
- [x] `git diff --check`：PASS。
- [ ] `cd desktop/lingji-control && npm run test:work-fact`：BLOCKED，当前 `package.json` 未注册该脚本（`npm error Missing script: "test:work-fact"`）；该文件不在 Task 1 允许修改范围。
- [x] `cd desktop/lingji-control && npm run build`：PASS；Vite 仅报告既有 dynamic-import chunk warning。
- [x] `./.venv/bin/python scripts/check_local_execution_handoff.py`：PASS（任务单仍为 IDLE，未触发真实安装/Artifact）。
- [ ] `./.venv/bin/python scripts/check_acceptance_sync.py`：待本条 docs 同步提交后重跑。

### 真机与主人确认

- [ ] 未执行发布版、8766 实机或 Desktop 逐页点击；`LOCAL_EXECUTION_TASK.md` 仍为 `IDLE`，按规则不得启动 Artifact 或主人验收。
- [ ] 主人确认前不得声明 Task 8 真机验收或 Phase 1 PASS。

### 回归项

- [x] callback→replay、replay→callback、restart→replay、重复终态和 older-failure-after-completed 矩阵覆盖。
- [x] 失败后立即成功的同一服务实例在任何 projector/replay 前 `pending_actions == []`。
- [x] 旧 duplicate capture canonical identity、8766 route DTO、队列 terminal status 和现有 Work Fact tests 均通过指定回归。

### 清理与回滚

- 临时数据：仅 pytest `tmp_path` synthetic fixtures，测试结束由 pytest 清理；未接触主人数据。
- 回滚：分别回滚产品 Commit `2f833aa` 与本条 docs/report Commit；不触碰 Vault、原始聊天证据、正式记忆、Qdrant、主人设置或第三方软件。

### 最终报告

- 报告路径：`docs/TEST_REPORTS/PHASE1_TASK8_WORK_TRANSITION_CLOSEOUT.md`
- 产品提交：`2f833aa`
- 报告/文档提交：待提交

## 2026-08-26 · Phase 1 Automatic Memory · Task 3 · Unified cited RAG context

- 产品分支：`codex/phase1-automatic-memory`
- 基线：`90832a1`
- 产品 Commit：`163fa5d` (`feat: unify cited automatic memory context`)
- 影响模块：`src/retrieval/context_pack.py`, `src/retrieval/hybrid.py`, `src/gateway/`, `src/mcp_server.py`, `src/sources/service.py`
- 风险等级：P0
- 用户可感知变化：ContextPack、MemoryGateway 和 MCP 现在共享当前/历史时态、项目/隐私/Agent 范围、稳定来源引用、结构化消息证据和明确 semantic 降级状态；无消息链接的记忆明确标记为缺失 provenance。
- 数据与安全边界：继续复用既有 `lingji_memory.db`、SourceReadModel、SourceQueryService、HybridRetriever 和认证 MCP；仅使用 pytest synthetic `tmp_path`，不读取或修改 Production、Vault、第三方 AI 数据，也不修改 Task 2 冻结评测夹具。

### 新增或修改的自动验收

- [x] RED：focused ContextPack/MCP/Task7 命令为 `20 passed, 1 failed`；失败为无结构化消息链接错误标记 `linked_pending`，而非明确 `missing`。
- [x] GREEN：同一 focused 命令为 `23 passed`。
- [x] 回归：ContextPack、MCP、Task7、memory retrieval、permanent gateway、source service、capability contract 共 `47 passed, 1 existing Pydantic warning`。
- [x] 覆盖：current/as_of/history/why、authority ordering、agent/privacy/project linked-message isolation、gateway/direct builder identity parity、source/conversation/message/memory citations、tuple dedup、12,000 字符边界、semantic absent/throwing lexical degradation。
- [x] Task 2 fixture SHA-256 未变化：corpus `bc1812fe6444402762d01fed82f6836889868da89101318beee399b90d58de94`；questions `338f5051c43902af1ef1358aebeb356ef1d409284a1aac1d6c289625f75d3612`。
- [x] `git diff --check`：PASS。
- [ ] 未执行 Artifact、真实 UI、主人观察、Production/Vault 数据或本机 ACTIVE 验收任务；`LOCAL_EXECUTION_TASK.md` 仍为 `IDLE`。

### 回归与限制

- [x] 不新增数据库、检索器、ContextPack builder、权限实现或 MCP 后端；bootstrap 只 wiring 同一 SourceReadModel/SourceQueryService。
- [x] semantic 异常不暴露异常文本、路径、token 或凭证；诊断为调用级状态，不使用共享 last-call 状态。
- [ ] 100 问 golden quality gate、10 万消息性能、Mac M5 发布版和 Windows parity 属于后续任务，不在本 Task 3 声称通过。

### 清理与回滚

- 临时数据：仅 pytest `tmp_path`，测试结束清理；未接触主人数据。
- 回滚：回滚产品 Commit `163fa5d` 与本条文档/报告 Commit；不触碰 Vault、原始聊天证据、正式记忆、Qdrant、主人设置或第三方软件。

### 最终报告

- 仓库报告：`docs/TEST_REPORTS/PHASE1_TASK9_UNIFIED_RAG.md`
- 产品提交：`163fa5d`
- 报告/文档提交：以本次文档提交的 Git 身份为准；报告不自引用自身 SHA。

## 2026-08-26 · Phase 1 Automatic Memory · Task 3 repair round 1

- 审查结论：Needs fixes；本轮仅修复 Task 3，不进入 Task 4。
- 产品 Commit：`1a36296` (`fix: harden unified rag evidence`)
- 修复内容：隐式 current/why 不复用跨时间缓存；core 应用 memory type/tag；仅可见 scope-filtered evidence 晋级 provenance；why 以安全、限长的 selection/exclusion/conflict/reason/covered ID 进入 Markdown/MCP。
- RED：新增回归首次运行 `22 passed, 4 failed`；四个失败分别对应上述重要问题。缓存测试初始 CJK 词不命中 FTS，改为命中的 synthetic 词后仍保持 RED，之后才实现修复。上一轮初始 RED 的完整输出已不可从历史提交可靠恢复，本条不伪造补写。
- GREEN：Task 3 focused `28 passed`；scoped regression `40 passed, 1 existing Pydantic warning`。
- MCP：新增真实 `MemoryGateway` 注册工具路径回归，证明 current 排除旧决定、why 解释进入 Markdown。
- 夹具：Task 2 corpus/questions SHA 保持 `bc1812fe6444402762d01fed82f6836889868da89101318beee399b90d58de94` / `338f5051c43902af1ef1358aebeb356ef1d409284a1aac1d6c289625f75d3612`。
- `git diff --check` 与 `git diff 90832a1..HEAD --check`：PASS；修复了报告中的 Markdown trailing whitespace。
- 真实 Artifact、UI、Production/Vault、Mac M5、Windows 仍未执行；`LOCAL_EXECUTION_TASK.md` 仍为 `IDLE`。
- 报告路径：`docs/TEST_REPORTS/PHASE1_TASK9_UNIFIED_RAG.md`；文档/报告提交不在文件内自引用自身 SHA。

## 2026-08-26 · Phase 1 Automatic Memory · Task 3 repair round 2

- 审查结论：生产 enhanced retriever 的短中文 fallback 未被 ContextPack 使用；本轮仅修复 Task 3。
- 产品 Commit：`e23cac5` (`fix: unify enhanced retrieval diagnostics`)
- RED：新 parity/diagnostic/ContextPack-Gateway-MCP 回归首次 `12 passed, 3 failed`；失败为 inherited `search_with_diagnostics` 短中文结果为空、语义异常仍无 fallback、注册 MCP 短中文证据为空。
- GREEN：Task 3 focused `31 passed`；scoped `40 passed, 1 existing Pydantic warning`。
- 实现：`search()` 与 `search_with_diagnostics()` 共用 enhanced 单次 fallback/fusion helper；base why attachment 可按调用抑制，enhanced 最终只附加一次；不新增 retriever、缓存状态或权限路径。
- 注册 MCP 实测：真实 `MemoryGateway` + registered tool path 能召回 `灵机` 记忆/消息，semantic absent diagnostics 正确；ContextPack/Gateway 同样通过。
- Task 2 fixture SHA 保持 corpus `bc1812fe6444402762d01fed82f6836889868da89101318beee399b90d58de94`、questions `338f5051c43902af1ef1358aebeb356ef1d409284a1aac1d6c289625f75d3612`。
- `git diff --check` 与 `git diff 90832a1..HEAD --check`：PASS；acceptance sync/local handoff 待本条文档提交后重跑。
- 真实 Artifact、UI、Production/Vault、Mac M5 与 Windows 仍未执行；`LOCAL_EXECUTION_TASK.md` 仍为 `IDLE`。
- 文档/报告提交不在文件内自引用自身 SHA。

## 2026-08-26 · Phase 1 Automatic Memory · Task 2 follow-up · Frozen 100-question quality gate

- 产品分支：`codex/phase1-automatic-memory`
- 基线：`d4bce2f`
- 产品 Commit：`e8b620e` (`test: define automatic memory quality gate`)
- 影响模块：`src/automatic_memory/evaluation.py` 与 synthetic evaluation fixtures/tests
- 风险等级：P0
- 用户可感知变化：冻结独立的 100 问质量合同与确定性 PASS/FAIL/BLOCKED 门禁；不改变 retrieval、ContextPack、MemoryGateway、MCP、promotion、Desktop、adapters、数据库或队列。
- 数据与安全边界：仅使用仓库内手工 synthetic JSONL；无网络、模型、Production、Vault、真实聊天、凭证或主人数据读取。

### 新增或修改的自动验收

- [x] RED：`./.venv/bin/python -m pytest -q tests/evaluation/test_automatic_memory_quality.py tests/test_automatic_memory_acceptance_gate.py`：收集失败，`ModuleNotFoundError: src.automatic_memory.evaluation`。
- [x] RED 修复轮：新 adversarial focused tests 在旧实现上 `55 failed, 13 passed`，暴露语义 fixture、identity score、raw context、strict counters 和递归隐私合同缺失。
- [x] RED 修复轮 2：语义 041/091、corpus-first evaluate_run、direct forged evidence、None/non-sequence evidence 和 embedded Windows/UNC path 测试在旧实现上 `16 failed, 69 passed`。
- [x] GREEN：同一命令：`86 passed`。
- [x] 自动记忆相关回归：指定 adapters/control/obsidian/resume/scheduler/snapshot/source_registry/watcher 加质量门禁：`238 passed, 3 warnings`。
- [x] `py_compile` 与 `git diff --check`：PASS。
- [x] mutation thresholds：89.999/90、94.999/95、保护误晋级、stale 泄漏、重复记录、Production 写入、99/100 问、消息/角色不匹配、零分母、owner/reboot 缺失及 `NaN` 均按契约阻断； measured FAIL 优先于 BLOCKED。
- [ ] 未执行 Artifact、真实 UI、主人观察、Production/Vault 数据或本机 ACTIVE 验收任务；`LOCAL_EXECUTION_TASK.md` 仍为 `IDLE`。

### 回归项

- [x] fixture 恰好 100 条 question；corpus 为关系所需的 `145` 条 record，九类问题数量严格为 `20/20/15/10/10/10/5/5/5`。
- [x] semantic fixture：`145` corpus records；superseded/temporal old→replacement、cross-session conversation、authority levels、scope project/privacy/agent、dedup content_hash 关系均有测试审计。
- [x] fixture SHA-256：corpus `bc1812fe6444402762d01fed82f6836889868da89101318beee399b90d58de94`；questions `338f5051c43902af1ef1358aebeb356ef1d409284a1aac1d6c289625f75d3612`。
- [x] question/result/corpus 重复 ID、缺少证据、结构错误、非有限分数、零分母、秘密样式和绝对路径样式均 fail-closed。
- [x] gate 百分比使用 0–100，并保留 numerator/denominator；不从生产检索或模型计算预期答案。

### 清理与回滚

- 临时数据：仅 pytest `tmp_path`（本任务无持久临时数据），未接触主人数据。
- 回滚：分别回滚产品 Commit `e8b620e` 与本条 docs/report Commit；不触碰 Vault、raw evidence、formal memory、Qdrant、主人设置或第三方软件。

### 最终报告

- 完整报告：`.superpowers/sdd/2026-08-26-phase1-automatic-memory-followup/task-2-report.md`
- 仓库报告：`docs/TEST_REPORTS/PHASE1_TASK9_GOLDEN_EVALUATION.md`
- 产品提交：`e8b620e`

## 2026-08-26 · Phase 1 Automatic Memory · Task 1 review round 1 · Work Fact ordering, pending-action persistence and Desktop smoke gate

- 产品分支：`codex/phase1-automatic-memory`
- 产品 Commit：`31a14a4` (`fix: harden work fact transition persistence`)
- 影响模块：`src/work/store.py`, `tests/test_task8_work_transition_matrix.py`, `desktop/lingji-control/package.json`
- 风险等级：P0
- 用户可感知变化：历史/混合时区 Work Fact 事件按真实 UTC instant 选择 current；同一 owner failure 永远只有一条真实 SQL action row，恢复后可复用并重新打开；Desktop `test:work-fact` 现在运行既有 smoke。
- 数据或安全边界变化：继续使用既有 `lingji_state.db` 和认证 8766 Work Fact；迁移只在现有 `pending_actions` 表上去重并建立唯一 action_id 索引；测试只使用 synthetic temporary SQLite。

### 新增或修改的自动验收

- [x] Repair RED：`./.venv/bin/python -m pytest -q tests/test_task8_work_transition_matrix.py`：`3 failed, 12 passed`，覆盖文本时间排序、重复 owner-failure SQL 行、legacy duplicate migration。
- [x] Repair GREEN：同一矩阵命令 `15 passed`。
- [x] Python regression：指定 Task 1–8 focused 命令 `32 passed, 2 existing warnings`；无新 warning 类别。
- [x] `cd desktop/lingji-control && npm run test:work-fact`：`work-fact-smoke: PASS`，精确映射现有 `scripts/work-fact-smoke.mjs`。
- [x] `cd desktop/lingji-control && npm run build`：PASS；仅既有 Vite dynamic-import warnings。
- [x] `py_compile`、`git diff --check`：PASS。
- [x] `./.venv/bin/python scripts/check_acceptance_sync.py`：待本条 docs 同步提交后重跑。
- [x] `./.venv/bin/python scripts/check_local_execution_handoff.py`：PASS；任务单仍为 IDLE。

### 回归项

- [x] `10:00+02:00` 与 `09:00Z` 解析为 UTC instant；naive timestamp 按 UTC 解释；malformed candidate fail-closed。
- [x] 旧 `pending_actions` duplicate 在 migration 前压缩；唯一索引建立；重复/恢复后 owner-failure 总行数与 unresolved 数均为 1。
- [x] 未创建第二个 Desktop smoke；不改变队列 terminal、duplicate-capture、8766 auth、DTO、Vault 或 memory promotion。

### 清理与回滚

- 临时数据：仅 pytest `tmp_path` synthetic fixtures，测试结束清理；未接触主人数据。
- 回滚：回滚产品 Commit `31a14a4` 和本条 docs/report Commit；不触碰 Vault、raw evidence、formal memory、Qdrant、主人设置或第三方软件。

### 最终报告

- 完整报告：`.superpowers/sdd/2026-08-26-phase1-automatic-memory-followup/task-1-report.md`
- 仓库报告：`docs/TEST_REPORTS/PHASE1_TASK8_WORK_TRANSITION_CLOSEOUT.md`
- 产品提交：`31a14a4`
- 报告/文档提交：待提交

## 2026-08-27 · Phase 1 Automatic Memory · Promotion safety closeout

- 基线：`a2023dc9bdc5e4036f9dfbd128e71494e89a4660`
- 影响模块：`src/auto_review/promotion.py`, `src/storage/state_db.py`, promotion transaction/recovery tests
- 风险等级：P0
- 用户可感知变化：普通晋级审计事件必须经过 `append_promotion_event`; 缺少安全记录器时 fail-closed；递归非有限数值在 SQLite 写入前拒绝；候选/结果序列化对非有限值保持 owner-safe。
- 数据与安全边界：不新增事实源、数据库、队列或服务；事件 payload 继续 allowlist/redact，禁止 token、owner path、fixture/evaluator label 与 exception 文本；仅 pytest `tmp_path` SQLite、synthetic Vault 与真实 MemoryGateway 读取链路。

### 新增或修改的自动验收

- [x] RED serialization：`./.venv/bin/python -m pytest -q tests/test_task4_reset_promotion_transaction.py -k 'safe_promotion_event_boundary or non_finite_nested_values'` → `4 failed, 48 deselected`。
- [x] GREEN serialization：同一命令 → `4 passed, 48 deselected`。
- [x] RED recovery matrix：新增 `tests/test_promotion_recovery_matrix.py`；12 个命名案例（case 11 含四种 temporal mode）均运行真实 SQLite durable rows、reopen、trigger/race、raw retrieval 与 Gateway 证据；已有行为记录为 baseline，不据此修改 recovery 代码。
- [x] GREEN focused：Task 4 promotion/recovery 与 Task 1–7 temporal/context 回归 → `150 passed, 2 existing warnings`。
- [ ] 未执行 Artifact、真实 UI、主人观察、Production/Vault 数据或本机 ACTIVE 验收任务；`LOCAL_EXECUTION_TASK.md` 保持 `IDLE`。

### 回归项

- [x] 12-case durable recovery matrix：second-link rollback；activation retry；独立连接竞争；start/prepare/link/activation 各重启边界；repair-required 单调性；NULL/foreign link ownership；authoritative SQLite temporal filter；raw/Gateway identity parity；promotion audit missing/extra/duplicate 计数。
- [x] 固定 Task 2 fixture SHA 未改变：corpus `bc1812fe6444402762d01fed82f6836889868da89101318beee399b90d58de94`；questions `338f5051c43902af1ef1358aebeb356ef1d409284a1aac1d6c289625f75d3612`。
- [x] `py_compile`、`git diff --check`、acceptance sync、local handoff 均纳入本轮完成门禁。

### 清理与回滚

- 临时数据：仅 pytest `tmp_path` synthetic SQLite/Vault；测试结束自动清理，未接触 Production、Vault、Qdrant 或主人配置。
- 回滚：分别回退本轮产品/测试提交与本条文档提交；不触碰正式记忆、原始证据、主人配置或第三方软件。

### 最终报告

- 完整报告：`.superpowers/sdd/2026-08-27-promotion-safety-closeout/task-0-report.md`
- 产品提交：`22be155e30279fdd43384a02cc2a456efb805144`（`fix: close promotion safety boundary`）
- 报告/文档提交：待提交（`docs: record promotion safety closeout`）

## 2026-08-27 · Phase 1 Automatic Memory · Task 1 Repair Round 2 · Thin quality runner and authority boundary

- 基线：`5c3bed8f8a4fb77632b41ec7e0c23c8ebeb72a78`
- 影响模块：`src/automatic_memory/quality_gate.py`, `src/automatic_memory/quality_evidence.py`, quality CLI/validation wiring and reset runner tests
- 风险等级：P0
- 用户可感知变化：无新的产品能力；质量报告仅发布真实、可重算的本地证据，并在 4R2 readiness 前保持 `functional_status=NOT_EVALUATED` / `phase_status=NOT_EVALUATED`。
- 数据与安全边界：质量运行只使用临时 Acceptance roots 和仓库冻结 synthetic fixtures；禁止读取或写入 Production/Vault，禁止触碰真实聊天、凭证、Qdrant、Desktop 或 100k 规模数据。

### 增量自动验收

- [x] Repair Round 2 RED/GREEN：历史 C1 断言恢复后 targeted RED `5 failed, 34 passed`；mode/access、lexical cleanup inventory、measured-failure precedence、release preflight spy、gateway enum、cleanup allowlist GREEN。
- [x] Task 1–5 reset regressions、冻结 corpus/questions SHA-256、`py_compile`、`git diff --check`、acceptance sync、local handoff；最终复跑含 `tests/test_task4_reset_promotion_transaction.py` 的完整矩阵 `336 passed`。
- [ ] 不执行 Artifact、真实 UI、主人观察、Production/Vault、4R2 或 100k；`LOCAL_EXECUTION_TASK.md` 仍为 `IDLE`。

### 清理与回滚

- 临时数据：仅 pytest `tmp_path` / OS temporary Acceptance roots，测试完成自动清理；不接触主人数据。
- 回滚：分别回退 Task 1 产品/测试提交与本条文档提交；不触碰 Vault、raw evidence、正式记忆、Qdrant、主人设置或第三方软件。

### 最终报告

- 完整报告：`.superpowers/sdd/2026-08-27-phase1-product-landing/task-1-report.md`
- 产品/测试提交：`2b99cc53d493929a0e2e75c0f79d6834355fb7dc`、`50cc0e0`、`5f75e3af9b2269519337de68db6a688bd4e654f0`
- 权威文档提交：`3414101d8fe30033aaea66eaa2cf615d580ad515`；先前报告证据：`d1c0185887e450945c5eb607aa7199b835cd2483`
- 独立报告提交：`3590c285ef586d028e23cfc5df78357630a91557`、`4201ab9fdd9a28ee0d90c057f66bd2ed99d43e55`
## 2026-08-27 · Phase 1 Automatic Memory · Task 2 Repair Round 2 (final)

- 基线：`5510b4f27b8fd0567f4fd89a7f5ba2f65635bb77`；影响模块：packaged runtime canonical composition, automatic-memory scheduler revocation lifecycle, runtime/packaged subprocess tests。
- 本轮仅修 I5/I3：撤销先禁用 scheduler jobs，再以 100ms bounded watcher stop 保留 survivor/stopping 状态并由 runtime status 暴露 cleanup pending；runtime fail-closed 校验 state_db、queue、pipeline.queue、registry.state_db、scheduler.state_db 必须解析到同一 canonical path。
- [x] Round2 focused：`./.venv/bin/python -m pytest -q tests/test_automatic_memory_runtime.py tests/test_packaged_control_api.py` → `32 passed, 6 warnings`。
- [x] Runtime/scheduler/watcher/state/worker/promotion sentinel：对应矩阵 → `167 passed, 6 warnings`。
- [x] Packaged wrapper subprocess：真实 `run_packaged_control_api.main()` 正常/启动失败清理、real jobs/thread ownership、one DB/queue assertions；仅 uvicorn network boundary stubbed。
- [x] Desktop smoke：`npm run test:runtime` → `runtime-sidecar-smoke: PASS`；compileall 与 `git diff --check` → PASS。
- [ ] broader promotion recovery matrix has one unrelated baseline failure (`test_recovery_case_06_restart_after_link_commit_activates_after_verification`: rolled_back vs VISIBLE_ACTIVE); no promotion code/seams were changed in Task2 Round2。
- [ ] 不执行 Artifact、真实 UI、Production/Vault、8766 live server、Task3 snapshot consumer/adapter/terminal extraction 或 owner acceptance；`LOCAL_EXECUTION_TASK.md` 保持 `IDLE`。Round2 后停止，不开启第三轮。

## 2026-08-27 · Phase 1 Automatic Memory · Task 3 · Authorized discovery → extraction → Work Fact

- 基线：`b36c597`；产品/测试提交：`bc3636a`；报告/文档提交：`0d7bb84`；分支：`codex/phase1-automatic-memory`。
- 影响模块：`src/automatic_memory/discovery.py`, `src/automatic_memory/path_policy.py`, `src/automatic_memory/checkpoint.py`, `src/automatic_memory/runtime.py`, `src/extraction/queue.py`, `src/extraction/pipeline.py`, `src/control/automatic_memory_api.py` 及 Task 3 focused tests。
- 用户可感知变化：在明确授权与 allowlist 内元数据发现来源，安全枚举受支持文件；通过既有 extraction registry/queue/pipeline/adapters 消费 internal snapshot，写入结构化 source/conversation/message 行，并暴露可追踪的 terminal Work Fact 与认证 8766 读取/动作接口。
- 安全边界：发现阶段不读聊天正文；拒绝 filesystem root、whole home、凭证/token/cookie/private DB、symlink escape、无界递归与未知格式；Obsidian 仅复用 managed-path/frontmatter discovery；不调用任何自动晋级 seam；不接触 Production/Vault/owner data。

### 增量自动验收

- [x] 严格 TDD RED：初次模块缺失导致 collection errors 后，测试先改为明确模块缺失断言；随后执行 focused behavioral RED：`./.venv/bin/python -m pytest -q tests/test_automatic_memory_discovery.py tests/test_automatic_memory_runtime_flow.py tests/test_automatic_memory_work_fact.py tests/test_automatic_memory_obsidian.py --tb=short` → `14 failed`。
- [x] GREEN focused：`./.venv/bin/python -m pytest -q tests/test_automatic_memory_discovery.py tests/test_automatic_memory_runtime_flow.py tests/test_automatic_memory_work_fact.py tests/test_automatic_memory_obsidian.py tests/test_automatic_memory_control_api.py tests/test_extraction_worker.py` → `24 passed, 1 warning`。
- [x] 直接受影响 runtime/extraction/worker/Obsidian/API 回归（排除 Task 2 已知 stale scheduler timing edge）：同一矩阵加 `-k 'not daily_integrity_job_runs_without_event'` → `195 passed, 1 deselected, 7 warnings`。不加排除项时唯一失败为既有 `integrity_seconds` 最小值 clamp 导致的 `test_daily_integrity_job_runs_without_event`；Task 3 未修改该边界。
- [x] `compileall`、`git diff --check`、acceptance sync、local handoff 纳入最终门禁；重复授权 snapshot 使用既有 idempotency key，来源失败不阻塞其他来源。
- [ ] 不执行 Artifact、真实 UI、Production/Vault、8766 live server、owner acceptance 或本机 ACTIVE 任务；`LOCAL_EXECUTION_TASK.md` 保持 `IDLE`。

### 清理与回滚

- 临时数据：仅 pytest `tmp_path` synthetic source files/SQLite/Vault；测试自动清理，未接触主人数据。
- 回滚：分别回退产品/测试提交 `bc3636a` 与本条 evidence/docs 提交 `0d7bb84`；不触碰正式记忆、raw evidence、Qdrant、主人设置或第三方软件。

### 最终报告

- 完整报告：`.superpowers/sdd/2026-08-27-phase1-product-landing/task-3-report.md`
- 产品/测试提交：`bc3636a`
- 报告/文档提交：`0d7bb84`

## 2026-08-27 · Phase 1 Automatic Memory · Task 3 Repair Round 1 · eight Important findings

- 基线/审查：`53c4ce0` / review `0d7bb84`；产品/测试提交：`f2f7312`；报告/文档提交：`4e5d744`；元数据修正提交：`95cfc90`；分支：`codex/phase1-automatic-memory`。
- 影响模块：existing extraction queue/pipeline, SnapshotJobRunner/ScanRun/ReconciliationReport, bounded Obsidian memory scope, automatic-memory path policy/runtime/API, existing WorkStore, and repair regression tests。
- 本轮仅修复 I1–I8：内部未授权快照终态失败并通知生命周期；Obsidian 只读有界 frontmatter 且保留 managed `lingji_memory:false` 优先级；敏感文件名大小写/分隔符变体排除；两次扫描新增/复用计数与结构化身份真实；scan API 通过已组合 runtime；WorkItem source/status 与 Outcome 一致；修正历史证据 SHA；automatic AI-chat snapshot 不调用 Vault 文档 sink、不改配置 Vault。
- 安全边界：不修改 Task 2 lifecycle/timing edge，不调用 promotion seams，不新增 store/parser/queue/API/indexer/UI/retrieval/vector/quality/release/100k，不执行 Artifact、live 8766、Production/Vault/owner 数据。

### 增量自动验收

- [x] 修复 RED：`./.venv/bin/python -m pytest -q tests/test_automatic_memory_repair_round1.py --tb=short` → `8 failed, 1 warning`，八项失败分别对应 I1–I8。
- [x] Repair focused GREEN：`./.venv/bin/python -m pytest -q tests/test_automatic_memory_repair_round1.py tests/test_automatic_memory_control_api.py tests/test_extraction_worker.py tests/test_automatic_memory_runtime_flow.py tests/test_automatic_memory_work_fact.py tests/test_automatic_memory_discovery.py tests/test_automatic_memory_obsidian.py tests/test_obsidian_memory_scope.py --tb=short` → `22 passed, 1 warning`。
- [x] Direct runtime/scheduler/snapshot/queue/worker/adapters/structured/Work Fact/API/Obsidian regression excluding only preserved Task 2 timing test → `209 passed, 1 deselected, 7 warnings`；unfiltered run remains `209 passed, 1 failed, 7 warnings`, failure is `test_daily_integrity_job_runs_without_event` due existing one-second clamp and is not hidden or changed。
- [x] `compileall`, `git diff --check` over repair range, `check_acceptance_sync.py`, and `check_local_execution_handoff.py` required before docs commit；handoff remains `IDLE`。
- [ ] 不执行 Artifact、真实 UI、Production/Vault、8766 live server、owner acceptance；`LOCAL_EXECUTION_TASK.md` 保持 `IDLE`。

### 清理与回滚

- 临时数据：仅 pytest `tmp_path` synthetic files/SQLite/Vault; 自动清理，未接触主人数据。
- 回滚：回退产品/测试提交 `f2f7312` 与本条 evidence/docs 提交 `4e5d744`；不触碰正式记忆、raw evidence、Qdrant、主人设置或第三方软件。

### 最终报告

- 完整报告：`.superpowers/sdd/2026-08-27-phase1-product-landing/task-3-repair-1-report.md`
- 产品/测试提交：`f2f7312`
- 报告/文档提交：`4e5d744`
- 元数据修正提交：`95cfc90`

## 2026-08-27 · Phase 1 Automatic Memory · Task 3 Repair Round 2 FINAL · four Important findings

- 基线/审查：`3edbfc8` / Repair Round 1 review；产品/测试提交：`7058da0`；报告/文档提交：`b83232d`；元数据修正提交：`843b9cb`；分支：`codex/phase1-automatic-memory`。
- 影响模块：bounded Obsidian frontmatter reader, existing Generic AI History adapter identity material, automatic-memory Work Fact projection, and Task 3 evidence metadata。
- 本轮仅修复四项最终 Important：LF/CRLF 与 BOM frontmatter 显式拒绝、自动 Generic AI 跨授权 source identity namespace、30%/70% pause-resume truthful Work Fact total、Round 1 三提交身份补全。无第三轮修复。
- 安全边界：不修改 Task 2 lifecycle/timing edge，不调用 promotion seams，不新增 parser/store/queue/API/indexer/UI，不写 Vault Markdown，不执行 Artifact、live 8766、Production/Vault/owner 数据。

### 增量自动验收

- [x] 修复 RED：`./.venv/bin/python -m pytest -q tests/test_automatic_memory_repair_round2.py --tb=short` → `5 failed in 0.75s`，覆盖五个新增断言（CRLF/BOM、跨来源身份、30%/70% 恢复计数、三 SHA 证据）。
- [x] Repair Round 2 focused GREEN：同一命令 → `5 passed in 0.86s`。
- [x] Task 3 repair 与直接受影响矩阵 → `223 passed, 7 warnings`；历史 Task 2 scheduler timing boundary 本次通过但仍保持隔离，不计为本轮修复。
- [x] `compileall`、`git diff --check 3edbfc8..HEAD`、`check_acceptance_sync.py`、`check_local_execution_handoff.py` required before final metadata；handoff remains `IDLE`。
- [ ] 不执行 Artifact、真实 UI、Production/Vault、8766 live server、owner acceptance；`LOCAL_EXECUTION_TASK.md` 保持 `IDLE`。

### 清理与回滚

- 临时数据：仅 pytest `tmp_path` synthetic files/SQLite/Vault；自动清理，未接触主人数据。
- 回滚：回退产品/测试提交 `7058da0` 与本条 evidence/docs 提交；不触碰正式记忆、raw evidence、Qdrant、主人设置或第三方软件。

### 最终报告

- 完整报告：`.superpowers/sdd/2026-08-27-phase1-product-landing/task-3-repair-2-report.md`
- 产品/测试提交：`7058da0`
- 报告/文档提交：`b83232d`
- 元数据修正提交：`843b9cb`
## 2026-08-28 · Phase 1 Product Landing · Task 6 Packaged Automation E2E

- 基线：Task 6A final review `22aae07be9accf7d56a4273e8d45a521b2323dab` accepted for Task 6; reviewed product head remains `efde650e77a4ecda7f7266aefe48b29b9e8712de` plus final review documentation. Task 5B final review `bd2ff43` remains `ACCEPT_FOR_TASK6`.
- 范围：仅在 pytest `tmp_path` / OS temporary Acceptance roots 中启动真实 `run_packaged_control_api` composition subprocess，驱动认证 loopback API 和持久 StateDB/queue/raw/structured/read-model/lexical evidence；不安装 Artifact、不访问 Production/Vault/主人数据、不占用真实 8766/8767。允许注入仅限测试网络端口、clock-jump equivalent and process crash/restart boundaries; no promotion seam is called.
- 自动验收：十个核心场景必须实际执行并保存 raw counts/timings：metadata-only discovery、one-time authorization/startup scan、watch event queue latency、suppressed-event accelerated reconciliation、30%/70% crash restart terminal parity、pause/resume/revoke/expiry、corrupt-source isolation、Qdrant outage truthful lexical fallback、sleep/wake clock-jump restart、recursive third-party/Vault sentinel. 每轮从 clean Acceptance root 开始并连续运行两轮；source/conversation/message/memory duplicate counts、queued residue、silent errors、heartbeat age 和 sentinel diff 均从持久状态/递归文件树重算，禁止常量和布尔自证。
- 失败边界：无法在 Acceptance-only 等价路径证明的项必须记录 `BLOCKED` 或 `FAIL`，不得跳过；任何 packaged composition、持久计数、隔离、降级 reason、恢复 parity 或 sentinel 变更失败即不通过。Qdrant 场景必须注入正式 vector client failure 并走正式 retrieval orchestration；不改变 promotion、quality runner、retrieval ranking/model/vector design、UI feature 或 API family。
- 清理：每个测试结束停止并按 PID/实例确认 packaged subprocess 退出，删除本轮临时 root、日志和 fixture；不得清理工作区主人数据。失败证据仅保留脱敏摘要/报告需要的 counts、timings、sentinel diff。
- 回滚：代码/测试提交与文档/证据提交分离；如集成 RED 暴露 Tasks 2–5 wiring bug，先停在最小复现并通知根代理，未经授权不扩改产品。
- UI/回归：注册 `focused -Area automatic-memory-landing` 与既有 `desktop/lingji-control/tests/e2e_owner_memory_flow.mjs` rendered command；另行执行 Task 2/3/4/5 regressions、compileall、diff-check、acceptance sync、local handoff。真实 UI、Artifact、主人观察和 release 仍为未完成状态。
- 报告：唯一权威报告 `docs/TEST_REPORTS/PHASE1_AUTOMATION_UI_GATE.md`；`.superpowers/sdd/2026-08-27-phase1-product-landing/task-6-report.md` 仅作交接引用。

### Task 6 Repair Round 1（diagnostic review `361733b3c660e1b5dc36e5500e1f2436da41572e`）

- 边界：仅修正 Task6 packaged harness 证据边界和批准的 scheduler/runtime durable `scan_id/work_id` wiring；不改变 DB schema、queue、retrieval、promotion、UI 或 API family。Task6A final review `22aae07be9accf7d56a4273e8d45a521b2323dab` 保持 `ACCEPT_FOR_TASK6`，不将本轮标为 Task6A。
- RED：新增 race/old-scan regression 首次失败为 `AttributeError: ReconciliationReport.scan_id`；修复后 scheduler/runtime 定向回归 `52 passed`。
- 自动化边界：真实 `run_packaged_control_api.py` subprocess、loopback authenticated API、StateDB/queue/raw/structured/Work Fact/lexical reads；每个 root 保存脱敏 stdout/stderr、PID/port/child inventory，并验证实例退出和端口重新 bind。启动前递归 sentinel 基线仅允许显式 VaultLayout bootstrap directory paths，第三方树零排除。
- 失败/阻塞边界：Qdrant 必须在 packaged ingestion 产生的正式 lexical record 上执行正式 retrieval orchestration；当前 automatic-memory ingestion 仅写 raw/structured read model、不产生 lexical `memory_documents`，预置 Vault fact 不计证据，scenario 8 保持 `BLOCKED`。现有 scheduler idle heartbeat 为 nullable/诚实 `NOT_MEASURED/BLOCKED`，不以终态 Work Fact 时间冒充，需另开 Task6H。
- 清理/回滚：仅清理本轮 pytest/`/private/tmp` Acceptance roots、logs 和 fixtures；按 PID/实例停止，端口重新绑定确认；代码/测试和报告文档分离提交。回滚本轮仅回退 `04eb1d3`、`b6e8c77`、`31f40a3` 及对应文档，不触碰主人数据。

## 2026-08-28 · Task 6L · Structured evidence lexical wiring

- 基线：`81ffaec967cf65a55ea692161b3c16ecd7d6d6e0`; bounded landing task only. The
  existing StructuredReadModel rows remain evidence authority; this change adds
  only a rebuildable `memory_documents`/FTS projection consumed by the existing
  HybridRetriever/Gateway/MCP/ContextPack paths.
- 边界：automatic imports never write Obsidian/Core Memory/candidates and never
  call promotion seams. Each valid message gets a deterministic evidence
  projection carrying source/conversation/message IDs, external identities,
  role/order/content hash, raw reference and occurred time. Empty/unsupported
  message bodies are not indexed; source identities remain namespaced.
- RED: add a real Generic AI History `ExtractionPipeline.execute()` test and
  prove formal lexical Gateway search is empty before the bridge. No direct
  `memory_documents` fixture seeding is used.
- Required GREEN/regression: same pipeline must yield an evidence lexical hit;
  Gateway, MCP and ContextPack must cite the same message identity; semantic
  client failures must preserve the lexical result with degraded diagnostics;
  repeated import must not add documents/chunks; deleting/rebuilding the
  rebuildable projection must restore it from structured rows. Run focused
  structured/extraction/retrieval/context/provenance/promotion regression plus
  compileall, diff-check, acceptance sync and local handoff checks.
- Explicit limitation to report: authorization registry revocation lives in
  `lingji_state.db`, while structured read-model source status is in
  `lingji_memory.db`; this task must not invent a second state bridge. If the
  current retrieval filters cannot observe revocation, leave it as a bounded
  blocker rather than expanding the state model.
- Safety: pytest temporary roots only; no live 8766/8767, Artifact,
  Production/Vault, owner data, Qdrant or UI acceptance. Product/tests and
  docs/evidence are separate commits.

## 2026-08-28 · Task 6L · Repair Round 1 — lifecycle isolation and update supersession

- 基线/审查：Task 6L product/test `9ced68b`，独立审查 `c69afdc`；本轮只修复
  Important I1（StateDB revoke/expired 在 current Gateway/Hybrid/MCP/ContextPack
  泄漏）和 I2（自动 snapshot 内容更新产生两个 active current evidence），并顺手
  修复同审查直接相关的 Minor M1（raw citation）与 M2（ContextPack role/sequence）。
  产品/测试提交：`5258ecef98e2b58dfb9c12af585a4fbd44c260dd`；无第二 repair。
- 边界：复用现有 `SourceRegistry` lifecycle listener、`SourceReadModel`、
  `memory_documents`/FTS 与 `MemoryDatabase.revision`；StateDB 仍是授权权威，
  `lingji_memory.db` 仍是可重建检索投影。自动聊天仍只写 raw + structured evidence，
  不写 Obsidian、不创建 candidate/Core/active memory、不调用 promotion seam，不改
  ranking/embedding/vector/evaluator/API family。未知/非 authorized 状态投影为
  archived，current fail-closed；启动时从持久 StateDB 状态重新投影。
- RED：新增真实 `SourceRegistry` + `ExtractionPipeline.execute()` 测试前，revoke
  后 Gateway current 仍有结果、内容更新后有两个 active 文档；未直接塞入
  `memory_documents`。GREEN：生命周期投影、稳定 automatic source namespace、
  citation/raw_reference 与 ContextPack role/sequence 修复后通过。
- focused/regression：`tests/test_structured_evidence_lexical.py` `9 passed, 1
  warning`；structured/extraction/retrieval/context matrix `57 passed, 1 warning`
  （修复前 focused aggregate 为 55，新增 2 个 repair tests）；审查候选/来源/时态
  matrix `46 passed, 2 warnings`；runtime/discovery/Obsidian/worker `36 passed,
  1 warning`；Gateway/MCP/ContextPack/Obsidian/promotion quarantine `75 passed,
  1 warning`；Task 6 packaged Qdrant lexical helper `1 passed, 1 warning`。
- 正式路径证据：真实 pipeline 导入的同一 message identity 在 Gateway current、
  ContextPack 与正式 MCP `search_memory` 中可检索；revoke/expired 后三者的
  current 结果为空，history/as_of 保留原始 structured evidence，重启后仍隔离；
  Qdrant client 抛错时 Gateway/ContextPack 保留 lexical structured evidence，
  diagnostics 为 `semantic=degraded` / `reason_code=semantic_query_failed`。
  内容 v1→v2 只保留一个 current document，same-bytes replay 新增/更新均为 0，
  cross-source identity 仍独立；raw reference、role、sequence 随 citation 返回。
- 验证：`python -m compileall -q src tests/test_structured_evidence_lexical.py`
  PASS；`git diff --check 81ffaec..5258ece` PASS。未执行 live 8766/8767、Artifact、
  release、Production/Vault、owner acceptance；`LOCAL_EXECUTION_TASK.md` 保持
  `IDLE`。Task 6 authority `docs/TEST_REPORTS/PHASE1_AUTOMATION_UI_GATE.md` 仍
  `IN_PROGRESS / NOT_ACCEPTED`，其 packaged crash/H 门禁与此前 scenario 8 blocker
  不因本轮 focused evidence 改写。
## 2026-08-28 · Task 6S · Query-time source authority and evidence versions

- 基线：Task6L Repair Round 1 product/test `5258ecef98e2b58dfb9c12af585a4fbd44c260dd`；终审 `3edbfc8`（`BLOCKED_AT_REPAIR_CAP`）确认四项 Important：自然授权过期 current 泄漏、投影异常吞错导致 current 泄漏、revoke 与 upsert 竞态回流、v1→v2 未保留 history。Task6S 是全新架构重规划，不是 Task6L Repair2。
- 范围：复用现有 `lingji_state.db` AutomaticMemory SourceRegistry/StateDatabase 作为唯一授权权威；通过正式 Gateway/Hybrid/MCP/ContextPack composition 注入查询时批量 resolver；复用 `lingji_memory.db`/`memory_documents`/FTS 保存 content-hash 版本、validity、supersession 元数据。不得新增 DB/API/retriever/queue/表或调用 promotion/Obsidian/Core。
- 风险等级：P0。current structured evidence 对 unknown、StateDB unavailable/locked/解析错误、revoked/expired 一律 fail closed；history/as_of 继续遵守 viewer/agent/project/privacy 范围。普通 Obsidian/非 structured memory 不得被 guard 误杀。
- RED：新增真实 pipeline/Gateway/ContextPack/MCP 测试，覆盖自然 expiry 无 callback、projection observer 抛错、threaded revoke-vs-upsert barrier、StateDB unavailable/locked、v1→v2 current/history/as_of、same bytes、cross-source、Qdrant outage、普通 Obsidian。
- GREEN：单次 query 批量检查 source status；授权变更立即影响 current 且 resolver diagnostics 诚实；新 hash 插入 active 版本并原子 archive 旧版本，保留 `valid_from/valid_to/superseded_by/supersedes/reason`；顺序重放 v1/v2 raw snapshot 可重建两版 history。
- 真机/主人确认：`LOCAL_EXECUTION_TASK.md` 保持 `IDLE`；不启动 live 8766/8767、Artifact、Production/Vault 或主人 UI/数据。本条不构成 Task6、release 或主人验收通过。
- 清理/回滚：仅 pytest 临时 SQLite/raw/fixture；报告与日志使用 `.superpowers/sdd/2026-08-27-phase1-product-landing/`，不 force-add ignored 报告。回滚本轮产品/测试与文档提交，不触碰主人数据。

## 2026-08-28 · Task 6S · Repair Round 1 — cache, orphan projection, linked evidence

- 审查基线：Task6S product/tests `5fb2966`、docs/evidence `bbdc037`；独立终审 `1816d361542a86141eeb28de0d88c66899aa0ce1` 保留三项 Important：显式 current/why cache 命中绕过 authority、read-model rebuild 后 active orphan structured projection、ContextPack linked raw evidence 绕过 authority。本轮是唯一批准 Repair Round 1；若仍有 Important 即 `BLOCKED_AT_REPAIR_CAP`。
- 最小范围：只改现有 `HybridRetriever` cache、`MemoryDatabase.sync_structured_evidence`、`ContextPackBuilder` 与同一 resolver 注入/测试；不新增 DB/API/retriever/服务/表，不改 history 语义、promotion、Vault/Core、ranking/vector。
- RED：新增 warm-cache→revoke、rebuild([])→sync orphan、ordinary anchor linked automatic message revoke 三项真实测试，修复前 `3 failed`。GREEN：每次 current/why（含显式 as_of）不缓存或重新授权检查；孤儿 active 版本原子 archived 并保留 history；linked message 批量 authority check 后才追加，普通 linked evidence 保留。
- 自动验收：Task6S/Task6L/context focused、Task2/3 lifecycle+ingestion、Task6 packaged lexical/Qdrant、compile、diff-check、acceptance sync、local handoff；仅 pytest 临时 roots。Task6 权威仍 `IN_PROGRESS / NOT_ACCEPTED`，Task6H heartbeat、crash、live/Artifact/owner acceptance 未执行。

## 2026-08-28 · Task 6M · Automatic-memory adapter transient lifecycle

- 基线：Task 6C Repair Round 1 blocker review `3fd8059da4ed10b8a1fcd0581793bd0fb2d177ee`；产品/测试提交 `1901628eee197e3d71d7e070c41c9e586d5468de`。
- 范围：仅修复 `src/extraction/pipeline.py` 解析 adapter dispatch 硬链接、`src/extraction/worker.py` stop/status receipt，以及新增 `src/extraction/transient.py`；复用现有 `extraction_jobs` 的 job/status/lease_token/locked_by/heartbeat_at，不新增数据库、队列、API、UI、检索或 Work Fact 事实源。
- 所有权：marker 为 `.automatic-memory-v1-{job_id}.{lease_token}{suffix}`，每段限 64 个安全字符，始终是 raw root 直接子 regular file；terminal 或已释放/过期/dead local worker lease 可清理，活跃同 lease 保留，unknown/malformed/foreign/mismatch/symlink/目录保留；未来版本保留。
- 可观测性：reconciliation 返回 machine-readable inventory，挂载到现有 pipeline process summary、worker status/stop outcome 与 runtime `cleanup_error/cleanup_pending`；unlink 失败计入 `errors` 且不计为 removed，下一次 start/worker reconciliation 可重试。
- RED/GREEN：新增 `tests/test_task6m_transient_lifecycle.py`，初始缺少 transient production boundary 时收集失败；实现后 Task6M `8 passed`，runtime receipt RED 为 stopped/期望 degraded 后 GREEN。覆盖 bounded job/lease identity、success/terminal/idempotent cleanup、active/expired lease、unknown/malformed/symlink/directory preservation、PermissionError visibility/retry、two-worker isolation、真实 pipeline adapter marker、真实 subprocess SIGKILL 后 restart pipeline cleanup、durable raw hash preservation 与 runtime error exposure。
- 回归：受影响 snapshot/resume/adapter/worker/runtime/scheduler matrix `150 passed, 3 warnings`；`.venv/bin/python -m compileall`、`git diff --check`、acceptance sync、local handoff 必须复跑。仅 pytest `tmp_path` synthetic roots；不启动 8766/8767，不访问 Artifact、Production/Vault、主人数据。
- 明确限制：Task 6 仍 `IN_PROGRESS / NOT_ACCEPTED`；本条仅关闭 Task 6C transient marker 产品缺口，不宣称 packaged/release/Artifact/owner acceptance 或 Task6 final validation。

## 2026-08-28 · Task 6M · Independent review disposition

- 审查报告：`.superpowers/sdd/2026-08-27-phase1-product-landing/task-6m-review.md`；审查
  HEAD `b65f81d659f787e349d545f51c4ddb94af770d4b`，产品/测试基线
  `1901628eee197e3d71d7e070c41c9e586d5468de`。结论为 `Spec Compliance FAIL /
  Task Quality NEEDS_FIXES`，Critical=0、Important=5、Minor=2。
- 关键阻塞：旧 `.automatic-memory-{uuid}.json` 已知残留只会被分类为
  `unknown_marker` 并永久保留；queued/retrying/terminal 分支未证明 lease
  ownership；queue/DB error 会在 pipeline startup 前逃逸，不能形成现有 runtime
  的 `cleanup_pending/cleanup_error` receipt；Task6C 修复后的 packaged 30/70
  crash/restart/stop 尚未 fresh 复验；runtime 字段虽由 API 返回但 Desktop 未消费具体
  cleanup 错误/残留。path-swap 与 failure cleanup 是 Minor 覆盖缺口。
- 已授权且最多一轮 `REPAIR_ROUND_1`：只允许同一 transient/现有 pipeline-worker-runtime
  边界内的 legacy 兼容策略、统一 lease/DB fail-closed receipt、必要的路径身份保护和
  packaged fresh gate；不得新增数据库/队列/API/UI/事实源，不得降低断言或由 harness
  直接 unlink。Task6 保持 `IN_PROGRESS / NOT_ACCEPTED`，不宣称
  `Task6M ACCEPTED_FOR_FINAL_VALIDATION`、release、Artifact、live 或 owner PASS。

## 2026-08-28 · Task 6M · Repair Round 1 — ownership proof and runtime visibility

- 审查基线：独立审查 `b65f81d659f787e349d545f51c4ddb94af770d4b`；产品/测试修复提交
  `4b51392fe448472e9099978ff2528f742dff887b`。本轮仅修复 I1/I2/I3/I5 与 M1/M2，
  不是 Task6C 第 2 轮；Task6 继续 `IN_PROGRESS / NOT_ACCEPTED`。
- RED：审查后行为矩阵 `8 passed, 4 failed`，失败为 legacy hardlink proof、v1 非同
  inode lease proof、queue RuntimeError 外逸、unlink 前 identity swap。GREEN：Task6M
  lifecycle/runtime `31 passed, 1 warning`；Desktop source smoke/build PASS；受影响
  snapshot/resume/queue/worker/runtime/Work Fact/adapter/structured/Task6A/6H/6S/Task8
  回归 `250 passed, 3 warnings`。
- 所有权与安全：legacy 仅 exact `.automatic-memory-{32hex}{suffix}` 且与同目录
  64hex、内容 hash=文件名 raw 证明同 dev/ino/size hardlink 才删；v1 terminal/
  released/expired/dead cleanup 需 queue job input_path、job id 与合法 raw hardlink
  proof；active/mismatch、unknown/future/malformed、copy、symlink、目录、DB/lease
  不可验证一律保留。unlink 前 lstat identity 变化保留。raw、授权源与 Vault sentinel
  不修改，重复 reconciliation 幂等，删除失败进入既有 machine-readable receipt 并可重试。
- 可见性：复用 `/api/automatic-memory/runtime` 的 `cleanup_pending/cleanup_error`；
  MemorySourcesPage 只显示“临时文件清理失败：灵机会自动重试，可重试。”，不显示路径、
  job id、lease/token；恢复后 notice 消失。未新增 API、DB、队列或事实源。
- I4 fresh packaged 30/70 crash/restart/stop 明确延期至全新 Task6V，本轮未伪造 packaged
  PASS；不启动 live 8766/8767，不运行 Artifact/release，不接触 Production/Vault/主人数据。
  报告：`.superpowers/sdd/2026-08-27-phase1-product-landing/task-6m-report.md`。

## 2026-08-28 · Task 6M · Repair Round 1 final independent review

- 审查报告：`.superpowers/sdd/2026-08-27-phase1-product-landing/task-6m-final-review.md`；docs
  HEAD `28f798557459b7cd7a1187d462969e43c871450a`，复核产品/测试
  `4b51392fe448472e9099978ff2528f742dff887b`。Fresh lifecycle/runtime `31 passed, 1 warning`，
  受影响回归 `250 passed, 3 warnings`，Desktop source smoke/build 与既有 rendered owner flow
  通过；acceptance sync、local handoff、diff-check 通过。
- 结论严格为 `FAIL / BLOCKED_AT_REPAIR_CAP`：Critical=0、Important=2、Minor=2。I2 仍发现
  terminal/queued/retrying marker 未验证 lease 即可删除 WRONG lease hard-link；I3 仍发现
  raw-root iteration 的非 OSError 会逃逸且 OSError 字符串未脱敏写入 receipt。I5/M1 与正常
  finally/SIGKILL inline 证据实现通过；cleanup-specific rendered proof 与完整双 worker/source
  sentinel 仅为 Minor evidence gaps。
- I4 packaged 30/70 明确属于后续 Task6V，不因未运行单独判本轮产品失败；Task 6M 保持
  `NOT_ACCEPTED`，Task6 保持 `IN_PROGRESS / NOT_ACCEPTED`，不再授权本轮修复，不得宣称
  release、Artifact、live、Production/Vault、owner 或 Phase 1 PASS。

## 2026-08-28 · Task 6L · Repair Round 1 final independent review

- 审查报告：`.superpowers/sdd/2026-08-27-phase1-product-landing/task-6l-final-review.md`；精确 HEAD
  `d328e58926e0466a912bde8c73fbaa5f64633cf5`，repair product/tests
  `2daac0733495798f3e576363a885c28e8c4ce392`，前审查记录
  `9edb9eab98b5abf58999b0e16d09ece729c2e45e`。
- 结论：`FAIL / BLOCKED_AT_REPAIR_CAP`，Critical=0、Important=1、Minor=0；Task6L
  `NOT_ACCEPTED`，Task6 `IN_PROGRESS / NOT_ACCEPTED`。字段名边界、private current-token
  seam、ownership predicate、worker lifecycle 和 Control/MCP 路由均复核通过，但
  terminal `complete/fail` 清除当前 token 后，普通 queue projection 的任意嵌套 result
  字符串与 `last_error` 仍可携带旧 plaintext lease token，I1 继续阻塞。
- Fresh evidence：required backend matrix `219 passed, 2 warnings`，Task6L focused `12 passed`；
  Desktop repair/source smoke、build、rendered flow、compileall、diff-check、acceptance sync、
  local handoff 全部 PASS。只使用临时 SQLite/fixture；未启动 live 8766/8767、Artifact、release、
Production/Vault 或主人数据。Task6M 历史结论不改写；本轮不再授权新的产品修复。

## 2026-08-28 · Task 6P · Repair Round 1 lifecycle callback projection

- 独立审查记录 `d61acdf39eefca8870b46b7a3172fe8ce20d5d6f` 对产品/tests
  `19525638ba3f33223fac005aa258f33dd2eb6091` 发现 I1：`process_next`、automatic
  `process_internal_next`/`process_job` 和 direct `execute` 的 lifecycle callback 仍能收到
  claimed job plaintext lease 或 nested explicit lease key。仅授权一轮有界 lifecycle repair，
  不改写 Task6L/M blocked 历史，不新增 schema/API/UI，LOCAL task 继续 IDLE。
- Repair 在唯一 `_notify_lifecycle` 边界对 job/result/error 使用现有 bounded scrubber，先收集
  explicit lease-key 值以覆盖 direct payload sibling strings，生成 callback 专用安全副本；
  scrub 失败时发送最小稳定 job envelope、`[REDACTED]`/generic error，不回滚已经完成的 queue
  terminal write。private claimed object 仍只供 worker lease 操作。
- RED 为普通 process success/failure callback 两项失败；新增 automatic/direct/custom-object
回归后 GREEN Task6P focused 为 `10 passed`；expanded matrix 排除两个既有 fixture failures 后
为 `354 passed, 2 deselected, 6 warnings`。Desktop source/repair/rendered/build、compile/
diff/sync/handoff 均通过；不执行 live/Artifact/release/
  Production/Vault/owner acceptance。Task6 仍 `IN_PROGRESS / NOT_ACCEPTED`。

## 2026-08-28 · Task 6R · Snapshot-owned terminal cleanup

- 本轮是有界 Crash Snapshot Terminal Cleanup，基线为 `adb42d6710d286be0b7b930aba3cab6e9f6be7e9`。
  仅修改现有 `src/automatic_memory/snapshot.py`、`checkpoint.py`、`runtime.py` 与 focused
  lifecycle tests；不修改 `.automatic-memory-v1` transient、检索/UI、queue schema 或永久 raw。
- `ConsistentSnapshot.reconcile_temporary_snapshots()` 取代一次性 startup-only 清理为明确、幂等、
  machine-readable seam；只扫描 raw root direct child 的 exact bounded `.snapshot-owned-*`/legacy
  `.snapshot-*` grammar，`lstat` regular/no-symlink，二次 identity 校验后 unlink。活跃/未过期 lease、
  running mismatch、unknown/malformed、symlink、目录保留；terminal/paused/stopped 可清理；raw
  content-addressed 对象不受影响。旧 `_cleanup_temporary_snapshots()` 保留兼容 wrapper。
- SnapshotJobRunner 在 lease 更新后、pause/release、failure/lease-loss、terminal/finally 以及
  completed retry 路径调用 reconcile；unlink/StateDB/root/stat 错误 fail closed，receipt 仅含稳定
  generic codes 并通过 scan `last_error`/runtime cleanup 状态可见、可重试。Runtime stop 复用相同 seam；
  cleanup failure 不把已完成扫描投影成干净 Work Fact。
- RED：新增恢复测试在旧实现真实复现 `completed` 但旧 snapshot-owned marker 残留；GREEN：Task6R
  focused `6 passed`，含真实子进程 SIGKILL/restart、active preserve、completed/paused/failed cleanup、
  retry、StateDB/root error sanitization。扩展 snapshot/resume/checkpoint/scheduler/runtime、Task6H/L/M/P/S
  回归 `179 passed, 2 warnings`；compileall、diff-check PASS。
- 所有测试仅使用 pytest 临时 roots、临时 SQLite/raw/source；未启动 live 8766/8767、Artifact/release、
  Production/Vault 或 owner 数据。Task6 仍 `IN_PROGRESS / NOT_ACCEPTED`，Task6V packaged 30/70 待重跑。
  报告：`.superpowers/sdd/2026-08-27-phase1-product-landing/task-6r-report.md`。

## 2026-08-28 · Task 7E · Runner error envelope and release-entry instrumentation

- 基线：Task 1 Repair Round 2 final review `956483b2655fca4a386f9a21bf1a3a46c09d2862`；
  当前产品树 `0047d75795d255b2c9a36217784751ec8fde8f4d`。本轮只关闭 I4/I7，
  不修改 retrieval/ranking、fixtures/evaluator、promotion、runtime、Desktop、
  4R2、100k、Artifact、Production/Vault 或主人数据。
- RED/GREEN：stage-hook adversarial matrix 覆盖 admission/root/sentinel/fixture/
  import/gateway/promotion/audit/scoring/evaluator/publication_pre，runner 异常均
  发布 fresh `QualityRunEnvelope`（report=None、三状态 NOT_EVALUATED、allowlisted
  reason、无路径 machine cleanup inventory）；旧 PASS 替换、publication failure
  与 cleanup/measured-failure 合同保持。相关测试 `28 passed`，Task4 readiness/
  validation guard `112 passed`。
- Release entry：`scripts/validate.ps1` 增加仅测试 opt-in 的
  `LINGJI_VALIDATE_TEST_HOOK`，按 preflight→scale-env→scale-command 记录顺序；
  当前 preflight 的 `BLOCKED_4R2_REQUIRED` 使后二者计数为零。新增 Python launcher
  仅探测并调用真实 PowerShell，不安装或用 Python 冒充执行。
- 本机只读搜索未找到 `pwsh`、`powershell` 或 `powershell.exe`（PATH、
  `/usr/local`、`/opt/homebrew`、`/Applications`、`/Library`、开发者目录均无匹配），
  故标记 `BLOCKED_POWERSHELL_RUNTIME_UNAVAILABLE`；未执行 release/100k/4R2/Artifact、
  live 8766/8767、Production/Vault 或 owner acceptance。`LOCAL_EXECUTION_TASK.md`
 保持 `IDLE`。详见 `.superpowers/sdd/2026-08-27-phase1-product-landing/task-7e-report.md`。

## 2026-08-28 · Task 7 · Measured quality and scale gate

- 本轮只修改既有 quality evidence/runner 与对应测试，不改变 retrieval、ranking、冻结题集、promotion、runtime、UI 或数据模型。
- 原始 100 问通过正式 `create_mcp_server` 注册路径逐题运行；导入 145/145、角色顺序 145/145、重复 0、自动激活 121/125、MCP 100/100。Qdrant 真实适配器故障注入记录 degraded，但探针题无 lexical 结果，故不计降级通过；单源损坏隔离真实注入并记录计数。
- 事实召回 0/106、引用准确率 0/106、ContextPack 压缩 55.28%（65990→29512），冻结门禁为 `FAIL_MEASURED_QUALITY`。按计划停止，100k、release、Artifact、live 服务、Production/Vault 和主人验收均未执行；Task8 不得开始。

## 2026-08-28 · Task 7 Measurement Repair · bounded measurement architecture

- 本轮只修复 measurement boundary：新增 `quality_degradation.py` 与
  `scale_benchmark.py`，不改变 retrieval/ranking/query/filter、冻结 evaluator/questions/
  thresholds、promotion policy、runtime/UI、向量 provider 或 MCP 工具语义。
- RED：新 measurement contract 首次收集失败 `ModuleNotFoundError: quality_degradation`。
  GREEN：measurement-focused 6 passed；Task4R reset/readiness/runner/scale/history 回归
  146 passed、1 warning；compileall/diff-check 通过。
- 生产/Vault 不可安全读取，故只记录 `production_pollution=null` 与
  `production_sentinel=NOT_MEASURED`；Acceptance protected boundary 单独记录，不映射为
  生产污染 0。清理库存采集文件/目录/字节/剩余数量，失败覆盖成功。
- 双授权临时来源实际执行损坏隔离：`attempted=2, completed=1, failed=1,
  continued=1, retrievable=1`。严格 MCP parity 只在完整 ordered identity、bounds、scope/
  lifecycle/mode 相等时计成功；本轮 `0/100`。选择前正式 baseline 无完整相关会话，保持
  `NOT_MEASURED`，不从 bounded ContextPack 反推。
- 修复后质量仍 `FAIL`（事实召回 0/106、引用 0/106、自动激活 121/125），100k、
  release、Artifact、live 8766/8767、Production/Vault 和主人验收均未执行。当前
  `MEASUREMENT_NOT_ACCEPTED`，等待全新独立审查，不得进入诊断或 Task8。

## 2026-08-28 · Task 7N1 · Scale admission and nullable baseline

- 产品/测试提交：`0ddb70b2451eb7224196bfefc4718ae8601aef7e`；报告：
  `.superpowers/sdd/2026-08-27-phase1-product-landing/task-7n1-report.md`。
- Scale loader 现在只接受与冻结 fixture hash、code commit 和正式 run identity
  完全一致的 envelope，并逐项核对 import、promotion provenance/links、Gateway、
  MCP、Qdrant lexical fallback、corruption terminal counts 和 context reduction；
  缺失/矛盾/伪造证据统一阻断 `BLOCKED_4R2_REQUIRED`。
- 未测量 Context baseline 在 runner 输出与 envelope round-trip 保持 `null`，不再使用
  0 表示未执行测量。聚焦回归 `128 passed, 1 warning`；未运行 100k、release、Artifact、
  live 服务、Production/Vault 或主人验收。Task 7 质量结果仍按真实测量保持未通过。

## 2026-08-28 · Task 7N2 · Corruption isolation retrieval evidence

- 本轮只收口 corruption isolation 的真实证据链：两个真实授权来源分别完成正式
  scan admission、durable queue、worker、Work Fact 和 structured read-model 路径；
  通过同一正式 `MemoryDatabase`/`HybridRetriever`/`MemoryGateway` 执行 lexical 与
  Gateway 检索。未修改 scale admission、promotion、baseline、检索算法、UI 或真实数据。
- 新测量发布精确 target source/scan/job 身份、队列终态计数、Work outcome/event 关联、
  适配器期望复合身份与 content hash、有效检索身份和坏源泄漏数。目标集合非恰好两个、
  任一非终态、Work Fact 缺失/错误/重复、read-model 坏源行、Gateway 空/错源/泄漏均为
  `failed`，reason 为稳定码，不包含正文、路径或异常文本。
- RED 为旧函数缺少 Gateway 参数且仅按 read-model 消息数报告可检索；GREEN 聚焦与
  Task7M/N1/quality runtime/Work/Gateway 直接回归 `125 passed`，compileall、diff-check
  通过。未运行 100 题 CLI、100k、release、Artifact、live 8766/8767、Production/Vault
  或主人验收。报告：`.superpowers/sdd/2026-08-27-phase1-product-landing/task-7n2-report.md`。
## 2026-08-28 · Task 7N3 · Promotion evidence and thin quality orchestration

- 本轮只拆出 `quality_promotion.py`、`quality_degradation.measure_semantic_degradation` 和
  `scale_benchmark.run_100k_benchmark` 的单一职责实现；`quality_gate.py` 保留冻结题集加载、
  正式组合、逐题调用和 envelope 编排。不修改 retrieval/ranking、向量算法、UI、运行时或真实数据。
- Promotion 测量必须逐条调用正式 `AutoMemoryPromotionService`，按冻结 Corpus 的显式字段记录
  category、expected/actual status、reason；从持久 read model 复算 active projection、message link、
  audit、missing/extra/duplicate，不以 runner 自己的 eligibility 判定或固定 0 代替。
- RED/GREEN：`tests/test_task7n3_promotion_thin.py` 覆盖 protected/assistant/conflict active、缺 link/audit、
  pending projection、重复/孤儿 evidence 的 fail-closed 合同；历史 end-to-end 两个直接调用方迁移到
  `evaluation_report=None`、`production_pollution=null` 和 raw measured counters，同时保留 opaque ID、
  SQLite 全值扫描、敏感信息与拒绝语义。 focused 命令：
  `./.venv/bin/pytest -q tests/test_task7n3_promotion_thin.py tests/test_task7n1_scale_admission.py tests/test_task7n2_corruption_retrieval.py tests/test_task7m_reset.py tests/test_task7_measurement_repair.py tests/evaluation/test_task4_reset_readiness.py tests/evaluation/test_task4r1_round5_final_red.py tests/evaluation/test_automatic_memory_end_to_end.py tests/performance/test_automatic_memory_100k.py --tb=short`。
- 质量 CLI 允许执行一次，仅用于确认当前测量仍诚实失败；禁止 100k、release、Artifact、live
  8766/8767、Production/Vault、真实主人数据。完成前需运行 compileall、diff-check、acceptance sync、
  local handoff，并写入 `.superpowers/sdd/2026-08-27-phase1-product-landing/task-7n3-report.md`。

## 2026-08-28 · Task 7O · Measurement contract closure (superseded by final review)

- 本轮实现曾试图关闭 Task7N 的 C1/C2/I1/M1：以 `CanonicalFunctionalEvidence` 作为 runner
  与 scale loader 共用的 typed artifact；真实 FAIL 输出被 loader 阻断。该实现声明已被下方
  最终独立审查 supersede，不能作为当前 acceptance 结论。
- 当前 automatic activation quarantine 的 low-risk expected/actual 均为
  `pending_owner_review`，accuracy 使用 `NOT_APPLICABLE`/`NOT_MEASURED` 与 null 计数；不
  恢复自动 approve，不改变 retrieval、ranking、向量、模型或产品策略。
- Promotion audit 从本次所有 imported message 的关系查询收集 links，并纳入
  owner-rejected 与 projection-error 等正式终态；pending/rejected/error 不得拥有 projection
  或 link，孤儿、缺失、额外、重复审计均阻断。旧 runner readiness 断言迁移到当前 MCP
  measured-failure 与 nullable baseline 合同；保留历史兼容导出 shim，不再保留第二套编排。
- 测试：Task7O contract closure、Task7N1/N2/N3、Task7M、Task7 measurement repair、Task4
  reset/readiness/runner 直接回归；质量 CLI 只运行一次，结果必须保留事实/引用/MCP FAIL、
  baseline NOT_MEASURED、activation NOT_APPLICABLE、production null。未运行 100k、release、
  Artifact、live 8766/8767、Production/Vault 或主人数据。报告路径：
  `.superpowers/sdd/2026-08-27-phase1-product-landing/task-7o-report.md`。

## 2026-08-28 · Task 7O · Final independent truth reconciliation

- 最终独立审查报告：`.superpowers/sdd/2026-08-27-phase1-product-landing/task-7o-final-review.md`，
  report commit `ce9807adb8aa9f4997819105ff3f1a949d93105b`。结论为
  `BLOCKED_AT_MEASUREMENT_CAP / NO_DIAGNOSTIC`，Critical=1、Important=3；C1/I1/I2/I3
  未关闭。具体为 loader duplicate evidence view/unknown 字段盲区、promotion orphan link
  过滤、缺失 memory identity 可 ready，以及 activation actual/reason/category 未验证。
- 当前 raw facts/citations/MCP 仍为 `0`，Context baseline 仍 `NOT_MEASURED`，但 measurement
  未接受；这些数字不得当作最终产品 retrieval 诊断。只允许一次有界 measurement-contract
  repair，修复前不得进入 retrieval diagnosis、100k、release 或 Task8。
- Tasks 2–6 的自动化/UI automated acceptance 不回退。未运行 100k、release、Artifact、Mac、
  owner、Production/Vault 或真实数据验收；`LOCAL_EXECUTION_TASK.md` 仍为 `IDLE`。
- 本条仅为现有权威文档事实对齐，不修改 `src/`、Desktop、tests 或 scripts；完成后必须
  运行 `./.venv/bin/python scripts/check_acceptance_sync.py`、
  `./.venv/bin/python scripts/check_local_execution_handoff.py`、diff-check，并远程复读提交。
