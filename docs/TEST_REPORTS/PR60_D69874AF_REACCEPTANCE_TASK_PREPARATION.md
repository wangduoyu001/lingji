# PR60 d69874af Reacceptance Task Preparation

## Goal

Retire the obsolete PR #60 acceptance identity `1c514877 / 8723868744` and make the repository task mailbox point only to the remediated Windows revision:

```text
product commit: d69874afd8def42a40c4a5cc5e678a71921d44b5
artifact: lingji-windows-0.1.0-d69874af
artifact id: 8762312712
```

## Why a new task is required

The previous Day 0 report identified:

```text
D0-UX-001
scan, connection, import, review and vector status did not form one understandable flow

D0-CODEX-002
Codex could appear configured while the codex command was unavailable

BLOCKED_POST_CLEANUP
acceptance-only temporary directories remained after the report was pushed
```

The product branch now contains remediation for the two product defects and a new exact-head Windows Artifact. The old report remains historical evidence and must not be reused as the verdict for the new revision.

## Updated task contract

The active task must verify:

- one visible current primary action;
- detected history metadata produces an explicit owner-authorized next step;
- config-file presence, client-command availability and real MCP verification are separate states;
- missing `codex` command is blocked, never ready;
- only real Codex CLI/MCP verification produces ready;
- Embedding/Qdrant shows configured model, active model, missing models, recent error, current Qdrant mode/state and required next action;
- lexical retrieval remains truthfully available while semantic retrieval is unavailable;
- unsupported Codex raw Session/JSONL import is not presented as completed or automatic;
- Day 0, owner checkpoints, lifecycle, candidate approval/rejection and real-data gates remain mandatory.

## Cleanup remediation

Add a repository-owned cleanup helper that:

- only operates inside an explicit acceptance root;
- refuses drive roots, home roots, Production roots, Vault roots and symlinks;
- previews deletions by default;
- requires an explicit apply flag;
- deletes children before the root;
- reports remaining paths and returns failure when cleanup is incomplete.

The helper does not bypass operating-system policy. A denied deletion remains `BLOCKED_POST_CLEANUP` and must be reported honestly.

## Validation

Required exact-tree checks:

```text
python scripts/check_local_execution_handoff.py
python -m pytest -q tests/test_local_execution_handoff.py
python -m pytest -q tests/test_cleanup_local_execution.py
python scripts/check_acceptance_sync.py
```

Required GitHub workflows:

```text
local-execution-handoff
acceptance-doc-sync
tests
P0 Windows Gate
```

## Status

```text
TASK MAILBOX UPDATE: IN PROGRESS
RESULT RECEIPT RESET: IN PROGRESS
SAFE CLEANUP HELPER: IN PROGRESS
EXACT-HEAD CI: PENDING
```
