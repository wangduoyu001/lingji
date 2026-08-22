# PROJECT_STATUS.md — LingJi 当前状态与开发指挥

> Updated: 2026-08-22
> Formal/default branch: `master`
> Active development branch: `feat/sb0-work-fact-contract`
> Active PR: `#106` / Draft / DO NOT MERGE
> Current product code SHA: `f23c20c6692d0390ae3c6930b5eba1882bbffb22`
> SB-1 verified repository head: `441d1d2ed50a38f4e6dfb7e9c7c3d28e4404e66a`
> SB-1 report commit: `26e2347cfd0a7ba7b1fcac3861ba3e2f8fce6e45`
> SB-2 acceptance contract commit: `8635c9fdefbcaf871eded0c7b7f2e0a5c7a70ecd`
> Product phase: `PHASE 1 — SECOND BRAIN COMPLETION`
> Last completed node: `SB-1 — CAPTURE → WORK → OUTCOME / AUTOMATED_PASS`
> Active node: `SB-2 — WORK → MEMORY / EVIDENCE / ACTIVE`
> Next node: `SB-3 — RETRIEVAL / VECTOR / MEMORY INSPECTOR VERIFICATION`
> Owner M5: `NOT ACTIVE`
> Opportunity Center: `FROZEN UNTIL PHASE 1 FINAL PASS`

Authority:

- architecture: `docs/ARCHITECTURE.md`
- code map: `docs/MODULES/CODE_MAP.md`
- acceptance root: `docs/ACCEPTANCE/README.md`
- SB-2 acceptance: `docs/ACCEPTANCE/SB2_WORK_MEMORY_EVIDENCE.md`
- incremental acceptance history: `docs/ACCEPTANCE/CHANGE_ACCEPTANCE_LOG.md`
- SB-1 automated report: `docs/TEST_REPORTS/SB1_CAPTURE_WORK_OUTCOME.md`
- future backlog: `docs/MODULES/FUTURE_DEVELOPMENT_TODO.md`

## 0. 跨对话开发接力协议

**本文件是唯一当前开发指挥文档。** 新窗口不要从聊天历史猜进度。

最小读取顺序：

```text
AGENTS.md
→ docs/PROJECT_STATUS.md
→ docs/MODULES/CODE_MAP.md 当前节点章节
→ docs/ACCEPTANCE/README.md
→ 当前节点专用 Acceptance contract / CHANGE_ACCEPTANCE_LOG 当前条目
→ 当前节点直接相关代码与测试
```

节点状态只允许：

```text
NOT_STARTED | ACTIVE | BLOCKED | AUTOMATED_PASS | OWNER_PASS | CLOSED
```

每完成一个可验证子节点立即更新本文件。产品代码变化必须记录精确产品 SHA；docs/test-only commit 不冒充产品 SHA。不得创建 `CURRENT_PLAN/NEXT_PLAN/FINAL_PLAN/handoff` 等平行指挥文档。

## 1. 当前接力快照

```text
Phase: PHASE 1 — SECOND BRAIN COMPLETION
Branch: feat/sb0-work-fact-contract
PR: #106 Draft / DO NOT MERGE
Product SHA: f23c20c6692d0390ae3c6930b5eba1882bbffb22
Completed: SB-0 AUTOMATED_PASS, SB-1 AUTOMATED_PASS
Active: SB-2 Work → Memory / Evidence
Next: SB-3 Retrieval / Vector / Inspector verification
Owner M5: NOT ACTIVE
Opportunity Center: FROZEN
```

当前动作：**SB-2 审计已形成精确缺口，下一步先登记 acceptance change，再做最小 canonical extension。不得重做 Memory 系统或 UI。**

## 2. 已完成节点

### 2.1 SB-0 — Work Fact Contract Repair

状态：`AUTOMATED_PASS`  
产品 SHA：`c02f73fde7fb4492a665b4c1fd3f93c900499d52`

已完成 canonical WorkItem/Event/Outcome/NextAction/PendingAction、WorkStore、8766 `/api/work/*`、Desktop Work contract 与跨平台自动门禁。

