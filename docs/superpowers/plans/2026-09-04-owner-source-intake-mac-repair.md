# Mac 来源接管可解释闭环实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

日期：2026-09-04

## 目标与边界

修复 Desktop“来源”页从只读发现、主人授权、扫描、处理到真实导入结果的可解释闭环。复用现有
`SourceRegistry`、`ScanRun`、extraction queue 与 Work Fact，禁止建立第二套数据库、队列、状态中心或端口。
只用合成 fixture，不读取主人真实 AI 软件数据；不启动、停止或写入目标软件，不读取 secrets。模型清单、
模型运行/兼容状态、灵机自检、系统健康和记忆健康链路不得改变。Mac 新候选通过并由主人确认前冻结 Windows。

## 全局约束与模型分工

- GPT-5.6 仅允许规划审查、增量验收设计和最终证据审查；不得编写或修复产品代码、测试和脚本。
- 产品代码与测试实现必须交给明确指定的非 GPT-5.6 低用量子代理；每项报告记录模型、允许文件和测试证据。
- 当前主代理只做协调、计划/验收文档同步、子代理审查包与最终 Mac 验收，不代替开发子代理补代码。
- 只用合成 fixture；不得读取主人真实 Codex、Claude、Cursor、ChatGPT 导出、数据库、配置或凭证。
- 扫描只做有界只读枚举：不启动/停止/注入目标软件，不写目标目录或配置，不发模型请求，不读取 `.env`、credentials、auth、token、cookie、secret、`.db`、`.sqlite`、`.sqlite3`，不跟随符号链接，不越过授权根。
- 复用现有 `StateDatabase`、`automatic_memory_scan_items`、extraction queue、Structured Read Model 和 Memory Inspector；不新增数据库、队列、状态中心、端口或第二套详情页。
- API 只返回白名单详情字段，不返回绝对路径、raw path、数据库路径、内部 job/lease ID、Token/Cookie、堆栈或原始任意 JSON。
- Mac 技术验收和主人体验确认是两个独立门；两者完成前禁止 Windows、push、PR、merge 和最终清理。

## 逐条详情契约

扫描详情必须提供有界分页（默认 20、最大 100）和稳定顺序。每条只允许：稳定公开条目标识、授权根内相对名称、来源显示名、阶段、结果、主人安全原因、更新时间、是否可重试，以及真实结构化导入数量（sources/conversations/messages）。

状态优先级固定为：待确认 → 已授权 → 扫描中 → 扫描完成等待处理 → 处理中 → 导入完成 / 部分失败 / 空目录 / 未识别支持格式 / 失败 / 取消 / 撤销。只有 extraction terminal facts 可判定导入完成；queued 和 reused 永远不能显示为已导入。

来源页除逐条文件结果外，必须有直接可见的“查看已导入具体内容”入口，复用 Memory Inspector 展示对话标题、消息预览和主人主动点开的正文；不得只给数量或只给技术 JSON。

## Task 0：冻结契约与 RED 证据（GPT-5.6 仅规划）

- [x] 5.6 审查计划并确认聚合 DTO、队列覆盖范围、隐私与保护链路缺口。
- [x] 把逐条白名单 DTO、分页、状态机、内容查看入口、模型分工和 Windows 冻结条件同步到验收日志。
- [x] 保留已有“扫描不等于导入”真实 RED/GREEN 证据；为逐条详情与内容入口新增真实 RED 后才允许生产实现。

## Task 1：处理阶段与逐条安全 DTO（非 5.6 低用量子代理，TDD）

**Files:**

- Modify: `src/control/automatic_memory_api.py`
- Modify only if exact per-scan queue querying is required: `src/extraction/queue.py`
- Preserve and finish the existing in-task patch: `src/automatic_memory/runtime.py`
- Test: `tests/test_automatic_memory_control_api.py`
- Test only if queue query changes: `tests/test_extraction_queue.py`

**Interfaces:**

- `GET /api/automatic-memory/scans/{scan_id}` keeps every existing field and accepts `limit` (default 20, range 1..100) plus `offset` (default 0, minimum 0).
- Detail adds `items: ScanItem[]` and `items_pagination: {limit, offset, total, has_more}`. List/summary/action routes do not carry `items`.
- `ScanItem` is a white-list DTO with exactly these owner fields: `item_id`, `name`, `source`, `stage`, `result`, `reason`, `updated_at`, `retryable`, `imported_sources`, `imported_conversations`, `imported_messages`.
- `item_id` is an opaque deterministic digest and is not a queue job id. `name` is a validated authorization-root-relative POSIX name; unsafe/absolute/traversal/sensitive-looking values fail closed to `无法安全显示名称`.
- `stage` is one of `snapshot`, `queued`, `extracting`, `completed`; `result` is one of `recorded`, `waiting`, `processing`, `imported`, `reused`, `failed`, `cancelled`.
- `reason` comes only from a closed Chinese mapping for the stage/result. It must never include raw `last_error`, paths, JSON, stack traces or credentials.
- Per-item import counts come only from numeric `result.structured_read_model.sources/conversations/messages`; absent evidence is `null`, never inferred from queued/reused.
- Merge `automatic_memory_scan_items` with exact per-scan extraction jobs by `relative_path`; include manifest-only and queue-only rows once, sorted by `name`, then paginate.
- Exact per-scan job querying may add queue methods but must not add tables, columns, indexes, persistence or expose queue payloads.

