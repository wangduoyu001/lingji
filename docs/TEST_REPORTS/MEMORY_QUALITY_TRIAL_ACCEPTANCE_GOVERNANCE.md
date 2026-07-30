# Memory Quality Trial Acceptance Governance

## Goal

Replace the separate PR #60 owner re-acceptance task with one governed execution flow:

```text
Day 0 safety gate
→ owner-authorized small real-data trial
→ incremental expansion
→ memory quality question set
→ owner sampling
→ remote report verification
→ local cleanup
```

## Added authority

```text
docs/ACCEPTANCE/MEMORY_QUALITY_TRIAL.md
```

The protocol defines:

- Day 0 safety and lifecycle gates before any real data;
- owner authorization before reading or importing real sources;
- Stage 1 minimum sample and Stage 2 controlled expansion;
- provenance, input hash, adapter version and idempotency checks;
- candidate-only memory boundary;
- screenplay and third-party content isolation from owner personal memory;
- factual, cross-document, source and negative-boundary questions;
- quality scoring and pass thresholds;
- five owner checkpoints;
- report, remote re-read and cleanup contracts.

## Updated active task

`LOCAL_EXECUTION_TASK.md` now uses:

```text
task_id: PR60-MEMORY-QUALITY-TRIAL-1C514877
execution_mode: DAY0_THEN_REAL_DATA_TRIAL
product_commit: 1c5148779624910f1c6072d95d6c6f6822f631e6
report_branch: acceptance/pr60-memory-quality-trial-1c514877
```

Day 0 must pass before real data. Codex may not infer authorization from repository access or previous conversations.

## Updated result receipt

`LOCAL_EXECUTION_RESULT.md` now records:

- Day 0, Stage 1 and Stage 2 results;
- real-data authorization;
- total quality questions and owner sample size;
- quality score, source accuracy and false-positive rate;
- real Codex MCP success rate;
- duplicate formal content and Production pollution counts;
- owner configuration preservation;
- existing remote verification and cleanup fields.

## Hard-gate thresholds

A PASS requires at least:

```text
Day 0: PASS
Stage 1: PASS
quality questions: 20
owner sampled questions: 10
quality score: 90%
source accuracy: 95%
false positive rate: no more than 5%
Codex MCP success: 95%
duplicate formal content: 0
Production pollution: 0
owner configuration preserved: PASS
```

## Automated validation

Updated:

```text
scripts/check_local_execution_handoff.py
tests/test_local_execution_handoff.py
```

The tests cover:

- valid pending task and receipt;
- valid completed PASS at exact thresholds;
- rejection of missing remote verification or cleanup;
- rejection of weakened quality thresholds;
- rejection of insufficient question and owner sample counts;
- rejection of source, false-positive and MCP threshold failures;
- rejection of duplicate formal content and Production pollution;
- rejection of Stage 1 before Day 0 PASS;
- valid FAIL report that stops after Day 0 without touching real data.

## Exact-head validation

Validated PR:

```text
PR #65
Head: 5990c10c84e74decadd2a05ece9ead4c31e5267f
```

Exact-head GitHub checks:

```text
local-execution-handoff #15: SUCCESS
acceptance-doc-sync #25: SUCCESS
tests #1106: SUCCESS
P0 Windows Gate #244: SUCCESS
```

Validated coverage includes:

- the current ACTIVE task and PENDING result receipt;
- memory-trial-specific threshold enforcement;
- Python 3.11 and 3.12 suites;
- Windows Python suite;
- Desktop Smoke and frontend build;
- MCP Smoke;
- Obsidian Plugin Smoke;
- Browser Capture Smoke;
- Windows PowerShell clean-install contracts;
- Rust/Tauri checks.

## Status

```text
DOCUMENTS: IMPLEMENTED AND VALIDATED
TASK: UPDATED AND VALIDATED
RESULT RECEIPT: UPDATED AND VALIDATED
HARD GATE: UPDATED AND VALIDATED
UNIT TESTS: PASS
EXACT-HEAD CI: PASS
PR #65: READY TO MERGE
```