SB-0 详细证据继续以既有测试/报告和 Git 历史为准，不在本指挥文档重复展开。

### 2.2 SB-1 — Capture → Work → Outcome

状态：`AUTOMATED_PASS`  
最终产品代码 SHA：`f23c20c6692d0390ae3c6930b5eba1882bbffb22`  
验证仓库 Head：`441d1d2ed50a38f4e6dfb7e9c7c3d28e4404e66a`  
报告：`docs/TEST_REPORTS/SB1_CAPTURE_WORK_OUTCOME.md`

完成事实链：

```text
Capture/Cmd+K
-> stable capture_id
-> stable work_id
-> extraction job_id
-> accepted/queued/started/retrying/completed|failed|cancelled events
-> Outcome success|failure|skipped
-> NextAction actor
-> exact work_id Desktop navigation
```

关键真实性修复：

- duplicate/restart 复用同一 WorkItem；
- retry 清除旧 terminal Outcome；
- failure 不伪造 PendingAction；
- Capture/QuickCapture 有真实 `work_id` 才能宣称“灵机已接手”；
- 历史 Capture A 的“查看工作”固定读取 `/api/work/A`，不会被 `/api/work/current` 的 B 顶包；
- Cmd/Ctrl+K 与 Capture Center 共用正式 `/api/capture/text`，没有旁路 `/api/memory` 或 localStorage 事实源。

最终自动验收：

```text
Linux Python 3.11: 585 passed / 11 skipped / 0 failed
Linux Python 3.12: 585 passed / 11 skipped / 0 failed
Windows Python 3.12: 585 passed / 11 skipped / 0 failed
Desktop full smoke/build: PASS
MCP smoke: PASS
Browser Capture smoke: PASS
Obsidian plugin smoke: PASS
acceptance-doc-sync: PASS
local-execution-handoff: PASS
P0 Windows Gate: PASS
macOS Desktop Gate: PASS
Windows Desktop Release Baseline: PASS
```

SB-1 release evidence:

```text
macOS
artifact: lingji-macos-arm64
artifact_id: 9471250404
verified_head: 441d1d2ed50a38f4e6dfb7e9c7c3d28e4404e66a
sha256: 256577b01f934708b2109032b4b4ac1c269a9188f3958ad590c27d3e2b8f3fe3

Windows
artifact: lingji-windows-0.1.0-441d1d2e
artifact_id: 9471266207
verified_head: 441d1d2ed50a38f4e6dfb7e9c7c3d28e4404e66a
sha256: 5d375dad7e965f7a8929f24dc8bfa1a15165041166fd50614b66ef04038e7464
```

SB-1 只代表自动工程门禁完成，不代表主人 M5、Memory 质量或 Phase 1 已通过。

## 3. 当前节点：SB-2 — Work → Memory / Evidence

状态：`ACTIVE`

验收合同：

```text
docs/ACCEPTANCE/SB2_WORK_MEMORY_EVIDENCE.md
```

### 3.1 目标

当系统说 Capture/Work 完成时，主人必须能证明：

```text
WorkItem(work_id)
-> actual produced Memory(memory_id) OR explicit no-memory/failure
-> readable body/summary
-> correct source/citation/provenance
-> Memory detail
-> originating work_id
```

要求 **Work → Memory 和 Memory → Work 双向稳定 ID 追踪**，不能靠 UI 状态、文本相似度或临时内存猜关联。

### 3.2 SB-2 硬边界

- Obsidian Vault + Git 继续是永久记忆/正式知识正文权威；
- lingji_state.db 只保存 Work/runtime/audit，不变成第二永久记忆库；
- lingji_memory.db/Qdrant 仍为可重建派生层；
- 不绕过 candidate/owner-review/Core Memory 权限；
- 不自动 destructive rebuild Qdrant；
- Desktop 仍只通过认证 8766；
- 不建立第二套 Memory 页面、队列、API 或数据库。

