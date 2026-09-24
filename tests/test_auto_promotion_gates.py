

def test_process_log_title_downgrades_to_evolving():
    """过程记录（审查/验收/修复流水）降级 Evolving，绝不进 Core（2026-09-24）。"""
    from src.memory.auto_promotion import AutoMemoryPromotionPipeline

    row = {
        "title": "Task5A 独立终审完成",
        "summary": "Task5A 独立终审通过，可进入 Task5B UI 开发。",
        "key_points_json": '["终审通过", "进入 Task5B"]',
        "category": "项目",
        "confidence": 0.95,
        "conversation_id": "conv-x",
    }
    decision, reasons, _ = AutoMemoryPromotionPipeline._decide_row(
        object.__new__(AutoMemoryPromotionPipeline),
        row,
        core_documents=[],
        title_conflicts={},
    )
    assert decision == "evolving"
    assert "process_log_downgraded" in reasons


def test_conclusion_title_not_downgraded():
    """非过程记录的正常结论不受降级规则影响（进入后续门槛判定）。"""
    from src.memory.auto_promotion import AutoMemoryPromotionPipeline

    row = {
        "title": "嵌入模型切换为 qwen3 且须防混库",
        "summary": "同维度换嵌入模型必须清空旧向量集合。",
        "key_points_json": '["qwen3", "指纹守卫"]',
        "category": "技术",
        "confidence": 0.95,
        "conversation_id": "conv-y",
    }
    pipeline = object.__new__(AutoMemoryPromotionPipeline)
    pipeline.setting_reader = None
    pipeline.semantic_similarity = None
    pipeline.settings = None
    decision, reasons, _ = pipeline._decide_row(
        row, core_documents=[], title_conflicts={},
    )
    assert "process_log_downgraded" not in reasons