1. Python API 测试先覆盖 scan completed 但 extraction running、全部 completed、部分 failed/cancelled、空目录和未识别支持格式。
2. 逐条详情测试先覆盖 manifest + queue 对齐、稳定排序、默认/最大分页、越界参数、安全字段白名单、部分失败和旧记录兼容，并确认旧实现 RED。
3. 从现有 scan manifest 和 extraction queue 投影逐条阶段/结果；缺少扫描事实时只做现有事实层的最小增量，不从前端猜测、不新增持久状态源。
4. 错误原因使用封闭分类映射；相对名称必须验证不绝对、不穿越、不含凭证形态。
5. 回归 scan list/summary/detail/action 字段一致性，修复当前先全队列 limit=200 再按 scan 过滤导致的静默漏项。

## Task 2：Desktop 状态、逐条详情与内容入口（非 5.6 低用量子代理，TDD）

1. Rendered E2E fixture 先覆盖排队不等于导入、扫描完成显示处理中、真实完成计数、空目录、无支持格式、
   部分失败、目录选择取消、单来源 busy 隔离、详情直达、安全错误原因、分页和“查看已导入具体内容”，并确认旧 UI RED。
2. 运行并确认旧 UI RED。
3. 扩展 TypeScript DTO 和来源状态投影；移除“扫描完成=已接管”“queued+reused=已导入”的错误语义。
4. 目录取消、授权中、扫描中、处理中和终态都有 aria-live 可见反馈；详情按钮移出“备用操作”。取消不得调用 authorize、不得留下 busy，且可立即重试。
5. busy 只锁定当前来源/动作，不锁死无关来源。
6. 普通详情列表逐条显示相对名称、来源、阶段、结果、真实导入对话/消息数和安全原因；技术 JSON 不作为主人详情。
7. “查看已导入具体内容”复用现有 Memory Inspector 与其完整正文读取，不新建内容数据库或第二套检查器。

## Task 3：安全和状态保护回归（非 5.6 低用量子代理）

1. 用完整合成 API fixture 深比较来源操作前后 `/api/health`、`/api/models/registry`、`/api/models`、`/api/brain/status`、`/api/overview` 和记忆健康 DTO；字段集合不得减少，模型运行/兼容状态与灵机自检值不得改变。
2. 覆盖授权根、子目录符号链接、敏感目录/文件、内部数据库、根目录拒绝与只读枚举；spy 证明无进程启动/停止/注入、目标配置写入和模型请求。
3. 运行 focused Python、Desktop 来源测试、owner E2E、smoke、build、compileall、diff-check、acceptance sync 与 handoff。

## Task 4：全新 Mac 候选验收

1. 固定新产品 SHA，创建全新隔离 Acceptance root；旧候选和当前运行实例在替换前保持不动。
2. 重跑 clean-root packaged 双轮，构建 arm64 sidecar/App/DMG，校验签名和 SHA256，whole-bundle 覆盖安装。
3. 仅用合成官方导出 fixture 遍历真实发布版来源全链路、每个可见控件及失败/空目录/部分失败场景。
4. 对比来源操作前后模型、自检和健康显示；确认 8766 仅 loopback、8765/8767 关闭且数据污染为 0。
5. 技术验收通过后保持 App/sidecar 打开等待主人确认。确认前不 push、不建 PR、不 merge、不清理、不做 Windows。

## 完成判据

- 每个已有安全扫描事实可逐条查看，成功项和失败项可区分；只显示数量判失败。
- 每条显示相对名称、来源、阶段、结果、安全原因、更新时间、可重试性和真实结构化导入数量。
- 主人可从来源页直接进入已导入对话/消息并主动打开正文；无内容时明确提示原因与下一步。
- 取消、空目录、无支持格式、扫描中、处理中、成功、部分失败、失败均有可见人话提示。
- 模型清单、模型运行/兼容状态、灵机自检、系统健康和记忆健康在来源操作前后保持完整。
- 5.6 最终只审读实现和 Mac 验收证据；发现问题只能退回非 5.6 开发代理修复。
