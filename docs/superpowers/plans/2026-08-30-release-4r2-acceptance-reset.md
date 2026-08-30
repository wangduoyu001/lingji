# Release / 4R2 Acceptance Reset Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在不增加产品功能、不替换现有记忆架构的前提下，修复发布验收工具与 4R2 质量证据合同，并用冻结的 100 问真实测量决定灵机能否进入 Mac 发布版验收。

**Architecture:** 保留现有 SQLite、Qdrant、`MemoryGateway`、正式 MCP、来源/时间线和 Desktop 主线。先让每次验证拥有独立证据目录，再让 runner 与 release loader 只接受一个严格、无歧义的 canonical artifact，最后用逐题、可恢复、可审计的离线 oracle 执行同一冻结题集。借鉴 Mem0 benchmark 的逐题结果/checkpoint/grouped metrics 和 LightRAG 的离线 recall@k/content-hash 模式，但使用 clean-room 小实现，不导入其后端或第二事实源。

**Tech Stack:** PowerShell 5.1/7、Python 3.12、pytest、现有 `src/automatic_memory` quality pipeline、现有 `MemoryGateway`、正式 FastMCP 注册路径、JSONL fixture、Markdown acceptance authority。

## Global Constraints

- 产品范围冻结：不新增 UI、数据源、数据库、队列、检索器、模型、云服务或产品能力。
- 不改变 retrieval/ranking/query/filter、promotion policy、冻结题目、答案、阈值、向量 provider 或 12,000 字符 ContextPack 产品上限，除非 Task 3 的真实测量已经证明某一现有实现违反既有合同；本计划本身不授权该产品修复。
- 根代理只维护计划、调度 Luna、审阅证据和最终验收；实现与修复全部由独立 `gpt-5.6-luna` 子代理完成。
- 每个代码任务必须严格 TDD：先提交或在报告中记录能复现缺陷的 RED，再写最小 GREEN；禁止删除、放宽、skip 或改写既有失败标准。
- 每个任务必须单独提交产品/tests，再提交 docs/evidence；每个任务后由全新 Luna 做 Spec Compliance 与 Task Quality 双结论审查。
- 不运行 100k、Artifact、安装、live 8766/8767、Production/Vault 或主人真实数据，直到本计划明确对应步骤授权。
- Task 1 不运行质量 CLI；Task 2 结束时质量 CLI 最多运行一次且必须诚实保留 FAIL/NOT_MEASURED；Task 3 不运行 100k 或 release。
- `LOCAL_EXECUTION_TASK.md` 在 release 成功和同 SHA Artifact 计划建立前保持 `IDLE`。
- 不复制 LoCoMo fixture 或 CC-BY-NC 代码；若实质复制 Apache-2.0/MIT 代码片段，必须在 `.research/ai-memory-acceptance-patterns/FINDINGS.md` 与仓库第三方声明中记录来源、版本、文件、修改和许可证。优先 clean-room 改写模式。
- 当前 Tasks 1–3 owner history/memory cards 的 PASS/APPROVED 不回退；本计划只关闭发布工具和质量证据阻塞。

---

### Task 1: Invocation-scoped release evidence

**Files:**
- Modify: `scripts/validate.ps1`
- Modify: `scripts/run_powershell_validation.py`
- Modify: `tests/test_00_task4_reset_validation_guard.py`
- Create: `tests/test_validation_invocation_isolation.py`
- Modify: `docs/ACCEPTANCE/CHANGE_ACCEPTANCE_LOG.md`
- Modify: `docs/MODULES/CODE_MAP.md`
- Report: `.superpowers/sdd/2026-08-30-release-4r2-acceptance-reset/task-1-report.md`

**Interfaces:**
- Consumes: existing `validate.ps1 -Mode focused|full|release`, `-TestReleaseEntryOnly`, `LINGJI_VALIDATE_TEST_ENTRY_ONLY`, `LINGJI_VALIDATE_TEST_HOOK`, and latest-summary behavior.
- Produces: one collision-resistant invocation ID and one invocation-owned output directory; nested validation may publish its own summary but may not delete or overwrite any live parent invocation directory.

