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

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "allow"

    @property
    def vault_path(self) -> Path:
        return Path(self.vault_dir)

    @property
    def storage_path(self) -> Path:
        return Path(self.storage_dir)

    @property
    def snapshot_path(self) -> Path:
        return Path(self.snapshot_dir)

    @property
    def backup_path(self) -> Path:
        return Path(self.backup_dir)

    @property
    def log_path(self) -> Path:
        return Path(self.log_dir)


settings = Settings()