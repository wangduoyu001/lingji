# P2-03 Structured Read Model（结构化读取模型）实施计划

> Updated（更新时间）: 2026-07-20  
> Branch（分支）: `work/p2-03-structured-read-model`  
> Verified Commit（已验证提交）: `b9950b4066fbb0b602c2ffba5109da2fa8371cf3`  
> Status（状态）: `IMPLEMENTED_NOT_TESTED`  
> Evidence（证据来源）: 正式分支代码审计、Schema（数据库结构）审计、静态编译与临时 SQLite 隔离冒烟

## 1. 目标

P2-03 建立一个可删除、可重建、只读查询优先的 Source/Conversation/Message Read Model（来源、对话、消息读取模型），为 P2-04 Memory Inspector（记忆检查器）提供稳定后端合同。

本阶段不开发 Tauri 页面，不执行生产聊天导入，不修改永久记忆正文，不切换生产 Embedding Model（嵌入模型），不创建或删除生产 Qdrant Collection（向量集合）。

## 2. 真实现状

### 2.1 Canonical Memory（正式记忆）

`src/retrieval/memory_db.py::MemoryDatabase` 已在 `lingji_memory.db` 中维护：

- `memory_documents`
- `memory_chunks`
- `memory_meta`
- `memory_fts`

该数据库是可重建索引，不是永久事实源。

### 2.2 Compatibility Data（兼容数据）

`second_brain/db.py` 中存在：

- `sources`
- `conversations`
- `messages`
- `memories`
- `memory_versions`
- `memory_relations`
- `conflicts`

这些表只作为迁移证据和 Dual-read Comparison（双读对比）来源。兼容库的记忆、版本正文和消息正文不能成为新权威。

### 2.3 Extraction Pipeline（采集流水线）

ChatGPT Adapter（ChatGPT 适配器）能够解析稳定 conversation ID、message node ID、角色、时间、模型、正文和分支信息，但当前 Sink（写入器）最终只保存整段对话 Markdown 和会话级 metadata（元数据）。逐条 Message 结构没有进入正式派生表。

因此本阶段增加幂等写入接口，但不自动扫描或导入生产历史。

## 3. 数据权威

```text
Obsidian Vault + Git
= 永久记忆和正式知识正文

workspace/raw
= 原始导入材料

lingji_state.db
= 任务、队列、状态与审计

lingji_memory.db
= 可重建词法索引、元数据索引和 Structured Read Model

Qdrant
= 可重建语义向量索引
```

## 4. 新增 Schema

Structured Read Model 使用独立 schema version（结构版本），避免修改 `MemoryDatabase.SCHEMA_VERSION`：

- `source_read_model_meta`
- `source_records`
- `conversation_records`
- `message_records`
- `message_memory_links`

### 4.1 Source

保存来源类型、显示名、外部 ID、安全引用、隐私、项目、Agent Scope（智能体读取范围）、状态、内容哈希和元数据。

### 4.2 Conversation

保存稳定 conversation ID、source ID、标题、参与者、起止时间、消息数、隐私、项目和 Agent Scope。

### 4.3 Message

保存稳定 message ID、conversation/source 关联、角色、作者、时间、稳定序号、派生正文、内容哈希、安全 raw reference（原始资料引用）和元数据。

Message 列表永远只返回：

- `content_preview`
- `content_length`
- `content_hash`

完整正文只由 Message Detail（消息详情）返回。

### 4.4 MessageMemoryLink

保存 Message→Memory 的显式关联：

- `relation_type`
- `confidence`
- `created_at`

`memory_id` 外键指向 `memory_documents`。重建或删除派生记忆索引时，失效关联自动删除，不影响 Vault 正文。

## 5. Stable ID（稳定 ID）

未提供正式 ID 时使用确定性 SHA-256：

```text
Source
= source_type + external_id/raw_reference/vault_reference/content_hash

Conversation
= source_id + external_id/content_hash

Message
= conversation_id + external_id/sequence+role+content_hash
```

相同导入重复执行得到相同 ID。外部 ID 已存在时优先复用数据库中的既有 ID，避免重复记录。

## 6. 查询与分页

统一分页合同：

```text
default limit = 50
minimum limit = 1
maximum limit = 200
offset >= 0
```

