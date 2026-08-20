from __future__ import annotations

import json
import logging
import threading
from datetime import datetime, timezone
from pathlib import Path, PureWindowsPath
from typing import Any, Mapping
from uuid import uuid4

from src.capture.models import CaptureEnvelope, CaptureStatus
from src.capture.policy import CaptureMode, CapturePolicy
from src.capture.service import CaptureService
from src.extraction.queue import SQLiteExtractionQueue

from .runtime_settings import RuntimeSettingsStore

logger = logging.getLogger("lingji.control.capture")

CAPTURE_PAUSED = "CAPTURE_PAUSED"
CAPTURE_FILE_NOT_FOUND = "CAPTURE_FILE_NOT_FOUND"
CAPTURE_FILE_TOO_LARGE = "CAPTURE_FILE_TOO_LARGE"
CAPTURE_JOB_NOT_FOUND = "CAPTURE_JOB_NOT_FOUND"
CAPTURE_JOB_RUNNING = "CAPTURE_JOB_RUNNING"
CAPTURE_JOB_NOT_RETRYABLE = "CAPTURE_JOB_NOT_RETRYABLE"
CAPTURE_JOB_NOT_CANCELLABLE = "CAPTURE_JOB_NOT_CANCELLABLE"
CAPTURE_SERVICE_UNAVAILABLE = "CAPTURE_SERVICE_UNAVAILABLE"
CAPTURE_INVALID_INPUT = "CAPTURE_INVALID_INPUT"

_FAILED_MESSAGE = "Capture processing failed; see local logs"
_MODE_LABELS = {"normal": "NORMAL", "low_power": "LOW_POWER", "paused": "PAUSED"}


class CaptureControlError(RuntimeError):
    def __init__(self, code: str, message: str, *, status_code: int):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


class CaptureRuntimeSettingsStore(RuntimeSettingsStore):
    """Runtime settings with the persisted P2-05 capture mode."""

    def definitions(self) -> dict[str, dict[str, Any]]:
        definitions = dict(super().definitions())
        definitions["capture_mode"] = self._choice(
            "capture",
            "手动采集模式",
            "normal 正常，low_power 低功耗，paused 暂停接收新任务。",
            "low_power",
            ["normal", "low_power", "paused"],
        )
        return definitions


class _PipelineProxy:
    def __init__(self, pipeline: Any):
        self.pipeline = pipeline
        self.adapter_name: str | None = None
        self.option_overrides: dict[str, Any] = {}
        self.last_outcome: dict[str, Any] = {}

    def enqueue(self, source_type: str, **kwargs: Any) -> dict[str, Any]:
        options = dict(kwargs.get("options") or {})
        options.update(self.option_overrides)
        kwargs["options"] = options
        if self.adapter_name:
            kwargs["adapter_name"] = self.adapter_name
        self.last_outcome = dict(self.pipeline.enqueue(source_type, **kwargs))
        return self.last_outcome

    def execute(self, source_type: str, **kwargs: Any) -> dict[str, Any]:
        return self.pipeline.execute(source_type, **kwargs)