- [ ] **Step 1: Write RED tests for parent/child evidence survival**

  Add tests that launch a temporary outer validation directory and a nested entry-only invocation in the same second and in different seconds. Assert both invocation directories, both logs, both `summary.json` files and the parent's final write survive. Assert the child cannot select the parent's invocation ID. The production change that makes these tests pass must be invocation-scoped naming/cleanup, not test sleeps.

- [ ] **Step 2: Write RED tests for bounded stale cleanup**

  Create `live-parent`, `live-child`, and an explicitly old completed run in a temporary validation root. Assert cleanup preserves both live directories and only deletes the completed stale run; symlinks, files outside the validation root and unresolved paths must remain untouched.

- [ ] **Step 3: Run RED and record the expected failure**

  Run:

  ```bash
  ./.venv/bin/pytest -q tests/test_validation_invocation_isolation.py tests/test_00_task4_reset_validation_guard.py --tb=short
  ```

  The new isolation cases must fail because current second-resolution directories and `Remove-StaleValidationRuns` delete sibling invocations. Record exact failed test names in the task report before modifying production code.

- [ ] **Step 4: Implement the minimum invocation ownership contract**

  Give every validation process a collision-resistant invocation ID, persist a bounded owner marker inside its directory, and make stale cleanup delete only directories proven completed and not active. The Python launcher may pass an explicit child identity/output hint, but must still invoke the real PowerShell script and must not reimplement validation logic. Preserve `latest-summary.json`/`.md` as convenience pointers; per-run `summary.json`/`.md` remain authoritative evidence.

- [ ] **Step 5: Prove release quarantine remains unchanged**

  On a real available PowerShell host, run the entry-only guard and assert exit is non-zero with `BLOCKED_4R2_REQUIRED`, hook events contain exactly `preflight`, and `scale-env`/`scale-command` counts are zero. Do not run full/release/quality/100k.

- [ ] **Step 6: Run GREEN and direct regressions**

  Run the focused tests above, `python scripts/check_acceptance_sync.py`, `python scripts/check_local_execution_handoff.py`, `python -m compileall -q scripts tests`, and `git diff --check`. Report exact commands, counts, PowerShell executable/version and output directories.

- [ ] **Step 7: Commit product/tests and evidence separately**

  Use `fix: isolate nested validation evidence` for product/tests and `docs: record validation isolation evidence` for docs/report. The worktree must be clean before review.

### Task 2: Strict canonical 4R2 measurement contract

**Files:**
- Modify: `src/automatic_memory/quality_evidence.py`
- Modify: `src/automatic_memory/quality_promotion.py`
- Modify: `src/automatic_memory/quality_gate.py` only where needed to emit the canonical contract
- Modify: `src/automatic_memory/scale_benchmark.py` only where needed to consume the canonical contract
- Modify: `tests/test_task7o_contract_closure.py`
- Create: `tests/test_task7o_contract_adversarial.py`
- Modify: `docs/ACCEPTANCE/CHANGE_ACCEPTANCE_LOG.md`
- Modify: `docs/MODULES/CODE_MAP.md`
- Report: `.superpowers/sdd/2026-08-30-release-4r2-acceptance-reset/task-2-report.md`

**Interfaces:**
- Consumes: `CanonicalFunctionalEvidence.from_mapping()/to_mapping()`, `readiness_from_envelope()`, `validate_promotion_measurement()`, `activation_measurement()`, the existing runner envelope and persisted source/message/promotion identities.
- Produces: exactly one canonical evidence view; unknown, duplicated, contradictory, orphaned or empty evidence fails closed with `BLOCKED_4R2_REQUIRED` and cannot become `scale_ready`.

- [ ] **Step 1: Write adversarial RED for the canonical loader**

  Starting from `CanonicalFunctionalEvidence.complete_for_test().to_mapping()`, mutate one case at a time: unknown top-level field; unknown nested field; top-level projection contradicting `evidence_details`; duplicate view with different counters/status; bool where integer is required; NaN/Infinity; missing fixture hash/run ID/code commit. Every case must be rejected, while an exact round-trip remains accepted.

