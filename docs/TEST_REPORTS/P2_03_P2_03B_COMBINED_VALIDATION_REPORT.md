# P2-03 + P2-03B Combined Validation Report（联合验证报告）

> Updated（更新时间）: 2026-07-21  
> Branch（分支）: `work/p2-03b-validation`  
> Base Commit（基础提交）: `432ae059454cc7db8ab0ba4aaa63d24f5c9173e9`  
> Tested Commit（计划验证的代码提交）: `432ae059454cc7db8ab0ba4aaa63d24f5c9173e9`  
> Final HEAD（本报告验证的代码 HEAD）: `432ae059454cc7db8ab0ba4aaa63d24f5c9173e9`  
> Report Commit（报告提交）: 由本文件提交生成，以远程分支最终 HEAD 为准  
> P2-03 Status（状态）: `IMPLEMENTED_NOT_TESTED`  
> P2-03B Status（状态）: `IMPLEMENTED_NOT_TESTED`  
> Validation State（验证状态）: `VERIFICATION_NOT_EXECUTED`  
> Merge Recommendation（合并建议）: `DO_NOT_MERGE`

## 1. 验证目标

本轮只负责 P2-03 Structured Read Model（结构化读取模型）与 P2-03B Structured Ingestion Wiring（结构化采集接线）的集中测试和合并门禁。

本轮没有：

- 开始 P2-04。
- 扩展信息入口。
- 修改 Tauri。
- 修改生产实现代码。
- 合并 `feature/second-brain-memory`。

## 2. 验证环境

```text
Python Version: 3.13.5
Operating System: Linux-4.4.0-x86_64-with-glibc2.41
Architecture: linux/amd64
CI Environment: true
pytest Version: 9.0.2
```

环境限制：

```text
GitHub 普通网络访问失败：Could not resolve host: github.com
GitHub Connector 可以读取和写入远程仓库
当前执行容器没有完整的 LingJi 工作树
发现的 /tmp/lingji_p203 仅包含旧任务留下的 P2-03 部分文件
该目录不是 Git 仓库，且缺少 P2-03B 与大量依赖模块
qdrant-client 未安装
```

因此不能在真实 `432ae059...` 完整工作树中执行要求的 `compileall` 和两组 pytest。

## 3. 分支准备

验证分支已从指定提交创建：

```text
work/p2-03b-validation
<- 432ae059454cc7db8ab0ba4aaa63d24f5c9173e9
```

创建后与基础提交比较：

```text
ahead: 0
behind: 0
status: identical
```

报告提交会使验证分支相对基础提交增加一个纯文档提交。

## 4. 要求执行的命令

### 4.1 低成本检查

```bash
python -m compileall src tests
```

结果：

```text
NOT EXECUTED
```

原因：当前容器不存在目标提交的完整 `src/` 与 `tests/` 工作树。对部分缓存目录运行不能代表目标分支。

### 4.2 第一组核心测试

```bash
python -m pytest \
  tests/test_structured_ingestion.py \
  tests/test_source_read_model.py \
  tests/test_source_service.py \
  tests/test_memory_inspector_facade.py \
  tests/test_memory_inspector_api.py \
  -v --tb=short
```

结果：

```text
NOT EXECUTED on the authoritative full branch worktree
```

### 4.3 第二组历史回归

```bash
python -m pytest \
  tests/test_memory_retrieval.py \
  tests/test_permanent_memory_gateway.py \
  tests/test_workspace_contract.py \
  tests/test_control_api.py \
  -v --tb=short
```

结果：

```text
NOT EXECUTED
```

按照门禁规则，第一组没有完成并通过，因此第二组不得被描述为已执行或通过。

## 5. 非权威环境诊断

为了确认缓存目录是否可用于验证，曾在 `/tmp/lingji_p203` 的部分文件副本上执行：

```bash
python -m pytest \
  tests/test_source_read_model.py \
  tests/test_source_service.py \
  tests/test_memory_inspector_facade.py \
  tests/test_memory_inspector_api.py \
  -v --tb=short
```

结果：

```text
collected: 0
collection errors: 4
duration: 0.74s
```

错误包括缺少：

```text
src.retrieval
src.gateway.adapters
src.control.runtime_settings
```

