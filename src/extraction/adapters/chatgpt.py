from __future__ import annotations

import json
import re
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping

from ..base import ExtractionAdapter
from ..models import ExtractedDocument, ExtractionBatch, ExtractionRequest


class ChatGPTExportAdapter(ExtractionAdapter):
    name = "chatgpt_export"
    version = "1.0.0"
    source_types = ("chatgpt", "chatgpt_export")

    def can_handle(
        self,
        source_type: str,
        input_path: Path | None,
        payload: Mapping[str, Any],
    ) -> bool:
        if source_type not in self.source_types or not input_path:
            return False
        if input_path.is_dir():
            return any(input_path.glob("conversations*.json"))
        return input_path.suffix.lower() in {".zip", ".json"}

    def extract(self, request: ExtractionRequest) -> ExtractionBatch:
        if not request.input_path:
            raise ValueError("ChatGPT export path is required")
        conversations, source_files = self._load_export(request.input_path)
        project = request.options.get("project_id") or request.options.get("project") or []
        documents = []
        warnings = []
        for conversation in conversations:
            try:
                documents.append(self._conversation_document(conversation, source_files, project))
            except Exception as exc:
                conversation_id = conversation.get("id") or conversation.get("conversation_id") or "unknown"
                warnings.append(f"{conversation_id}: {exc}")
        return ExtractionBatch(
            documents=tuple(documents),
            summary={
                "conversations_found": len(conversations),
                "documents_created": len(documents),
                "source_files": source_files,
            },
            warnings=tuple(warnings),
        )

    def _load_export(self, path: Path) -> tuple[list[dict[str, Any]], list[str]]:
        loaded: list[dict[str, Any]] = []
        source_files: list[str] = []
        if path.is_dir():
            files = sorted(
                file_path
                for pattern in ("conversations*.json", "conversation*.json")
                for file_path in path.glob(pattern)
            )
            for file_path in self._dedupe_paths(files):
                loaded.extend(self._decode_conversation_payload(file_path.read_text(encoding="utf-8-sig")))
                source_files.append(file_path.name)
        elif path.suffix.lower() == ".zip":
            with zipfile.ZipFile(path) as archive:
                names = sorted(
                    name
                    for name in archive.namelist()
                    if not name.endswith("/")
                    and Path(name).name.lower().startswith("conversation")
                    and Path(name).suffix.lower() == ".json"
                )
                if not names:
                    raise ValueError("No conversations.json or numbered conversation JSON files found")
                for name in names:
                    raw = archive.read(name).decode("utf-8-sig")
                    loaded.extend(self._decode_conversation_payload(raw))
                    source_files.append(name)
        else:
            loaded.extend(self._decode_conversation_payload(path.read_text(encoding="utf-8-sig")))
            source_files.append(path.name)

        by_id: dict[str, dict[str, Any]] = {}
        for index, conversation in enumerate(loaded):
            if not isinstance(conversation, dict):
                continue
            conversation_id = str(
                conversation.get("id")
                or conversation.get("conversation_id")
                or f"unknown-{index}"
            )
            existing = by_id.get(conversation_id)
            if existing is None or self._timestamp(conversation.get("update_time")) >= self._timestamp(
                existing.get("update_time")
            ):
                by_id[conversation_id] = conversation
        return list(by_id.values()), source_files

    @staticmethod
    def _decode_conversation_payload(raw: str) -> list[dict[str, Any]]:
        data = json.loads(raw)
        if isinstance(data, list):
            return [item for item in data if isinstance(item, dict)]
        if isinstance(data, dict):
            for key in ("conversations", "items", "data"):
                value = data.get(key)
                if isinstance(value, list):
                    return [item for item in value if isinstance(item, dict)]
            if "mapping" in data or "conversation_id" in data or "id" in data:
                return [data]
        raise ValueError("Unsupported ChatGPT export JSON structure")

    def _conversation_document(
        self,
        conversation: dict[str, Any],
        source_files: list[str],
        project: Any,
    ) -> ExtractedDocument:
        conversation_id = str(
            conversation.get("id") or conversation.get("conversation_id") or ""
        ).strip()
        if not conversation_id:
            raise ValueError("conversation id is missing")
        title = str(conversation.get("title") or "未命名 ChatGPT 对话").strip()
        mapping = conversation.get("mapping") or {}
        if not isinstance(mapping, dict):
            mapping = {}
        current_node = str(conversation.get("current_node") or "")
        main_path = self._main_path(mapping, current_node)
        messages = []
        models = set()
        attachments = []
        for position, (node_id, node) in enumerate(mapping.items()):
            if not isinstance(node, dict):
                continue
            message = node.get("message")
            if not isinstance(message, dict):
                continue
            text = self._message_text(message.get("content"))
            if not text.strip():
                continue
            author = message.get("author") or {}
            role = str(author.get("role") or "unknown")
            name = str(author.get("name") or "")
            metadata = message.get("metadata") or {}
            model = str(
                metadata.get("model_slug")
                or metadata.get("default_model_slug")
                or metadata.get("model")
                or ""
            )
            if model:
                models.add(model)
            message_attachments = self._attachments(metadata)
            attachments.extend(message_attachments)
            messages.append(
                {
                    "node_id": str(node_id),
                    "parent": str(node.get("parent") or ""),
                    "role": role,
                    "name": name,
                    "text": text,
                    "created_at": self._iso(message.get("create_time")),
                    "model": model,
                    "is_branch": bool(main_path and str(node_id) not in main_path),
                    "position": position,
                    "attachments": message_attachments,
                }
            )
        messages.sort(
            key=lambda item: (
                self._timestamp(item["created_at"]),
                item["position"],
            )
        )
        branch_count = sum(1 for message in messages if message["is_branch"])
        created_at = self._iso(conversation.get("create_time"))
        updated_at = self._iso(conversation.get("update_time"))
        body = self._render_conversation(title, conversation_id, messages, attachments)
        stable_id = "LJ-CHATGPT-" + self._stable_token(conversation_id)
        return ExtractedDocument(
            stable_id=stable_id,
            title=title,
            body=body,
            source_type="chatgpt",
            destination="source_archive",
            external_id=conversation_id,
            created_at=created_at,
            updated_at=updated_at,
            metadata={
                "conversation_id": conversation_id,
                "current_node": current_node,
                "message_count": len(messages),
                "branch_message_count": branch_count,
                "models": sorted(models),
                "attachments": attachments,
                "source_export_files": source_files,
                "project": project,
                "tags": ["chatgpt", "conversation"],
                "status": "active",
            },
        )

    def _render_conversation(
        self,
        title: str,
        conversation_id: str,
        messages: list[dict[str, Any]],
        attachments: list[dict[str, Any]],
    ) -> str:
        lines = [
            f"# {title}",
            "",
            f"> ChatGPT conversation ID: `{conversation_id}`",
            "",
        ]
        for index, message in enumerate(messages, 1):
            role_label = {
                "user": "用户",
                "assistant": "ChatGPT",
                "system": "系统",
                "tool": "工具",
            }.get(message["role"], message["role"])
            suffix = " · 分支消息" if message["is_branch"] else ""
            model = f" · {message['model']}" if message["model"] else ""
            timestamp = f" · {message['created_at']}" if message["created_at"] else ""
            lines.extend(
                [
                    f"## {index}. {role_label}{timestamp}{model}{suffix}",
                    "",
                    message["text"].rstrip(),
                    "",
                ]
            )
            if message["attachments"]:
                lines.append("附件：")
                for item in message["attachments"]:
                    lines.append(f"- `{item.get('name') or item.get('id') or 'unknown'}`")
                lines.append("")
        if attachments:
            lines.extend(["## 对话附件索引", ""])
            seen = set()
            for item in attachments:
                key = json.dumps(item, ensure_ascii=False, sort_keys=True)
                if key in seen:
                    continue
                seen.add(key)
                lines.append("- " + ", ".join(f"{k}: {v}" for k, v in item.items() if v))
            lines.append("")
        return "\n".join(lines)

    @staticmethod
    def _message_text(content: Any) -> str:
        if not isinstance(content, dict):
            return ""
        parts = content.get("parts")
        if isinstance(parts, list):
            rendered = []
            for part in parts:
                text = ChatGPTExportAdapter._flatten_part(part)
                if text:
                    rendered.append(text)
            return "\n\n".join(rendered)
        for key in ("text", "result", "content"):
            value = content.get(key)
            if isinstance(value, str):
                return value
        return ""

    @staticmethod
    def _flatten_part(part: Any) -> str:
        if isinstance(part, str):
            return part
        if isinstance(part, dict):
            for key in ("text", "content", "result", "caption"):
                value = part.get(key)
                if isinstance(value, str):
                    return value
            if part.get("content_type") == "image_asset_pointer":
                pointer = part.get("asset_pointer") or part.get("pointer")
                return f"[图片附件: {pointer}]" if pointer else "[图片附件]"
            return json.dumps(part, ensure_ascii=False, sort_keys=True)
        if part is None:
            return ""
        return str(part)

    @staticmethod
    def _attachments(metadata: Any) -> list[dict[str, Any]]:
        if not isinstance(metadata, dict):
            return []
        candidates = []
        raw = metadata.get("attachments") or metadata.get("files") or []
        if isinstance(raw, dict):
            raw = [raw]
        if isinstance(raw, list):
            for item in raw:
                if isinstance(item, dict):
                    candidates.append(
                        {
                            "id": item.get("id")
                            or item.get("file_id")
                            or item.get("asset_pointer")
                            or "",
                            "name": item.get("name")
                            or item.get("file_name")
                            or item.get("filename")
                            or "",
                            "mime_type": item.get("mime_type") or "",
                            "size": item.get("size") or "",
                        }
                    )
                elif isinstance(item, str):
                    candidates.append({"id": item, "name": "", "mime_type": "", "size": ""})
        return candidates

    @staticmethod
    def _main_path(mapping: dict[str, Any], current_node: str) -> set[str]:
        result = set()
        node_id = current_node
        while node_id and node_id not in result:
            result.add(node_id)
            node = mapping.get(node_id)
            if not isinstance(node, dict):
                break
            node_id = str(node.get("parent") or "")
        return result

    @staticmethod
    def _iso(value: Any) -> str:
        if value in (None, ""):
            return ""
        if isinstance(value, (int, float)):
            try:
                return datetime.fromtimestamp(float(value), tz=timezone.utc).isoformat(timespec="seconds")
            except (ValueError, OSError, OverflowError):
                return ""
        text = str(value)
        try:
            return datetime.fromisoformat(text.replace("Z", "+00:00")).isoformat(timespec="seconds")
        except ValueError:
            return text

    @staticmethod
    def _timestamp(value: Any) -> float:
        if value in (None, ""):
            return 0.0
        if isinstance(value, (int, float)):
            return float(value)
        try:
            return datetime.fromisoformat(str(value).replace("Z", "+00:00")).timestamp()
        except ValueError:
            return 0.0

    @staticmethod
    def _stable_token(value: str) -> str:
        cleaned = re.sub(r"[^A-Za-z0-9_-]+", "-", value).strip("-")
        return cleaned[:80] or "UNKNOWN"

    @staticmethod
    def _dedupe_paths(paths: Iterable[Path]) -> list[Path]:
        result = []
        seen = set()
        for path in paths:
            resolved = path.resolve()
            if resolved not in seen:
                seen.add(resolved)
                result.append(path)
        return result
