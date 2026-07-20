# P2-03 + P2-03B Combined Validation Report（联合验证报告）

> Updated（更新时间）: 2026-07-21  
> Branch（分支）: `work/p2-03b-validation`  
> Base Commit（基础提交）: `432ae059454cc7db8ab0ba4aaa63d24f5c9173e9`  
> Validation Start Commit（验证起始提交）: `491002a67b2d3ed08c01d852c3c033ebf61c2630`  
> Security Fix Commit（安全修复代码与测试提交）: `27cdb55953d8537376116e221ea877fb544cba32`  
> Final HEAD（本报告对应代码 HEAD）: `27cdb55953d8537376116e221ea877fb544cba32`  
> Report Commit（报告提交）: 由本文件更新生成，以远程分支最终 HEAD 为准  
> P2-03 Status（状态）: `IMPLEMENTED_NOT_TESTED`  
> P2-03B Status（状态）: `IMPLEMENTED_NOT_TESTED`  
> Security Fix State（安全修复状态）: `SECURITY_FIX_IMPLEMENTED_NOT_TESTED`  
> Merge State（合并状态）: `NOT_MERGED`

## 1. 本轮目标

本轮只修复 Memory Inspector Vector Response（记忆检查器向量响应）的本机路径与异常原文泄漏，并补充 Facade（门面层）与 HTTP API（HTTP 接口）测试代码。

没有开始新功能，没有修改数据库 Schema（数据库结构），没有修改 SourceReadModel（来源读取模型），没有进入 `src/extraction/`、`src/capture/` 或 `desktop/lingji-control/`。

## 2. 修改文件

```text
src/gateway/memory_inspector.py
tests/test_memory_inspector_facade.py
tests/test_memory_inspector_api.py
docs/TEST_REPORTS/P2_03_P2_03B_COMBINED_VALIDATION_REPORT.md
```

未修改其他生产实现文件。

## 3. 安全问题

修复前，`MemoryInspectorFacade.memory_vector()` 会把以下内容直接放入 HTTP 200 响应：

```text
semantic.exists() 抛出的异常原文
snapshot.last_error 原文
```

例如：

```text
D:\Users\Secret\qdrant.db contains private provider details
```

可能进入：

```text
vector.last_error
vector.chunks[].last_error
```

## 4. 正式修复

新增模块 logger（日志记录器）：

```python
logger = logging.getLogger("lingji.gateway.memory_inspector")
```

新增唯一稳定外部摘要：

```text
Vector status unavailable; see local logs
```

正式常量：

```python
VECTOR_ERROR_MESSAGE = "Vector status unavailable; see local logs"
```

### 4.1 Semantic Provider 失败

当 `semantic.exists(chunk_id)` 抛出异常时：

```text
完整异常 -> logger.exception()
外部 exists -> null
外部 source -> unavailable
外部 last_error -> Vector status unavailable; see local logs
```

不使用正则，也不尝试保留异常中的“安全部分”。

### 4.2 Snapshot 错误

`snapshot.last_error` 不再直接进入外部响应。

规则：

```text
snapshot.last_error 为空 -> null
snapshot.last_error 非空 -> Vector status unavailable; see local logs
```

该规则同时应用于：

```text
vector.last_error
vector.chunks[].last_error
```

## 5. 保持不变的合同

本轮没有改变：

```text
exists = true
exists = false
exists = null
rebuild_required = true / false / null
collection
dimension
chunk_id
```

Live Provider（实时提供器）正常返回时，`exists` 仍转换为布尔值，Chunk 的 `source` 仍为 `live`。

没有 Provider 或 Provider 失败时，`exists` 仍为 `null`。

## 6. 新增 Facade 测试代码

`tests/test_memory_inspector_facade.py` 新增：

```text
test_vector_errors_are_sanitized_without_changing_tristate_contract
```

覆盖：

1. `semantic.exists()` 抛出包含 Windows 绝对路径的异常。
2. `snapshot.last_error` 包含 Windows 绝对路径。
3. 顶层与 Chunk 错误均等于固定摘要。
4. `exists is None`。
5. `rebuild_required` 分别为 `True`、`False`、`None` 时保持原值。
6. `chunk_id`、`collection`、`dimension` 保持不变。
7. 序列化响应不包含：

```text
D:\
Users
qdrant.db
private provider details
```

## 7. 新增 HTTP 200 测试代码

`tests/test_memory_inspector_api.py` 新增：

```text
test_vector_200_response_sanitizes_provider_and_snapshot_errors
```

