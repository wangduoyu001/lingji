# Acceptance Criteria

- Re-importing identical chat content creates no duplicate conversation.
- A confirmed new rule can supersede an old rule while retaining version history.
- Qdrant can be deleted and rebuilt from active SQLite memories.
- Original LingJi startup files remain byte-identical to `master`.
- Stopping or crashing the second-brain service does not stop or modify the original service.
## Desktop acceptance

- Desktop shortcut targets the project-local pythonw.exe and opens a native window.
- Acceptance run reports 22 passed and 0 failed without changing production counts.
- Qt offscreen navigation tests pass and long operations use QRunnable/QThreadPool.
- Closing the UI leaves the API running unless the explicit checkbox is enabled.
