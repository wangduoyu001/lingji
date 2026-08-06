# PR60 Assistant Hub Guided Flow Defects

## Source

Owner Day 0 feedback on product commit `1c5148779624910f1c6072d95d6c6f6822f631e6`.

## Confirmed defects

1. The scan detects local AI software and metadata, but the page does not convert the result into one explicit next action.
2. The import section requires manual file selection without first explaining what was discovered, what can be imported, what will be read, and what remains unsupported.
3. Codex can simultaneously appear configured while a live test reports that the `codex` command is missing.
4. The connector test treats missing Codex CLI verification too weakly and does not persist a clear blocking state.
5. Embedding and Qdrant are shown as unavailable or inactive without a concise root cause and a direct repair action on the same page.
6. Scan, connection, import, review, and vector readiness are displayed as separate cards instead of one ordered setup state machine.

## Required product behavior

```text
scan
→ explain exactly what was found
→ classify each source as importable / export-required / unsupported
→ ask for owner confirmation before reading content
→ show one primary next action
→ expose blockers with reason and repair action
→ never show configured as equivalent to usable
```

## Safety boundary

- Discovery remains metadata-only.
- No real content is read before owner confirmation.
- No arbitrary directory scan is added.
- No automatic permanent-memory write is added.
- Unsupported raw histories are described honestly rather than silently imported.

## Status

```text
D0-UX-001: CONFIRMED
D0-CODEX-002: CONFIRMED
PRODUCT FIX: REQUIRED
OLD ARTIFACT: DO NOT RETEST
```
