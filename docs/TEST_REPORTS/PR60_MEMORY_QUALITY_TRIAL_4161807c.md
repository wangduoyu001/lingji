# PR60 Memory Quality Trial — 4161807c

## Verdict

**FAIL** — Day 0 did not meet the required autonomous-import and clear-guidance experience. Stage 1 and Stage 2 were not run; real-material body reads remained zero.

## Identity and isolation

- Product commit: `4161807ce4598cc1696093da4a703de101648280`
- Artifact: `8821878623` (`lingji-windows-0.1.0-4161807c`); ZIP, installer, portable executable, sidecar, manifest, and build metadata SHA-256 values matched the task sheet.
- Runtime binding: PASS. The installed Desktop and Local Control API consistently reported the task-scoped DataRoot, workspace `acceptance`, and binding-contract version `1`.
- Global desktop bootstrap: PASS. Existence and SHA-256 were unchanged before and after the trial; its contents were never opened.
- Production isolation: PASS. No production DataRoot, Vault, database, Qdrant store, AI-client configuration, or real-content body was read or modified.

## Day 0 results

| Area | Result | Evidence / outcome |
|---|---|---|
| Pre-cleanup and port isolation | PASS | Task root was absent before the run; 8766/8767 and LingJi processes were clear. |
| Contract install and startup | PASS | Fixed installer installed into the task root and launched with the required contract environment. |
| DataRoot identity | PASS | UI and `/api/runtime/ping` agreed on the task-scoped root and `acceptance`. |
| Metadata-only AI scan | PASS | Scan returned installation/configuration metadata only; no real conversation, Vault, script, or JSONL body was read. |
| Model and hardware refresh | PASS | Seven local models and the NVIDIA GPU were detected through the runtime. No model was downloaded. |
| Real MCP protocol | PARTIAL / FAIL | A real authenticated Streamable HTTP MCP handshake and tool calls reached the task runtime and returned synthetic acceptance data. The installed Codex CLI could not be run from this environment (`Access is denied`), so a new real Codex client session was not proven. |
| Embedding and Qdrant presentation | FAIL | Control API reported the embedded Qdrant directory locked and semantic retrieval unavailable; after reboot MCP health instead reported ready with zero vectors. These incompatible states do not clearly explain cause, impact, or recovery. |
| Synthetic candidate lifecycle | PASS | Two synthetic candidates were created through MCP. Owner-approved A moved to task-scoped Core Memory; owner-rejected B moved to the task-scoped rejected-candidate archive; no candidate remained pending. |
| Core/Sidecar recovery | PARTIAL / FAIL | Restart cycles 2 and 3 recovered with the correct binding in five seconds. Cycle 1 did not recover within the initial 45-second observation window, then later recovered. |
| Desktop and Windows restart | PASS | Desktop reopened with the same task contract. After owner-authorized Windows restart, the Desktop window was normal with no black screen; binding and candidate state recovered. |
| Autonomous import UX | FAIL | Owner reported that the UI was not understandable and did not provide the expected automatic import or a clear single-step guide for sources that cannot be imported automatically. This violates the Day 0 requirement that the owner must not be made to locate paths or drive routine import steps. |

## Owner observations and decisions

- Window after reboot: normal; no black screen.
- Synthetic candidate decision: A approved, B rejected.
- Windows reboot: explicitly authorized and completed.
- Product feedback: imports should run automatically where possible. When a source requires an official export or another owner action, the UI must provide one clear guided action rather than requiring path-by-path discovery.

## Real-data gate

The owner later gave broad permission to import real material. It was intentionally not used: Stage 1 requires a PASS Day 0 and a named, minimized data scope. Day 0 is FAIL, so real-material body reads are **0** and no real data was imported.

## Required follow-up

1. Replace path-driven import setup with automatic discovery/import where supported and a concise one-step export/import guide otherwise.
2. Make the Codex configuration-directory, command, and real-call states consistent and testable with an isolated Codex client session.
3. Resolve or accurately represent embedded-Qdrant ownership, vector availability, search impact, and recovery progress.
4. Ensure the first Core/Sidecar recovery meets its bounded recovery contract.

## Scope and privacy

This report contains no tokens, real-content excerpts, private database contents, full real source paths, or screenshots. The task-specific temporary root is cleaned only after the first remote report verification.
