import json
import logging
import re
from datetime import datetime
from pathlib import Path

logger = logging.getLogger("pemis.integrity")

WIKILINK_PATTERN = re.compile(r"^\[\[([^\]|#]+)(?:#[^\]|]+)?(?:\|[^\]]+)?\]\]$")
SOURCE_REQUIRED_TYPES = {"knowledge", "decision", "opportunity"}
ACTIVE_STATUSES = {
    "received",
    "queued",
    "running",
    "processing",
    "needs_review",
    "active",
    "blocked",
    "waiting",
    "todo",
    "done",
    "completed",
    "superseded",
    "expired",
    "archived",
    "failed",
    "cancelled",
}
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
)


class IntegrityChecker:
    def __init__(self, settings):
        self.settings = settings
        self.log_dir = Path(settings.log_dir) / "integrity"
        self.log_dir.mkdir(parents=True, exist_ok=True)

    def check(self, index=None):
        report = {
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "healthy": True,
            "errors": [],
            "warnings": [],
            "counts": {},
            "details": {
                "missing_sources": [],
                "broken_links": [],
                "invalid_statuses": [],
                "private_leaks": [],
                "orphan_notes": [],
                "duplicate_hashes": [],
            },
        }
        if not index:
            report["healthy"] = False
            report["errors"].append("Index is unavailable")
            return self._write(report)

        entries = index.get_all()
        report["counts"]["index_entries"] = len(entries)
        hash_paths = {}
        known_paths = {
            str(entry.get("relative_path") or "").removesuffix(".md")
            for entry in entries
            if entry.get("relative_path")
        }

        for entry in entries:
            relative_path = str(entry.get("relative_path") or "")
            content_hash = str(entry.get("content_hash") or "")
            if content_hash:
                hash_paths.setdefault(content_hash, []).append(relative_path or entry.get("id"))

            if entry.get("is_private") and not getattr(self.settings, "index_private", False):
                report["details"]["private_leaks"].append(relative_path or entry.get("id"))

            memory_type = str(entry.get("memory_type") or entry.get("type") or "")
            has_source = bool(
                entry.get("source_id")
                or entry.get("source_path")
                or entry.get("sources")
                or entry.get("source_url")
            )
            if memory_type in SOURCE_REQUIRED_TYPES and not has_source:
                report["details"]["missing_sources"].append(relative_path or entry.get("id"))

            status = str(entry.get("status") or "active")
            if status not in ACTIVE_STATUSES:
                report["details"]["invalid_statuses"].append(
                    {"path": relative_path or entry.get("id"), "status": status}
                )

            relationship_count = 0
            for field in RELATION_FIELDS:
                for value in entry.get(field) or []:
                    relationship_count += 1
                    match = WIKILINK_PATTERN.match(str(value).strip())
                    if not match:
                        continue
                    target = match.group(1).replace("\\", "/").removesuffix(".md")
                    if target not in known_paths and not (self.settings.vault_path / (target + ".md")).exists():
                        report["details"]["broken_links"].append(
                            {"from": relative_path or entry.get("id"), "field": field, "target": target}
                        )

            if (
                memory_type not in {"dashboard", "system_rule", "system_guide", "command", "template"}
                and not entry.get("project")
                and relationship_count == 0
            ):
                report["details"]["orphan_notes"].append(relative_path or entry.get("id"))

        report["details"]["duplicate_hashes"] = [
            paths for paths in hash_paths.values() if len(paths) > 1
        ]
        for key, values in report["details"].items():
            report["counts"][key] = len(values)

        if report["details"]["private_leaks"]:
            report["healthy"] = False
            report["errors"].append("Restricted notes appeared in the normal index")
        if report["details"]["broken_links"]:
            report["warnings"].append("Broken Obsidian links detected")
        if report["details"]["missing_sources"]:
            report["warnings"].append("Derived memories without traceable sources detected")
        if report["details"]["invalid_statuses"]:
            report["warnings"].append("Unknown lifecycle statuses detected")
        if report["details"]["duplicate_hashes"]:
            report["warnings"].append("Duplicate content hashes detected")

        return self._write(report)

    def _write(self, report):
        target = self.log_dir / "system_integrity_report.json"
        temporary = target.with_suffix(".json.tmp")
        temporary.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        temporary.replace(target)
        logger.info(
            "Integrity check: healthy=%s, entries=%d, warnings=%d",
            report["healthy"],
            report.get("counts", {}).get("index_entries", 0),
            len(report["warnings"]),
        )
        return report
