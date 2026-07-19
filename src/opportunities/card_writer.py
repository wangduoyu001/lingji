from __future__ import annotations

import hashlib
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from src.obsidian.frontmatter import atomic_write, render_frontmatter


class OpportunityCardWriter:
    """Write traceable opportunity cards with stable IDs and filenames."""

    def __init__(self, output_dir: Path | str, vault_root: Path | str):
        self.output_dir = Path(output_dir)
        self.vault_root = Path(vault_root)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def write(
        self,
        source_path: Path | str,
        source_id: str,
        source_hash: str,
        analysis: dict[str, Any],
        model: str = "",
        prompt_version: str = "opportunity-v1",
    ) -> dict[str, Any]:
        source = Path(source_path)
        stable_key = hashlib.sha256(source_id.encode("utf-8")).hexdigest()[:12]
        opportunity_id = f"LJ-OPP-{stable_key.upper()}"
        title = str(analysis.get("title") or "未命名机会").strip()
        filename = f"opp_{stable_key}_{self._slug(title)}.md"
        target = self.output_dir / filename
        now = datetime.now().isoformat(timespec="seconds")

        try:
            relative_source = source.resolve(strict=False).relative_to(
                self.vault_root.resolve(strict=False)
            ).as_posix()
        except ValueError:
            relative_source = str(source)

        score = self._score(analysis)
        metadata = {
            "schema_version": 1,
            "id": opportunity_id,
            "title": title,
            "memory_type": "opportunity",
            "status": "needs_review",
            "review_status": "needs_review",
            "source_type": "derived_opportunity",
            "source_id": source_id,
            "source_path": relative_source,
            "source_content_hash": source_hash,
            "generated_by": "lingji",
            "generated_at": now,
            "updated_at": now,
            "model": model,
            "prompt_version": prompt_version,
            "verification_status": "unverified",
            "score": score,
            "speed": str(analysis.get("speed") or "mid"),
            "monetization": str(analysis.get("direction") or "服务"),
            "difficulty": self._integer(analysis.get("difficulty"), 3),
            "confidence": score,
            "privacy": "private",
            "tags": ["signal/opportunity", "attention/review"],
            "sources": [f"[[{relative_source[:-3] if relative_source.endswith('.md') else relative_source}]]"],
        }
        body = self._body(title, analysis, score)
        atomic_write(target, render_frontmatter(metadata, body))
        return {
            "file": filename,
            "path": str(target),
            "id": opportunity_id,
            "title": title,
            "score": score,
            "source_id": source_id,
        }

    @staticmethod
    def _integer(value: Any, default: int) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    @classmethod
    def _score(cls, analysis: dict[str, Any]) -> float:
        summary = str(analysis.get("summary") or "")
        steps = str(analysis.get("how") or "")
        reference = str(analysis.get("reference") or "")
        reference_url = str(analysis.get("reference_url") or "")
        difficulty = cls._integer(analysis.get("difficulty"), 3)
        score = 0.5
        if len(summary) > 100:
            score += 0.15
        if len(steps) > 100:
            score += 0.15
        if reference:
            score += 0.05
        if reference_url:
            score += 0.05
        if difficulty <= 2:
            score += 0.1
        return min(round(score, 2), 0.95)

    @staticmethod
    def _slug(title: str) -> str:
        value = re.sub(r"[^\w\u4e00-\u9fff-]+", "_", title[:30], flags=re.UNICODE)
        return value.strip("_").lower() or "opportunity"

    @staticmethod
    def _body(title: str, analysis: dict[str, Any], score: float) -> str:
        sections = [
            f"# {title}",
            "",
            f"> AI机会评分：{score}。当前仍为待验证草稿，不等于事实或正式决策。",
            "",
            "## 一句话结论",
            "",
            str(analysis.get("summary") or "待补充"),
            "",
            "## 执行方案",
            "",
            str(analysis.get("how") or "待补充"),
            "",
            "## 内容结构",
            "",
            str(analysis.get("content_structure") or "待补充"),
            "",
            "## 运营结构",
            "",
            str(analysis.get("operation_structure") or "待补充"),
            "",
            "## 商业结构",
            "",
            str(analysis.get("business_structure") or "待补充"),
            "",
            "## 可行性与卡点",
            "",
            str(analysis.get("feasibility") or "待补充"),
            "",
            str(analysis.get("bottleneck") or "待补充"),
            "",
            "## 风险与待验证",
            "",
            str(analysis.get("risk_analysis") or "待补充"),
            "",
            "## MVP与下一步",
            "",
            str(analysis.get("mvp") or "待补充"),
            "",
            str(analysis.get("next_action") or "待补充"),
            "",
            "## 参考案例",
            "",
            str(analysis.get("reference") or "待补充"),
            "",
            str(analysis.get("reference_url") or ""),
            "",
            "## 主人判断",
            "",
            "- 是否值得继续：",
            "- 我能否执行：",
            "- 何时执行：",
            "- 备注：",
            "",
        ]
        return "\n".join(sections)
