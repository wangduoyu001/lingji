import hashlib
import json
import logging
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from src.memory.vault_layout import VaultLayout
from src.obsidian.frontmatter import FrontmatterError, split_frontmatter
from src.obsidian.memory_scope import ObsidianMemoryScope

logger = logging.getLogger("pemis.indexer")

RELATION_FIELDS = (
    "project",
    "people",
    "organizations",
    "tools",
    "models",
    "sources",
    "tasks",
    "decisions",
    "related",
    "related_ids",
)


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
        self._last_sync_result = None

    def _parse_frontmatter(self, text):
        try:
            metadata, _ = split_frontmatter(text)
            return metadata
        except FrontmatterError as exc:
            logger.warning("Invalid frontmatter: %s", exc)
            return {}

    def _extract_summary(self, text):
        try:
            _, body = split_frontmatter(text)
        except FrontmatterError:
            body = text
        for line in body.splitlines():
            line = line.strip()
            if not line or line.startswith(("# ", "**", "---", ">")):
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
        if path.stem.lower().startswith("opp_"):
            return "opportunity"
        classification = self.layout.classify(path)
        return "source" if classification.is_inbox else "note"

    @staticmethod
    def _list(value: Any) -> list[Any]:
        if value in (None, ""):
            return []
        if isinstance(value, list):
            return value
        if isinstance(value, (tuple, set)):
            return list(value)
        return [value]

    @staticmethod
    def _number(value: Any, default: float = 0.0) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    def _parse_md_file(self, path):
        path = Path(path)
        if not self.layout.should_index(path, include_private=self.include_private):
            return None
        try:
            text = path.read_text(encoding="utf-8-sig")
            stat = path.stat()
        except Exception as exc:
            logger.warning("Read failed %s: %s", path, exc)
            return None

        meta = self._parse_frontmatter(text)
        classification = self.layout.classify(path)
        file_id = str(meta.get("id") or classification.relative_path)
        title = str(meta.get("title") or path.stem)
        for line in text.splitlines():
            if line.startswith("# "):
                title = line[2:].strip()
                break
        dtype = self._infer_type(path, meta)
        relations = {field: self._list(meta.get(field)) for field in RELATION_FIELDS}
        project_links = relations["project"] or self._list(meta.get("project_id"))

        entry = {
            "id": file_id,
            "schema_version": meta.get("schema_version", 1),
            "type": dtype,
            "memory_type": str(meta.get("memory_type") or dtype),
            "title": title or path.stem,
            "aliases": self._list(meta.get("aliases")),
            "summary": str(meta.get("summary") or self._extract_summary(text)),
            "content_hash": hashlib.md5(text.encode("utf-8")).hexdigest(),
            "created": meta.get("created_at") or meta.get("created", ""),
            "updated": meta.get("updated_at") or datetime.now().isoformat(),
            "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "size": stat.st_size,
            "source": meta.get("source", "vault"),
            "source_type": meta.get("source_type") or classification.source_type,
            "source_id": meta.get("source_id", ""),
            "source_path": meta.get("source_path", ""),
            "source_url": meta.get("source_url", ""),
            "project": project_links,
            "project_id": meta.get("project_id", ""),
            "status": meta.get("status", "active"),
            "privacy": meta.get("privacy") or classification.privacy,
            "importance": meta.get("importance", ""),
            "review_status": meta.get("review_status", ""),
            "tags": self._list(meta.get("tags")),
            "supersedes": self._list(meta.get("supersedes")),
            "superseded_by": self._list(meta.get("superseded_by")),
            "score": self._number(meta.get("score"), 0.0),
            "speed": meta.get("speed", ""),
            "monetization": meta.get("monetization", ""),
            "difficulty": int(self._number(meta.get("difficulty"), 0)),
            "confidence": meta.get("confidence", 0.0),
            "relative_path": classification.relative_path,
            "top_level": classification.top_level,
            "category": classification.category,
            "is_private": classification.is_private,
            "is_inbox": classification.is_inbox,
            "is_archive": classification.is_archive,
            "properties": meta,
        }
        entry.update(relations)
        entry["project"] = project_links
        return entry

    def build_index(self, force=False):
        """Build the first index, then synchronize incrementally on later calls."""
        if force or not self.index_path.exists():
            return self.rebuild_index()
        try:
            return self.sync_index()["index"]
        except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
            logger.warning("Existing index cannot be synchronized; rebuilding: %s", exc)
            return self.rebuild_index()

    def rebuild_index(self):
        entries = {}
        md_files = self._vault_markdown_files()
        for markdown_file in md_files:
            entry = self._parse_md_file(markdown_file)
            if entry:
                if entry["id"] in entries:
                    logger.warning("Duplicate memory id: %s (%s)", entry["id"], markdown_file)
                entries[entry["id"]] = entry
        self._add_external_opportunities(entries)
        idx = self._new_index(entries, full_rebuild=True)
        with self._lock:
            self._index = idx
            self.save_index(idx)
        self._last_sync_result = {
            "full_rebuild": True,
            "added": len(entries),
            "updated": 0,
            "removed": 0,
            "unchanged": 0,
            "changed_paths": [entry.get("relative_path") for entry in entries.values() if entry.get("relative_path")],
            "removed_paths": [],
            "index": idx,
        }
        logger.info("Index rebuilt: %d entries from %d vault files", len(entries), len(md_files))
        return idx

    def sync_index(self):
        with self._lock:
            old = self._load()
            old_entries = dict(old.get("entries") or {})
        old_by_path = {
            str(entry.get("relative_path")): (file_id, entry)
            for file_id, entry in old_entries.items()
            if entry.get("relative_path")
        }
        entries = {}
        current_paths = set()
        changed_paths = []
        added = 0
        updated = 0
        unchanged = 0

        for path in self._vault_markdown_files():
            relative = self.layout.relative(path).as_posix()
            current_paths.add(relative)
            previous_pair = old_by_path.get(relative)
            previous = previous_pair[1] if previous_pair else None
            stat = path.stat()
            modified_at = datetime.fromtimestamp(stat.st_mtime).isoformat()
            if previous and int(previous.get("size") or -1) == stat.st_size and previous.get("modified_at") == modified_at:
                entries[str(previous_pair[0])] = previous
                unchanged += 1
                continue
            parsed = self._parse_md_file(path)
            if not parsed:
                continue
            entries[parsed["id"]] = parsed
            changed_paths.append(relative)
            if previous:
                updated += 1
            else:
                added += 1

        removed_paths = sorted(set(old_by_path) - current_paths)
        self._add_external_opportunities(entries)
        idx = self._new_index(entries, full_rebuild=False)
        idx["meta"]["sync"] = {
            "added": added,
            "updated": updated,
            "removed": len(removed_paths),
            "unchanged": unchanged,
        }
        with self._lock:
            self._index = idx
            self.save_index(idx)
        result = {
            "full_rebuild": False,
            "added": added,
            "updated": updated,
            "removed": len(removed_paths),
            "unchanged": unchanged,
            "changed_paths": changed_paths,
            "removed_paths": removed_paths,
            "index": idx,
        }
        self._last_sync_result = result
        logger.info(
            "Index synchronized: %d added, %d updated, %d removed, %d unchanged",
            added,
            updated,
            len(removed_paths),
            unchanged,
        )
        return result

    def _vault_markdown_files(self):
        return [
            path
            for path in self.vault_dir.rglob("*.md")
            if not self._is_dashboard_file(path)
            and self.layout.should_index(path, include_private=self.include_private)
        ]

    def memory_entries(self) -> list[dict[str, Any]]:
        """Return only files authorized for automatic-memory projection.

        This is deliberately separate from ``build_index``: callers that need
        the compatibility PEMIS index retain the historical broad behavior,
        while automatic-memory consumers get the fail-closed scope contract.
        """
        scope = ObsidianMemoryScope(self.vault_dir)
        entries: list[dict[str, Any]] = []
        for decision in scope.iter_markdown():
            entry = self._parse_md_file(decision.path)
            if entry:
                entry["memory_scope_reason"] = decision.reason
                entry["memory_scope_explicit_flag"] = decision.explicit_flag
                entries.append(entry)
        return entries

    def build_memory_index(self) -> dict[str, Any]:
        """Build an in-memory automatic-memory view without changing legacy index."""
        entries = {str(entry["id"]): entry for entry in self.memory_entries()}
        return self._new_index(entries, full_rebuild=True)

    def _add_external_opportunities(self, entries):
        if not self.opp_dir.exists():
            return
        for markdown_file in self.opp_dir.glob("*.md"):
            entry = self._parse_external_opp_file(markdown_file)
            if entry:
                entries.setdefault(entry["id"], entry)

    def _new_index(self, entries, full_rebuild):
        now = datetime.now()
        return {
            "meta": {
                "version": "2.2",
                "layout_version": "1",
                "total": len(entries),
                "last_build": now.timestamp(),
                "updated_at": now.isoformat(),
                "include_private": self.include_private,
                "full_rebuild": bool(full_rebuild),
            },
            "entries": entries,
        }

    @property
    def last_sync_result(self):
        return self._last_sync_result

    def _parse_external_opp_file(self, path):
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
            "score": self._number(meta.get("score"), 0.0),
            "tags": self._list(meta.get("tags")),
            "title": str(meta.get("title") or Path(path).stem),
            "summary": str(meta.get("summary") or self._extract_summary(text)),
            "content_hash": hashlib.md5(text.encode("utf-8")).hexdigest(),
            "created": meta.get("generated_at") or meta.get("created", ""),
            "updated": meta.get("updated_at") or datetime.now().isoformat(),
            "source": "storage/opportunities",
            "source_type": meta.get("source_type", "derived_opportunity"),
            "source_id": meta.get("source_id", ""),
            "source_path": meta.get("source_path", ""),
            "source_content_hash": meta.get("source_content_hash", ""),
            "project": self._list(meta.get("project")),
            "sources": self._list(meta.get("sources")),
            "related": self._list(meta.get("related")),
            "relative_path": "",
            "top_level": "",
            "category": "opportunity",
            "privacy": meta.get("privacy", "private"),
            "status": meta.get("status", "needs_review"),
            "review_status": meta.get("review_status", "needs_review"),
            "is_private": False,
            "is_inbox": False,
            "is_archive": False,
            "speed": meta.get("speed", ""),
            "monetization": meta.get("monetization", ""),
            "difficulty": int(self._number(meta.get("difficulty"), 0)),
            "confidence": meta.get("confidence", 0.0),
            "properties": meta,
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
            old_ids = [
                file_id
                for file_id, existing in idx.get("entries", {}).items()
                if existing.get("relative_path") == entry.get("relative_path") and file_id != entry["id"]
            ]
            for old_id in old_ids:
                del idx["entries"][old_id]
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
                snapshot[str(markdown_file)] = (
                    markdown_file.stat().st_mtime,
                    markdown_file.stat().st_size,
                )
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
        return next(
            (entry for entry in self.get_all() if entry.get("relative_path") == relative),
            None,
        )

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
            self._index = {"meta": {"version": "2.2", "total": 0}, "entries": {}}
        return self._index

    @staticmethod
    def _touch_meta(index):
        index.setdefault("meta", {})
        index["meta"]["total"] = len(index.setdefault("entries", {}))
        index["meta"]["updated_at"] = datetime.now().isoformat()