- [ ] **Step 2: Write adversarial RED for promotion identity and links**

  Cover empty/whitespace `memory_id`, duplicate outcome identity, duplicate projection/audit/link, imported-message link to an outcome not present in projections, link for pending/rejected/error, orphan link outside the filtered candidate set, missing audit and extra audit. Each malformed case must fail; one complete, unique, active-link case and protected pending cases must pass.

- [ ] **Step 3: Write adversarial RED for activation truth**

  For every frozen category (`core/protected`, `high-risk`, `authority-conflict`, `assistant-only`, `low-risk-user`), assert the measurement compares expected status with actual persisted status and validates category plus required reason codes. A protected item reported `active`, a wrong category, missing reason, or an `error` disguised as pending must fail/not become ready. The current quarantine remains unchanged; this task must not auto-activate low-risk memory.

- [ ] **Step 4: Run RED and record exact failures**

  Run:

  ```bash
  ./.venv/bin/pytest -q tests/test_task7o_contract_closure.py tests/test_task7o_contract_adversarial.py --tb=short
  ```

  Record which C1/I1/I2/I3 case each failure reproduces before production edits.

- [ ] **Step 5: Implement one strict canonical contract**

  Parse the artifact once, reject unknown keys recursively in measured sections, remove or strictly compare any compatibility duplicate view, and pass the immutable canonical object to scale admission. Promotion collection must scan every imported message relationship before candidate filtering and validate non-empty unique identities. Activation measurement must use actual status/category/reason evidence, never runner eligibility assumptions or fixed zero counters.

- [ ] **Step 6: Run GREEN and the direct Task7 matrix**

  Run the two focused files plus `tests/test_task7n1_scale_admission.py`, `tests/test_task7n2_corruption_retrieval.py`, `tests/test_task7n3_promotion_thin.py`, `tests/test_task7_measurement_repair.py`, `tests/test_task7_quality_scale.py`, `tests/evaluation/test_task4_reset_readiness.py`, and `tests/evaluation/test_automatic_memory_end_to_end.py`. Also run compileall, diff-check, acceptance sync and local handoff.

- [ ] **Step 7: Run the quality CLI exactly once**

  Use isolated Acceptance roots and the unchanged frozen fixture. Publish the canonical artifact even if metrics are FAIL/NOT_MEASURED. Record fixture hashes, code commit, run ID, per-section readiness and cleanup inventory. Do not run 100k, release, Artifact, live services or owner data. A failed quality result is a successful Task 2 outcome if the evidence is complete and honest.

- [ ] **Step 8: Commit product/tests and evidence separately**

  Use `fix: close the 4r2 measurement contract` and `docs: record canonical 4r2 evidence`. The worktree must be clean before review.

### Task 3: Frozen 100-question diagnostic evidence

**Files:**
- Modify: `tests/evaluation/fixtures/automatic_memory_corpus.jsonl` only to add missing immutable evidence metadata without changing existing source facts
- Modify: `tests/evaluation/fixtures/automatic_memory_questions.jsonl` only to add missing expected/disallowed identities, answer atoms, mode and budget without making questions easier
- Create: `src/automatic_memory/quality_oracle.py`
- Modify: `src/automatic_memory/quality_gate.py`
- Modify: `scripts/automatic_memory_quality_gate.py`
- Create: `tests/test_task7p_frozen_oracle.py`
- Modify: `tests/evaluation/test_automatic_memory_end_to_end.py`
- Modify: `docs/TEST_REPORTS/PHASE1_TASK9_QUALITY_SCALE_GATE.md`
- Modify: `docs/ACCEPTANCE/CHANGE_ACCEPTANCE_LOG.md`
- Modify: `docs/MODULES/CODE_MAP.md`
- Report: `.superpowers/sdd/2026-08-30-release-4r2-acceptance-reset/task-3-report.md`

