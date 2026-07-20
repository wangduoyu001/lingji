# P2-03B Structured Ingestion Wiring（结构化采集接线）

> Updated（更新时间）: 2026-07-21  
> Branch（分支）: `work/p2-03b-ingestion-wiring`  
> Base Branch（基础分支）: `origin/work/p2-03-structured-read-model`  
> Base Commit（基础提交）: `f135e7d5a22557c44bb6108b94d0001fa16c47d8`  
> Implementation Commit（实现提交）: `dfebef348616c4f11ae4739f1909d435d34fa5ca`  
> Status（状态）: `IMPLEMENTED_NOT_TESTED`

## 1. 任务目标

让 ChatGPT Export Adapter（ChatGPT 导出适配器）在继续生成 Vault Markdown（知识库 Markdown）的同时，输出强类型 Structured Source/Conversation/Message（结构化来源、对话、消息），并通过 `SourceReadModel.upsert_bundle()` 幂等写入 P2-03 Structured Read Model（结构化读取模型）。

本任务不修改 P2-03 读取模型，不开发 Memory Inspector（记忆检查器）前端，不访问生产数据。

## 2. 开始前真实代码分析

1. `ExtractionRequest` 包含任务 ID、来源类型、适配器、输入路径、payload、options 和创建时间。
2. `ExtractedDocument` 包含稳定 ID、标题、正文、来源类型、Vault 目标、外部 ID、时间和 metadata。
3. 原 `ExtractionBatch` 只包含 documents、summary、warnings，无法传递逐条消息。
4. ChatGPT Adapter 在 `_conversation_document()` 中解析 mapping、node、parent、role、author、时间、model、branch、position 和 attachments。
5. 消息结构在 Adapter 内部临时字典渲染为 Markdown 后丢失。
6. Raw Snapshot（原始快照）在 `adapter.extract()` 之前由 `VaultExtractionSink.preserve_raw()` 生成。
7. Vault Markdown 在 Adapter 返回后由 `VaultExtractionSink.write_batch()` 写入。
8. Memory Index Callback（记忆索引回调）在 Vault 写入后执行。
9. `SourceReadModel.upsert_bundle()` 接收 `source` 和 `conversations`；Conversation 内嵌 `messages`，Message 可内嵌 `memory_links`。
10. 本实现只通过 `from src.sources import SourceReadModel` 使用公开合同，未修改 `src/sources/`。
11. 新增不可变 StructuredMessage、StructuredConversation、StructuredSource 传输模型。
12. 新增单一 StructuredReadModelSink（结构化读取模型写入器）。
13. Structured Sink 失败时返回 degraded，不回滚 Raw/Vault；Memory Link 不可用时只跳过链接并警告。
14. 测试采用临时目录、Fake Read Model（伪读取模型）、Fake Memory Database（伪记忆数据库）和小型 ChatGPT fixture（测试夹具）。

## 3. 新数据流

```text
Input File / ChatGPT Export
-> preserve_raw()
-> ChatGPTExportAdapter.extract()
-> ExtractionBatch
     -> documents
     -> structured_sources
-> VaultExtractionSink.write_batch()
-> on_documents_written
-> StructuredReadModelSink.write_batch()
-> SourceReadModel.upsert_bundle()
-> execution response
```

Pipeline（处理管线）不包含 ChatGPT 特殊分支。未来 Adapter 可复用同一 StructuredSource 合同。

## 4. 数据权威

- Obsidian Vault + Git：永久知识正文权威。
- `storage/raw`：原始材料权威。
- SourceReadModel：可重建结构化查询数据。
- Qdrant：可重建语义索引。

SourceReadModel 不成为新的永久正文权威。

## 5. 实现内容

### 5.1 结构化传输模型

`src/extraction/models.py` 新增：

- `StructuredMessage`
- `StructuredConversation`
- `StructuredSource`

