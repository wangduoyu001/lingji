"""Session value gate for automatic-memory intake (PERF_RESOURCE_ROOT_CAUSE_20260927 B1).

主人 2026-09-27 拍板：从源头减少扫描压力——简短的、没有价值信号的会话不再入队，
避免 raw 存储/队列/提取/嵌入/回填的全链路成本。红线：绝不静默丢弃——被拒会话
必须进入调用方的 skipped 审计（计数 + 滚动样本），且可按来源重扫撤销。

本模块是纯规则引擎（零推理成本）：只有「轮数少 且 字数少 且 零价值信号」的会话
才被拒绝；任何价值信号（代码、链接、决策措辞、命令、路径）都会放行。
阈值由调用方从 RuntimeSettingsStore 传入，默认保守（2 轮 / 300 字符）。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping

DEFAULT_MIN_TURNS = 2
DEFAULT_MIN_CHARS = 300

_VALUE_SIGNAL_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"```"),  # fenced code block
    re.compile(r"https?://", re.IGNORECASE),  # URL
    re.compile(r"(?:^|\s)(?:[A-Za-z]:\\|/(?:Users|home|etc|var|opt)/)", re.IGNORECASE),  # file paths
    re.compile(r"(?:^|\n)\s*\$\s+\S"),  # shell command line
    re.compile(
        r"(决定|拍板|结论|方案|确认|部署|上线|发布|修复|排查|报错|bug|Bug|BUG|"
        r"错误|完成|交付|验收|迁移|回滚|密码|密钥|token|Token|key|API|"
        r"decide|decision|conclusion|deploy|release|fix|bug|error|root cause|"
        r"ship|done|migrate|rollback)",
        re.IGNORECASE,
    ),
)


@dataclass(frozen=True)
class ValueGateDecision:
    approved: bool
    reason: str
    message_count: int
    total_chars: int
    signals: tuple[str, ...] = field(default_factory=tuple)

    def as_dict(self) -> dict[str, Any]:
        return {
            "approved": self.approved,
            "reason": self.reason,
            "message_count": self.message_count,
            "total_chars": self.total_chars,
            "signals": list(self.signals),
        }


def _iter_message_texts(messages: Iterable[Any]) -> Iterable[str]:
    for message in messages:
        if isinstance(message, Mapping):
            text = message.get("content") or message.get("text") or ""
        elif isinstance(message, str):
            text = message
        else:
            text = str(getattr(message, "content", "") or "")
        if text:
            yield str(text)


def evaluate_session_value(
    messages: Iterable[Any],
    *,
    min_turns: int = DEFAULT_MIN_TURNS,
    min_chars: int = DEFAULT_MIN_CHARS,
) -> ValueGateDecision:
    """Decide whether a captured session is worth the full intake pipeline.

    A session is rejected only when it is short on BOTH axes (turns and
    characters) AND carries none of the value signals. Everything else is
    approved; the caller records rejections in its skipped audit trail.
    """
    texts = list(_iter_message_texts(messages))
    message_count = len(texts)
    total_chars = sum(len(text) for text in texts)
    signals: list[str] = []
    if total_chars:
        joined = "\n".join(texts)
        for pattern in _VALUE_SIGNAL_PATTERNS:
            if pattern.search(joined):
                signals.append(pattern.pattern[:40])

    min_turns = max(int(min_turns), 0)
    min_chars = max(int(min_chars), 0)
    short_on_turns = message_count < min_turns
    short_on_chars = total_chars < min_chars
    if short_on_turns and short_on_chars and not signals:
        return ValueGateDecision(
            approved=False,
            reason=(
                f"session below value floor: {message_count} message(s) < {min_turns} "
                f"and {total_chars} chars < {min_chars}, no value signal"
            ),
            message_count=message_count,
            total_chars=total_chars,
            signals=(),
        )
    return ValueGateDecision(
        approved=True,
        reason="session carries content or value signals",
        message_count=message_count,
        total_chars=total_chars,
        signals=tuple(signals),
    )
