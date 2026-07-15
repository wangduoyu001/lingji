# Acceptance Criteria

- Re-importing identical chat content creates no duplicate conversation.
- A confirmed new rule can supersede an old rule while retaining version history.
- Qdrant can be deleted and rebuilt from active SQLite memories.
- Original LingJi startup files remain byte-identical to `master`.
- Stopping or crashing the second-brain service does not stop or modify the original service.
