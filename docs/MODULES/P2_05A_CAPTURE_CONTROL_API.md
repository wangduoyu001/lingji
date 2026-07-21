# P2-05A Capture Control API

> Updated（更新时间）: 2026-07-21  
> Branch（分支）: `work/p2-05a-capture-control-api`  
> Base Commit（基础提交）: `224c83881e934ffb9fd7c07b016a52ac8711ae1f`  
> Queue Finalization Commit（队列收口提交）: `8497b7c1dd0fd9f70e791779f060a5a5611fb726`  
> Control API Finalization Commit（接口收口提交）: `bbb370c237e741eee7b74bce29e3bc26e9192f95`  
> Status（状态）: `IMPLEMENTED_NOT_TESTED`  
> Merge State（合并状态）: `NOT_MERGED_AWAITING_COORDINATED_REVIEW`

## 1. 目标

P2-05A 提供 Manual Capture（手动采集）的本机 Control API（控制接口）、任务分页、取消、重试、暂停、恢复、脱敏 DTO（数据传输对象）和 Audit Event（审计事件）。

不包含 Desktop、Adapter 修改、新数据库或第二套任务队列。

## 2. 正式数据流

```text
Local Control API
-> CaptureControlService
-> CaptureService
-> ExtractionPipeline.enqueue()
-> SQLiteExtractionQueue
```

`CaptureControlService` 和其内部 `CaptureService` 在 Control App 生命周期内只构造一次，后续 HTTP 请求复用同一对象。文本、网页、文件和媒体均强制 `process_later=True`，不在请求线程调用同步 `execute()`。

## 3. 修改文件

```text
src/control/api.py
src/control/_api_core.py
src/control/capture.py
src/extraction/queue.py
src/extraction/_queue_core.py
tests/test_capture_control.py
tests/test_capture_api.py
tests/test_extraction_queue.py
docs/MODULES/P2_05A_CAPTURE_CONTROL_API.md
docs/TEST_REPORTS/P2_05A_CAPTURE_CONTROL_API_TEST_REPORT.md
```

`_api_core.py` 与 `_queue_core.py` 保存基础提交中的既有实现，公开入口仍分别是 `src/control/api.py::create_control_app` 和 `src/extraction/queue.py::SQLiteExtractionQueue`。没有创建第二个数据库、任务表或状态机。

这两个私有兼容内核属于本轮连接器提交方式产生的实现偏差，协调审查时必须确认是否接受，或者在完整本地工作树中合并回公开文件后再集成。

## 4. API

```text
POST /api/capture/text
POST /api/capture/web
POST /api/capture/file
POST /api/capture/media
GET  /api/capture/status
GET  /api/capture/capabilities
GET  /api/capture/jobs
GET  /api/capture/jobs/{job_id}
POST /api/capture/jobs/{job_id}/retry
POST /api/capture/jobs/{job_id}/cancel
POST /api/capture/pause
POST /api/capture/resume
POST /api/share
```

全部继续使用 `X-LingJi-Token`。提交新任务返回 HTTP 202；重复任务返回 HTTP 200；暂停或状态冲突返回 HTTP 409；不存在返回 HTTP 404；输入校验失败返回 HTTP 422；服务初始化异常返回稳定 HTTP 503。

提交响应至少包含：

```text
capture_id
status
job_id
duplicate
reason
```

兼容入口 `/api/share` 已移除旧同步执行路径，转发到同一个 `CaptureControlService`。

## 5. Capture Mode

`CaptureRuntimeSettingsStore` 复用现有 Runtime Settings（运行时设置）文件并增加：

```text
capture_mode = normal | low_power | paused
默认 = low_power
```

映射：

```text
normal    -> NORMAL
low_power -> LOW_POWER
paused    -> PAUSED
```

暂停只拒绝新提交，不删除既有任务。恢复默认回到 `low_power`。设置写入现有 Runtime Settings JSON，未创建新数据库。

## 6. Queue 合同

`SQLiteExtractionQueue` 新增：

```text
cancel(job_id)
retry(job_id)
get_by_idempotency_key(idempotency_key)
list_page(status, source_type, q, limit, offset)
count(status, source_type, q)
```

### cancel

```text
queued/retrying -> cancelled
completed_at = now
清除 locked_at / locked_by / lease_token / heartbeat_at
running/completed/cancelled -> 拒绝
```

### retry

```text
failed/cancelled -> queued
attempts = 0
last_error = null
result_json = null
completed_at = null
next_run_at = now
清除 lease 与旧进度
```

### list_page

分页直接通过 SQLite `LIMIT / OFFSET` 执行，支持 `status`、`source_type` 和 `q`。

```text
limit: 1-200
超出范围: ValueError
某 offset < 0: ValueError
```

旧 `list(status, limit)` 保持基础实现兼容，不受新的 200 上限影响。

## 7. 脱敏规则

Capture Job DTO 只返回：

```text
job_id
source_type
adapter_name
status
priority
attempts
max_attempts
progress_current
progress_total
progress_message
created_at
updated_at
completed_at
error_code
error_message
result_summary
result_refs
file_name
```

明确不返回：

```text
payload
options
完整 input_path
原始 last_error
lease_token
locked_by
heartbeat_at
正文全文
Token / Cookie / API Key
```

`file_name` 只返回 basename。失败任务对外只返回稳定摘要：

```text
Capture processing failed; see local logs
```

完整异常仅写 logger。

## 8. 稳定错误码

```text
CAPTURE_PAUSED
CAPTURE_FILE_NOT_FOUND
CAPTURE_FILE_TOO_LARGE
CAPTURE_JOB_NOT_FOUND
CAPTURE_JOB_RUNNING
CAPTURE_JOB_NOT_RETRYABLE
CAPTURE_JOB_NOT_CANCELLABLE
CAPTURE_SERVICE_UNAVAILABLE
CAPTURE_INVALID_INPUT
```

## 9. Audit Event

记录：

```text
capture_submitted
capture_duplicate
capture_paused
capture_resumed
capture_job_cancelled
capture_job_retried
```

Payload 只包含 capture/job/source/status/mode 等安全标识，不包含正文或绝对路径。审计写入失败使用 `logger.exception`，主操作继续。

## 10. 测试

隔离合同测试实际结果：

```text
18 passed
0 failed
0 skipped
0 xfailed
1.40s
```

完整权威工作树中的五文件集中 pytest 未执行，因此状态不能升级为 `IMPLEMENTED_FOCUSED_TESTED`。

## 11. 已知限制

```text
running 任务本阶段不强制终止
resume 固定恢复 low_power
未启动真实 Worker、Qdrant、Ollama 或 Desktop
完整仓库重点 pytest 尚未在权威工作树执行
私有兼容内核文件需要协调审查
```

## 12. 回滚方式

在协调合并前，可直接放弃分支 `work/p2-05a-capture-control-api`。若需要逐提交回滚，按相反顺序 revert 文档、Control API 和 Queue 提交；不需要迁移数据库，因为本轮没有修改 Schema。
