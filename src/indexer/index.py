import hashlib
import json
import logging
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from src.memory.vault_layout import VaultLayout

logger = logging.getLogger("pemis.indexer")


class PEMISIndex:
    def __init__(self, vault_dir, storage_dir, include_private=False):
        self.vault_dir = Path(vault_dir)
        self.storage_dir = Path(storage_dir)
        self.opp_dir = self.storage_dir / "opportunities"
        self.index_path = self.storage_dir / "pemis_index.json"
        self.layout = VaultLayout(self.vault_dir)
        self.include_private = bool(include_private)
        self._index = None
        self._lock = threading.RLock()
        self._watchdog_running = False
        self._watchdog_thread = None
        self._watchdog_snapshot = {}
        self._callback = None
        self._legacy_dash_dir = self.vault_dir / "PEMIS" / "dashboard"

    def _parse_frontmatter(self, text):
        meta: dict[str, Any] = {}
        lines = text.lstrip("\ufeff").splitlines()
        if not lines or lines[0].strip() != "---":
            return meta

        current_list_key = None
        for raw_line in lines[1:]:
            line = raw_line.rstrip()
            if line.strip() == "---":
                break
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            if current_list_key and stripped.startswith("-"):
                meta[current_list_key].append(self._parse_scalar(stripped[1:].strip()))
                continue
            if ":" not in line:
                current_list_key = None
                continue
            key, _, raw_value = line.partition(":")
            key = key.strip().lower()
            raw_value = raw_value.strip()
            if not key:
                continue
            if raw_value == "":
                meta[key] = []
                current_list_key = key
                continue
            current_list_key = None
            if raw_value.startswith("[") and raw_value.endswith("]"):
                values = raw_value[1:-1].strip()
                meta[key] = [self._parse_scalar(value.strip()) for value in values.split(",") if value.strip()]
            else:
                meta[key] = self._parse_scalar(raw_value)
        return meta

    @staticmethod
    def _parse_scalar(value):
        value = value.strip().strip('"').strip("'")
        lowered = value.lower()
        if lowered in {"true", "false"}:
            return lowered == "true"
        if lowered in {"null", "none", "~"}:
            return None
        try:
            if "." in value:
                return float(value)
            return int(value)
        except ValueError:
            return value

    def _extract_summary(self, text):
        """Extract a useful summary from the body text after frontmatter."""
        body = text.lstrip("\ufeff").strip()
        if body.startswith("---"):
            end = body.find("---", 3)
            if end != -1:
                body = body[end + 3 :].strip()
        for line in body.splitlines():
            line = line.strip()
            if not line or line.startswith(("# ", "**", "---")):
                continue
            clean = line.replace("**", "").replace("[", "").replace("]", "")
            if len(clean) > 20:
                return clean[:300]
        return ""

    def _is_dashboard_file(self, path):
        try:
            return self._legacy_dash_dir in path.parents or self.layout.dashboard_dir in path.parents
        except Exception:
            return False

    def _infer_type(self, path, meta):
        value = meta.get("memory_type") or meta.get("type") or ""
        if value and value != "note":
            return str(value)
        name = path.stem.lower()
        if name.startswith("opp_"):
            return "opportunity"
        classification = self.layout.classify(path)
        if classification.is_inbox:
            return "source"
        return "note"

    def _parse_md_file(self, path):
        path = Path(path)
        if not self.layout.should_index(path, include_private=self.include_private):
            return None
        try:
            text = path.read_text(encoding="utf-8-sig")
        except Exception as exc:
            logger.warning("Read failed %s: %s", path, exc)
            return None

        meta = self._parse_frontmatter(text)
        classification = self.layout.classify(path)
        file_id = str(meta.get("id") or path.stem)
        content_hash = hashlib.md5(text.encode("utf-8")).hexdigest()
        title = str(meta.get("title") or path.stem)
        for line in text.splitlines():
            if line.startswith("# "):
                title = line[2:].strip()
                break
        dtype = self._infer_type(path, meta)
        summary = str(meta.get("summary") or self._extract_summary(text))
        try:
            difficulty = int(meta.get("difficulty", 0) or 0)
        except (TypeError, ValueError):
            difficulty = 0

        stat = path.stat()
        return {
            "id": file_id,
            "schema_version": meta.get("schema_version", 1),
            "type": dtype,
            "memory_type": str(meta.get("memory_type") or dtype),
            "score": meta.get("score", 0.0),
            "tags": meta.get("tags", []),
            "title": title or path.stem,
            "summary": summary,
            "content_hash": content_hash,
            "created": meta.get("created_at") or meta.get("created", ""),
            "updated": meta.get("updated_at") or datetime.now().isoformat(),
            "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "size": stat.st_size,
            "source": meta.get("source", "vault"),
            "source_type": meta.get("source_type") or classification.source_type,
            "source_id": meta.get("source_id", ""),
            "source_path": meta.get("source_path", ""),
            "source_url": meta.get("source_url", ""),
            "project_id": meta.get("project_id", ""),
            "status": meta.get("status", "active"),
            "privacy": meta.get("privacy") or classification.privacy,
            "importance": meta.get("importance", ""),
            "review_status": meta.get("review_status", ""),
            "related_ids": meta.get("related_ids", []),
            "supersedes": meta.get("supersedes", ""),
            "superseded_by": meta.get("superseded_by", ""),
            "speed": meta.get("speed", ""),
            "monetization": meta.get("monetization", ""),
            "difficulty": difficulty,
            "confidence": meta.get("confidence", 0.0),
            "relative_path": classification.relative_path,
            "top_level": classification.top_level,
            "category": classification.category,
            "is_private": classification.is_private,
            "is_inbox": classification.is_inbox,
            "is_archive": classification.is_archive,
        }

    def build_index(self):
        entries = {}
        md_files = [
            path
            for path in self.vault_dir.rglob("*.md")
            if not self._is_dashboard_file(path)
            and self.layout.should_index(path, include_private=self.include_private)
        ]
        for markdown_file in md_files:
            entry = self._parse_md_file(markdown_file)
            if entry:
                entries[entry["id"]] = entry

        if self.opp_dir.exists():
            for markdown_file in self.opp_dir.glob("*.md"):
                entry = self._parse_external_opp_file(markdown_file)
                if entry:
                    entries.setdefault(entry["id"], entry)

        idx = {
            "meta": {
                "version": "2.0",
                "layout_version": "1",
                "total": len(entries),
                "last_build": datetime.now().timestamp(),
                "updated_at": datetime.now().isoformat(),
                "include_private": self.include_private,
            },
            "entries": entries,
        }
        with self._lock:
            self._index = idx
            self.save_index(idx)
        opp_count = sum(1 for entry in entries.values() if entry.get("type") == "opportunity")
        logger.info(
            "Index built: %d entries (%d opportunities) from %d vault files",
            len(entries),
            opp_count,
            len(md_files),
        )
        return idx

    def _parse_external_opp_file(self, path):
        """Parse legacy storage/opportunities files without pretending they live in the vault."""
        try:
            text = Path(path).read_text(encoding="utf-8-sig")
        except Exception:
            return None
        meta = self._parse_frontmatter(text)
        return {
            "id": str(meta.get("id") or Path(path).stem),
            "schema_version": meta.get("schema_version", 1),
            "type": "opportunity",
            "memory_type": "opportunity",
            "score": meta.get("score", 0.0),
            "tags": meta.get("tags", []),
            "title": Path(path).stem,
            "summary": meta.get("summary") or self._extract_summary(text),
            "content_hash": hashlib.md5(text.encode("utf-8")).hexdigest(),
            "created": meta.get("created", ""),
            "updated": datetime.now().isoformat(),
            "source": "storage/opportunities",
            "source_type": "legacy_opportunity",
            "relative_path": "",
            "top_level": "",
            "category": "opportunity",
            "privacy": "private",
            "is_private": False,
            "is_inbox": False,
            "is_archive": False,
            "speed": meta.get("speed", ""),
            "monetization": meta.get("monetization", ""),
            "difficulty": meta.get("difficulty", 0),
            "confidence": meta.get("confidence", 0.0),
        }

    def incremental_add(self, file_path):
        path = Path(file_path)
        if self._is_dashboard_file(path):
            return False
        entry = self._parse_md_file(path)
        if not entry:
            return False
        with self._lock:
            idx = self._load()
            idx["entries"][entry["id"]] = entry
            self._touch_meta(idx)
            self.save_index(idx)
        return True

    def incremental_update(self, file_path):
        return self.incremental_add(file_path)

    def incremental_remove(self, file_ref):
        reference = str(file_ref)
        candidates = {reference, Path(reference).stem}
        relative_candidate = None
        try:
            relative_candidate = self.layout.relative(reference).as_posix()
        except ValueError:
            pass

        with self._lock:
            idx = self._load()
            target_id = None
            for file_id, entry in idx.get("entries", {}).items():
                if file_id in candidates:
                    target_id = file_id
                    break
                if relative_candidate and entry.get("relative_path") == relative_candidate:
                    target_id = file_id
                    break
            if target_id:
                del idx["entries"][target_id]
                self._touch_meta(idx)
                self.save_index(idx)
                logger.info("Incremental remove: %s", target_id)
                return True
        return False

    def start_watchdog(self, callback=None):
        if self._watchdog_running:
            return
        self._callback = callback
        self._watchdog_snapshot = self._snapshot_files()
        self._watchdog_running = True
        self._watchdog_thread = threading.Thread(target=self._watchdog_loop, daemon=True)
        self._watchdog_thread.start()
        logger.info("Watchdog started")

    def _snapshot_files(self):
        snapshot = {}
        for markdown_file in self.vault_dir.rglob("*.md"):
            if self._is_dashboard_file(markdown_file):
                continue
            if not self.layout.should_index(markdown_file, include_private=self.include_private):
                continue
            try:
                snapshot[str(markdown_file)] = (markdown_file.stat().st_mtime, markdown_file.stat().st_size)
            except OSError:
                continue
        return snapshot

    def _watchdog_loop(self):
        known = dict(self._watchdog_snapshot)
        while self._watchdog_running:
            try:
                current = self._snapshot_files()
                for path_str, signature in current.items():
                    if path_str not in known:
                        if self.incremental_add(path_str):
                            self._notify("created", path_str)
                    elif signature != known[path_str]:
                        if self.incremental_update(path_str):
                            self._notify("modified", path_str)
                for path_str in set(known) - set(current):
                    if self.incremental_remove(path_str):
                        self._notify("deleted", path_str)
                known = current
                self._watchdog_snapshot = current
                time.sleep(10)
            except Exception as exc:
                logger.error("Watchdog error: %s", exc)
                time.sleep(30)

    def _notify(self, action, file_path):
        if not self._callback:
            return
        try:
            self._callback(action, file_path)
        except Exception as exc:
            logger.error("Watchdog callback error: %s", exc)

    def stop_watchdog(self):
        self._watchdog_running = False
        self._callback = None

    def get_entry(self, file_id):
        idx = self._load()
        return idx.get("entries", {}).get(file_id)

    def get_all(self):
        idx = self._load()
        return list(idx.get("entries", {}).values())

    def find_by_path(self, path):
        try:
            relative = self.layout.relative(path).as_posix()
        except ValueError:
            return None
        return next((entry for entry in self.get_all() if entry.get("relative_path") == relative), None)

    def save_index(self, index):
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        temp_path = self.index_path.with_suffix(".json.tmp")
        with open(temp_path, "w", encoding="utf-8") as handle:
            json.dump(index, handle, ensure_ascii=False, indent=2)
        temp_path.replace(self.index_path)

    def _load(self):
        if self._index is not None:
            return self._index
        if self.index_path.exists():
            with open(self.index_path, "r", encoding="utf-8-sig") as handle:
                self._index = json.load(handle)
        else:
            self._index = {"meta": {"version": "2.0", "total": 0}, "entries": {}}
        return self._index

    @staticmethod
    def _touch_meta(index):
        index.setdefault("meta", {})
        index["meta"]["total"] = len(index.setdefault("entries", {}))
        index["meta"]["updated_at"] = datetime.now().isoformat()