### 3.3 审计完成：可复用基础

已经确认：

1. `VaultExtractionSink` 写入的 Markdown 正文是可读 Memory 内容，frontmatter 会保留非保留 metadata；永久正文权威仍在 Vault。
2. `PEMISIndex._parse_md_file()` 会把完整 Vault frontmatter 保留在 `entry.properties`，并单独抽取关系字段。
3. `MemoryDatabase` 是派生索引，会把指定关系投影到 `relationships_json`，Memory Inspector 已能从 chunks/citation renderer 返回可读内容。
4. `SourceReadModel` 已有 `message_memory_links`，支持 `memory_links(memory_id)` 反查 `message_id/conversation_id/source_id`；不需要新建 Source↔Memory 表。
5. `MemoryReviewService` 与 lifecycle 已保留 owner-confirmed review/Core 权限边界，SB-2 不需要重新设计审核系统。
6. `ExtractionRequest.options` 已携带 SB-1 的 `_lingji_work_id`，所以 Work origin 可以在提取执行时进入 canonical Memory metadata，无需 UI 猜测。

### 3.4 审计完成：真实缺口

#### Gap A — Structured sink 丢失实际 IDs

`StructuredReadModelSink.write_batch()` 当前只返回：

```text
state
sources/conversations/messages/links counts
warnings
```

虽然内部 `SourceReadModel.upsert_bundle()` 会生成真实 `source_id`，并建立 message→memory link，但这些实际 IDs 没返回给 extraction result。

结果：SB-1 `_result_evidence()` 预留了 ref 容器，却经常拿不到真正的 source/message/memory refs。

#### Gap B — Work evidence 只接受单值 string

`src/extraction/bootstrap.py::_result_evidence()` 只读取：

```text
memory_id
source_id
conversation_id
message_id
```

而且只接受单个字符串。多 documents、多 conversations、多 messages、多 memories 会静默丢失。

#### Gap C — Memory 没有 durable origin Work relationship

Capture 产生的 `ExtractedDocument.metadata` 当前没有稳定 Work relationship。Memory Inspector 因而无法从 Memory 反向找到 originating `work_id`。

不能用 UI state 或文本匹配补这个洞。

#### Gap D — 任意 frontmatter properties 不会直接进入 MemoryDatabase

`PEMISIndex` 虽保留完整 `properties`，但 `MemoryDatabase._upsert_document()` 只投影已知字段。单纯新增一个任意 `origin_work_id` frontmatter 会在派生数据库/Inspector 层消失。

因此最小 canonical 方案固定为：

```text
Vault frontmatter: work relation = source of truth
PEMISIndex RELATION_FIELDS: project the relation
MemoryDatabase relationships_json: rebuildable derived projection
Memory Inspector: derive origin_work_id/work_ids from relationships
```

不新增第二永久关系表，不把 SQLite 变成关系权威。

#### Gap E — no-memory 与 produced-memory 尚未显式区分

Extraction completed 目前总是生成 success Outcome，但 evidence 可能没有 memory refs。SB-2 必须让 evidence 明确记录：

```text
memory_state = produced | not_applicable | unavailable/failed
memory_ids = [...]
```

不能让“提取成功”和“永久记忆已产生”继续混成一句话。

### 3.5 第一批实现范围

在第一笔 SB-2 产品提交前，先登记 acceptance change。随后只做这些最小改动：

```text
1. Pipeline 将 _lingji_work_id 注入 ExtractedDocument 的 canonical `work` relationship metadata；
2. PEMISIndex 将 `work` 纳入 RELATION_FIELDS；
3. MemoryDatabase 将 `work` 纳入 relationships_json 派生投影，不新增 schema column；
4. StructuredReadModelSink 返回稳定 source_ids/conversation_ids/message_ids/memory_ids；
5. _result_evidence 保存数组 refs 和明确 memory_state，不静默截断；
6. Memory Inspector/detail 暴露由 relationships 派生的 origin_work_id/work_ids；
7. Work/Desktop 只使用这些 stable refs 做 exact Memory handoff；
8. 增加真实 Work↔Memory/restart/reindex/multiple/no-memory/failure/non-Work fixtures。
```

