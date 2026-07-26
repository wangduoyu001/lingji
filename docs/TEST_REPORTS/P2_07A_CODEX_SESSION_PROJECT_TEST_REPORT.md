# P2-07A Project Resolver + Codex Session Bridge Test Report

> Updated: 2026-07-21  
> Branch: `work/p2-07a-codex-session-project`  
> Base Commit: `8b033eba1be6d4e7509a763b8333299672d2161b`  
> Tested Implementation Commit: `f53dfc3fcce16e235f22d66c3c008444c61a4bf7`  
> Status: `IMPLEMENTED_NOT_TESTED`  
> Merge State: `NOT_MERGED_AWAITING_COORDINATED_REVIEW`

## 1. 环境

```text
Operating System: Linux container
Python: 3.13.5
pytest: 9.0.2
Authoritative full Git worktree: unavailable
GitHub remote writes: available through connector
```

普通 Git 无法解析 `github.com`，因此不能在完整权威工作树执行任务指定的七文件集中测试。没有把隔离镜像的结果包装成完整仓库验收。

## 2. compileall

执行：

```bash
python -m compileall -q \
  src/project_context \
  src/codex_sessions \
  src/extraction/adapters/codex_session.py \
  src/control/codex_api.py \
  src/mcp_server.py \
  tests/test_project_context.py \
  tests/test_codex_session_service.py \
  tests/test_codex_session_adapter.py \
  tests/test_codex_session_api.py \
  tests/test_codex_mcp_tools.py
```

隔离实现结果：

```text
PASS
syntax failures: 0
```

## 3. 已执行聚焦测试

执行：

```bash
PYTHONPATH=. python -m pytest \
  tests/test_project_context.py \
  tests/test_codex_session_service.py \
  tests/test_codex_session_adapter.py \
  tests/test_codex_session_api.py \
  tests/test_codex_mcp_tools.py \
  -q --tb=short
```

结果：

```text
passed: 15
failed: 0
skipped: 0
xfailed: 0
duration: 2.88s
```

覆盖：

- Manifest 正常解析、非法拒绝和父目录查找。
- Git Common Dir Worktree 归一化。
- UNASSIGNED 降级。
- Registry 原子写入、稳定排序、Root 去重和损坏降级。
- 路径 DTO 脱敏。
- Session Start / Checkpoint / Close。
- 外部 Session ID 稳定恢复。
- event_id 幂等与 content_hash 重复识别。
- 关闭后 Checkpoint 409。
- JSONL 不完整尾行恢复。
- 递归敏感信息脱敏。
- `documents=()`，不生成 Obsidian Transcript。
- Structured Source / Conversation / Message / project_id / Raw Reference。
- MCP 工具存在且不提供 Vault/Core Memory 写参数。
- API 401 / 404 / 409 / 稳定 503。
- Activity 增量查询。
- Audit 写入失败不影响 Raw 和 Structured 主操作。

## 4. 任务要求的完整命令

要求：

```bash
python -m pytest \
  tests/test_project_context.py \
  tests/test_codex_session_service.py \
  tests/test_codex_session_adapter.py \
  tests/test_codex_session_api.py \
  tests/test_codex_mcp_tools.py \
  tests/test_structured_ingestion.py \
  tests/test_mcp_server.py \
  -v --tb=short
```

状态：

```text
NOT EXECUTED ON AUTHORITATIVE FULL WORKTREE
```

原因：当前容器没有完整分支工作树，普通 Git DNS 不可用。现有 `test_structured_ingestion.py` 和 `test_mcp_server.py` 未被复制到隔离镜像执行，不能宣称回归通过。

正式统计：

```text
passed: NOT EXECUTED
failed: NOT EXECUTED
skipped: NOT EXECUTED
xfailed: NOT EXECUTED
duration: NOT AVAILABLE
```

## 5. 数据与安全

```text
Database Schema modified: NO
New Project/Session database table: NO
Second Extraction Pipeline created: NO
Obsidian Transcript written: NO
Core Memory written: NO
Codex private SQLite read: NO
Codex private cache scanned: NO
Keyboard/clipboard/folder monitoring: NO
Production Vault accessed: NO
Production SQLite accessed: NO
Production Qdrant accessed: NO
Production Ollama accessed: NO
Real user content accessed: NO
Desktop modified: NO
```

测试只使用 TemporaryDirectory、临时 JSONL、Fake Pipeline、Fake State DB 与 FastAPI TestClient。

## 6. 已知风险

1. 仍需在完整分支工作树执行任务指定七文件 pytest。
2. `register_codex_routes(...)` 尚未装配进正式 Control API，需由协调集成阶段完成。
3. 大量 Session 的列表目前扫描 Raw JSONL，符合本阶段无新表合同，但规模化性能尚未验证。
4. Windows 真实 Git Worktree 命令与文件锁行为尚未真机验证。

## 7. 合并建议

```text
DO_NOT_MERGE_UNTIL_FOCUSED_REGRESSION_PASSES
```

解除门禁：

1. 在完整 `work/p2-07a-codex-session-project` 工作树执行指定 compileall。
2. 执行七文件集中 pytest。
3. `failed = 0`。
4. 记录真实 passed / failed / skipped / xfailed / duration。
5. 协调者审查正式路由装配与其他 P2-07 分支冲突。

## 8. 最终状态

```text
IMPLEMENTED_NOT_TESTED
NOT_MERGED_AWAITING_COORDINATED_REVIEW
```
