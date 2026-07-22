from __future__ import annotations

from typing import Any, Mapping

from .settings_governance import OwnerSettingsRegistry


class CompleteOwnerSettingsRegistry(OwnerSettingsRegistry):
    """Current owner-visible catalog, including settings added after P2-05."""

    def definitions(self) -> dict[str, dict[str, Any]]:
        definitions = super().definitions()
        configured_mode = str(getattr(self.settings, "auto_review_mode", "OFF") or "OFF").upper()
        safe_mode = configured_mode if configured_mode in {"OFF", "SHADOW"} else "OFF"
        definitions.update(
            {
                "auto_review_mode": self._annotate(
                    self._choice(
                        "auto_review",
                        "Auto Review 模式",
                        "OFF 完全关闭；SHADOW 只记录建议和风险，不执行记忆变更。",
                        safe_mode,
                        ["OFF", "SHADOW"],
                    ),
                    recommended="SHADOW",
                    recommendation_reason="完成本机验收后可使用 SHADOW 积累审计样本，同时保持零自动写入。",
                    when_to_change="需要暂停自动审查观察时切回 OFF；当前版本不得启用 ACTIVE。",
                    performance_impact="SHADOW 会增加确定性规则评估和少量审计写入。",
                    storage_impact="决策与反馈事件会产生少量 SQLite 审计记录。",
                    cost_impact="确定性评估无云端费用；本地 AI 是否运行由独立开关控制。",
                    privacy_impact="SHADOW 不扩大记忆写入权限，也不自动修改 Obsidian 或 Qdrant。",
                    risk_level="medium",
                    confirmation_required=False,
                ),
                "auto_review_ai_enabled": self._annotate(
                    self._boolean(
                        "auto_review",
                        "启用本地 AI 风险补充",
                        "允许本机 Ollama 在确定性结果之后增加风险点和简短说明。",
                        bool(getattr(self.settings, "auto_review_ai_enabled", False)),
                    ),
                    recommended=False,
                    recommendation_reason="默认关闭，先依赖确定性规则；配置好本地模型角色后再启用。",
                    when_to_change="已配置 auto_review_primary/fallback，且需要观察 AI 风险补充质量时开启。",
                    performance_impact="每次评估可能触发一次本地模型推理，增加 GPU/CPU 和等待时间。",
                    storage_impact="只额外保存简短风险摘要和模型状态，不保存私有思维链。",
                    cost_impact="仅允许本机 loopback Ollama，不产生云端调用费用。",
                    privacy_impact="候选内容只发送到本机 Ollama；远程地址会被后端拒绝。",
                    risk_level="medium",
                    confirmation_required=False,
                ),
                "auto_review_timeout_seconds": self._annotate(
                    self._number(
                        "auto_review",
                        "本地 AI 审查超时",
                        "本地 Ollama 单次风险审查允许等待的最长时间。",
                        float(getattr(self.settings, "auto_review_timeout_seconds", 20.0)),
                        0.1,
                        300.0,
                    ),
                    recommended=20.0,
                    recommendation_reason="20 秒足以覆盖常见本地模型，同时避免审查队列长期阻塞。",
                    when_to_change="模型较慢且经常超时时提高；希望更快回退到确定性规则时降低。",
                    unit="秒",
                    performance_impact="数值越高，模型故障时等待越久。",
                    storage_impact="无明显存储影响。",
                    cost_impact="不产生云端费用。",
                    privacy_impact="不改变本地-only 数据边界。",
                    risk_level="low",
                    confirmation_required=False,
                ),
            }
        )
        for definition in definitions.values():
            definition.setdefault("editable", True)
            definition.setdefault("scope", "runtime")
            definition.setdefault("restart_required", False)
            definition.setdefault("task_required", False)
            definition.setdefault("dependencies", [])
            definition.setdefault("conflicts", [])
        return definitions

    def groups(self, definitions: Mapping[str, Mapping[str, Any]] | None = None) -> list[dict[str, Any]]:
        groups = super().groups(definitions)
        for item in groups:
            if item["id"] == "auto_review":
                item.update(
                    {
                        "label": "自动审查",
                        "description": "控制 OFF/SHADOW 模式、本地 AI 风险补充与超时。",
                        "order": 35,
                    }
                )
        return sorted(groups, key=lambda item: (item["order"], item["label"]))
