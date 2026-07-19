from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    llm_model: str = "qwen3:8b"
    fallback_llm: str = "qwen3:8b"
    embed_model: str = "nomic-embed-text"
    fallback_embed_model: str = "nomic-embed-text"
    ollama_base_url: str = "http://127.0.0.1:11434"
    vault_dir: str = "vault"
    storage_dir: str = "storage"
    snapshot_dir: str = "snapshot"
    backup_dir: str = "D:/codex/backups/pemis"
    log_dir: str = "logs"
    safety_mode: str = "NORMAL"
    topk_normal: int = 10
    topk_degraded: int = 6
    topk_safe: int = 3
    cache_max: int = 100
    decision_history_days: int = 90
    watchdog_enabled: bool = True

    # Single Obsidian Vault foundation
    vault_auto_init: bool = True
    vault_layout_version: str = "1"
    index_private: bool = False
    obsidian_interaction_auto_init: bool = True

    # Persistent runtime state
    state_db_name: str = "lingji_state.db"
    scheduler_poll_seconds: float = 60.0
    scheduler_workers: int = 2
    manual_command_interval_minutes: int = 2
    extraction_request_interval_minutes: int = 1

    # Unified extraction framework and SQLite queue
    extraction_worker_enabled: bool = True
    extraction_poll_seconds: float = 5.0
    extraction_batch_size: int = 5
    extraction_max_attempts: int = 3
    extraction_lease_heartbeat_seconds: float = 30.0
    extraction_stale_after_seconds: int = 1800

    # Safe web and social capture
    web_network_fetch_enabled: bool = False
    web_network_timeout_seconds: float = 15.0
    web_max_response_bytes: int = 8 * 1024 * 1024

    # Skill registry. Comma-separated roots are optional and never copied into the Vault.
    skill_auto_sync_roots: str = ""

    # Rebuildable permanent-memory retrieval index
    memory_db_name: str = "lingji_memory.db"
    memory_chunk_max_chars: int = 1400
    memory_chunk_overlap_chars: int = 180
    memory_search_cache_size: int = 256
    memory_search_cache_ttl_seconds: float = 120.0
    memory_default_context_chars: int = 12000
    memory_index_check_hours: float = 6.0

    # MCP server; localhost is the safe default
    mcp_server_name: str = "LingJi Memory Gateway"
    mcp_host: str = "127.0.0.1"
    mcp_port: int = 8765
    mcp_transport: str = "stdio"
    mcp_default_agent_id: str = "lingji-local"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "allow"

    @property
    def vault_path(self) -> Path:
        return Path(self.vault_dir).expanduser()

    @property
    def storage_path(self) -> Path:
        return Path(self.storage_dir).expanduser()

    @property
    def snapshot_path(self) -> Path:
        return Path(self.snapshot_dir).expanduser()

    @property
    def backup_path(self) -> Path:
        return Path(self.backup_dir).expanduser()

    @property
    def log_path(self) -> Path:
        return Path(self.log_dir).expanduser()

    @property
    def state_db_path(self) -> Path:
        return self.storage_path / self.state_db_name

    @property
    def memory_db_path(self) -> Path:
        return self.storage_path / self.memory_db_name

    @property
    def skill_sync_paths(self) -> list[Path]:
        return [
            Path(value.strip()).expanduser()
            for value in self.skill_auto_sync_roots.split(",")
            if value.strip()
        ]


settings = Settings()
