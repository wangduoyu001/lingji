# Owner Work Fact Chain Verification

## Goal

Validate the single owner-visible fact chain:

```
SourceObject
  -> WorkItem
  -> ExecutionEvent
  -> Outcome
  -> NextAction
  -> PendingAction / MemoryRecord
```

## Completed

- Work fact model foundation exists.
- Control read adapter added.
- Work read API contract added.

## Remaining validation

- Wire LocalControlService to WorkService.
- Register work routes in API startup.
- Replace Desktop derived state with API projection.
- Add end-to-end fixture: capture -> work -> outcome.
- Verify empty states only show real facts.

## Acceptance rule

A UI state is valid only when it can be traced back to a real WorkItem or PendingAction.
