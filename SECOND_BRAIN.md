# SECOND_BRAIN.md — Compatibility Notice

This file previously described the early parallel PySide6/8765 prototype. That flow is no longer the formal LingJi product path and must not be used as current startup guidance.

Current formal runtime:

```text
Tauri Desktop
-> Rust RuntimeManager
-> packaged Python Sidecar
-> authenticated 127.0.0.1:8766 Local Control API
-> shared Python Service Layer
```

Current authorities:

- Repository entry: `README.md`
- Development/AI entry: `AGENTS.md`
- Current state: `docs/PROJECT_STATUS.md`
- Architecture and migration boundary: `docs/ARCHITECTURE.md`
- Code ownership and validation: `docs/MODULES/CODE_MAP.md`

Compatibility rules:

- `second_brain/` may remain for migration, compatibility reads, export and acceptance evidence.
- Do not add new primary product features to it.
- Do not attach the formal 8766 Sidecar lifecycle to `start_lingji.py`, `start_lingji.bat` or the old 8765 chain.
- Do not write runtime data into `C:\Users\Administrator\Documents\New project-ai`.

Historical prototype instructions remain available in Git history.
