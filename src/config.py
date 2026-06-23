from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "qwen2.5:7b"
    embedding_model: str = "bge-m3"
    vault_dir: str = "vault"
    storage_dir: str = "storage"
    snapshot_dir: str = "snapshot"
    backup_dir: str = "D:/codex/backups"
    log_dir: str = "logs"
    safety_mode: str = "NORMAL"
    qdrant_host: str = "127.0.0.1"
    qdrant_port: int = 6333
    cron_job_1: str = "scan,6"
    cron_job_2: str = "distill,24"
    cron_job_3: str = "integrity,24"
    topk_normal: int = 10
    topk_degraded: int = 6
    topk_safe: int = 3
    cache_max: int = 100

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

    @property
    def p4_task_enabled(self) -> bool:
        return self.safety_mode == "MAINTENANCE"


settings = Settings()
