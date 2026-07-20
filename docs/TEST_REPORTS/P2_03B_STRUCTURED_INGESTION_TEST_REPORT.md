# P2-03B Structured Ingestion Test Report（结构化采集测试报告）

> Updated（更新时间）: 2026-07-21  
> Branch（分支）: `work/p2-03b-ingestion-wiring`  
> Base Commit（基础提交）: `f135e7d5a22557c44bb6108b94d0001fa16c47d8`  
> Implementation Commit（实现提交）: `dfebef348616c4f11ae4739f1909d435d34fa5ca`  
> Verified Commit（已验证提交）: `NOT_EXECUTED`  
> Status（状态）: `IMPLEMENTED_NOT_TESTED`

## 1. 测试范围

新增 `tests/test_structured_ingestion.py`，覆盖：

- 旧 `ExtractionBatch(documents=...)` 调用兼容。
- `structured_sources` 默认空。
- Frozen Dataclass（不可变数据类）。
- ChatGPT 单轮标准化同时产生 Markdown 与 StructuredConversation。
- Conversation ID、Message node ID、role、author、time、model、branch 和稳定顺序。
- Source account identity（来源账号身份）可由 options 设置。
- Structured Sink 写入 Source/Conversation/Message。
- Raw 与 Vault 使用安全相对引用。
- 绝对路径不进入读取模型 bundle。
- 重复写入使用同一逻辑身份。
- Memory 不存在时跳过 Link 并产生 warning。
- 无结构化数据返回 `not_applicable`。
- 写入异常返回 `degraded` 且响应脱敏。

## 2. 计划执行命令

```powershell
python -m pytest `
  tests/test_chatgpt_extraction.py `
  tests/test_structured_ingestion.py `
  tests/test_extraction_pipeline.py `
  -v --tb=short
```

真实仓库中测试文件是否存在应在本地执行时确认；不存在的文件不硬跑。

## 3. 实际执行

```text
pytest: NOT EXECUTED
py_compile: NOT EXECUTED
npm: NOT EXECUTED
Tauri: NOT EXECUTED
Ollama: NOT EXECUTED
Qdrant: NOT EXECUTED
```

原因：当前连接器环境可以读取和提交 GitHub 文件，但没有可联网克隆仓库的本地运行环境。未安装依赖，未访问生产环境，也没有冒充测试通过。

## 4. 结果

```text
passed: NOT EXECUTED
failed: NOT EXECUTED
skipped: NOT EXECUTED
xfailed: NOT EXECUTED
```

## 5. 静态审查证据

- `SourceReadModel` 通过 `from src.sources import SourceReadModel` 导入。
- 未导入或修改 `src.sources.read_model_contract`。
- Pipeline 顺序为 Raw -> Adapter -> Vault -> Index Callback -> Structured Sink。
- Pipeline 不含 `if source_type == "chatgpt"`。
- Structured Sink 不直接写 SQL。
- Structured Sink 不创建 Qdrant Client。
- Structured Sink 只调用 `SourceReadModel.upsert_bundle()`。
- Raw 引用通过 `storage/raw` 相对路径生成。
- Vault 引用使用 Vault Sink 返回的 `relative_path`。
- Structured 错误对外使用固定安全摘要，完整异常仅进入本地 logger。

## 6. 数据安全

```text
读取 Production ChatGPT 正文: NO
修改 Production Vault: NO
修改 Production SQLite: NO
访问 Production Qdrant: NO
切换生产模型: NO
运行生产导入: NO
暴露绝对路径到读取模型: NO（设计与测试覆盖，尚待 pytest 验证）
```

## 7. Workspace（工作区）隔离

Bootstrap 使用传入 settings 的 `memory_db_path`、`storage_path` 和 `state_db_path`。因此 Production（生产）与 Acceptance（验收）是否隔离由现有 Workspace Contract（工作区合同）决定，本任务没有硬编码共享路径。

本轮新增测试使用 Temporary Directory（临时目录）与 Fake Database（伪数据库），不使用生产路径。

## 8. 已知未验证项

- ChatGPT Adapter 与仓库既有 `tests/test_chatgpt_extraction.py` 的完整回归兼容。
- Pipeline 队列 lease、heartbeat、retry 的运行时回归。
- `MemoryDatabase.fetch_memory()` 与索引回调的真实时序。
- `SourceReadModel.upsert_bundle()` 在真实临时 SQLite 中的幂等结果。
- Acceptance 与 Production 的端到端读取模型隔离。

## 9. 当前结论

```text
IMPLEMENTED_NOT_TESTED
NOT_MERGED_AWAITING_COORDINATED_REVIEW
```

不能标记为测试通过。等待统一里程碑测试与代码审查。
