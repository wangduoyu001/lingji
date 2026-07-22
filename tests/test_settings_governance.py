from __future__ import annotations

from pathlib import Path

import pytest

from src.config import Settings
from src.control import RuntimeSettingsStore
from src.control.settings_catalog import CompleteOwnerSettingsRegistry
from src.control.settings_governance import (
    CONFIRM_HIGH_RISK_SETTINGS,
    OwnerSettingsRegistry,
)


class _StateDB:
    def __init__(self):
        self.events = []

    def append_event(self, *args):
        self.events.append(args)


def registry(tmp_path: Path, **overrides) -> CompleteOwnerSettingsRegistry:
    settings = Settings(
        _env_file=None,
        storage_dir=str(tmp_path),
        **overrides,
    )
    return CompleteOwnerSettingsRegistry(settings, state_db=_StateDB())


def test_control_package_exports_complete_governed_registry():
    assert RuntimeSettingsStore is CompleteOwnerSettingsRegistry
    assert issubclass(CompleteOwnerSettingsRegistry, OwnerSettingsRegistry)


def test_settings_model_default_overrides_duplicate_registry_literal(tmp_path: Path):
    store = registry(tmp_path, media_keyframe_interval_seconds=45.0)

    definition = store.definitions()["media_keyframe_interval_seconds"]

    assert definition["default"] == 45.0
    assert store.snapshot()["values"]["media_keyframe_interval_seconds"] == 45.0


def test_auto_review_settings_are_owner_visible_and_active_is_not_a_choice(tmp_path: Path):
    definitions = registry(tmp_path).definitions()

    assert definitions["auto_review_mode"]["choices"] == ["OFF", "SHADOW"]
    assert "auto_review_ai_enabled" in definitions
    assert "auto_review_timeout_seconds" in definitions
    assert "ACTIVE" not in definitions["auto_review_mode"]["choices"]


def test_invalid_active_default_is_clamped_to_off(tmp_path: Path):
    definition = registry(tmp_path, auto_review_mode="ACTIVE").definitions()["auto_review_mode"]

    assert definition["default"] == "OFF"
    assert definition["recommended"] == "SHADOW"


def test_every_owner_visible_definition_has_complete_governance_metadata(tmp_path: Path):
    definitions = registry(tmp_path).definitions()
    required = {
        "recommended",
        "recommendation_reason",
        "when_to_change",
        "performance_impact",
        "storage_impact",
        "cost_impact",
        "privacy_impact",
        "risk_level",
        "editable",
        "confirmation_required",
    }

    assert definitions
    for key, definition in definitions.items():
        assert not (required - set(definition)), key
        assert definition["risk_level"] in {"low", "medium", "high"}


def test_preview_returns_only_effective_changes(tmp_path: Path):
    store = registry(tmp_path)

    preview = store.preview(
        {
            "media_keyframe_interval_seconds": 30.0,
            "media_max_keyframes": 600,
        }
    )

    assert preview["change_count"] == 1
    assert preview["normalized_values"] == {"media_max_keyframes": 600}
    assert preview["changes"][0]["key"] == "media_max_keyframes"
    assert preview["requires_confirmation"] is False


def test_high_risk_change_requires_explicit_confirmation(tmp_path: Path):
    store = registry(tmp_path)

    preview = store.preview({"storage_auto_cleanup_enabled": True})

    assert preview["requires_confirmation"] is True
    assert preview["confirmation_phrase"] == CONFIRM_HIGH_RISK_SETTINGS
    with pytest.raises(PermissionError, match="explicit impact confirmation"):
        store.update({"storage_auto_cleanup_enabled": True})

    snapshot = store.update(
        {"storage_auto_cleanup_enabled": True},
        confirmation=CONFIRM_HIGH_RISK_SETTINGS,
    )
    assert snapshot["values"]["storage_auto_cleanup_enabled"] is True
    assert any(event[0] == "runtime_settings_high_risk_confirmed" for event in store.state_db.events)


def test_cross_setting_dependencies_block_invalid_commit(tmp_path: Path):
    store = registry(tmp_path)

    preview = store.preview({"media_auto_transcribe": True})

    assert preview["can_commit"] is False
    assert "自动转写需要选择 ASR Provider" in preview["errors"]
    with pytest.raises(ValueError, match="ASR Provider"):
        store.update({"media_auto_transcribe": True})


def test_unavailable_capability_is_visible_with_reason(tmp_path: Path):
    store = registry(tmp_path)

    snapshot = store.snapshot(
        {
            "faster_whisper": {
                "available": False,
                "optional_requirements": "requirements-media.txt",
            }
        }
    )
    definition = snapshot["definitions"]["media_asr_model"]

    assert definition["availability_state"] == "unavailable"
    assert definition["disabled_reason"] == "requirements-media.txt"
    assert snapshot["summary"]["unavailable_count"] > 0


def test_groups_are_backend_owned_and_ordered(tmp_path: Path):
    groups = registry(tmp_path).snapshot()["groups"]

    assert groups[0]["id"] == "media_processing"
    assert any(group["id"] == "auto_review" and group["label"] == "自动审查" for group in groups)
    assert all(group["label"] and group["description"] for group in groups)
    assert [group["order"] for group in groups] == sorted(group["order"] for group in groups)


def test_formal_control_startup_wires_governed_service_and_routes():
    source = Path("run_control_api.py").read_text(encoding="utf-8")

    assert "GovernedLocalControlService" in source
    assert "register_settings_governance_routes" in source
    assert "service = GovernedLocalControlService" in source
