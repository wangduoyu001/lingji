# P2-09B Canonical Idempotency and MCP Queue Wiring

> 文档角色：历史实施/验证快照，不是当前进度或当前架构权威。
> 当前状态看 `docs/PROJECT_STATUS.md`；当前代码入口看 `docs/MODULES/CODE_MAP.md`。

## Goal

Provide one durable identity algorithm for extraction jobs and ensure MCP capture/report tools always create or reuse a SQLite queue job before work is executed.

## Original problems

The extraction pipeline hashed file content and directory manifests, while the queue fallback hashed the input path string. Identical business input could therefore receive different keys depending on which entry point created the job.

`submit_codex_work_report` and `capture_web_source` called `pipeline.execute()` directly. Those calls had no durable queued state, lease, heartbeat, retry record or job status lookup.

## Canonical identity

`src/extraction/idempotency.py` is the single implementation source. The canonical material contains:

- `schema_version`
- `source_type`
- adapter name and version
- normalized input identity
- normalized payload
- effective options

The final key is SHA-256 of canonical UTF-8 JSON with sorted keys and fixed separators.

## File identity

Files are identified by size and a streaming SHA-256 content hash. The absolute path is not part of the file content identity, so moving identical content does not create a different core identity. Missing and unreadable files raise errors instead of being treated as empty input.

## Directory identity

Directories use a sorted manifest of normalized relative paths, entry type, size and content hash. The manifest itself is hashed before inclusion in the durable identity. Symbolic links are not followed. Their target text is hashed so the manifest cannot leak the target path while still detecting a link change.

## Payload and options

Mappings are key-sorted, sets are sorted by canonical representation, lists preserve business order, and Path/Enum/date/datetime values have stable representations. Unsupported arbitrary objects fail explicitly; Python `repr()` and `hash()` are not durable identity inputs.

## Compatibility entry points

`ExtractionPipeline._idempotency_key()`, `_sha256_file()` and `_directory_manifest()` remain as compatibility wrappers and delegate to the canonical module.

`SQLiteExtractionQueue.build_idempotency_key()` keeps its previous public signature but also delegates to the canonical module. The duplicated queue algorithm has been removed.

Existing jobs retain their stored keys. New submissions use schema version 1 of the canonical algorithm; identical historical requests created by the old queue-only path may receive a different new key because the old path used absolute input paths.

## CaptureDeduplicator boundary

`CaptureDeduplicator` remains unchanged. It handles short-window submission de-duplication. Extraction idempotency is the persistent queue identity. Neither replaces the other, and no third identity store was introduced.

## MCP behavior

### Previous

MCP tool → `pipeline.execute()` → synchronous extraction with no durable job.

### Current

MCP tool → validation → `pipeline.enqueue()` → SQLite job → worker or `process_job()`.

The following tools now default to queue-only behavior:

- `submit_codex_work_report`
- `capture_web_source`

Both accept `process_now=False` and `force=False`. With `process_now=True`, the tool still enqueues first and then processes that job through the normal queue path.

## Job DTO

Responses preserve the existing job fields and explicitly include:

- `job_id`
- `status`
- `idempotency_key`
- `source_type`
- `adapter_name`
- `created_at`
- `existing_job`
- `retry_count`
- `message`

A queued job is never described as completed.

## Work Report validation

Work Reports require non-empty `task_id`, `execution_id`, `repository` and `branch`, plus list-shaped `commits`, `changed_files` and `tests`. Nested sensitive credential fields are rejected before persistence. Validation only establishes a durable review input; it does not approve memory, execute lifecycle writes or create Core Memory.

## Queue guarantees preserved

The existing SQLite table, unique key, force requeue semantics, retry backoff, lease token, heartbeat, stale lease release, completion/failure state and job lookup remain in place. No database schema or second queue was added.

## Changed files

- `src/extraction/idempotency.py`
- `src/extraction/pipeline.py`
- `src/extraction/queue.py`
- `src/mcp/extraction_submission.py`
- `src/mcp_server.py`
- `tests/test_extraction_idempotency.py`
- `tests/test_mcp_extraction_submission.py`

## Known limits

- Large directory identity calculation is intentionally proportional to the number and size of files.
- Existing historical keys are not rewritten.
- Real concurrent SQLite and worker behavior still requires CI or machine execution.

## Rollback

Revert the P2-09B commits. No database migration or destructive data operation is required. Existing persisted jobs remain readable because their schema did not change.