### 3.6 当前代码入口

```text
src/extraction/pipeline.py
src/extraction/models.py
src/extraction/structured_sink.py
src/extraction/bootstrap.py
src/extraction/sink.py
src/indexer/index.py
src/retrieval/memory_db.py
src/gateway/memory_inspector.py
src/sources/read_model.py
Desktop Work / Memory Inspector exact-ID handoff
相关 tests
```

注意代码地图里的旧 `src/gateway/memory.py` 路径已过时，真实 MemoryGateway 是：

```text
src/gateway/memory_gateway.py
```

Code Map 在本节点后续文档同步中修正。

### 3.7 SB-2 下一步

```text
A. update CHANGE_ACCEPTANCE_LOG for the audited change scope
B. implement canonical work relationship + multi-ref evidence
C. add real Work<->Memory lifecycle tests
D. add exact Work→Memory / Memory→Work Desktop smoke
E. focused gates
F. current-tree full/platform gates
G. SB-2 report + AUTOMATED_PASS
H. activate SB-3
```

SB-2 未 `AUTOMATED_PASS` 前，不开始 SB-3 功能实现。

## 4. Phase 1 节点总表

| Node | Scope | Status |
|---|---|---|
| SB-0 | Work Fact Contract Repair | `AUTOMATED_PASS` |
| SB-1 | Capture → Work → Outcome | `AUTOMATED_PASS` |
| SB-2 | Work → Memory / Evidence | `ACTIVE` |
| SB-3 | Retrieval / Vector / Inspector verification | `NOT_STARTED` |
| SB-4 | AI Memory Access / Context Pack / MCP | `NOT_STARTED` |
| SB-5 | Owner UI continuity | `NOT_STARTED` |
| SB-6 | Compatibility / Migration completion | `NOT_STARTED` |
| SB-7 | Automatic E2E Acceptance Gate | `NOT_STARTED` |
| SB-8 | Release + Owner Final Acceptance | `NOT_STARTED` |

## 5. Phase 1 最终 PASS 条件

以下全部满足才允许进入机会面板：

- Work Fact E2E；
- Capture → Work → Memory/Failure 可追踪；
- Memory 正文/来源可读可验证；
- lifecycle 无 owner-review/Core 越权；
- lexical/semantic/Qdrant/embedding 真值一致；
- Source/Conversation/Message provenance 成立；
- MemoryGateway/Context Pack/MCP 共享同一记忆与权限；
- Home/Work/Attention/Capture/Memory 不矛盾；
- compatibility runtime disabled 后正式能力仍成立；
- Production/Acceptance 无污染；
- required full/release gates PASS；
- final same-SHA Artifact 身份锁定；
- 当前本机验收任务完成；
- 主人最终 M5=`PASS`。

任一项 `FAIL / BLOCKED / NOT_TESTED`，Phase 1 不得完成。

## 6. Phase 2 启动门禁

只有 Phase 1 最终 PASS 后，本文件才允许切换：

```text
PHASE 2 — OPPORTUNITY CENTER
```

届时先审计并复用现有 `src/opp_generator.py`、`src/opportunities/` 和已经验收通过的 Source + Work Fact + Evidence 基础设施，再开发机会面板。

## 7. 稳定边界

- `src/` = 长期平台主线；
- `desktop/lingji-control/` = 唯一正式 Desktop UI；
- `second_brain/` = 兼容/迁移/验收来源，不新增主产品能力；
- 8766 = Desktop 唯一认证后端；
- Obsidian Vault + Git = 永久正文权威；
- Acceptance/Production 物理隔离；
- 不自动批准永久记忆；
- 不自动破坏性 rebuild Qdrant；
- 不为美化 UI 建第二事实源。

Opportunity Center、Opportunity Score、机会数据模型扩展、每日简报、LLM Router、AnySearch 新阶段继续冻结。