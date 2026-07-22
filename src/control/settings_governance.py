from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from .runtime_settings import RuntimeSettingsStore


CONFIRM_HIGH_RISK_SETTINGS = "CONFIRM_HIGH_RISK_SETTINGS"


_GROUPS: dict[str, dict[str, Any]] = {
    "media_processing": {
        "label": "媒体处理",
        "description": "控制关键帧、FFmpeg、文件体积、时长和任务资源上限。",
        "order": 10,
        "performance_impact": "数值越激进，媒体处理占用和耗时通常越高。",
        "storage_impact": "更多关键帧和更高分辨率会增加派生文件占用。",
        "cost_impact": "默认仅使用本机资源，不产生云端费用。",
        "privacy_impact": "媒体处理默认在本机完成。",
    },
    "media_ai": {
        "label": "媒体 AI",
        "description": "控制本地转写、OCR 和镜头检测 Provider。",
        "order": 20,
        "performance_impact": "启用本地 AI 会增加 CPU、GPU 和内存占用。",
        "storage_impact": "模型和分析结果会占用额外磁盘空间。",
        "cost_impact": "当前 Provider 为本地开源实现，不产生云端调用费用。",
        "privacy_impact": "输入默认不离开本机；启用云端 Provider 前必须另行设计和确认。",
    },
    "hardware_compute": {
        "label": "系统与算力",
        "description": "控制 CPU/GPU 选择与资源状态采样频率。",
        "order": 30,
        "performance_impact": "设备选择和采样频率会影响处理速度与监控开销。",
        "storage_impact": "通常无明显存储影响。",
        "cost_impact": "仅使用本机算力，不产生云端费用。",
        "privacy_impact": "只读取本机硬件与运行状态。",
    },
    "storage": {
        "label": "存储与生命周期",
        "description": "控制容量预警、保留周期、冷存储和可恢复清理策略。",
        "order": 40,
        "performance_impact": "扫描、迁移和清理计划会产生磁盘 IO。",
        "storage_impact": "直接影响派生文件、日志、缓存和历史版本的保留范围。",
        "cost_impact": "本地磁盘或用户自有存储成本可能变化。",
        "privacy_impact": "冷存储目录可能改变资料所在位置，应确认访问权限。",
    },
    "obsidian": {
        "label": "Obsidian",
        "description": "控制正式 Vault 与 Obsidian CLI 的本机连接。",
        "order": 50,
        "performance_impact": "CLI 调用频率和超时会影响交互等待时间。",
        "storage_impact": "Vault 路径决定正式知识正文所在位置。",
        "cost_impact": "默认不产生云端费用。",
        "privacy_impact": "路径和 Vault 选择会决定哪些本机资料可被灵机访问。",
    },
    "backup": {
        "label": "备份与恢复",
        "description": "控制备份默认范围，不直接执行恢复。",
        "order": 60,
        "performance_impact": "完整备份耗时通常高于元数据备份。",
        "storage_impact": "完整备份会占用更多磁盘空间。",
        "cost_impact": "仅使用用户自有存储。",
        "privacy_impact": "备份可能包含敏感资料，应限制目录访问权限。",
    },
}


