"""Regression tests for secret redaction (4.2, 2026-09-27).

zhipu_api_key 曾在 /api/settings 原样返回全密钥。修复后：服务层展示一律
脱敏（前 4 + … + 后 4），掩码回写被识别为"未修改"绝不覆盖真值；真值只进
本机文件（chmod 600）且内部消费方（提炼调用）继续从 snapshot() 拿全值。
"""

from __future__ import annotations

import json
import stat
from pathlib import Path
from types import SimpleNamespace

from src.control.runtime_settings import (
    RuntimeSettingsStore,
    mask_secret,
    redact_secret_values,
)

_KEY = "dac0fb006cb246f8ae1c419fa08ec7a2.aqp1QhAIHizoTuqn"


def _store(tmp_path: Path, state_db=None) -> RuntimeSettingsStore:
    settings = SimpleNamespace(
        storage_path=tmp_path, runtime_settings_file="runtime_settings.json"
    )
    return RuntimeSettingsStore(settings, state_db=state_db)


def test_mask_shape() -> None:
    assert mask_secret(_KEY) == "dac0…Tuqn"
    assert mask_secret("") == ""
    assert mask_secret("short") == "…"


def test_redacted_snapshot_masks_but_snapshot_keeps_real_value(tmp_path: Path) -> None:
    store = _store(tmp_path)
    store.update({"zhipu_api_key": _KEY})
    redacted = redact_secret_values(store.snapshot())
    assert redacted["values"]["zhipu_api_key"] == "dac0…Tuqn"
    assert redacted["values"]["zhipu_api_key_set"] is True
    assert _KEY not in json.dumps(redacted, ensure_ascii=False)
    # 内部消费方（提炼/向量化真实调用）必须继续拿到全值。
    assert store.snapshot()["values"]["zhipu_api_key"] == _KEY


def test_mask_round_trip_is_a_noop(tmp_path: Path) -> None:
    store = _store(tmp_path)
    store.update({"zhipu_api_key": _KEY})
    before = store.path.read_text(encoding="utf-8")
    store.update({"zhipu_api_key": mask_secret(_KEY)})
    assert store.path.read_text(encoding="utf-8") == before, "掩码回写绝不能覆盖真值"
    assert store.snapshot()["values"]["zhipu_api_key"] == _KEY


def test_new_key_round_trips_and_file_is_0600(tmp_path: Path) -> None:
    store = _store(tmp_path)
    store.update({"zhipu_api_key": _KEY})
    mode = stat.S_IMODE(store.path.stat().st_mode)
    assert mode == 0o600, f"runtime_settings.json 权限 {oct(mode)}，必须 600"
    store.update({"zhipu_api_key": "ffffffffeeeeeeeeddddddddcccccccc.bbbb"})
    assert store.snapshot()["values"]["zhipu_api_key"] == "ffffffffeeeeeeeeddddddddcccccccc.bbbb"
    redacted = redact_secret_values(store.snapshot())
    assert redacted["values"]["zhipu_api_key"] == "ffff…bbbb"


def test_reset_removes_key_and_redaction_reports_unset(tmp_path: Path) -> None:
    store = _store(tmp_path)
    store.update({"zhipu_api_key": _KEY})
    redacted = redact_secret_values(store.reset(["zhipu_api_key"]))
    assert redacted["values"]["zhipu_api_key_set"] is False


def test_service_get_settings_redacts(tmp_path: Path) -> None:
    from src.control.service import LocalControlService
    from src.storage.state_db import StateDatabase

    storage = tmp_path / "storage"
    storage.mkdir()
    control = LocalControlService.__new__(LocalControlService)
    control.state_db = StateDatabase(storage / "lingji_state.db")
    control.runtime_settings = RuntimeSettingsStore(
        SimpleNamespace(storage_path=storage, runtime_settings_file="runtime_settings.json"),
        state_db=control.state_db,
    )
    control.runtime_settings.update({"zhipu_api_key": _KEY})
    payload = control.get_settings()
    assert _KEY not in json.dumps(payload, ensure_ascii=False)
    assert payload["values"]["zhipu_api_key"] == "dac0…Tuqn"
