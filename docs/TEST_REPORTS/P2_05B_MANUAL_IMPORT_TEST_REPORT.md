# P2-05B Manual Import Test Report

> Branch: `work/p2-05b-manual-import-wiring`  
> Base: `224c83881e934ffb9fd7c07b016a52ac8711ae1f`  
> Status: `IMPLEMENTED_NOT_TESTED`

## Added focused coverage

- formal helper capture methods
- default queued/private semantics
- ChatGPT ZIP, JSON and directory classification
- explicit Codex mode and no generic JSON guessing
- HTML/TXT/Web input mapping
- existing media extension mapping
- PDF/DOCX/XLSX/PPTX/unknown binary stable rejection
- source/adapter conflict rejection
- metadata contract protection
- LOW_POWER media option enforcement
- disabled/deferred capabilities
- stable path-safe errors

Existing Adapter, StructuredSource, Markdown compatibility and Message Memory Link tests remain in the requested focused suite.

## Required commands

```bash
python -m compileall -q \
  src/capture \
  src/extraction/adapters \
  tests/test_manual_capture.py

python -m pytest \
  tests/test_manual_capture.py \
  tests/test_capture_models.py \
  tests/test_capture_policy.py \
  tests/test_capture_service.py \
  tests/test_capture_adapters.py \
  tests/test_structured_ingestion.py \
  -v --tb=short
```

## Execution result

```text
compileall: NOT EXECUTED
pytest: NOT EXECUTED
failed: UNKNOWN
```

The current execution container cannot resolve `github.com`, so the remote branch cannot be cloned into the Python runtime. No passing result is claimed without evidence.

## Safety

```text
Control API modified: NO
Desktop modified: NO
Queue modified: NO
New database: NO
Listener developed: NO
Production data accessed: NO
```
