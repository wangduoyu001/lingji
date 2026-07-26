from __future__ import annotations

import os
import re
from dataclasses import asdict, dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Mapping

_QDRANT_MODES = {"embedded", "remote", "memory"}
_WINDOWS_ABSOLUTE = re.compile(r"^[A-Za-z]:[\\/]")


class WorkspaceValidationError(ValueError):
    """Raised when a workspace configuration is unsafe or ambiguous."""


class WorkspaceName(str, Enum):
    PRODUCTION = "production"
    ACCEPTANCE = "acceptance"

    @classmethod
    def parse(cls, value: object) -> "WorkspaceName":
        if isinstance(value, cls):
            return value
        normalized = str(value or "").strip().lower()
        try:
            return cls(normalized)
        except ValueError as exc:
            supported = ", ".join(item.value for item in cls)
            raise WorkspaceValidationError(
                f"Unknown workspace: {value!r}. Expected one of: {supported}"
            ) from exc


@dataclass(frozen=True)
class WorkspaceContext:
    """Immutable, serializable resources for one LingJi workspace."""

    name: WorkspaceName
    vault_path: Path
    raw_path: Path
    storage_path: Path
    state_db_path: Path
    memory_db_path: Path
    qdrant_mode: str
    qdrant_path: Path | None
    qdrant_url: str | None
    qdrant_collection: str
    log_path: Path
    cache_path: Path
    runtime_settings_path: Path
    queue_db_path: Path
    backup_path: Path
    derived_path: Path
    temp_path: Path
    reports_path: Path

    def to_dict(self) -> dict[str, Any]:
        values = asdict(self)
        values["name"] = self.name.value
        return {
            key: str(value) if isinstance(value, Path) else value
            for key, value in values.items()
        }

    def mutable_paths(self) -> dict[str, Path]:
        values = {
            "vault_path": self.vault_path,
            "raw_path": self.raw_path,
            "storage_path": self.storage_path,
            "state_db_path": self.state_db_path,
            "memory_db_path": self.memory_db_path,
            "log_path": self.log_path,
            "cache_path": self.cache_path,
            "runtime_settings_path": self.runtime_settings_path,
            "queue_db_path": self.queue_db_path,
            "backup_path": self.backup_path,
            "derived_path": self.derived_path,
            "temp_path": self.temp_path,
            "reports_path": self.reports_path,
        }
        if self.qdrant_path is not None:
            values["qdrant_path"] = self.qdrant_path
        return values

    def validate(self) -> None:
        mode = self.qdrant_mode.strip().lower()
        if mode not in _QDRANT_MODES:
            raise WorkspaceValidationError(
                f"Unsupported Qdrant mode for {self.name.value}: {self.qdrant_mode!r}"
            )
        if not self.qdrant_collection.strip():
            raise WorkspaceValidationError(
                f"Qdrant collection is required for {self.name.value}"
            )
        if mode == "embedded" and self.qdrant_path is None:
            raise WorkspaceValidationError(
                f"Embedded Qdrant requires qdrant_path for {self.name.value}"
            )
        if mode == "remote" and not (self.qdrant_url or "").strip():
            raise WorkspaceValidationError(
                f"Remote Qdrant requires qdrant_url for {self.name.value}"
            )
        if mode != "remote" and self.qdrant_url:
            raise WorkspaceValidationError(
                f"qdrant_url is only valid in remote mode for {self.name.value}"
            )
        if mode != "embedded" and self.qdrant_path is not None:
            raise WorkspaceValidationError(
                f"qdrant_path is only valid in embedded mode for {self.name.value}"
            )
        for field_name, path in self.mutable_paths().items():
            if not path.is_absolute():
                raise WorkspaceValidationError(
                    f"{self.name.value}.{field_name} must resolve to an absolute path: {path}"
                )
            _reject_system_drive(path, f"{self.name.value}.{field_name}")