该测试通过真实 `MemoryInspectorFacade.memory_vector()` 生成响应，再由 Control API（控制接口）返回 HTTP 200。

验证：

```text
status_code == 200
vector.last_error == Vector status unavailable; see local logs
vector.chunks[0].last_error == Vector status unavailable; see local logs
exists is None
rebuild_required is None
```

响应正文不得包含：

```text
D:\
Users
qdrant.db
private provider details
snapshot failure
```

不连接真实 Qdrant。

## 8. 实际执行命令

### 8.1 定向 compileall

执行：

```bash
python -m compileall \
  /tmp/lingji_p203/src/gateway \
  /tmp/lingji_p203/tests/test_memory_inspector_facade.py \
  /tmp/lingji_p203/tests/test_memory_inspector_api.py
```

结果：

```text
PASS
syntax failures: 0
```

说明：缓存目录中的三个修改前文件 blob SHA 与远程起始版本一致；修改后内容被推送到当前验证分支。该检查只证明目标文件语法可编译，不等于正式 pytest 通过。

### 8.2 指定 pytest

要求命令：

```bash
python -m pytest \
  tests/test_memory_inspector_facade.py \
  tests/test_memory_inspector_api.py \
  -v --tb=short
```

当前容器在不完整缓存目录 `/tmp/lingji_p203` 中尝试执行，结果：

```text
collected: 0
collection errors: 2
duration: 0.71s
exit status: 2
```

收集错误：

```text
ModuleNotFoundError: No module named 'src.gateway.adapters'
ModuleNotFoundError: No module named 'src.control.runtime_settings'
```

原因是当前容器没有完整 LingJi 工作树，缓存目录仅保存 P2-03 的部分文件。这是 Environment Limitation（环境限制），不是修复代码的权威测试失败。

正式 pytest 状态：

```text
NOT EXECUTED ON AUTHORITATIVE FULL WORKTREE
```

## 9. 辅助烟雾测试

使用精确修改后的 `memory_inspector.py`，通过隔离 import stub（导入桩）执行三种 `rebuild_required` 情况：

```text
True
False
None
```

结果：

```text
auxiliary vector sanitization smoke: PASS
cases: 3
```

验证了：

```text
Provider 异常只进入日志
顶层错误摘要稳定
Chunk 错误摘要稳定
exists 保持 null
三态保持原值
响应不包含 Windows 路径和异常原文
```

该辅助检查不是正式 pytest，不能用于升级为 `IMPLEMENTED_FOCUSED_TESTED`。

## 10. 正式测试数字

```text
passed: NOT EXECUTED
failed: NOT EXECUTED
skipped: NOT EXECUTED
xfailed: NOT EXECUTED
duration: NOT AVAILABLE
```

不把缓存目录的两个 collection error 计入正式失败数，因为目标完整工作树根本不存在。

## 11. Environment Limitations（环境限制）

```text
普通 Git 网络无法解析 github.com
GitHub Connector 可以读写远程仓库
当前容器没有完整 LingJi 工作树
缓存目录缺少 gateway/control/retrieval 等依赖模块
```

因此无法完成权威的两文件 pytest。

## 12. Production Data Access（生产数据访问）

```text
Production ChatGPT Export: NO
Production Vault: NO
Production SQLite: NO
Production Qdrant: NO
Production Ollama: NO
Real User Content: NO
Production Configuration Modified: NO
```

所有测试数据都是 Fake Provider（伪提供器）和固定测试字符串。

## 13. Git 与边界状态

```text
New branch created: NO
Rebase: NO
Force push: NO
Formal branch merged: NO
Tauri modified: NO
Extraction modified: NO
Capture modified: NO
Database Schema modified: NO
SourceReadModel modified: NO
```

## 14. Merge Recommendation（合并建议）

```text
DO_NOT_MERGE_YET
```

安全修复方向和测试代码已经完成，定向语法检查及辅助烟雾测试通过，但指定 pytest 尚未在完整工作树执行。

解除门禁条件：

```text
1. 在完整 work/p2-03b-validation 工作树执行指定 compileall
2. 执行 tests/test_memory_inspector_facade.py
3. 执行 tests/test_memory_inspector_api.py
4. 两个测试文件全部通过
5. 记录真实 passed / failed / skipped / xfailed / duration
```

## 15. 最终状态

```text
P2-03 / P2-03B:
IMPLEMENTED_NOT_TESTED

Security Fix:
SECURITY_FIX_IMPLEMENTED_NOT_TESTED

Merge State:
NOT_MERGED
```

本轮完成后停止，不开始 P2-04，不领取新功能。
