# Task8E Safe Polling Fallback Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use test-driven-development and verification-before-completion.

**Goal:** Disable unreliable macOS `watchfiles` event admission in the formal runtime while preserving startup, scheduled reconciliation, daily integrity, manual scan, authorization, and revoke behavior.

**Architecture:** The scheduler receives an explicit event-watcher policy and defaults the packaged runtime to the safe periodic mode. Existing watcher behavior remains available only when explicitly injected/enabled for compatibility tests. Runtime/API expose the existing status surface with a truthful `periodic reconciliation` mode, and the existing source page renders that mode without adding a page.

**Tech Stack:** Python, pytest, FastAPI DTOs, React/TypeScript, existing CronScheduler and source registry.

## Global Constraints

- Do not use `watchfiles` event scans in the formal macOS runtime.
- Keep startup incremental scan, 15-minute reconciliation, daily integrity, immediate manual scan, authorization, and revoke.
- Do not add deletion invalidation, a read-model seam, a second queue/database, or ordinary Obsidian reads.
- UI must say periodic checking / latest within 15 minutes and never claim 30-second real-time takeover.
- Acceptance remains blocked for the 30-second event SLA and Phase 1 automatic takeover gate.

### Task 1: Red tests

Add backend and UI contract tests proving default fallback does not start an event watcher, scheduled reconciliation still runs, manual/revoke remain effective, and source copy reports periodic mode. Run them against `c70ce6b` and capture the expected failures.

### Task 2: Minimal fallback implementation

Add the explicit scheduler policy and runtime status fields. Keep cron jobs unchanged and only skip watcher startup/stop work in fallback mode; retain injected watcher compatibility for existing lifecycle tests.

### Task 3: UI wiring

Extend existing source types/API display with the mode and a concise periodic-check explanation, using current source page only.

### Task 4: Verification and report

Run focused backend and Desktop smoke/build, compile/diff/sync/handoff checks, write the required report with the 30-second SLA disposition, and create separate product/test and docs commits.