class CaptureControlService:
    """Long-lived CaptureService orchestration and sanitized queue projection."""

    def __init__(
        self,
        settings: Any,
        *,
        pipeline: Any,
        queue: SQLiteExtractionQueue | None = None,
        runtime_settings: CaptureRuntimeSettingsStore | None = None,
        state_db: Any | None = None,
        capture_service: CaptureService | None = None,
    ):
        self.settings = settings
        self.pipeline = pipeline
        self.queue = queue or getattr(pipeline, "queue", None)
        if self.queue is None:
            raise ValueError("Capture control requires the existing extraction queue")
        self.state_db = state_db
        self.runtime_settings = runtime_settings or CaptureRuntimeSettingsStore(
            settings, state_db=state_db
        )
        self._proxy = _PipelineProxy(pipeline)
        mode = self._mode()
        self.capture_service = capture_service or CaptureService(
            self._proxy, policy=CapturePolicy.for_mode(mode)
        )
        self._lock = threading.RLock()
        self._job_by_key: dict[str, str] = {}
        self._apply_mode(mode)

    def submit_text(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        text = str(payload.get("text") or "").strip()
        if not text:
            self._invalid("Capture text is required")
        return self._submit(
            self._envelope(
                payload,
                source_type=str(payload.get("source_type") or "text"),
                capture_method=str(payload.get("capture_method") or "manual_text"),
                text=text,
            ),
            adapter_name=self._adapter(payload),
        )

    def submit_web(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        url = str(payload.get("url") or payload.get("source_url") or "").strip()
        text = str(payload.get("text") or payload.get("selected_text") or "")
        html = str(payload.get("html") or "")
        if not any((url, text.strip(), html.strip())):
            self._invalid("Capture URL, text or HTML is required")
        return self._submit(
            self._envelope(
                payload,
                source_type=str(payload.get("source_type") or "web"),
                capture_method=str(payload.get("capture_method") or "manual_web"),
                url=url,
                text=text,
                html=html,
                author=str(payload.get("author") or ""),
                account_name=str(payload.get("account_name") or ""),
                published_at=str(payload.get("published_at") or ""),
                platform=str(payload.get("platform") or ""),
                description=str(payload.get("description") or ""),
                external_id=str(payload.get("external_id") or ""),
            ),
            adapter_name=self._adapter(payload),
        )

    def submit_file(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        source_type = str(payload.get("source_type") or "web")
        adapter_name = str(payload.get("adapter_name") or "")
        capture_method = str(payload.get("capture_method") or "")
        if not capture_method:
            if source_type == "chatgpt_export":
                capture_method = "manual_chatgpt_export"
            elif source_type == "codex_report" or adapter_name == "codex_work_report":
                capture_method = "manual_codex_report"
            else:
                capture_method = "manual_file"
        return self._submit_path(payload, source_type, capture_method=capture_method)

    def submit_media(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        return self._submit_path(
            payload,
            "media",
            capture_method=str(payload.get("capture_method") or "manual_media"),
            options={
                "allow_ocr": bool(payload.get("allow_ocr", False)),
                "allow_video_transcription": bool(payload.get("allow_transcription", False)),
                "extract_keyframes": bool(payload.get("extract_keyframes", False)),
                "extract_audio": bool(payload.get("extract_audio", False)),
            },
        )

    def submit_share(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        if str(payload.get("input_path") or "").strip():
            source_type = str(payload.get("source_type") or payload.get("platform") or "web")
            return self.submit_media(payload) if source_type in {"media", "video", "audio"} else self.submit_file(payload)
        if any(str(payload.get(key) or "").strip() for key in ("url", "source_url", "html", "platform")):
            return self.submit_web(payload)
        forwarded = dict(payload)
        forwarded["text"] = payload.get("text") or payload.get("selected_text") or ""
        return self.submit_text(forwarded)

    def status(self) -> dict[str, Any]:
        mode = self._mode().value
        service_status = self.capture_service.status()
        queue_stats = self.queue.stats()
        return {
            "capture_mode": mode,
            "mode": mode,
            "mode_label": _MODE_LABELS[mode],
            "paused": mode == "paused",
            "worker_state": "available",
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "submitted": int(service_status.get("submitted") or 0),
            "queue": queue_stats,
            **{
                status: int(queue_stats.get(status, 0))
                for status in ("queued", "running", "retrying", "completed", "failed", "cancelled")
            },
        }

    def capabilities(self) -> dict[str, Any]:
        mode = self._mode().value
        policy = self.capture_service.policy
        heavy_allowed = policy.permits_heavy_media()
        return {
            "capture_mode": mode,
            "state": "paused" if mode == "paused" else "healthy",
            "inputs": {name: {"enabled": True, "enqueue_only": True} for name in ("text", "web", "file", "media")},
            "operations": {
                "cancel": ["queued", "retrying"],
                "retry": ["failed", "cancelled"],
                "running_termination": False,
            },
            "file_modes": ["web_snapshot", "chatgpt_export", "codex_report"],
            "media": {
                "ocr": bool(policy.allow_ocr),
                "transcription": bool(policy.allow_video_transcription),
                "keyframes": heavy_allowed,
                "extract_audio": heavy_allowed,
                "reasons": {} if heavy_allowed else {"low_power": "当前采集策略禁止重媒体处理"},
            },
        }

    def list_jobs(
        self,
        *,
        status: str | None = None,
        source_type: str | None = None,
        q: str | None = None,
        limit: int = 30,
        offset: int = 0,
    ) -> dict[str, Any]:
        rows = self.queue.list_page(status=status, source_type=source_type, q=q, limit=limit, offset=offset)
        total = self.queue.count(status=status, source_type=source_type, q=q)
        limit = max(min(int(limit), 200), 1)
        offset = max(int(offset), 0)
        return {
            "items": [self.job_dto(row) for row in rows],
            "pagination": {"limit": limit, "offset": offset, "total": total, "has_more": offset + len(rows) < total},
            "stats": self.queue.stats(),
        }

    def get_job(self, job_id: str) -> dict[str, Any]:
        try:
            return self.job_dto(self.queue.get(job_id))
        except LookupError as exc:
            raise CaptureControlError(CAPTURE_JOB_NOT_FOUND, "Capture job not found", status_code=404) from exc

    def cancel_job(self, job_id: str) -> dict[str, Any]:
        current = self._get_for_operation(job_id)
        status = str(current.get("status") or "")
        if status == "running":
            raise CaptureControlError(CAPTURE_JOB_RUNNING, "Running capture jobs cannot be cancelled in this version", status_code=409)
        if status not in {"queued", "retrying"}:
            raise CaptureControlError(CAPTURE_JOB_NOT_CANCELLABLE, "Capture job is not cancellable", status_code=409)
        row = self.queue.cancel(job_id)
        self._audit("capture_job_cancelled", job_id, {"job_id": job_id})
        return self.job_dto(row)

    def retry_job(self, job_id: str) -> dict[str, Any]:
        current = self._get_for_operation(job_id)
        status = str(current.get("status") or "")
        if status == "running":
            raise CaptureControlError(CAPTURE_JOB_RUNNING, "Running capture jobs cannot be retried", status_code=409)
        if status not in {"failed", "cancelled"}:
            raise CaptureControlError(CAPTURE_JOB_NOT_RETRYABLE, "Capture job is not retryable", status_code=409)
        row = self.queue.retry(job_id)
        self._audit("capture_job_retried", job_id, {"job_id": job_id})
        return self.job_dto(row)

    def pause(self) -> dict[str, Any]:
        self.runtime_settings.update({"capture_mode": "paused"}, actor="local_control")
        self._apply_mode(CaptureMode.PAUSED)
        self._audit("capture_paused", "capture", {"capture_mode": "paused"})
        return self.status()

    def resume(self) -> dict[str, Any]:
        self.runtime_settings.update({"capture_mode": "low_power"}, actor="local_control")
        self._apply_mode(CaptureMode.LOW_POWER)
        self._audit("capture_resumed", "capture", {"capture_mode": "low_power"})
        return self.status()

    def job_dto(self, row: Mapping[str, Any]) -> dict[str, Any]:
        payload = row.get("payload") if isinstance(row.get("payload"), Mapping) else {}
        result = row.get("result") if isinstance(row.get("result"), Mapping) else {}
        status = str(row.get("status") or "").lower()
        refs = self._result_refs(result)
        outcome = self._work_outcome(status, result)
        return {
            "job_id": str(row.get("job_id") or ""),
            "work_item_id": str(row.get("job_id") or ""),
            "capture_id": str(payload.get("capture_id") or "") or None,
            "title": self._job_title(payload, row),
            "capture_method": str(payload.get("capture_method") or "") or None,
            "source_type": str(row.get("source_type") or ""),
            "adapter_name": str(row.get("adapter_name") or "") or None,
            "status": status,
            "outcome_state": outcome["state"],
            "outcome_summary": outcome["summary"],
            "next_actor": outcome["next_actor"],
            "next_action": outcome["next_action"],
            "priority": int(row.get("priority") or 0),
            "attempts": int(row.get("attempts") or 0),
            "max_attempts": int(row.get("max_attempts") or 0),
            "progress_current": int(row.get("progress_current") or 0),
            "progress_total": int(row.get("progress_total") or 0),
            "created_at": row.get("created_at"),
            "updated_at": row.get("updated_at"),
            "completed_at": row.get("completed_at"),
            "error_code": "CAPTURE_JOB_FAILED" if status == "failed" else None,
            "error_message": _FAILED_MESSAGE if status == "failed" else None,
            "result_summary": self._result_summary(result),
            "result_refs": refs,
            "result_object_ids": self._result_object_ids(result),
            "file_name": self._basename(str(row.get("input_path") or "")),
        }

    def _submit_path(
        self,
        payload: Mapping[str, Any],
        source_type: str,
        *,
        capture_method: str = "manual_file",
        options: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        raw_path = str(payload.get("input_path") or "").strip()
        if not raw_path:
            self._invalid("Capture input path is required")
        path = Path(raw_path).expanduser()
        return self._submit(
            self._envelope(payload, source_type=source_type, capture_method=capture_method, title=str(payload.get("title") or path.name), input_path=path),
            adapter_name=self._adapter(payload),
            option_overrides=options,
        )

    def _submit(
        self,
        envelope: CaptureEnvelope,
        *,
        adapter_name: str | None = None,
        option_overrides: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        mode = self._mode()
        self._apply_mode(mode)
        if mode is CaptureMode.PAUSED:
            raise CaptureControlError(CAPTURE_PAUSED, "Capture is paused", status_code=409)
        with self._lock:
            self._proxy.adapter_name = adapter_name
            self._proxy.option_overrides = dict(option_overrides or {})
            self._proxy.last_outcome = {}
            try:
                result = self.capture_service.submit(envelope)
            except FileNotFoundError as exc:
                logger.info("Capture file not found", exc_info=True)
                raise CaptureControlError(CAPTURE_FILE_NOT_FOUND, "Capture file not found", status_code=404) from exc
            except ValueError as exc:
                logger.info("Capture input rejected", exc_info=True)
                if envelope.input_path and envelope.input_path.exists() and envelope.input_path.stat().st_size > self.capture_service.policy.max_file_bytes:
                    raise CaptureControlError(CAPTURE_FILE_TOO_LARGE, "Capture file exceeds the configured size limit", status_code=422) from exc
                raise CaptureControlError(CAPTURE_INVALID_INPUT, "Capture input is invalid", status_code=422) from exc
            except Exception as exc:
                logger.exception("Capture service submission failed")
                raise CaptureControlError(CAPTURE_SERVICE_UNAVAILABLE, "Capture service unavailable; see local logs", status_code=503) from exc
            finally:
                self._proxy.adapter_name = None
                self._proxy.option_overrides = {}

        outcome = self._proxy.last_outcome
        job_id = str(result.extraction_job_id or outcome.get("job_id") or "")
        duplicate = (
            result.status is CaptureStatus.DUPLICATE
            or bool(outcome.get("duplicate"))
            or bool(outcome.get("existing_job"))
        )
        if result.deduplication_key and job_id:
            self._job_by_key[result.deduplication_key] = job_id
        if not job_id and result.deduplication_key:
            job_id = self._job_by_key.get(result.deduplication_key, "")
        canonical_capture_id = self._job_capture_id(job_id) if duplicate and job_id else ""
        canonical_capture_id = canonical_capture_id or result.capture_id
        response = {
            "capture_id": canonical_capture_id,
            "status": "duplicate" if duplicate else result.status.value,
            "job_id": job_id or None,
            "duplicate": duplicate,
            "reason": result.reason or ("Existing capture job reused" if duplicate else ""),
        }
        self._audit(
            "capture_duplicate" if duplicate else "capture_submitted",
            canonical_capture_id,
            {
                "capture_id": canonical_capture_id,
                "request_capture_id": result.capture_id,
                "job_id": job_id or None,
                "source_type": envelope.source_type,
                "duplicate": duplicate,
            },
        )
        return response

    def _envelope(self, payload: Mapping[str, Any], *, source_type: str, capture_method: str = "local_control_share", **content: Any) -> CaptureEnvelope:
        return CaptureEnvelope(
            capture_id=str(payload.get("capture_id") or f"LJ-CAP-{uuid4().hex[:16].upper()}"),
            source_type=source_type,
            capture_method=capture_method,
            process_later=True,
            project_ids=self._items(payload.get("project_ids")),
            tags=self._items(payload.get("tags")),
            privacy=str(payload.get("privacy") or "private"),
            priority=int(payload.get("priority") or 100),
            metadata=dict(payload.get("metadata") or {}) if isinstance(payload.get("metadata"), Mapping) else {},
            **content,
        )

    def _get_for_operation(self, job_id: str) -> dict[str, Any]:
        try:
            return self.queue.get(job_id)
        except LookupError as exc:
            raise CaptureControlError(CAPTURE_JOB_NOT_FOUND, "Capture job not found", status_code=404) from exc

    def _mode(self) -> CaptureMode:
        value = str(self.runtime_settings.snapshot().get("values", {}).get("capture_mode", "low_power"))
        return CaptureMode(value)

    def _apply_mode(self, mode: CaptureMode) -> None:
        self.capture_service.policy = CapturePolicy.for_mode(mode)
        self.capture_service.pause() if mode is CaptureMode.PAUSED else self.capture_service.resume()

    def _audit(self, event_type: str, entity_id: str, payload: Mapping[str, Any]) -> None:
        if self.state_db is None:
            return
        try:
            self.state_db.append_event(event_type, "capture", entity_id, dict(payload))
        except Exception:
            logger.exception("Capture audit event failed: %s", event_type)

    def _job_capture_id(self, job_id: str) -> str:
        if not job_id:
            return ""
        try:
            row = self.queue.get(job_id)
        except LookupError:
            return ""
        payload = row.get("payload") if isinstance(row.get("payload"), Mapping) else {}
        return str(payload.get("capture_id") or "")

    @staticmethod
    def _invalid(message: str) -> None:
        raise CaptureControlError(CAPTURE_INVALID_INPUT, message, status_code=422)

    @staticmethod
    def _adapter(payload: Mapping[str, Any]) -> str | None:
        value = str(payload.get("adapter_name") or "").strip()
        return value or None

    @staticmethod
    def _items(value: Any) -> tuple[str, ...]:
        if value is None:
            return ()
        if isinstance(value, str):
            return tuple(item.strip() for item in value.split(",") if item.strip())
        return tuple(str(item) for item in value if str(item).strip())

    @staticmethod
    def _basename(value: str) -> str | None:
        if not value:
            return None
        windows_name = PureWindowsPath(value).name
        posix_name = Path(value).name
        return windows_name if "\\" in value else posix_name

    @classmethod
    def _job_title(cls, payload: Mapping[str, Any], row: Mapping[str, Any]) -> str:
        title = str(payload.get("title") or "").strip()
        if title:
            return title[:180]
        filename = cls._basename(str(row.get("input_path") or ""))
        if filename:
            return filename[:180]
        source_type = str(row.get("source_type") or "资料").strip()
        return source_type[:180] or "资料"

    @staticmethod
    def _work_outcome(status: str, result: Mapping[str, Any]) -> dict[str, str]:
        created = len(result.get("created") or []) if isinstance(result.get("created"), list) else 0
        updated = len(result.get("updated") or []) if isinstance(result.get("updated"), list) else 0
        skipped = len(result.get("skipped") or []) if isinstance(result.get("skipped"), list) else 0
        if status == "queued":
            return {"state": "pending", "summary": "已进入处理队列，尚未产生执行结果。", "next_actor": "system", "next_action": "开始解析和整理这项工作。"}
        if status in {"leased", "running"}:
            return {"state": "running", "summary": "正在执行解析和整理。", "next_actor": "system", "next_action": "继续当前执行直到产生真实结果。"}
        if status == "retrying":
            return {"state": "retrying", "summary": "上一次执行未完成，正在按既定策略自动重试。", "next_actor": "system", "next_action": "继续重试，直到成功或达到重试上限。"}
        if status == "failed":
            return {"state": "failed", "summary": "自动执行和既定重试已结束，失败证据已保留。", "next_actor": "none", "next_action": "没有自动生成主人待办；需要排查时可查看高级任务记录并手动重试。"}
        if status == "cancelled":
            return {"state": "cancelled", "summary": "这项工作已停止，原始资料和历史记录未被删除。", "next_actor": "none", "next_action": "除非重新提交，否则不会继续执行。"}
        if status == "completed":
            parts = []
            if created:
                parts.append(f"新增 {created} 条")
            if updated:
                parts.append(f"更新 {updated} 条")
            if skipped:
                parts.append(f"去重跳过 {skipped} 条")
            detail = "，".join(parts) if parts else "任务结果已持久化"
            if result.get("indexed") is True:
                detail += "，索引同步完成"
                next_action = "工作已完成；可从结果对象或记忆页面继续查看。"
            elif result.get("indexed") is False:
                detail += "，但索引同步未完成"
                next_action = "正文结果已保留；当前不宣称索引会自动恢复，可在高级状态中检查。"
            else:
                next_action = "工作已完成；是否形成可取回记忆以真实结果对象为准。"
            return {"state": "succeeded", "summary": detail + "。", "next_actor": "none", "next_action": next_action}
        return {"state": "unknown", "summary": "已记录这项工作，但没有足够事实解释当前结果。", "next_actor": "none", "next_action": "等待真实状态更新，不推测后续动作。"}

    @staticmethod
    def _result_summary(result: Mapping[str, Any]) -> str | None:
        allowed = ("execution_id", "source_type", "adapter", "adapter_version", "indexed", "document_count", "memory_count")
        summary = {
            key: result[key]
            for key in allowed
            if key in result and isinstance(result[key], (str, int, float, bool, type(None)))
        }
        return json.dumps(summary, ensure_ascii=False, sort_keys=True) if summary else None

    @staticmethod
    def _result_refs(result: Mapping[str, Any]) -> dict[str, str] | None:
        refs: dict[str, str] = {}
        structured = result.get("structured_read_model")
        containers = (result, structured if isinstance(structured, Mapping) else {})
        for container in containers:
            for key in ("memory_id", "source_id", "conversation_id", "message_id"):
                value = container.get(key)
                if isinstance(value, str) and value:
                    refs[key] = value
        return refs or None

    @staticmethod
    def _result_object_ids(result: Mapping[str, Any]) -> list[str]:
        output: list[str] = []
        for bucket in ("created", "updated", "skipped"):
            items = result.get(bucket)
            if not isinstance(items, list):
                continue
            for item in items:
                if not isinstance(item, Mapping):
                    continue
                value = str(item.get("id") or "").strip()
                if value and value not in output:
                    output.append(value)
        return output[:100]
