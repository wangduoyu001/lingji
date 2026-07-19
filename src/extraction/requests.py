from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from src.obsidian.frontmatter import atomic_write, render_frontmatter, split_frontmatter


class ExtractionRequestInbox:
    """Process owner-created extraction request notes from Obsidian."""

    ALLOWED_TYPES = {"chatgpt_import", "web_capture", "media_extract", "skill_sync"}

    def __init__(self, layout, pipeline, skill_registry=None, state_db=None):
        self.layout = layout
        self.pipeline = pipeline
        self.skill_registry = skill_registry
        self.state_db = state_db
        self.queue_dir = layout.root / "00-System" / "Extraction" / "Requests"
        self.queue_dir.mkdir(parents=True, exist_ok=True)

    def process_pending(self, limit: int = 20) -> dict[str, Any]:
        summary = {"processed": 0, "succeeded": 0, "failed": 0, "results": []}
        for path in sorted(self.queue_dir.glob("*.md"))[: max(int(limit), 1)]:
            try:
                metadata, body = split_frontmatter(path.read_text(encoding="utf-8-sig"))
            except Exception as exc:
                summary["failed"] += 1
                summary["results"].append({"path": str(path), "error": str(exc)})
                continue
            if metadata.get("memory_type") != "extraction_request" or metadata.get("status") != "queued":
                continue
            summary["processed"] += 1
            try:
                self._set_status(path, metadata, body, "running", started_at=self._now())
                result = self._execute(metadata, body)
                self._set_status(
                    path,
                    metadata,
                    body,
                    "done",
                    result_json=json.dumps(result, ensure_ascii=False, default=str),
                    finished_at=self._now(),
                )
                summary["succeeded"] += 1
                summary["results"].append({"path": str(path), "result": result})
                self._event("extraction_request_completed", path.stem, result)
            except Exception as exc:
                self._set_status(
                    path,
                    metadata,
                    body,
                    "failed",
                    last_error=str(exc)[:2000],
                    finished_at=self._now(),
                )
                summary["failed"] += 1
                summary["results"].append({"path": str(path), "error": str(exc)})
                self._event("extraction_request_failed", path.stem, {"error": str(exc)})
        return summary

    def _execute(self, metadata: dict[str, Any], body: str) -> dict[str, Any]:
        request_type = str(metadata.get("request_type") or "")
        if request_type not in self.ALLOWED_TYPES:
            raise PermissionError(f"Unsupported extraction request: {request_type}")
        if request_type == "chatgpt_import":
            input_path = str(metadata.get("input_path") or "")
            if not input_path:
                raise ValueError("input_path is required")
            job = self.pipeline.enqueue(
                "chatgpt",
                input_path=input_path,
                options={
                    "project_id": metadata.get("project") or metadata.get("project_id") or [],
                    "privacy_scan": metadata.get("privacy_scan", True),
                },
                adapter_name="chatgpt_export",
                force=bool(metadata.get("force", False)),
            )
            return {"job": job}
        if request_type == "media_extract":
            input_path = str(metadata.get("input_path") or metadata.get("media_path") or "")
            if not input_path:
                raise ValueError("input_path is required")
            source_type = str(metadata.get("source_type") or metadata.get("media_type") or "media")
            options = {
                "project_id": metadata.get("project") or metadata.get("project_id") or [],
                "extract_audio": bool(metadata.get("extract_audio", False)),
                "extract_keyframes": bool(metadata.get("extract_keyframes", False)),
                "transcript_path": metadata.get("transcript_path") or "",
                "ocr_path": metadata.get("ocr_path") or "",
                "visual_notes_path": metadata.get("visual_notes_path") or "",
            }
            optional_overrides = {
                "keyframe_interval_seconds": metadata.get("keyframe_interval_seconds"),
                "max_keyframes": metadata.get("max_keyframes"),
                "keyframe_max_dimension": metadata.get("keyframe_max_dimension"),
                "ffmpeg_max_concurrency": metadata.get("ffmpeg_max_concurrency"),
                "ffmpeg_threads": metadata.get("ffmpeg_threads"),
                "max_input_bytes": metadata.get("max_input_bytes"),
                "max_duration_seconds": metadata.get("max_duration_seconds"),
                "probe_timeout_seconds": metadata.get("probe_timeout_seconds"),
                "ffmpeg_timeout_seconds": metadata.get("ffmpeg_timeout_seconds"),
            }
            options.update(
                {key: value for key, value in optional_overrides.items() if value not in (None, "")}
            )
            priority_value = metadata.get("priority")
            job = self.pipeline.enqueue(
                source_type,
                input_path=input_path,
                payload={
                    "title": metadata.get("title") or Path(input_path).stem,
                    "transcript": metadata.get("transcript") or "",
                    "ocr_text": metadata.get("ocr_text") or "",
                    "visual_notes": metadata.get("visual_notes") or "",
                },
                options=options,
                adapter_name="media_local",
                priority=int(priority_value) if priority_value not in (None, "") else None,
                force=bool(metadata.get("force", False)),
            )
            return {"job": job}
        if request_type == "skill_sync":
            if not self.skill_registry:
                raise RuntimeError("Skill registry is not configured")
            input_path = str(metadata.get("input_path") or "")
            if not input_path:
                raise ValueError("input_path is required")
            return self.skill_registry.sync_directory(input_path)

        source_type = str(metadata.get("source_type") or metadata.get("platform") or "web")
        payload = {
            "url": metadata.get("source_url") or metadata.get("url") or "",
            "title": metadata.get("title") or path_title(metadata),
            "author": metadata.get("author") or "",
            "account_name": metadata.get("account_name") or "",
            "description": metadata.get("description") or "",
            "published_at": metadata.get("published_at") or "",
            "duration_seconds": metadata.get("duration_seconds") or "",
            "cover_url": metadata.get("cover_url") or "",
            "media_url": metadata.get("media_url") or "",
            "text": metadata.get("captured_text") or body,
            "transcript": metadata.get("transcript") or "",
            "ocr_text": metadata.get("ocr_text") or "",
            "platform": metadata.get("platform") or source_type,
            "capture_method": "obsidian_request",
        }
        return self.pipeline.execute(
            source_type,
            payload=payload,
            options={"project_id": metadata.get("project") or metadata.get("project_id") or []},
            adapter_name="web_capture",
        )

    @staticmethod
    def _set_status(
        path: Path,
        metadata: dict[str, Any],
        body: str,
        status: str,
        **updates: Any,
    ) -> None:
        current = dict(metadata)
        current["status"] = status
        current["updated_at"] = datetime.now().isoformat(timespec="seconds")
        current.update(updates)
        atomic_write(path, render_frontmatter(current, body))

    def status(self) -> dict[str, int]:
        result = {"queued": 0, "running": 0, "done": 0, "failed": 0}
        for path in self.queue_dir.glob("*.md"):
            try:
                metadata, _ = split_frontmatter(path.read_text(encoding="utf-8-sig"))
                status = str(metadata.get("status") or "")
                if status in result:
                    result[status] += 1
            except Exception:
                result["failed"] += 1
        return result

    @staticmethod
    def _now() -> str:
        return datetime.now().isoformat(timespec="seconds")

    def _event(self, event_type: str, entity_id: str, payload: Any) -> None:
        if self.state_db:
            self.state_db.append_event(event_type, "extraction_request", entity_id, payload)


def path_title(metadata: dict[str, Any]) -> str:
    return str(metadata.get("name") or "网页采集请求")
