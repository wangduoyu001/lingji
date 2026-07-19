from __future__ import annotations

import hashlib
import json
import os
import shutil
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Iterable, Mapping
from uuid import uuid4


@dataclass(frozen=True)
class StorageCategory:
    name: str
    path: Path
    protected: bool
    cleanup_allowed: bool
    cold_archive_allowed: bool


class StorageLifecycleManager:
    """Inventory storage and execute owner-confirmed, recoverable lifecycle plans.

    Plans never permanently delete files. Cleanup actions move files into a plan-
    scoped recovery area. Raw sources and the Vault are protected from automatic
    cleanup regardless of UI input.
    """

    SCHEMA_VERSION = 1
    PROTECTED_CATEGORIES = {"raw", "vault", "backups"}

    def __init__(self, settings: Any, state_db: Any | None = None):
        self.settings = settings
        self.state_db = state_db
        self.plan_root = settings.storage_path / "plans" / "storage"
        self.trash_root = settings.storage_path / "trash" / "storage"
        self.restore_root = settings.storage_path / "restore-staging"

    def categories(self) -> dict[str, StorageCategory]:
        storage = self.settings.storage_path
        return {
            "raw": StorageCategory("raw", storage / "raw", True, False, True),
            "versions": StorageCategory("versions", storage / "versions", False, True, True),
            "derived": StorageCategory("derived", storage / "derived", False, True, True),
            "cache": StorageCategory("cache", storage / "cache", False, True, False),
            "temp": StorageCategory("temp", storage / "temp", False, True, False),
            "logs": StorageCategory("logs", self.settings.log_path, False, True, True),
            "backups": StorageCategory("backups", self.settings.backup_path, True, False, False),
            "vault": StorageCategory("vault", self.settings.vault_path, True, False, True),
        }

    def inventory(self) -> dict[str, Any]:
        category_rows: dict[str, Any] = {}
        total_bytes = 0
        total_files = 0
        for name, category in self.categories().items():
            stats = self._scan_path(category.path)
            total_bytes += stats["bytes"]
            total_files += stats["files"]
            category_rows[name] = {
                **stats,
                "path": str(category.path),
                "protected": category.protected,
                "cleanup_allowed": category.cleanup_allowed,
                "cold_archive_allowed": category.cold_archive_allowed,
            }
        disk_anchor = self.settings.storage_path
        disk_anchor.mkdir(parents=True, exist_ok=True)
        disk = shutil.disk_usage(disk_anchor)
        return {
            "generated_at": self._now(),
            "totals": {
                "bytes": total_bytes,
                "files": total_files,
                "disk_total_bytes": disk.total,
                "disk_used_bytes": disk.used,
                "disk_free_bytes": disk.free,
                "disk_free_percent": round((disk.free / disk.total * 100) if disk.total else 0.0, 2),
            },
            "categories": category_rows,
        }

    def create_plan(self, policy: Mapping[str, Any]) -> dict[str, Any]:
        """Create a persisted preview plan from UI policy values.

        Supported policy keys:
        - retention_days: mapping category -> days; zero disables age cleanup.
        - max_category_gb: mapping category -> size cap; zero disables size cleanup.
        - cold_storage_enabled / cold_storage_path.
        - archive_categories: categories moved to cold storage instead of recovery trash.
        """

        retention = dict(policy.get("retention_days") or {})
        caps = dict(policy.get("max_category_gb") or {})
        archive_categories = {str(value) for value in policy.get("archive_categories") or []}
        cold_enabled = bool(policy.get("cold_storage_enabled", False))
        cold_root_text = str(policy.get("cold_storage_path") or "").strip()
        cold_root = Path(cold_root_text).expanduser() if cold_root_text else None

        actions: list[dict[str, Any]] = []
        for name, category in self.categories().items():
            if not category.cleanup_allowed:
                continue
            files = list(self._iter_files(category.path))
            selected: dict[str, Path] = {}
            days = max(float(retention.get(name, 0) or 0), 0.0)
            if days:
                cutoff = datetime.now().timestamp() - timedelta(days=days).total_seconds()
                for path in files:
                    try:
                        if path.stat().st_mtime < cutoff:
                            selected[str(path)] = path
                    except OSError:
                        continue

            cap_gb = max(float(caps.get(name, 0) or 0), 0.0)
            if cap_gb:
                cap_bytes = int(cap_gb * 1024**3)
                current_bytes = sum(self._safe_size(path) for path in files)
                for path in sorted(files, key=self._safe_mtime):
                    if current_bytes <= cap_bytes:
                        break
                    selected[str(path)] = path
                    current_bytes -= self._safe_size(path)

            use_cold = (
                cold_enabled
                and cold_root is not None
                and category.cold_archive_allowed
                and name in archive_categories
            )
            for path in sorted(selected.values()):
                stat = path.stat()
                relative = path.relative_to(category.path).as_posix()
                action = "move_cold" if use_cold else "move_trash"
                destination = ""
                if use_cold and cold_root is not None:
                    destination = str(cold_root / name / relative)
                actions.append(
                    {
                        "category": name,
                        "source": str(path),
                        "relative_path": relative,
                        "action": action,
                        "destination": destination,
                        "size": int(stat.st_size),
                        "mtime_ns": int(stat.st_mtime_ns),
                    }
                )

        plan_id = f"LJ-STORAGE-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{uuid4().hex[:8]}"
        payload = {
            "schema_version": self.SCHEMA_VERSION,
            "plan_id": plan_id,
            "status": "preview",
            "created_at": self._now(),
            "policy": dict(policy),
            "actions": actions,
            "summary": self._summarize_actions(actions),
        }
        payload["digest"] = self._plan_digest(payload)
        self._write_plan(payload)
        self._event("storage_plan_created", plan_id, payload["summary"])
        return payload

    def execute_plan(self, plan_id: str, confirmation: str) -> dict[str, Any]:
        expected = f"EXECUTE_STORAGE_PLAN:{plan_id}"
        if confirmation != expected:
            raise PermissionError("Storage plan confirmation does not match")
        plan = self.get_plan(plan_id)
        if plan.get("status") not in {"preview", "partial"}:
            raise RuntimeError(f"Storage plan is not executable: {plan.get('status')}")
        if plan.get("digest") != self._plan_digest(plan):
            raise RuntimeError("Storage plan digest is invalid")

        completed: list[dict[str, Any]] = []
        errors: list[dict[str, str]] = []
        for action in plan.get("actions") or []:
            try:
                result = self._execute_action(plan_id, action)
                completed.append(result)
            except Exception as exc:
                errors.append({"source": str(action.get("source") or ""), "error": str(exc)[:1000]})

        plan["status"] = "completed" if not errors else "partial"
        plan["executed_at"] = self._now()
        plan["completed_actions"] = completed
        plan["errors"] = errors
        plan["result_summary"] = self._summarize_actions(completed)
        plan["digest"] = self._plan_digest(plan)
        self._write_plan(plan)
        self._event(
            "storage_plan_executed",
            plan_id,
            {"status": plan["status"], "completed": len(completed), "errors": len(errors)},
        )
        return plan

    def restore_plan(self, plan_id: str, confirmation: str) -> dict[str, Any]:
        expected = f"RESTORE_STORAGE_PLAN:{plan_id}"
        if confirmation != expected:
            raise PermissionError("Storage restore confirmation does not match")
        plan = self.get_plan(plan_id)
        restored: list[dict[str, Any]] = []
        errors: list[dict[str, str]] = []
        for item in reversed(plan.get("completed_actions") or []):
            if item.get("action") != "move_trash":
                continue
            source = Path(str(item.get("recovery_path") or ""))
            destination = Path(str(item.get("source") or ""))
            try:
                self._assert_within(source, self.trash_root / plan_id)
                if not source.exists():
                    raise FileNotFoundError(source)
                if destination.exists():
                    raise FileExistsError(destination)
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(source), str(destination))
                restored.append({"source": str(source), "destination": str(destination)})
            except Exception as exc:
                errors.append({"source": str(source), "error": str(exc)[:1000]})
        plan["restored_at"] = self._now()
        plan["restore_status"] = "completed" if not errors else "partial"
        plan["restored"] = restored
        plan["restore_errors"] = errors
        plan["digest"] = self._plan_digest(plan)
        self._write_plan(plan)
        self._event(
            "storage_plan_restored",
            plan_id,
            {"status": plan["restore_status"], "restored": len(restored), "errors": len(errors)},
        )
        return plan

    def list_plans(self, limit: int = 50) -> list[dict[str, Any]]:
        if not self.plan_root.exists():
            return []
        rows = []
        for path in sorted(self.plan_root.glob("*.json"), reverse=True)[: max(int(limit), 1)]:
            try:
                data = json.loads(path.read_text(encoding="utf-8-sig"))
                rows.append(
                    {
                        "plan_id": data.get("plan_id"),
                        "status": data.get("status"),
                        "created_at": data.get("created_at"),
                        "executed_at": data.get("executed_at"),
                        "summary": data.get("summary") or {},
                    }
                )
            except (OSError, json.JSONDecodeError):
                continue
        return rows

    def get_plan(self, plan_id: str) -> dict[str, Any]:
        path = self._plan_path(plan_id)
        if not path.exists():
            raise LookupError(f"Unknown storage plan: {plan_id}")
        return json.loads(path.read_text(encoding="utf-8-sig"))

    def _execute_action(self, plan_id: str, action: Mapping[str, Any]) -> dict[str, Any]:
        category_name = str(action.get("category") or "")
        category = self.categories().get(category_name)
        if not category or not category.cleanup_allowed:
            raise PermissionError(f"Category cannot be cleaned automatically: {category_name}")
        if category_name in self.PROTECTED_CATEGORIES:
            raise PermissionError(f"Protected category cannot be cleaned: {category_name}")
        source = Path(str(action.get("source") or ""))
        self._assert_within(source, category.path)
        if not source.is_file() or source.is_symlink():
            raise FileNotFoundError(source)
        stat = source.stat()
        if stat.st_size != int(action.get("size") or -1) or stat.st_mtime_ns != int(action.get("mtime_ns") or -1):
            raise RuntimeError(f"File changed after preview: {source}")

        result = dict(action)
        if action.get("action") == "move_cold":
            destination = Path(str(action.get("destination") or ""))
            if not str(destination):
                raise ValueError("Cold storage destination is missing")
            destination.parent.mkdir(parents=True, exist_ok=True)
            if destination.exists():
                if self._sha256(destination) != self._sha256(source):
                    raise FileExistsError(destination)
            else:
                temporary = destination.with_suffix(destination.suffix + ".partial")
                shutil.copy2(source, temporary)
                if self._sha256(temporary) != self._sha256(source):
                    temporary.unlink(missing_ok=True)
                    raise IOError(f"Cold storage verification failed: {source}")
                temporary.replace(destination)
            source.unlink()
            result["cold_path"] = str(destination)
            return result

        recovery = self.trash_root / plan_id / category_name / str(action.get("relative_path") or source.name)
        recovery.parent.mkdir(parents=True, exist_ok=True)
        if recovery.exists():
            raise FileExistsError(recovery)
        shutil.move(str(source), str(recovery))
        result["recovery_path"] = str(recovery)
        return result

    @staticmethod
    def _scan_path(root: Path) -> dict[str, int]:
        files = 0
        total = 0
        if root.exists():
            for path in StorageLifecycleManager._iter_files(root):
                files += 1
                total += StorageLifecycleManager._safe_size(path)
        return {"files": files, "bytes": total}

    @staticmethod
    def _iter_files(root: Path) -> Iterable[Path]:
        if not root.exists():
            return ()
        return (path for path in root.rglob("*") if path.is_file() and not path.is_symlink())

    @staticmethod
    def _safe_size(path: Path) -> int:
        try:
            return int(path.stat().st_size)
        except OSError:
            return 0

    @staticmethod
    def _safe_mtime(path: Path) -> float:
        try:
            return float(path.stat().st_mtime)
        except OSError:
            return float("inf")

    @staticmethod
    def _summarize_actions(actions: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
        rows = list(actions)
        by_category: dict[str, dict[str, int]] = {}
        for row in rows:
            category = str(row.get("category") or "unknown")
            bucket = by_category.setdefault(category, {"files": 0, "bytes": 0})
            bucket["files"] += 1
            bucket["bytes"] += int(row.get("size") or 0)
        return {
            "files": len(rows),
            "bytes": sum(int(row.get("size") or 0) for row in rows),
            "by_category": by_category,
        }

    def _write_plan(self, payload: Mapping[str, Any]) -> None:
        self.plan_root.mkdir(parents=True, exist_ok=True)
        path = self._plan_path(str(payload["plan_id"]))
        temporary = path.with_suffix(".json.tmp")
        temporary.write_text(json.dumps(dict(payload), ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        temporary.replace(path)

    def _plan_path(self, plan_id: str) -> Path:
        safe = "".join(character for character in str(plan_id) if character.isalnum() or character in "-_")
        if safe != plan_id or not safe:
            raise ValueError("Invalid storage plan id")
        return self.plan_root / f"{safe}.json"

    @staticmethod
    def _plan_digest(payload: Mapping[str, Any]) -> str:
        material = {key: value for key, value in payload.items() if key != "digest"}
        encoded = json.dumps(material, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
        return hashlib.sha256(encoded.encode("utf-8")).hexdigest()

    @staticmethod
    def _sha256(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    @staticmethod
    def _assert_within(path: Path, root: Path) -> None:
        resolved = path.resolve(strict=False)
        boundary = root.resolve(strict=False)
        try:
            resolved.relative_to(boundary)
        except ValueError as exc:
            raise PermissionError(f"Path is outside allowed root: {path}") from exc

    @staticmethod
    def _now() -> str:
        return datetime.now().isoformat(timespec="seconds")

    def _event(self, event_type: str, entity_id: str, payload: Mapping[str, Any]) -> None:
        if self.state_db:
            self.state_db.append_event(event_type, "storage_plan", entity_id, dict(payload))