_SETTING_POLICY: dict[str, dict[str, Any]] = {
    "media_auto_transcribe": {
        "risk_level": "medium",
        "capability": "faster_whisper",
        "recommendation_reason": "默认关闭，避免未准备模型时自动占用大量算力。",
        "when_to_change": "确认 faster-whisper 已安装且确实需要自动转写时开启。",
    },
    "media_asr_provider": {"capability": "faster_whisper", "risk_level": "medium"},
    "media_asr_model": {"capability": "faster_whisper", "risk_level": "medium"},
    "media_asr_device": {"capability": "faster_whisper", "risk_level": "medium"},
    "media_asr_compute_type": {"capability": "faster_whisper", "risk_level": "medium"},
    "media_asr_language": {"capability": "faster_whisper"},
    "media_auto_ocr": {
        "risk_level": "medium",
        "capability": "paddleocr",
        "recommendation_reason": "默认关闭，避免每张关键帧都执行 OCR。",
        "when_to_change": "确认 PaddleOCR 已安装且画面文字确实需要结构化时开启。",
    },
    "media_ocr_provider": {"capability": "paddleocr", "risk_level": "medium"},
    "media_ocr_language": {"capability": "paddleocr"},
    "media_detect_scenes": {
        "risk_level": "medium",
        "capability": "pyscenedetect",
        "recommendation_reason": "默认关闭，避免无需求时增加整段视频扫描。",
        "when_to_change": "需要镜头边界或分镜分析且 PySceneDetect 可用时开启。",
    },
    "media_scene_provider": {"capability": "pyscenedetect", "risk_level": "medium"},
    "media_scene_threshold": {"capability": "pyscenedetect"},
    "storage_auto_cleanup_enabled": {
        "risk_level": "high",
        "confirmation_required": True,
        "task_required": True,
        "recommendation_reason": "默认关闭，先生成可审计计划并由主人检查后再执行。",
        "when_to_change": "只有在恢复区、冷存储和保留策略均验证后开启。",
    },
    "storage_cold_enabled": {
        "risk_level": "medium",
        "recommendation_reason": "默认关闭，避免未选择目录时产生错误迁移计划。",
        "when_to_change": "已选择稳定、可访问且有备份的冷存储目录后开启。",
    },
    "storage_cold_path": {
        "risk_level": "high",
        "confirmation_required": True,
        "recommendation_reason": "留空表示不使用冷存储，不应自动猜测机器目录。",
        "when_to_change": "需要迁移旧版本或日志，并已确认目录权限和容量时修改。",
    },
    "compute_preferred_gpu_id": {
        "risk_level": "medium",
        "recommendation_reason": "单显卡电脑留空即可，系统会选择可用设备。",
    },
    "obsidian_cli_enabled": {
        "risk_level": "medium",
        "capability": "obsidian_cli",
        "recommendation_reason": "启用后才允许正式 CLI 状态和命令能力。",
    },
    "obsidian_cli_path": {
        "risk_level": "medium",
        "capability": "obsidian_cli",
        "recommendation_reason": "留空时使用安全的自动发现流程。",
    },
    "obsidian_vault_path": {
        "risk_level": "high",
        "confirmation_required": True,
        "recommendation_reason": "默认使用当前 Workspace Vault，避免错误访问其他资料目录。",
        "when_to_change": "只有在迁移正式 Vault 且完成备份、路径检查和权限确认后修改。",
    },
    "obsidian_vault_name": {"risk_level": "medium", "capability": "obsidian_cli"},
    "obsidian_cli_timeout_seconds": {"capability": "obsidian_cli"},
    "obsidian_cli_dry_run": {
        "risk_level": "low",
        "capability": "obsidian_cli",
        "recommendation_reason": "排查写命令或首次连接新 Vault 时建议临时开启。",
    },
    "backup_default_profile": {
        "risk_level": "medium",
        "recommendation_reason": "元数据备份更快且占用更低；需要完整离线恢复时再选择 full。",
    },
}


