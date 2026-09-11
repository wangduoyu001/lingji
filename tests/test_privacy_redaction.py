"""敏感信息脱敏：API Key/凭据/证件号在入记忆层与上云前擦除（主人红线）。"""

from __future__ import annotations

from dataclasses import replace

from src.extraction.models import ExtractionBatch, StructuredConversation, StructuredMessage, StructuredSource
from src.extraction.pipeline import ExtractionPipeline
from src.extraction.privacy import PrivacyClassifier


def test_detects_platform_credentials_and_bearer_tokens():
    c = PrivacyClassifier()
    text = (
        "key dac0fb006cb246f8ae1c419fa08ec7a2.aqp1QhAIHizoTuqn "
        "Authorization: Bearer abcdef1234567890abcdef1234 "
        "token: ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ123456"
    )
    assessment = c.assess(text)
    assert assessment.restricted
    kinds = set(assessment.kinds())
    assert {"credential_pair", "bearer_token", "api_key"} <= kinds
    redacted = c.redact(text)
    assert "dac0fb006cb246f8ae1c419fa08ec7a2" not in redacted
    assert "abcdefgh1234567890" not in redacted
    assert "[REDACTED:" in redacted


def test_redact_preserves_surrounding_text():
    c = PrivacyClassifier()
    redacted = c.redact("开始 正常内容 dac0fb006cb246f8ae1c419fa08ec7a2.aqp1QhAIHizoTuqn 结尾也是正常内容")
    assert redacted.startswith("开始 正常内容 ")
    assert redacted.endswith(" 结尾也是正常内容")
    assert "REDACTED" in redacted


def test_pipeline_redacts_structured_batch_before_memory_write():
    """接缝测试：结构化批次进入记忆层前，标题与消息内容必须已完成脱敏。"""
    pipeline = object.__new__(ExtractionPipeline)
    message = StructuredMessage(
        external_id="m1", role="user", sequence=0,
        content="我的智谱Key是 dac0fb006cb246f8ae1c419fa08ec7a2.aqp1QhAIHizoTuqn 请帮我配置",
        occurred_at="2026-09-12T00:00:00+00:00",
    )
    conversation = StructuredConversation(
        external_id="c1", title="配置 dac0fb006cb246f8ae1c419fa08ec7a2.aqp1QhAIHizoTuqn 问题",
        messages=(message,),
    )
    source = StructuredSource(source_type="codex_rollout", external_id="s1", display_name="Codex", conversations=(conversation,))
    batch = ExtractionBatch(documents=(), structured_sources=(source,))

    redacted = ExtractionPipeline._redact_structured_batch(pipeline, batch)

    conv = redacted.structured_sources[0].conversations[0]
    assert "dac0fb006cb246f8ae1c419fa08ec7a2" not in conv.title
    assert "dac0fb006cb246f8ae1c419fa08ec7a2" not in conv.messages[0].content
    assert "REDACTED" in conv.messages[0].content
    assert redacted.structured_sources[0].conversations[0].messages[0].content.count("REDACTED") >= 1
    summary = redacted.summary or {}
    assert summary.get("redacted_messages", 0) >= 1


def test_redaction_is_idempotent():
    c = PrivacyClassifier()
    once = c.redact("password: hunter2 和 sk-abcdefghijklmnopqrstuvwx")
    twice = c.redact(once)
    assert once == twice, "重复脱敏不应改变内容（[REDACTED:*] 标记不被二次改写）"
