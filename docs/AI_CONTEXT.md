# AI_CONTEXT.md — Deprecated

> Deprecated: 2026-07-26  
> Reason: this file previously duplicated architecture, current status and mandatory reading rules, and had become stale.

Do not use this file as a current implementation or planning authority.

Current authorities:

- Repository execution entry: `AGENTS.md`
- Stable architecture and boundaries: `docs/ARCHITECTURE.md`
- Current stage, risks, blockers and next step: `docs/PROJECT_STATUS.md`
- Code entry points, ownership and focused tests: `docs/MODULES/CODE_MAP.md`
- Durable development and governance rules: `docs/DEVELOPMENT_RULES.md`
- Executed validation evidence: `docs/TEST_REPORTS/`

Default task context:

```text
AGENTS.md
-> relevant PROJECT_STATUS section
-> relevant CODE_MAP section
-> directly affected code and tests
```

Read architecture, governance rules and historical reports only when the task actually depends on those contracts.

Historical content remains available through Git history. Do not add new current-state content to this file.