class WorkspaceResolver:
    """Resolve workspace resources without creating or migrating data."""

    @classmethod
    def resolve(
        cls,
        settings: Any,
        workspace: WorkspaceName | str | None = None,
        overrides: Mapping[str, Any] | None = None,
        *,
        environ: Mapping[str, str] | None = None,
        project_root: Path | str | None = None,
    ) -> WorkspaceContext:
        override = dict(overrides or {})
        env = os.environ if environ is None else environ
        name = WorkspaceName.parse(
            workspace
            if workspace is not None
            else override.get("name", override.get("workspace"))
            or env.get("LINGJI_WORKSPACE")
            or getattr(settings, "workspace_name", "production")
        )
        prefix = f"LINGJI_{name.value.upper()}_"
        root = Path(project_root or Path.cwd()).expanduser().resolve(strict=False)

        workspace_root = cls._path(
            cls._value(
                override,
                "workspace_root",
                env.get("LINGJI_WORKSPACE_ROOT"),
                getattr(settings, "workspace_root", None),
                Path(getattr(settings, "storage_path", getattr(settings, "storage_dir", "storage")))
                / "workspaces",
            ),
            root,
            "workspace_root",
        )
        storage_path = cls._path(
            cls._value(
                override,
                "storage_path",
                env.get(prefix + "STORAGE"),
                getattr(settings, f"{name.value}_storage_dir", None),
                workspace_root / name.value,
            ),
            root,
            f"{name.value}.storage_path",
        )

        def resource(key: str, env_name: str, setting_name: str, default: Path) -> Path:
            return cls._path(
                cls._value(
                    override,
                    key,
                    env.get(prefix + env_name),
                    getattr(settings, f"{name.value}_{setting_name}", None),
                    default,
                ),
                root,
                f"{name.value}.{key}",
            )

        def derived(key: str, env_name: str, default: Path | str) -> Path:
            return cls._path(
                cls._value(
                    override,
                    key,
                    env.get(prefix + env_name),
                    None,
                    storage_path / default,
                ),
                root,
                f"{name.value}.{key}",
            )

        vault_path = resource("vault_path", "VAULT", "vault_dir", storage_path / "vault")
        raw_path = resource("raw_path", "RAW", "raw_dir", storage_path / "raw")
        state_db_path = resource(
            "state_db_path",
            "STATE_DB",
            "state_db_path",
            storage_path / "state" / str(getattr(settings, "state_db_name", "lingji_state.db")),
        )
        memory_db_path = resource(
            "memory_db_path",
            "MEMORY_DB",
            "memory_db_path",
            storage_path / "index" / str(getattr(settings, "memory_db_name", "lingji_memory.db")),
        )
        qdrant_mode = str(
            cls._value(
                override,
                "qdrant_mode",
                env.get(prefix + "QDRANT_MODE"),
                getattr(settings, f"{name.value}_qdrant_mode", None),
                "embedded",
            )
        ).strip().lower()
        qdrant_collection = str(
            cls._value(
                override,
                "qdrant_collection",
                env.get(prefix + "QDRANT_COLLECTION"),
                getattr(settings, f"{name.value}_qdrant_collection", None),
                f"lingji_memory_{name.value}",
            )
        ).strip()
        qdrant_url_value = cls._optional_value(
            override,
            "qdrant_url",
            env.get(prefix + "QDRANT_URL"),
            getattr(settings, f"{name.value}_qdrant_url", None),
            None,
        )
        qdrant_path_value = cls._optional_value(
            override,
            "qdrant_path",
            env.get(prefix + "QDRANT_PATH"),
            getattr(settings, f"{name.value}_qdrant_path", None),
            storage_path / "qdrant" if qdrant_mode == "embedded" else None,
        )
        qdrant_path = (
            cls._path(qdrant_path_value, root, f"{name.value}.qdrant_path")
            if qdrant_path_value not in (None, "")
            else None
        )
        qdrant_url = (
            str(qdrant_url_value).strip()
            if qdrant_url_value not in (None, "")
            else None
        )

        context = WorkspaceContext(
            name=name,
            vault_path=vault_path,
            raw_path=raw_path,
            storage_path=storage_path,
            state_db_path=state_db_path,
            memory_db_path=memory_db_path,
            qdrant_mode=qdrant_mode,
            qdrant_path=qdrant_path,
            qdrant_url=qdrant_url,
            qdrant_collection=qdrant_collection,
            log_path=derived("log_path", "LOGS", "logs"),
            cache_path=derived("cache_path", "CACHE", "cache"),
            runtime_settings_path=derived(
                "runtime_settings_path",
                "RUNTIME_SETTINGS",
                Path("runtime") / str(getattr(settings, "runtime_settings_file", "runtime_settings.json")),
            ),
            queue_db_path=resource(
                "queue_db_path", "QUEUE_DB", "queue_db_path", state_db_path
            ),
            backup_path=derived("backup_path", "BACKUP", "backups"),
            derived_path=derived("derived_path", "DERIVED", "derived"),
            temp_path=derived("temp_path", "TEMP", "temp"),
            reports_path=derived("reports_path", "REPORTS", "reports"),
        )
        context.validate()
        return context

    @classmethod
    def resolve_all(
        cls,
        settings: Any,
        overrides: Mapping[str, Mapping[str, Any]] | None = None,
        *,
        environ: Mapping[str, str] | None = None,
        project_root: Path | str | None = None,
    ) -> dict[WorkspaceName, WorkspaceContext]:
        override_map = dict(overrides or {})
        contexts = {
            name: cls.resolve(
                settings,
                name,
                override_map.get(name.value),
                environ=environ,
                project_root=project_root,
            )
            for name in WorkspaceName
        }
        cls.validate_isolation(*contexts.values())
        return contexts

    @staticmethod
    def validate_isolation(*contexts: WorkspaceContext) -> None:
        if len(contexts) < 2:
            return
        names = [context.name.value for context in contexts]
        if len(set(names)) != len(names):
            raise WorkspaceValidationError(f"Duplicate workspace contexts: {names}")
        conflicts: list[str] = []
        for index, left in enumerate(contexts):
            for right in contexts[index + 1 :]:
                for left_name, left_path in left.mutable_paths().items():
                    for right_name, right_path in right.mutable_paths().items():
                        if _paths_overlap(left_path, right_path):
                            conflicts.append(
                                f"{left.name.value}.{left_name}={left_path} conflicts with "
                                f"{right.name.value}.{right_name}={right_path}"
                            )
                if left.qdrant_collection.casefold() == right.qdrant_collection.casefold():
                    conflicts.append(
                        f"Qdrant collection is shared by {left.name.value} and "
                        f"{right.name.value}: {left.qdrant_collection}"
                    )
        if conflicts:
            raise WorkspaceValidationError(
                "Workspace isolation failed: " + "; ".join(conflicts)
            )

    @staticmethod
    def _value(
        override: Mapping[str, Any],
        key: str,
        environment: Any,
        setting: Any,
        default: Any,
    ) -> Any:
        if key in override and override[key] not in (None, ""):
            return override[key]
        if environment not in (None, ""):
            return environment
        if setting not in (None, ""):
            return setting
        return default

    @staticmethod
    def _optional_value(
        override: Mapping[str, Any],
        key: str,
        environment: Any,
        setting: Any,
        default: Any,
    ) -> Any:
        if key in override:
            return override[key]
        if environment not in (None, ""):
            return environment
        if setting not in (None, ""):
            return setting
        return default

    @staticmethod
    def _path(value: Any, project_root: Path, label: str) -> Path:
        text = str(value or "").strip()
        if not text:
            raise WorkspaceValidationError(f"Path is required: {label}")
        _reject_system_drive_text(text, label)
        path = Path(text).expanduser()
        if not path.is_absolute():
            path = project_root / path
        resolved = path.resolve(strict=False)
        _reject_system_drive(resolved, label)
        return resolved


def _path_key(path: Path) -> str:
    return str(path.resolve(strict=False)).replace("\\", "/").rstrip("/").casefold()


def _paths_overlap(left: Path, right: Path) -> bool:
    left_key = _path_key(left)
    right_key = _path_key(right)
    return (
        left_key == right_key
        or left_key.startswith(right_key + "/")
        or right_key.startswith(left_key + "/")
    )


def _reject_system_drive_text(value: str, label: str) -> None:
    normalized = value.strip().replace("\\", "/")
    if _WINDOWS_ABSOLUTE.match(normalized) and normalized[:2].casefold() == "c:":
        raise WorkspaceValidationError(
            f"{label} must not use the Windows system drive: {value}"
        )


def _reject_system_drive(path: Path, label: str) -> None:
    if str(path.drive or "").casefold() == "c:":
        raise WorkspaceValidationError(
            f"{label} must not use the Windows system drive: {path}"
        )
