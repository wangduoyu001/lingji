# P2-05B Manual Import Wiring

> Branch: `work/p2-05b-manual-import-wiring`  
> Base: `224c83881e934ffb9fd7c07b016a52ac8711ae1f`  
> Implementation HEAD: `ac14617d391a322ae5786737ee11cd6aeb74df6b`  
> Status: `IMPLEMENTED_NOT_TESTED`

## Input classification

`src/capture/manual.py` provides `ManualCaptureKind`, `ManualCaptureClassification`, `classify_manual_input()` and `build_manual_envelope()`.

| Input | source_type | capture_method | existing adapter |
|---|---|---|---|
| pasted text | web | manual_text | web_capture |
| URL/raw HTML | web | manual_web | web_capture |
| HTML/TXT/MD/Web JSON file | web | manual_file | web_capture |
| ChatGPT ZIP/JSON/export directory | chatgpt_export | manual_chatgpt_export | chatgpt_export |
| explicit Codex JSON mode | codex_report | manual_codex_report | codex_work_report |
| supported audio/video | media | manual_media | media_local |

The existing `MediaExtractionAdapter` registry name is `media_local`; it was not renamed. No second Registry was introduced.

## Stable rejection

PDF, DOCX, XLSX, PPTX and unknown binary files return `CAPTURE_UNSUPPORTED_TYPE`. Generic JSON is treated as Web Snapshot JSON and is never guessed as Codex. Codex requires explicit mode selection.

## Helper semantics

`submit_text`, `submit_web`, `submit_file`, `submit_media`, `submit_chatgpt_export` and `submit_codex_report` default to `process_later=True` and `privacy=private`. `submit_file()` always records `manual_file`; specialized helpers record their dedicated methods.

## Adapter conflict protection

The classified `source_type` and `adapter_name` are passed to the existing `ExtractionPipeline`. A mismatch is rejected before enqueue/execute; the service never silently chooses another Adapter.

## Media policy

Requested OCR, transcription, keyframes and audio extraction are intersected with CapturePolicy. LOW_POWER cannot be bypassed by request booleans. Existing Pipeline runtime settings and Media Adapter provider, size and duration checks remain authoritative.

## Capabilities

Manual methods are enabled. Mobile share, browser extension, clipboard and folder watch are disabled/deferred. Keyboard and fullscreen capture listeners remain disabled.

## Privacy

User-visible file validation uses stable codes rather than absolute paths. Metadata recursively rejects secrets and cannot override source type, method, adapter, path, privacy, projects, tags or priority. Structured Message path redaction and Vault Markdown behavior are unchanged.

## Rollback

Revert commits `ac14617d391a322ae5786737ee11cd6aeb74df6b` and `e51b1972486cd82bc1ee9f087fdc8ce553c017c4`. No schema, queue, Control API or Desktop migration is required.