这些是“不完整缓存目录”的环境错误，不是目标分支测试失败，不能计入正式 passed/failed 数字，也不能用于 `VALIDATION_FAILED` 判定。

## 6. 正式测试数字

```text
Passed: NOT EXECUTED
Failed: NOT EXECUTED
Skipped: NOT EXECUTED
Xfailed: NOT EXECUTED
Duration: NOT AVAILABLE
py_compile / compileall: NOT EXECUTED
```

不得把文件读取、静态代码审查、blob SHA 一致或部分目录的导入错误描述成 pytest 通过。

## 7. 文件与提交一致性检查

缓存目录中存在的 P2-03 文件通过 `git hash-object` 与远程 blob SHA 对比，确认以下文件内容与远程目标提交一致：

```text
src/control/api.py
src/gateway/memory_inspector.py
src/sources/read_model.py
src/sources/service.py
tests/test_source_read_model.py
tests/test_source_service.py
tests/test_memory_inspector_facade.py
tests/test_memory_inspector_api.py
```

该检查只能证明这些单独文件内容一致，不能证明完整依赖树、导入行为或测试运行结果。

## 8. 十八项合同审查

| # | 合同 | 静态证据 | 运行验证状态 |
|---|---|---|---|
| 1 | `SourceReadModel` 包导出与直接模块导出为同一对象 | `src/sources/__init__.py` 直接导出；测试已编写 | `NOT EXECUTED` |
| 2 | `MemoryInspectorFacade` 包导出与直接模块导出为同一对象 | `src/gateway/__init__.py` 直接导出；测试已编写 | `NOT EXECUTED` |
| 3 | 三个旧包装文件不存在 | 三个路径远程读取均为 404 | 静态确认，pytest 未执行 |
| 4 | 未知 Schema Version 拒绝启动 | 正式实现抛出 `SourceReadModelError`；测试已编写 | `NOT EXECUTED` |
| 5 | Source 权限同步继承型 Conversation | SQL 同步逻辑和测试存在 | `NOT EXECUTED` |
| 6 | Conversation 权限同步继承型 Message | SQL 同步逻辑存在 | `NOT EXECUTED` |
| 7 | 显式子级覆盖不被父级覆盖 | inherited 标记逻辑和测试存在 | `NOT EXECUTED` |
| 8 | `rebuild_required` 保持 true/false/null | Facade 未强制转 bool；null 测试存在 | `NOT EXECUTED` |
| 9 | 503 不泄漏 SQLite 路径 | API 固定返回稳定 503；测试存在 | `NOT EXECUTED` |
| 10 | URL 用户名、密码、敏感参数和 fragment 删除 | `_safe_http_url()` 实现和测试存在 | `NOT EXECUTED` |
| 11 | ChatGPT 同时生成 Markdown 和结构化数据 | Adapter 共用标准化结果；测试存在 | `NOT EXECUTED` |
| 12 | Source/Conversation/Message 幂等写入 | 稳定 ID、Upsert 与真实临时 SQLite 测试存在 | `NOT EXECUTED` |
| 13 | Memory Link 缺失时不丢 Message | Structured Sink 降级逻辑和测试存在 | `NOT EXECUTED` |
| 14 | 索引失败不回滚 Vault 与结构化数据 | Pipeline 降级逻辑和测试存在 | `NOT EXECUTED` |
| 15 | Audit Event 写入 StateDatabase | `append_event()` 接线及真实临时 DB 测试存在 | `NOT EXECUTED` |
| 16 | Audit Event 失败不影响主流程 | `_event()` 捕获异常；测试存在 | `NOT EXECUTED` |
| 17 | 外部响应不泄漏 Windows 路径 | Extraction 与 503 路径有覆盖；发现 Vector 200 响应静态风险 | `STATIC BLOCKER / NOT EXECUTED` |
| 18 | Production 与 Acceptance 数据库隔离 | 临时目录隔离测试和 Workspace 测试存在 | `NOT EXECUTED` |

## 9. 静态阻塞风险：Vector 错误原文可能泄漏

发现一个可达的外部响应风险：

```text
src/gateway/memory_inspector.py
MemoryInspectorFacade.memory_vector()
```

当 live Semantic Provider（实时语义提供器）的 `exists()` 抛出异常时，代码执行：

```python
last_error = self._safe_error(exc)
```