`ExtractionBatch.structured_sources` 默认空 tuple（元组），保持旧 Adapter 向后兼容。

### 5.2 ChatGPT 映射

Adapter 先生成 `_NormalizedConversation`，同一轮标准化结果同时用于：

- Markdown Document（Markdown 文档）
- StructuredConversation（结构化对话）

消息映射：

- external_id = node_id
- role = author.role
- author = author.name
- occurred_at = create_time
- sequence = 稳定排序后的顺序
- content = 标准化文本
- metadata = parent/model/is_branch/original_position/attachments

对话 metadata 包含 current_node、message_count、branch_message_count、models、source_export_files、document_stable_id。

Source Identity（来源身份）优先级：

```text
source_external_id
-> account_id
-> profile_id
-> chatgpt:default
```

### 5.3 Privacy（隐私）

- Source 默认 `private`。
- Conversation 使用对应 Markdown 文档的 Privacy Scan（隐私扫描）结果。
- Message 不显式覆盖时继承 Conversation。
- 单个 restricted Conversation 不会把整个 Source 提升为 restricted。

### 5.4 Raw/Vault 安全引用

Raw 引用只允许：

```text
raw:<relative path under storage/raw>
```

Vault 引用只允许：

```text
vault:<relative_path>
```

读取模型不保存输入文件、Vault 或数据库的绝对路径。

### 5.5 Message -> Memory Link

写入顺序保证 Memory 回调先于 Structured Sink。

只有同时满足以下条件才写链接：

- Memory 回调成功。
- `document_stable_id` 存在。
- `MemoryDatabase.fetch_memory()` 确认 Memory 已存在。

否则仍写 Source/Conversation/Message，并返回 warning。

### 5.6 失败降级

- Raw/Vault 失败：主采集失败。
- Structured Sink 失败：主采集不回滚，返回 `degraded`。
- 无结构化数据：返回 `not_applicable`。
- 对外 warning 不包含 traceback、Token、Cookie、API Key、数据库路径或用户目录。

## 6. Bootstrap（运行时装配）

`build_extraction_pipeline()` 使用当前 Workspace（工作区）的：

- `settings.memory_db_path`
- `settings.storage_path`
- `settings.state_db_path`

创建并复用：

- `MemoryDatabase`
- `SourceReadModel`
- `StructuredReadModelSink`

未启动 Qdrant、Ollama、Tauri、8765 或 8767。

## 7. 幂等机制

- Source：`source_type + source_external_id`
- Conversation：`source_id + conversation_id`
- Message：`conversation_id + node_id`
- Vault：保持原稳定 `ExtractedDocument.stable_id`

重复导入由 SourceReadModel 的正式 Upsert（更新或插入）合同处理，不复制其 SQL 或稳定 ID 算法。

## 8. 修改文件

- `src/extraction/models.py`
- `src/extraction/adapters/chatgpt.py`
- `src/extraction/structured_sink.py`
- `src/extraction/pipeline.py`
- `src/extraction/bootstrap.py`
- `src/extraction/__init__.py`
- `tests/test_structured_ingestion.py`
- `docs/MODULES/P2_03B_STRUCTURED_INGESTION_WIRING.md`
- `docs/TEST_REPORTS/P2_03B_STRUCTURED_INGESTION_TEST_REPORT.md`

## 9. 回滚方式

回滚本分支提交即可。Structured Read Model 是可重建派生数据，回滚不影响 Raw Snapshot 或 Vault 正文权威。

## 10. 已知限制

- 本轮未执行 pytest，因此不能声称测试通过。
- 仅 ChatGPT Adapter 输出结构化来源；Codex、Web、Media 保持默认空结构化输出。
- Memory Link 依赖索引回调完成后 `memory_documents` 已可见；不可见时按合同跳过并警告。
- 未执行生产数据导入或历史数据回填。

## 11. 下一步

等待1号与2号开发报告统一审查。  
不自行开始 P2-04。
