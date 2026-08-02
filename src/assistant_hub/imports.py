from __future__ import annotations

import hashlib
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping

_MAX_CANDIDATES = 20
_MAX_SCAN_DEPTH = 2


@dataclass(frozen=True)
class ImportCandidate:
    candidate_id: str
    source_id: str
    source_type: str
    adapter_name: str
    display_name: str
    size_bytes: int
    modified_at: str | None


class AssistantImportPlanner:
    """Build one owner-facing import plan without reading source bodies.

    Only a narrow allowlist of likely export locations, file names and suffixes is
    inspected. Candidate authorization resolves the id against a fresh scan, so
    callers never submit an arbitrary hidden path through this API.
    """

    def __init__(
        self,
        *,
        storage_path: Path | str,
        home: Path | str | None = None,
        env: Mapping[str, str] | None = None,
    ) -> None:
        self.storage_path = Path(storage_path).expanduser().resolve(strict=False)
        self.home = Path(home or Path.home()).expanduser().resolve(strict=False)
        self.env = dict(env or os.environ)

    def plan(self) -> dict[str, Any]:
        candidates = self._scan_candidates()
        grouped = {
            source_id: [asdict(item) for item in candidates if item.source_id == source_id]
            for source_id in ("chatgpt", "codex")
        }
        return {
            "schema_version": 1,
            "scanned_at": datetime.now(timezone.utc).isoformat(),
            "safety": {
                "metadata_only": True,
                "content_read": False,
                "arbitrary_path_submission": False,
                "owner_authorization_required": True,
                "automatic_core_memory_write": False,
            },
            "summary": {
                "candidate_count": len(candidates),
                "automatic_ready": sum(1 for values in grouped.values() if values),
                "guided_sources": sum(1 for values in grouped.values() if not values),
            },
            "sources": [
                self._source(
                    source_id="chatgpt",
                    label="ChatGPT 历史",
                    candidates=grouped["chatgpt"],
                    supported=True,
                    primary_action=(
                        "授权最近导出包并开始导入"
                        if grouped["chatgpt"]
                        else "选择官方导出包并立即导入"
                    ),
                    guide=(
                        "在 ChatGPT 设置的“数据控制”中导出数据。下载完成后回到这里，"
                        "点击一次按钮选择 ZIP；选择后灵机会立即入队，不再要求填写路径或再次提交。"
                    ),
                ),
                self._source(
                    source_id="codex",
                    label="Codex 工作记录",
                    candidates=grouped["codex"],
                    supported=True,
                    primary_action=(
                        "授权最近工作报告并开始导入"
                        if grouped["codex"]
                        else "选择 Codex 工作报告并立即导入"
                    ),
                    guide=(
                        "当前正式适配器接收结构化 Codex Work Report JSON。选择文件后立即入队；"
                        "原始 Session/JSONL 仍不会被悄悄读取。"
                    ),
                ),
                self._source(
                    source_id="claude_code",
                    label="Claude Code 历史",
                    candidates=[],
                    supported=False,
                    primary_action="等待正式适配器",
                    guide="当前只检测安装与文件数量元数据，不读取正文，也不展示无效的导入按钮。",
                ),
                self._source(
                    source_id="workbuddy",
                    label="WorkBuddy 历史",
                    candidates=[],
                    supported=False,
                    primary_action="等待官方导出能力",
                    guide="没有稳定官方导出目录时，灵机不会猜数据库位置或要求主人逐个找路径。",
                ),
            ],
        }

    def resolve_authorized_candidate(self, candidate_id: str) -> dict[str, str]:
        selected = str(candidate_id or "").strip().lower()
        if not selected:
            raise ValueError("candidate_id is required")
        for candidate, path in self._scan_candidate_paths():
            if candidate.candidate_id == selected:
                return {
                    "input_path": str(path),
                    "source_id": candidate.source_id,
                    "source_type": candidate.source_type,
                    "adapter_name": candidate.adapter_name,
                    "display_name": candidate.display_name,
                }
        raise ValueError("Import candidate is no longer available; refresh the import plan")

    @staticmethod
    def expected_confirmation(candidate_id: str) -> str:
        return f"AUTHORIZE_ASSISTANT_IMPORT_{str(candidate_id or '').strip().upper()}"

    @staticmethod
    def _source(
        *,
        source_id: str,
        label: str,
        candidates: list[dict[str, Any]],
        supported: bool,
        primary_action: str,
        guide: str,
    ) -> dict[str, Any]:
        return {
            "id": source_id,
            "label": label,
            "state": (
                "candidate_ready"
                if candidates
                else "guided_action_required"
                if supported
                else "not_supported"
            ),
            "supported": supported,
            "automatic_candidate_available": bool(candidates),
            "owner_action_count": 1 if supported else 0,
            "primary_action": primary_action,
            "guide": guide,
            "candidates": candidates,
        }

    def _scan_candidates(self) -> list[ImportCandidate]:
        return [candidate for candidate, _ in self._scan_candidate_paths()]

    def _scan_candidate_paths(self) -> list[tuple[ImportCandidate, Path]]:
        result: list[tuple[ImportCandidate, Path]] = []
        seen: set[str] = set()
        for root in self._candidate_roots():
            for path in self._iter_files(root):
                kind = self._classify(path)
                if kind is None:
                    continue
                try:
                    normalized = path.resolve(strict=True)
                    stat = normalized.stat()
                except OSError:
                    continue
                key = str(normalized).casefold()
                if key in seen:
                    continue
                seen.add(key)
                source_id, source_type, adapter_name = kind
                candidate = ImportCandidate(
                    candidate_id=self._candidate_id(source_id, normalized),
                    source_id=source_id,
                    source_type=source_type,
                    adapter_name=adapter_name,
                    display_name=normalized.name,
                    size_bytes=int(stat.st_size),
                    modified_at=datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
                )
                result.append((candidate, normalized))
                if len(result) >= _MAX_CANDIDATES:
                    break
            if len(result) >= _MAX_CANDIDATES:
                break
        result.sort(
            key=lambda item: item[0].modified_at or "",
            reverse=True,
        )
        return result

    def _candidate_roots(self) -> list[Path]:
        roots = [
            self.home / "Downloads",
            self.home / "Desktop",
            self.storage_path / "assistant_hub" / "import_inbox",
        ]
        user_profile = str(self.env.get("USERPROFILE") or "").strip()
        if user_profile:
            roots.extend([Path(user_profile) / "Downloads", Path(user_profile) / "Desktop"])
        result: list[Path] = []
        seen: set[str] = set()
        for root in roots:
            try:
                normalized = root.expanduser().resolve(strict=False)
            except OSError:
                continue
            key = str(normalized).casefold()
            if key in seen or not normalized.is_dir() or normalized.is_symlink():
                continue
            seen.add(key)
            result.append(normalized)
        return result

    @staticmethod
    def _iter_files(root: Path) -> Iterable[Path]:
        root_parts = len(root.parts)
        for current, directories, files in os.walk(root, followlinks=False):
            current_path = Path(current)
            depth = len(current_path.parts) - root_parts
            directories[:] = [
                name
                for name in directories
                if depth < _MAX_SCAN_DEPTH and not (current_path / name).is_symlink()
            ]
            for name in files:
                path = current_path / name
                if not path.is_symlink():
                    yield path

    @staticmethod
    def _classify(path: Path) -> tuple[str, str, str] | None:
        name = path.name.casefold()
        suffix = path.suffix.casefold()
        if suffix in {".zip", ".json"} and (
            "chatgpt" in name
            or name == "conversations.json"
            or ("openai" in name and "export" in name)
        ):
            return "chatgpt", "chatgpt_export", "chatgpt_export"
        if suffix == ".json" and "codex" in name and (
            "report" in name or "work" in name
        ):
            return "codex", "codex_report", "codex_work_report"
        return None

    @staticmethod
    def _candidate_id(source_id: str, path: Path) -> str:
        value = f"{source_id}:{str(path).casefold()}".encode("utf-8", errors="surrogatepass")
        return hashlib.sha256(value).hexdigest()[:24]
