# P2-05A Capture Control API Test Report

> Updated（更新时间）: 2026-07-21  
> Branch（分支）: `work/p2-05a-capture-control-api`  
> Base Commit（基础提交）: `224c83881e934ffb9fd7c07b016a52ac8711ae1f`  
> Queue Finalization Commit（队列收口提交）: `8497b7c1dd0fd9f70e791779f060a5a5611fb726`  
> Control API Finalization Commit（接口收口提交）: `bbb370c237e741eee7b74bce29e3bc26e9192f95`  
> Verified Commit（权威验证提交）: `NOT_EXECUTED`  
> Status（状态）: `IMPLEMENTED_NOT_TESTED`  
> Merge State（合并状态）: `NOT_MERGED_AWAITING_COORDINATED_REVIEW`

## 1. 测试目标

覆盖：

```text
所有提交默认 enqueue
CaptureControlService 长生命周期
capture_mode 持久化
paused 拒绝提交
resume 恢复
SQLite 分页和筛选
取消 queued/retrying
拒绝取消 running/completed/cancelled
重试 failed/cancelled
拒绝重试 running/completed
DTO 脱敏
401 / 404 / 409 / 422
/api/share 转发
Audit Event
Audit 失败不影响主操作
```

## 2. 要求命令

```bash
python -m compileall -q \
  src/control \
  src/extraction/queue.py \
  tests/test_capture_control.py \
  tests/test_capture_api.py

python -m pytest \
  tests/test_capture_control.py \
  tests/test_capture_api.py \
  tests/test_control_api.py \
  tests/test_extraction_queue.py \
  tests/test_capture_service.py \
  -v --tb=short
```

## 3. 环境

```text
Operating System: Linux container
Python: available
pytest: 9.0.2
FastAPI: 0.128.2
Pydantic: 2.13.4
Authoritative full Git worktree: unavailable
GitHub remote writes: available through connector
```

普通 Git 无法解析 `github.com`，因此无法物化完整权威工作树。没有把隔离镜像结果冒充完整仓库验收，毕竟数字不因写进 Markdown 就获得神力。

## 4. compileall

实际执行：

```bash
cd /tmp/lingji_p205a
python -m compileall -q \
  src/control \
  src/extraction/queue.py \
  tests/test_capture_control.py \
  tests/test_capture_api.py
```

结果：

```text
PASS
syntax failures: 0
```

该结果只证明目标代码可编译，不等于集中 pytest 已通过。

## 5. 隔离合同测试

实际重新执行：

```bash
cd /tmp/lingji_p205a
PYTHONPATH=. python -m pytest \
  tests/test_capture_control.py \
  tests/test_capture_api.py \
  tests/test_extraction_queue.py \
  -q --tb=short
```

结果：

```text
passed: 18
failed: 0
skipped: 0
xfailed: 0
duration: 1.40s
```

使用：

```text
TemporaryDirectory
临时 SQLite
FastAPI TestClient
Fake Pipeline
Fake Capture Service / Audit Store
小型临时文件
```

没有访问生产数据。

## 6. 合同结果

```text
文本默认 enqueue: PASS
网页默认 enqueue: PASS
文件默认 enqueue: PASS
媒体默认 enqueue: PASS
HTTP 内同步 execute 禁止: PASS
真实 job_id: PASS
CaptureControlService 长生命周期: PASS
capture_mode 默认 low_power: PASS
capture_mode 持久化: PASS
paused 拒绝提交: PASS
resume 恢复: PASS
SQLite LIMIT/OFFSET 分页: PASS
status/source_type/q 筛选: PASS
cancel queued/retrying: PASS
cancel running/completed/cancelled 拒绝: PASS
retry failed/cancelled: PASS
retry running/completed 拒绝: PASS
DTO 白名单与 basename: PASS
原始 last_error / input_path / lease 字段隐藏: PASS
401 / 404 / 409 / 422: PASS
/api/share 转发: PASS
Audit Event: PASS
Audit 失败主操作继续: PASS
```

## 7. 未执行的权威集中测试

以下命令未能在完整工作树执行：

```bash
python -m pytest \
  tests/test_capture_control.py \
  tests/test_capture_api.py \
  tests/test_control_api.py \
  tests/test_extraction_queue.py \
  tests/test_capture_service.py \
  -v --tb=short
```

正式统计：

```text
passed: NOT EXECUTED
failed: NOT EXECUTED
skipped: NOT EXECUTED
xfailed: NOT EXECUTED
duration: NOT AVAILABLE
```

因此最终状态保持：

```text
IMPLEMENTED_NOT_TESTED
NOT_MERGED_AWAITING_COORDINATED_REVIEW
```

## 8. 数据与边界

```text
Production ChatGPT Export accessed: NO
Production Vault accessed: NO
Production SQLite accessed: NO
Production database modified: NO
Production Qdrant accessed: NO
Production Ollama accessed: NO
Real user content accessed: NO
Desktop modified: NO
Adapter modified: NO
Database Schema modified: NO
New database created: NO
Second queue created: NO
Formal branch merged: NO
```

## 9. 已知风险

```text
1. 仍需在完整工作树运行指定五文件 pytest。
2. src/control/_api_core.py 与 src/extraction/_queue_core.py 是连接器提交形成的私有兼容内核，超出原始文件所有权清单，需要协调审查。
3. running 任务不支持强制终止，这是本阶段明确限制。
4. resume 默认恢复 low_power，不恢复暂停前的 normal 状态。
```

## 10. Merge Recommendation

```text
DO_NOT_MERGE_UNTIL_FOCUSED_TESTS_PASS
```

解除门禁条件：

```text
1. 在完整 work/p2-05a-capture-control-api 工作树运行任务指定 compileall。
2. 执行五文件集中 pytest。
3. failed = 0。
4. 记录真实 passed / failed / skipped / xfailed / duration。
5. 协调者决定是否接受私有兼容内核，或在完整本地工作树将其折回公开文件。
```
