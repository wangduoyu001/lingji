# P2-05 Manual Capture Center — Integrated Implementation Report

> Status: `READY_FOR_FORMAL_MERGE`  
> Validated Integration Tree: `1bf95b8d16a9daea52b60518f0e920a0c0bd50db`  
> Date: 2026-07-21

## 1. Scope

P2-05 establishes the owner-controlled manual information entry center for LingJi.

Implemented:

- Manual text, web, supported file, media, ChatGPT Export, and Codex Report submission.
- Persistent Extraction Queue submission by default.
- Capture Mode persistence: `normal`, `low_power`, and `paused`.
- Capture job pagination, details, cancel, retry, pause, and resume.
- Sanitized Capture Job DTOs and stable error codes.
- Audit Events for submit, duplicate, pause, resume, cancel, and retry.
- Tauri Capture Center with the official Dialog Plugin and minimal permission.
- Memory Inspector navigation from completed capture jobs.

Explicitly excluded:

- Clipboard or global keyboard monitoring.
- Folder or filesystem watchers.
- Mobile share client.
- Browser extension.
- PDF, DOCX, XLSX, or PPTX parser.
- Forced termination of a running extraction job.

## 2. Integration Order

```text
P2-05B Manual Import Wiring
-> f01e3b2cc49065cda69f1c8909933dd0c530e4ff

P2-05A Capture Control API
-> 46a0c5276252734c121f0cad7a56cf3a4a7c4bdc

P2-05C Capture Center Desktop UI
-> fab0ba1b816c1228b8cfb3618aa04b5e2f2c4c3d

Final integrated cleanup and validation tree
-> 1bf95b8d16a9daea52b60518f0e920a0c0bd50db
```

## 3. Final Architecture

```text
Tauri Capture Center
-> authenticated Local Control API :8766
-> CaptureControlService
-> CaptureService
-> ExtractionPipeline.enqueue()
-> SQLiteExtractionQueue
-> existing Adapter Registry
-> Raw / Vault / Structured Read Model / Memory Index
```

Permanent modules:

```text
src/capture/manual.py
src/capture/service.py
src/control/capture.py
src/control/capture_api.py
src/control/api.py
src/extraction/queue.py
desktop/lingji-control/src/AppPages.tsx
desktop/lingji-control/src/pages/CaptureCenterPage.tsx
```

Temporary `src/control/_api_core.py` and `src/extraction/_queue_core.py` files were folded back into the formal modules and deleted.

## 4. Capture Methods

```text
manual_text
manual_web
manual_file
manual_media
manual_chatgpt_export
manual_codex_report
local_control_share  # compatibility alias only
```

Legacy mobile, browser, clipboard, and folder methods remain parse-compatible, but capabilities advertise them as disabled or deferred.

## 5. Supported Inputs

- Pasted text.
- URL, text, or HTML web capture.
- HTML, TXT, and Markdown web snapshots.
- Web Snapshot JSON.
- ChatGPT ZIP, JSON, or export directory.
- Explicit Codex Work Report JSON.
- Existing supported audio and video formats.

Unsupported Office documents and unknown binary input return `CAPTURE_UNSUPPORTED_TYPE`.

## 6. Queue and API

Queue operations:

```text
cancel(job_id)
retry(job_id)
list_page(status, source_type, q, limit, offset)
count(...)
```

Authenticated API routes:

```text
POST /api/capture/text
POST /api/capture/web
POST /api/capture/file
POST /api/capture/media
GET  /api/capture/status
GET  /api/capture/capabilities
GET  /api/capture/jobs
GET  /api/capture/jobs/{job_id}
POST /api/capture/jobs/{job_id}/retry
POST /api/capture/jobs/{job_id}/cancel
POST /api/capture/pause
POST /api/capture/resume
```

`POST /api/share` remains a compatibility alias and routes through the same Capture Control Service.

## 7. Desktop

The Capture Center provides:

- Six manual submission tabs.
- Capture status and queue counts.
- Backend pagination, status/source filters, and search.
- Cancel and retry controls only for valid job states.
- Completed-job navigation to Memory Inspector.
- AbortController and request-ID race protection.
- Official Tauri 2 Dialog Plugin with `dialog:default` only.
- Exact npm and Cargo lock files.

`AppPages.tsx` owns page routing so `App.tsx` remains below the modular size gate.

## 8. Privacy and Data Authority

- User-facing DTOs do not expose payloads, options, absolute paths, lease tokens, cookies, API keys, or raw exceptions.
- File names use basename only.
- Obsidian Vault + Git remain the permanent knowledge authority.
- SQLite, Structured Read Model, and Qdrant remain rebuildable derived data.
- No new database, queue, or Schema was introduced.

## 9. Rollback

Rollback the final P2-05 integration and the three P2-05 merge commits. No production data or database migration rollback is required because this phase did not alter Schema or production data.
