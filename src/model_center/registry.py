from __future__ import annotations

from copy import deepcopy
from typing import Any


_CAPABILITIES = {
    "chat_reasoning": {
        "label": "对话与推理",
        "description": "对话、总结、推理和工具调用。",
    },
    "embedding": {
        "label": "Embedding 语义索引",
        "description": "把文本转换为向量。切换时必须新建并验证索引。",
    },
    "asr": {
        "label": "ASR 语音识别",
        "description": "把音频和视频语音转换为文字。",
    },
    "ocr": {
        "label": "OCR 文字识别",
        "description": "识别图片和关键帧中的文字。",
    },
    "vision": {
        "label": "视觉理解",
        "description": "理解图片、视频帧和多模态内容。",
    },
    "reranker": {
        "label": "Reranker 重排",
        "description": "对有限候选结果重新排序，故障时回退到 RRF。",
    },
}

_PROVIDERS = {
    "ollama": {
        "label": "Ollama",
        "kind": "local_runtime",
        "capabilities": ["chat_reasoning", "embedding", "vision"],
        "inventory_source": ["/api/tags", "/api/ps", "/api/show"],
        "mutating_operations_enabled": False,
    },
    "faster_whisper": {
        "label": "faster-whisper",
        "kind": "python_provider",
        "capabilities": ["asr"],
        "inventory_source": ["python_package", "configured_model_path"],
        "mutating_operations_enabled": False,
    },
    "paddleocr": {
        "label": "PaddleOCR",
        "kind": "python_provider",
        "capabilities": ["ocr"],
        "inventory_source": ["python_package", "PADDLE_OCR_BASE_DIR"],
        "mutating_operations_enabled": False,
    },
    "not_configured_vision": {
        "label": "未配置视觉 Provider",
        "kind": "placeholder",
        "capabilities": ["vision"],
        "inventory_source": [],
        "mutating_operations_enabled": False,
    },
    "not_configured_reranker": {
        "label": "未配置 Reranker",
        "kind": "placeholder",
        "capabilities": ["reranker"],
        "inventory_source": [],
        "mutating_operations_enabled": False,
    },
}


def registry_snapshot() -> dict[str, Any]:
    return {
        "capabilities": deepcopy(_CAPABILITIES),
        "providers": deepcopy(_PROVIDERS),
        "compatibility_states": [
            "unverified",
            "compatible",
            "compatible_with_limits",
            "cpu_only",
            "unavailable",
        ],
        "compatibility_process": [
            "static_specification",
            "dependency_check",
            "small_load_test",
            "short_benchmark",
            "measured_conclusion",
        ],
        "mutating_operations_enabled": False,
    }