class OwnerSettingsRegistry(RuntimeSettingsStore):
    """Owner-visible settings registry and change-governance authority.

    The Desktop receives all defaults, recommendations, risk metadata and group
    labels from this backend registry. Frontend code must not duplicate them.
    """

    def definitions(self) -> dict[str, dict[str, Any]]:
        definitions = deepcopy(super().definitions())
        for key, definition in definitions.items():
            if hasattr(self.settings, key):
                definition["default"] = getattr(self.settings, key)
            group = _GROUPS.get(str(definition.get("group") or ""), {})
            policy = _SETTING_POLICY.get(key, {})
            definition.update(policy)
            definition.setdefault("recommended", definition["default"])
            definition.setdefault(
                "recommendation_reason",
                "系统默认值是当前本地优先、可恢复运行策略的稳定基准。",
            )
            definition.setdefault(
                "when_to_change",
                "只有在存在明确需求并理解影响时修改；不确定时保持系统默认。",
            )
            definition.setdefault("performance_impact", group.get("performance_impact", "无明显性能影响。"))
            definition.setdefault("storage_impact", group.get("storage_impact", "无明显存储影响。"))
            definition.setdefault("cost_impact", group.get("cost_impact", "不产生额外云端费用。"))
            definition.setdefault("privacy_impact", group.get("privacy_impact", "不扩大默认数据访问范围。"))
            definition.setdefault("risk_level", "low")
            definition.setdefault("scope", "runtime")
            definition.setdefault("editable", True)
            definition.setdefault("confirmation_required", definition["risk_level"] == "high")
            definition.setdefault("task_required", False)
            definition.setdefault("dependencies", [])
            definition.setdefault("conflicts", [])
        return definitions

    def groups(self, definitions: Mapping[str, Mapping[str, Any]] | None = None) -> list[dict[str, Any]]:
        selected = definitions or self.definitions()
        counts: dict[str, int] = {}
        for definition in selected.values():
            group = str(definition.get("group") or "other")
            counts[group] = counts.get(group, 0) + 1
        groups = []
        for key, count in counts.items():
            metadata = _GROUPS.get(key, {})
            groups.append(
                {
                    "id": key,
                    "label": metadata.get("label", key),
                    "description": metadata.get("description", "运行设置"),
                    "order": int(metadata.get("order", 999)),
                    "setting_count": count,
                }
            )
        return sorted(groups, key=lambda item: (item["order"], item["label"]))

    def snapshot(self, capabilities: Mapping[str, Mapping[str, Any]] | None = None) -> dict[str, Any]:
        payload = super().snapshot()
        definitions = self._with_availability(payload["definitions"], capabilities or {})
        payload["definitions"] = definitions
        payload["groups"] = self.groups(definitions)
        payload["summary"] = {
            "setting_count": len(definitions),
            "override_count": len(payload["overrides"]),
            "high_risk_count": sum(1 for item in definitions.values() if item.get("risk_level") == "high"),
            "unavailable_count": sum(1 for item in definitions.values() if item.get("availability_state") == "unavailable"),
        }
        payload["confirmation_phrase"] = CONFIRM_HIGH_RISK_SETTINGS
        return payload

    def preview(
        self,
        values: Mapping[str, Any],
        *,
        capabilities: Mapping[str, Mapping[str, Any]] | None = None,
    ) -> dict[str, Any]:
        current = super().snapshot()
        definitions = self._with_availability(current["definitions"], capabilities or {})
        changes: list[dict[str, Any]] = []
        normalized_values: dict[str, Any] = {}
        for key, value in values.items():
            if key not in definitions:
                raise KeyError(f"Unknown runtime setting: {key}")
            definition = definitions[key]
            if definition.get("editable") is False:
                raise PermissionError(f"Runtime setting is not editable: {key}")
            normalized = self._validate_value(key, value, definition)
            if normalized == current["values"][key]:
                continue
            normalized_values[key] = normalized
            changes.append(
                {
                    "key": key,
                    "label": definition["label"],
                    "group": definition["group"],
                    "from": current["values"][key],
                    "to": normalized,
                    "default": definition["default"],
                    "recommended": definition["recommended"],
                    "risk_level": definition["risk_level"],
                    "confirmation_required": bool(definition.get("confirmation_required")),
                    "restart_required": bool(definition.get("restart_required")),
                    "task_required": bool(definition.get("task_required")),
                    "availability_state": definition.get("availability_state", "unknown"),
                    "disabled_reason": definition.get("disabled_reason"),
                    "impacts": {
                        "performance": definition["performance_impact"],
                        "storage": definition["storage_impact"],
                        "cost": definition["cost_impact"],
                        "privacy": definition["privacy_impact"],
                    },
                }
            )
        effective = dict(current["values"])
        effective.update(normalized_values)
        errors, warnings = self._cross_validate(effective, definitions)
        high_risk = [item for item in changes if item["confirmation_required"]]
        return {
            "changes": changes,
            "normalized_values": normalized_values,
            "change_count": len(changes),
            "high_risk_changes": high_risk,
            "requires_confirmation": bool(high_risk),
            "confirmation_phrase": CONFIRM_HIGH_RISK_SETTINGS if high_risk else None,
            "errors": errors,
            "warnings": warnings,
            "can_commit": bool(changes) and not errors,
        }

    def update(
        self,
        values: Mapping[str, Any],
        *,
        actor: str = "owner",
        confirmation: str = "",
        capabilities: Mapping[str, Mapping[str, Any]] | None = None,
    ) -> dict[str, Any]:
        preview = self.preview(values, capabilities=capabilities)
        if preview["errors"]:
            raise ValueError("; ".join(preview["errors"]))
        if preview["requires_confirmation"] and confirmation != CONFIRM_HIGH_RISK_SETTINGS:
            raise PermissionError("High-risk settings require explicit impact confirmation")
        if not preview["changes"]:
            return self.snapshot(capabilities)
        result = super().update(preview["normalized_values"], actor=actor)
        if self.state_db and preview["high_risk_changes"]:
            self.state_db.append_event(
                "runtime_settings_high_risk_confirmed",
                "settings",
                "runtime",
                {
                    "actor": actor,
                    "keys": [item["key"] for item in preview["high_risk_changes"]],
                    "confirmation": CONFIRM_HIGH_RISK_SETTINGS,
                },
            )
        return self.snapshot(capabilities)

    @staticmethod
    def _with_availability(
        definitions: Mapping[str, Mapping[str, Any]],
        capabilities: Mapping[str, Mapping[str, Any]],
    ) -> dict[str, dict[str, Any]]:
        output: dict[str, dict[str, Any]] = {}
        for key, raw in definitions.items():
            definition = dict(raw)
            capability = str(definition.get("capability") or "")
            if not capability:
                definition["availability_state"] = "available"
                definition["disabled_reason"] = None
            else:
                status = dict(capabilities.get(capability) or {})
                available = status.get("available")
                if available is True:
                    definition["availability_state"] = "available"
                    definition["disabled_reason"] = None
                elif available is False:
                    definition["availability_state"] = "unavailable"
                    definition["disabled_reason"] = str(
                        status.get("reason")
                        or status.get("optional_requirements")
                        or f"{capability} 当前不可用"
                    )
                else:
                    definition["availability_state"] = "unknown"
                    definition["disabled_reason"] = str(status.get("reason") or "能力状态尚未检测")
            output[key] = definition
        return output

    @staticmethod
    def _cross_validate(
        values: Mapping[str, Any],
        definitions: Mapping[str, Mapping[str, Any]],
    ) -> tuple[list[str], list[str]]:
        errors: list[str] = []
        warnings: list[str] = []
        dependencies = (
            ("media_auto_transcribe", "media_asr_provider", "off", "自动转写需要选择 ASR Provider"),
            ("media_auto_ocr", "media_ocr_provider", "off", "自动 OCR 需要选择 OCR Provider"),
            ("media_detect_scenes", "media_scene_provider", "off", "镜头切分需要选择 Scene Provider"),
        )
        for enabled_key, provider_key, off_value, message in dependencies:
            if values.get(enabled_key) and values.get(provider_key) == off_value:
                errors.append(message)
        if values.get("storage_cold_enabled") and not str(values.get("storage_cold_path") or "").strip():
            errors.append("启用冷存储前必须选择冷存储目录")
        for key, definition in definitions.items():
            if key not in values:
                continue
            if definition.get("availability_state") == "unavailable" and values[key] != definition.get("default"):
                warnings.append(f"{definition['label']} 依赖能力当前不可用：{definition.get('disabled_reason')}")
        return errors, warnings