**Interfaces:**
- Consumes: accepted Task 2 canonical evidence, unchanged `MemoryGateway`, production `create_mcp_server`, existing hybrid/full-text/vector retrieval, existing `current|as_of|history|why` modes and 12,000-character ContextPack cap.
- Produces: one immutable per-question result stream and grouped deterministic metrics that distinguish import, retrieval, provenance, temporal filtering, MCP parity, fallback and context-budget failures. It does not tune retrieval.

- [ ] **Step 1: Audit and freeze fixture truth**

  Verify every corpus row has stable source/conversation/message identity, content hash, sequence, role, time and lifecycle. Verify every question has `question_id`, category, original query, expected answer atoms, expected and disallowed source/message identities or explicit negative expectation, mode (`current|as_of|history|why`), MCP expectation and character budget. Compute and publish corpus/question file hashes. Do not change wording or expected truth to match current output.

- [ ] **Step 2: Write RED for a deterministic offline oracle**

  Add tests proving the oracle: requires expected/disallowed evidence; compares complete ordered identity rather than text similarity alone; counts false-positive forbidden evidence; checks citations and time mode; rejects missing/extra/unknown result fields; enforces the 12,000-character cap; checkpoints one atomic JSON result per question; resumes without rerunning completed matching fixture/run identities; rejects stale/mismatched checkpoints.

- [ ] **Step 3: Write RED for Gateway/MCP parity and failure buckets**

  Using the production Gateway and formally registered MCP tool, assert each question records both result identities, used characters, current/history state and reason. A mismatch must be assigned to a concrete bucket (`import`, `retrieval`, `provenance`, `temporal`, `mcp`, `fallback`, `context`) and may not be swallowed as an ordinary empty answer.

- [ ] **Step 4: Run RED and record exact failures**

  Run:

  ```bash
  ./.venv/bin/pytest -q tests/test_task7p_frozen_oracle.py tests/evaluation/test_automatic_memory_end_to_end.py --tb=short
  ```

  Record the expected missing oracle/checkpoint/parity behavior before production edits.

- [ ] **Step 5: Implement the minimum oracle and runner integration**

  Use clean-room code modeled on Mem0's per-question result/checkpoint separation and LightRAG's offline oracle. Keep the runner a thin orchestrator. Do not add an LLM judge to the hard gate; RAGAS/DeepEval may be mentioned only as optional future diagnostics.

- [ ] **Step 6: Run focused GREEN, then one frozen quality run**

  Run the focused files and the direct Task7 matrix. Then run the quality CLI once on isolated Acceptance roots. Report totals and grouped results for exact fact, cross-document, source/citation, temporal, negative/boundary and corruption/fallback/context; include every failed question ID and bucket without private text. Do not modify retrieval after observing the run in this task.

- [ ] **Step 7: Apply the existing acceptance thresholds without reinterpretation**

  PASS requires fact recall at least 90%, citation accuracy at least 95%, real MCP parity at least 95%, false positives at most 5%, duplicate records 0, Production pollution 0 when actually measured, automatic Core writes 0, and every required degradation/corruption case measured. If any threshold or required measurement fails, status is `MEASURED_FAIL` with the exact bucket counts; do not run 100k or release.

- [ ] **Step 8: Commit product/tests and evidence separately**

  Use `test: add frozen automatic memory oracle` for code/tests/fixtures and `docs: record frozen memory quality results` for evidence. The final report must state either `READY_FOR_100K` or `MEASURED_FAIL`; it must never infer readiness from process exit or synthetic fixture success.

## Final decision after Task 3

- If Task 3 is `MEASURED_FAIL`, create a new bounded repair plan only for the measured failing buckets. Do not reopen Tasks 1–3 UI/history work and do not redesign the architecture.
- If Task 3 is `READY_FOR_100K`, run the existing isolated 100k gate next; only after 100k passes may root run one release validation, create an ACTIVE Mac task, build the exact-SHA arm64 Artifact, traverse every visible control, and leave the app open for owner confirmation.
- Mac owner acceptance remains the final product proof: the owner must be able to see real remembered events, their development/result/current validity, source, raw/structured/vector/permanent states, and safe correct/invalidate/archive actions without reading technical diagnostics.
