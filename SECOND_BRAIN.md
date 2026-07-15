# LingJi Second Brain Parallel Upgrade

This module runs beside the original LingJi service. It does not replace or alter the original `start_lingji.bat` chain.

## Data boundaries

- Automatic memory input: JSON AI-chat files under `data/inbox/ai_chat`.
- Codex writeback input: JSON task files under `data/inbox/codex_tasks`.
- Manual knowledge input: only the configured `SECOND_BRAIN_OBSIDIAN_DIR` Markdown tree.
- No drive-wide scanning is implemented.
- SQLite, embedded Qdrant, archives, logs, and PID files stay under this D-drive worktree.

## Start and stop

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\second_brain\start.ps1
powershell -ExecutionPolicy Bypass -File .\scripts\second_brain\health.ps1
powershell -ExecutionPolicy Bypass -File .\scripts\second_brain\stop.ps1
```

The API and watcher are independently switchable with `start-api.ps1`, `stop-api.ps1`, `start-watcher.ps1`, and `stop-watcher.ps1` in the same directory.

API: `http://127.0.0.1:8765`
OpenAPI: `http://127.0.0.1:8765/docs`

The API is needed for search and ingestion. The watcher is optional: keep it running for automatic folder ingestion, or stop it and call the API manually.

## Optional startup task

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\second_brain\register-autostart.ps1
powershell -ExecutionPolicy Bypass -File .\scripts\second_brain\unregister-autostart.ps1
```

Registration is not automatic. Run it only if you want the service to start when you log in.

## Rollback

1. Run `scripts\second_brain\stop.ps1`.
2. Continue using the untouched original project and its original `start_lingji.bat`.
3. Remove the optional scheduled task if it was registered.
4. Delete this worktree only after preserving any wanted second-brain data.

The pre-upgrade backup is under `D:\codex\backups\lingji-second-brain\20260715-225503`.
