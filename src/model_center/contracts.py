from __future__ import annotations

from typing import Any, Iterable


_CAPABILITY_MAP = {
    "completion": "chat_reasoning",
    "tools": "chat_reasoning",
    "thinking": "chat_reasoning",
    "embedding": "embedding",
    "vision": "vision",
}


def mapped_capabilities(values: Iterable[Any]) -> list[str]:
    output: list[str] = []
    for raw in values:
        mapped = _CAPABILITY_MAP.get(str(raw).strip().lower())
        if mapped and mapped not in output:
            output.append(mapped)
    return output


def unverified_compatibility(reason: str = "load_and_benchmark_required") -> dict[str, Any]:
    return {
        "status": "unverified",
        "requires_load_test": True,
        "requires_benchmark": True,
        "reason": reason,
        "tested_at": None,
        "benchmark_id": None,
        "limitations": [],
    }


def first_model_info(model_info: dict[str, Any], suffix: str) -> Any:
    for key, value in model_info.items():
        if str(key).lower().endswith(suffix.lower()):
            return value
    return None


def model_name(value: dict[str, Any]) -> str:
    return str(value.get("name") or value.get("model") or "").strip()
