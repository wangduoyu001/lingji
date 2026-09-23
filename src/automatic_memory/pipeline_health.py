"""后台管线的故障可见性（治"静默失败"）。

历史教训（2026-09-23 真机）：提炼/晋升/回填三个 daemon 循环都在 `except` 里
静默吞异常——向量重建高负载下提炼循环连续秒败数小时，唯一发现方式是主人
盯着 UI 数字不动。本模块给每个循环三件事：

1. 连续失败计数 + 最近错误留痕（status API 直接透出）；
2. 限频审计事件（首败立即报，持续失败每 5 分钟至多一条，恢复立即报）——
   故障可见但不会把 events 表撑爆；
3. degraded 判定（连续 >= 3 次失败），供状态页与未来告警使用。

只做记录与计数，不做重试策略——重试节奏仍归各循环自己的退避逻辑。
"""

from __future__ import annotations

from datetime import datetime, timezone
import time
from typing import Any

_DEGRADED_AFTER_CONSECUTIVE = 3


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class PipelineHealth:
    """单个后台管线的故障计数器与限频上报器。线程安全（循环单线程读写）。"""

    def __init__(
        self,
        name: str,
        state_db: Any = None,
        *,
        event_interval_seconds: float = 300.0,
        clock: Any = time.monotonic,
    ):
        self.name = str(name)
        self._state_db = state_db
        self._clock = clock
        self._event_interval = max(float(event_interval_seconds), 1.0)
        self._consecutive = 0
        self._total_failures = 0
        self._last_error: str | None = None
        self._last_success_at: str | None = None
        self._last_failure_at: str | None = None
        self._last_event_at = self._clock() - self._event_interval
        self._reported_failure = False

    def record_success(self) -> None:
        recovered = self._consecutive >= _DEGRADED_AFTER_CONSECUTIVE
        self._consecutive = 0
        self._last_success_at = _now_iso()
        if recovered:
            self._reported_failure = False
            self._emit("recovered", {"last_error": self._last_error})

    def record_failure(self, error: str) -> None:
        self._consecutive += 1
        self._total_failures += 1
        self._last_error = str(error or "unknown error")[:500]
        self._last_failure_at = _now_iso()
        now = self._clock()
        due = (now - self._last_event_at) >= self._event_interval
        if not self._reported_failure or due:
            self._reported_failure = True
            self._last_event_at = now
            self._emit(
                "failed",
                {
                    "consecutive": self._consecutive,
                    "total_failures": self._total_failures,
                    "error": self._last_error,
                },
            )

    @property
    def degraded(self) -> bool:
        return self._consecutive >= _DEGRADED_AFTER_CONSECUTIVE

    def snapshot(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "consecutive_failures": self._consecutive,
            "total_failures": self._total_failures,
            "degraded": self.degraded,
            "last_error": self._last_error,
            "last_success_at": self._last_success_at,
            "last_failure_at": self._last_failure_at,
        }

    def _emit(self, outcome: str, payload: dict[str, Any]) -> None:
        append = getattr(self._state_db, "append_event", None)
        if not callable(append):
            return
        try:
            append(
                f"pipeline_{self.name}_{outcome}",
                "automatic_memory_pipeline",
                self.name,
                payload,
            )
        except Exception:
            # 上报通道自身的故障绝不能反噬业务循环。
            return


__all__ = ["PipelineHealth"]
