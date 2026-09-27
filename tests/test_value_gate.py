"""Regression tests for PERF_RESOURCE_ROOT_CAUSE_20260927 (B1) value gate."""

from __future__ import annotations

from src.automatic_memory.value_gate import evaluate_session_value


def test_short_signal_free_session_is_rejected() -> None:
    decision = evaluate_session_value(["你好"], min_turns=2, min_chars=300)
    assert decision.approved is False
    assert decision.message_count == 1
    assert decision.total_chars < 300
    assert decision.signals == ()


def test_short_session_with_value_signal_is_approved() -> None:
    decision = evaluate_session_value(
        ["这个 bug 的 root cause 是队列锁互抢"], min_turns=2, min_chars=300
    )
    assert decision.approved is True
    assert decision.signals


def test_long_session_is_approved_even_without_signals() -> None:
    decision = evaluate_session_value(["字" * 400], min_turns=2, min_chars=300)
    assert decision.approved is True


def test_url_and_code_blocks_count_as_signals() -> None:
    decision = evaluate_session_value(
        ["看这个 https://example.com/a 的说明"], min_turns=2, min_chars=300
    )
    assert decision.approved is True


def test_thresholds_are_configurable() -> None:
    strict = evaluate_session_value(
        ["决定：采用方案 A"], min_turns=2, min_chars=300
    )
    assert strict.approved is True
    looser = evaluate_session_value(
        ["你好呀"], min_turns=1, min_chars=1
    )
    assert looser.approved is True
    strictest = evaluate_session_value(
        ["随便聊聊"], min_turns=2, min_chars=300
    )
    assert strictest.approved is False


def test_decision_dict_is_json_serializable() -> None:
    decision = evaluate_session_value(["你好"], min_turns=2, min_chars=300)
    import json

    payload = json.dumps(decision.as_dict(), ensure_ascii=False)
    assert "reason" in payload