排序：

```text
Source:
updated_at DESC, source_id DESC

Conversation:
started_at/updated_at DESC, conversation_id DESC

Message:
occurred_at DESC, sequence DESC, message_id DESC

Memory:
modified_at/updated_at DESC, memory_id DESC
```

所有查询使用参数化 SQL。关键词使用转义后的 `LIKE`，不创建第二套 Memory 排名算法。

## 7. 权限合同

### Owner（主人）

Local Control API 代表 Owner，响应明确包含：

```text
viewer_scope = owner
viewer_agent_id = lingji-local
```

Owner 可以读取 `public/private/restricted`。

### Agent（智能体）

`SourceQueryService.agent_viewer()` 复用 `AIProfileRegistry`：

- allowed privacy 生效
- Agent Scope 生效
- Source 的 privacy/project/scope 自动继承给 Conversation 和 Message
- 无权请求 restricted 时返回空集，不静默放宽

## 8. 安全引用

API 不返回开发者绝对路径。

Workspace 内路径转换为：

```text
raw:<relative path>
vault:<relative path>
```

Workspace 外绝对路径返回 `null`。Token、API Key、Cookie、Password、Secret 等 metadata key 不返回。

## 9. Facade（只读门面）

`MemoryInspectorFacade` 组合：

- `MemoryDatabase`
- `SourceReadModel`
- `SourceQueryService`
- `MemoryStatisticsService`
- 已注入的 `MemoryGateway`
- 已注入的 Semantic Provider（语义提供器）

Memory 列表直接读取 canonical `memory_documents`，不增加第二套排名。

## 10. Vector Linkage（向量关联诊断）

优先级：

1. 已注入 Gateway 的 Semantic Provider
2. `MemoryStatisticsService` 状态
3. snapshot（快照）
4. unknown/null

只有 live provider 可调用 `exists(chunk_id)`。

没有 live provider 时：

```json
{
  "exists": null,
  "source": "unavailable"
}
```

不得为诊断创建第二个 Embedded Qdrant Client（嵌入式 Qdrant 客户端），不得返回 raw vector（原始向量）或完整 payload。

## 11. 8766 API

只增加 GET：

```text
/api/memory/inspector/status
/api/memory/inspector/sources
/api/memory/inspector/sources/{source_id}
/api/memory/inspector/conversations
/api/memory/inspector/conversations/{conversation_id}
/api/memory/inspector/conversations/{conversation_id}/messages
/api/memory/inspector/messages
/api/memory/inspector/messages/{message_id}
/api/memory/inspector/memories
/api/memory/inspector/memories/{memory_id}
/api/memory/inspector/memories/{memory_id}/source
/api/memory/inspector/memories/{memory_id}/vector
```

认证继续使用 `X-LingJi-Token`。

错误：

```text
401 token 错误
404 实体不存在
422 参数错误
503 Read Model 不可读取
```

单个向量诊断失败不会让 Memory Detail 返回 503。

## 12. 数据写入边界

代码提供：

- idempotent upsert（幂等更新或插入）
- explicit rebuild（显式重建）
- temporary acceptance import（临时验收导入）

代码不提供：

- 自动生产 migration（迁移）
- 自动 ChatGPT 历史导入
- 自动 compatibility DB 导入
- API 写入、修改或删除记忆
- Qdrant 重建或模型切换按钮

## 13. 测试计划

重点测试：

- `tests/test_source_read_model.py`
- `tests/test_source_service.py`
- `tests/test_memory_inspector_facade.py`
- `tests/test_memory_inspector_api.py`

覆盖 Schema、稳定 ID、幂等、外键、分页、稳定排序、筛选、隐私、Agent Scope、Workspace 隔离、认证、404/422/503 和 vector unknown。

当前对话没有完整仓库 checkout，要求的 pytest 尚未执行。只记录静态编译和临时 SQLite 冒烟，不冒充完整测试通过。

## 14. 回滚

回滚代码提交即可。

派生表可安全删除：

```sql
DROP TABLE message_memory_links;
DROP TABLE message_records;
DROP TABLE conversation_records;
DROP TABLE source_records;
DROP TABLE source_read_model_meta;
```

回滚不需要修改 Vault、Git、生产 Qdrant 或永久记忆。
