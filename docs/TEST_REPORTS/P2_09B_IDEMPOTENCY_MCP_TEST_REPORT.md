# P2-09B Idempotency and MCP Queue Test Report

## Environment

Development was performed through the writable GitHub connector on branch `work/p2-09b-idempotency-mcp`.

No local Python or SQLite runtime was attached to this conversation. Test execution status must be taken from GitHub Actions after the PR is opened.

## Tests added

### `tests/test_extraction_idempotency.py`

Covers:

- canonical mapping order;
- stable datetime normalization;
- adapter version sensitivity;
- identical file content at different paths;
- file content changes;
- sorted and content-sensitive directory manifests;
- missing input errors;
- queue compatibility entry point using the same key;
- duplicate job reuse and `existing_job` reporting.

### `tests/test_mcp_extraction_submission.py`

Covers:

- required Work Report identity fields;
- list-shaped commits/files/tests;
- rejection of nested sensitive fields;
- default queue-only submission;
- `process_now` enqueue-before-process behavior;
- absence of direct `execute()` calls;
- truthful queued Job DTO status.

## Existing queue behavior preserved in code

- unique idempotency key;
- terminal force requeue;
- lease token and ownership;
- heartbeat;
- stale lease release;
- retry backoff;
- completion/failure state;
- cancel/retry operations;
- paged list and count.

## Execution status

Status at document creation: `TESTS_ADDED_NOT_EXECUTED`.

GitHub Actions must run the repository Python suites after PR creation. Real-machine verification should also exercise concurrent duplicate enqueue, lease expiry, heartbeat and a worker processing Work Report/Web Capture jobs.

## Database impact

- Schema changed: no.
- New queue/database introduced: no.
- Historical jobs rewritten: no.
- CaptureDeduplicator changed: no.
- Memory lifecycle or Core Memory writes added: no.

## Compatibility note

New requests use canonical schema version 1. A historical request originally keyed through the old queue-only absolute-path algorithm may not share the same key as an equivalent new request. Existing stored rows remain valid and are not migrated.

## Final commit

Record the final PR head SHA after CI-driven fixes.