当前 `_safe_error()` 返回：

```python
f"{type(exc).__name__}: {exc}"[:500]
```

随后该文本被放入每个 Chunk（文本分块）的：

```text
vector.chunks[].last_error
```

并通过 Memory Inspector Vector API（记忆检查器向量接口）以 HTTP 200 返回。

如果 Provider 异常包含：

```text
D:\Users\Secret\qdrant.db
```

该本机路径可能原样进入外部响应。顶层 `snapshot.last_error` 也被直接透传，存在同类风险。

这是对合同 17 的静态合并阻塞风险。现有测试覆盖了：

- Inspector 503 SQLite 路径脱敏。
- Extraction Pipeline 索引错误脱敏。
- ChatGPT warning 脱敏。

但没有覆盖 `memory_vector()` 的 live provider 异常路径。

### 最小修复建议

涉及文件：

```text
src/gateway/memory_inspector.py
tests/test_memory_inspector_facade.py
tests/test_memory_inspector_api.py
```

建议：

1. 完整 Provider 异常只写入 logger。
2. 对外 `last_error` 使用稳定摘要，例如：

```text
Vector status unavailable; see local logs
```

3. 对 `snapshot.last_error` 进入外部响应前采用同一安全合同。
4. 增加包含 Windows 路径的 Fake Semantic Provider 回归测试。
5. 验证 HTTP 200 vector response 不包含 `C:\`、`D:\`、`Users`、数据库文件名或异常原文。

根据本轮文件所有权规则，未直接修改 `src/gateway/memory_inspector.py`。

## 10. 失败根因分类

```text
Authoritative pytest failure: NONE RECORDED
Validation environment failure: YES
Static production contract risk: YES
```

环境根因：

```text
无法通过普通 Git 网络取得完整仓库
当前容器没有目标提交的完整工作树
缓存目录只是部分旧任务文件，依赖不完整
```

静态风险根因：

```text
MemoryInspectorFacade._safe_error() 保留异常原文
memory_vector() 将该原文写入 HTTP 200 响应的 last_error
相关路径缺少脱敏回归测试
```

## 11. Production Data Access（生产数据访问）

```text
Production ChatGPT Export: NO
Production Vault: NO
Production SQLite: NO
Production Qdrant: NO
Production Ollama: NO
Production Model: NO
Real User Content: NO
Production Configuration Modified: NO
```

## 12. 代码修改范围

```text
Production source code modified: NO
Tests modified: NO
Tauri modified: NO
New validation report: YES
Formal branch merged: NO
```

本轮仅新增该验证报告。

## 13. Known Risks（已知风险）

1. 正式 `compileall` 未执行。
2. 第一组核心 pytest 未执行。
3. 第二组历史回归未执行。
4. `memory_vector()` 存在 live provider 异常原文及 Windows 路径泄漏风险。
5. `snapshot.last_error` 进入 Vector API 前缺少统一外部脱敏合同。
6. 没有完整运行证据，不能确认 Python 3.13 下的导入、SQLite、FastAPI TestClient 和 Pydantic 兼容性。

## 14. Merge Recommendation（合并建议）

```text
DO_NOT_MERGE
```

原因：

1. 指定的 `compileall` 和两组 pytest 没有在完整目标提交上执行。
2. 合同 17 存在静态可达的 Vector HTTP 200 响应路径泄漏风险。
3. 缺少针对该风险的回归测试。

解除门禁条件：

```text
1. 在完整 work/p2-03b-validation 工作树执行 python -m compileall src tests
2. 第一组核心测试全部通过
3. 修复并覆盖 memory_vector() / snapshot.last_error 脱敏
4. 重新执行第一组核心测试并全部通过
5. 执行第二组历史回归并全部通过
6. 记录真实 passed / failed / skipped / xfailed / duration
7. 状态更新为 PASSED_AWAITING_COORDINATED_MERGE
```

## 15. 最终状态

```text
P2-03: IMPLEMENTED_NOT_TESTED
P2-03B: IMPLEMENTED_NOT_TESTED
Validation State: VERIFICATION_NOT_EXECUTED
Merge Recommendation: DO_NOT_MERGE
Formal Merge State: NOT_MERGED
```

本轮到此停止，不开始 P2-04，不领取新功能任务。
