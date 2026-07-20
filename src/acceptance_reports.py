from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class AcceptanceReportStore:
    """Persist reports outside the inspected input set."""

    def __init__(self, report_dir: Path):
        self.report_dir = Path(report_dir)

    def save(self, report: dict[str, Any]) -> dict[str, Any]:
        self.report_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f")
        json_path = self.report_dir / f"acceptance-{stamp}.json"
        markdown_path = self.report_dir / f"acceptance-{stamp}.md"
        self._atomic_write(json_path, json.dumps(report, ensure_ascii=False, indent=2, default=str) + "\n")
        self._atomic_write(markdown_path, render_markdown(report))
        return {"report": report, "json_path": str(json_path), "markdown_path": str(markdown_path)}

    def list_reports(self, limit: int = 100) -> list[dict[str, Any]]:
        if not self.report_dir.is_dir():
            return []
        output = []
        paths = sorted(self.report_dir.glob("acceptance-*.json"), reverse=True)
        for path in paths[: max(1, min(int(limit), 1000))]:
            try:
                payload = json.loads(path.read_text(encoding="utf-8-sig"))
            except (OSError, ValueError, TypeError, json.JSONDecodeError):
                continue
            output.append(
                {
                    "path": str(path),
                    "markdown_path": str(path.with_suffix(".md")),
                    "generated_at": payload.get("generated_at"),
                    "status": payload.get("status"),
                    "error_count": payload.get("error_count", 0),
                    "warning_count": payload.get("warning_count", 0),
                    "inputs_unchanged": payload.get("inputs_unchanged"),
                }
            )
        return output

    @staticmethod
    def _atomic_write(path: Path, content: str) -> None:
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_text(content, encoding="utf-8")
        temporary.replace(path)


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# 灵机真实环境只读验收报告",
        "",
        f"- 生成时间：{report['generated_at']}",
        f"- 总状态：**{report['status']}**",
        f"- 错误：{report['error_count']}",
        f"- 警告：{report['warning_count']}",
        f"- 输入未变化：{'是' if report.get('inputs_unchanged') else '否'}",
        "- 模式：只读检查；只允许向验收报告目录写入报告",
        "",
        "## 环境",
        "",
        "```json",
        json.dumps(report.get("environment") or {}, ensure_ascii=False, indent=2, default=str),
        "```",
        "",
        "## 检查结果",
        "",
    ]
    for item in report["checks"]:
        lines.extend(
            [
                f"### {item['name']} · {item['status']}",
                "",
                item["message"],
                "",
                "```json",
                json.dumps(item.get("details") or {}, ensure_ascii=False, indent=2, default=str),
                "```",
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"
