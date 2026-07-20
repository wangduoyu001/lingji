# CONFIGURATION.md — LingJi Configuration Reference

> Generated: 2026-07-20

## PEMIS v6 Configuration (src/config.py)

Configured via `.env` file and `Settings` class (pydantic-settings):

| Key | Default | Description |
|-----|---------|-------------|
| LLM_MODEL | qwen3:8b | Primary LLM model for PEMIS |
| FALLBACK_LLM | qwen3:8b | Fallback LLM model |
| EMBED_MODEL | nomic-embed-text | Embedding model |
| FALLBACK_EMBED_MODEL | nomic-embed-text | Fallback embedding model |
| OLLAMA_BASE_URL | http://127.0.0.1:11434 | Ollama server URL |
| VAULT_DIR | vault | Obsidian vault directory |
| STORAGE_DIR | storage | PEMIS working storage |
| SNAPSHOT_DIR | snapshot | Snapshot storage |
| BACKUP_DIR | D:/codex/backups/pemis | Backup destination |
| LOG_DIR | logs | Log directory |
| SAFETY_MODE | NORMAL | Operating mode |
| TOPK_NORMAL | 10 | Results in NORMAL mode |
| TOPK_DEGRADED | 6 | Results in DEGRADED mode |
| TOPK_SAFE | 3 | Results in SAFE mode |
| CACHE_MAX | 100 | Embedding cache size |
| DECISION_HISTORY_DAYS | 90 | Decision history window |
| WATCHDOG_ENABLED | True | File change watchdog |

## Second Brain Configuration (.env.second-brain)

| Key | Default in Example | Description |
|-----|-------------------|-------------|
| SECOND_BRAIN_HOST | 127.0.0.1 | API bind address |
| SECOND_BRAIN_PORT | 8765 | API port |
| SECOND_BRAIN_DB | data/second_brain.sqlite3 | SQLite database path |
| SECOND_BRAIN_RAW_DIR | data/raw/ai_chat | Raw chat archive |
| SECOND_BRAIN_AI_INBOX | data/inbox/ai_chat | AI chat input |
| SECOND_BRAIN_CODEX_INBOX | data/inbox/codex_tasks | Codex task input |
| SECOND_BRAIN_QDRANT_PATH | data/qdrant | Embedded Qdrant path |
| SECOND_BRAIN_QDRANT_COLLECTION | lingji_memories_v1 | Qdrant collection name |
| SECOND_BRAIN_OLLAMA_URL | http://127.0.0.1:11434 | Ollama server |
| SECOND_BRAIN_EMBED_MODEL | bge-m3 | Primary embed model |
| SECOND_BRAIN_FALLBACK_EMBED_MODEL | nomic-embed-text | Fallback embed model |
| SECOND_BRAIN_OBSIDIAN_DIR | (optional) | Obsidian knowledge directory |
| SECOND_BRAIN_POLL_SECONDS | 5 | Watcher poll interval |
| SECOND_BRAIN_LOG_DIR | logs/second_brain | Log directory |
| SECOND_BRAIN_RUNTIME_DIR | data/runtime | Watcher state storage |

## Obsidian CLI Environment Variables

| Key | Description |
|-----|-------------|
| OBSIDIAN_CLI_PATH | Path to Obsidian.com executable |
| OBSIDIAN_VAULT_PATH | Vault directory path |
| OBSIDIAN_VAULT_NAME | Vault display name |
| OBSIDIAN_CLI_TIMEOUT | Command timeout (default 15s) |
| OBSIDIAN_CLI_DRY_RUN | Set "1" to enable dry-run |

## DeepSeek API

Set `DEEPSEEK_API_KEY` in `.env` for PEMIS v6 LLM access.
