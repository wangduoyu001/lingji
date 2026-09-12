# 实施设计：任务② 历史数据清洗

> 状态：DESIGNED。目标：把脱敏功能上线**之前**已入库的存量内容重跑脱敏，
> 并同步重建派生层（记忆块/FTS/向量），使全库达到同一脱敏基线。

## 清洗范围（全部在 lingji_memory.db + qdrant）

| 表 | 动作 |
| --- | --- |
| message_records.content | 逐行 redact，变更行 UPDATE（记录 message_id） |
| conversation_records.title | 同上 |
| distilled_knowledge.summary / key_points_json | 同上（提炼产物可能复述过敏感串） |
| memory_documents / memory_chunks | 由消息派生——受影响的重建或逐块 redact+FTS 同步更新 |
| qdrant 向量 payload.content | 删除受影响 message_id 的点 → 现有回填自动重嵌入（payload 带脱敏后文本） |

## 执行器

`src/automatic_memory/history_scrub.py` → `HistoryScrubber(settings).run(batch=500)`：

1. 分批 SELECT 未处理行（内存安全），redact，diff，UPDATE。
2. 受影响 message_id 集合返回给调用方。
3. qdrant：`client.delete(points)` 按 `_point_id(message_id)`；调度器下一轮回填自动补。
4. FTS/chunks：对 memory_documents/chunks 直接 redact + 更新 FTS 行（或调用既有
   `rebuild_from_index` 全量重建——量级 1 万条，秒级）。
5. 幂等：重复执行第二遍 0 变更。

## 触发方式

- 一次性：本任务内直接对真机执行并验证。
- 长效：`POST /api/maintenance/scrub`（管理端点，后续任务挂）。

## 验收

- 清洗前后：库内匹配已知敏感样串（如主人贴过的智谱 Key）计数 → 后归零。
- FTS/向量检索仍正常；提炼/检索不回退。
