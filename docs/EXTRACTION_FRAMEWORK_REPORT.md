# 灵机统一提取框架开发报告

> 文档角色：历史实施/验证快照，不是当前进度或当前架构权威。
> 当前状态看 `docs/PROJECT_STATUS.md`；当前代码入口看 `docs/MODULES/CODE_MAP.md`。

## 1. 本阶段目标

本阶段完成四项基础能力：

1. 统一提取框架。
2. 基于 SQLite 的持久化任务队列。
3. ChatGPT 官方数据导入器。
4. Codex 工作报告写回。

所有功能复用现有单一 Obsidian Vault、`storage/lingji_state.db`、Memory Gateway 和审计事件，不新建第二套状态数据库。

## 2. 总体架构

```text
外部来源
  ↓
ExtractionAdapter
  ↓
ExtractionBatch
  ↓
VaultExtractionSink
  ├── storage/raw/ 保存原始快照
  └── Obsidian Vault 保存标准化 Markdown

异步任务：
提交请求
  ↓
SQLiteExtractionQueue
  ↓
ExtractionWorker
  ↓
ExtractionPipeline
  ↓
Adapter + Sink
```

核心模块：

| 文件 | 职责 |
|---|---|
| `src/extraction/models.py` | 统一请求、文档和批次数据模型 |
| `src/extraction/base.py` | 提取适配器接口 |
| `src/extraction/registry.py` | 适配器注册和解析 |
| `src/extraction/queue.py` | SQLite 持久化任务队列 |
| `src/extraction/pipeline.py` | 入队、执行、重试和批处理 |
| `src/extraction/sink.py` | 原始快照、Markdown 标准化和目录路由 |
| `src/extraction/worker.py` | 后台队列 Worker |
| `src/extraction/bootstrap.py` | 运行时组装 |

## 3. SQLite 任务队列

队列复用：

```text
storage/lingji_state.db
```

新增表：

```text
extraction_jobs
```

主要状态：

```text
queued
retrying
running
completed
failed
cancelled
```

每个任务保存：

- `job_id`
- `source_type`
- `adapter_name`
- `input_path`
- `payload_json`
- `options_json`
- `idempotency_key`
- `status`
- `priority`
- `attempts`
- `max_attempts`
- `next_run_at`
- `locked_at`
- `locked_by`
- `last_error`
- `result_json`
- 创建、更新和完成时间

### 3.1 幂等策略

幂等键由以下信息共同生成：

- 来源类型
- 适配器名称
- 适配器版本
- 输入文件 SHA-256 或目录清单
- 请求 Payload

同一输入不会重复创建任务。处理器升级后，由于适配器版本变化，可以重新处理旧数据。

### 3.2 并发和重试

- 使用 SQLite `BEGIN IMMEDIATE` 原子领取任务。
- 任务领取后记录 Worker 和锁定时间。
- 失败后指数退避，默认最多三次。
- 超过最大次数进入 `failed`。
- Worker 异常退出后，过期锁会被释放为 `retrying`。
- 支持 `force` 将已完成或失败的同一任务重新入队。

## 4. 原始数据和标准化数据

### 4.1 原始快照

文件原始快照保存到：

```text
storage/raw/<source_type>/<sha256>/
```

单文件直接复制并保留文件名。目录输入生成带文件路径、大小和 SHA-256 的清单。

原始数据只追加，不由提取器覆盖或删除。

### 4.2 标准化 Markdown

所有适配器输出 `ExtractedDocument`，再由统一 Sink 写入 Vault。Frontmatter 至少包含：

```yaml
schema_version: 1
id: LJ-...
title: ...
memory_type: ...
source_type: ...
external_id: ...
status: active
privacy: private
project: []
created_at: ...
updated_at: ...
captured_at: ...
extractor: ...
extractor_version: ...
content_hash: ...
raw_snapshot_path: ...
raw_sha256: ...
```

输出文件名只依赖稳定 ID。标题变化只更新原文件，不产生重复笔记。

## 5. ChatGPT 导入器

适配器：

```text
chatgpt_export 1.0.0
```

支持输入：

- ChatGPT 官方导出 ZIP。
- `conversations.json`。
- 编号的 conversation JSON 文件。
- 已解压的导出目录。

支持的 JSON 结构：

- 顶层对话数组。
- 包含 `conversations`、`items` 或 `data` 的对象。
- 单个 Conversation 对象。

### 5.1 提取内容

- Conversation ID
- 标题
- 创建和更新时间
- 当前节点
- 全部消息
- 用户、助手、系统和工具角色
- 模型标识
- 附件元数据
- 父节点关系
- 非当前分支消息

同一 Conversation ID 重复出现时，保留更新时间较新的版本。

### 5.2 输出目录

```text
02-Sources/Conversations/ChatGPT/YYYY/MM/LJ-CHATGPT-<conversation-id>.md
```

历史 Unix 时间戳统一按 UTC 解析，避免不同电脑时区造成日期漂移。

### 5.3 命令行

立即导入：

```powershell
python scripts/import_chatgpt_export.py "D:\exports\chatgpt.zip"
```

指定项目：

```powershell
python scripts/import_chatgpt_export.py "D:\exports\chatgpt.zip" --project LingJi
```

只入队：

```powershell
python scripts/import_chatgpt_export.py "D:\exports\chatgpt.zip" --enqueue-only
```

强制重跑：

```powershell
python scripts/import_chatgpt_export.py "D:\exports\chatgpt.zip" --force
```

## 6. Codex 写回

适配器：

```text
codex_work_report 1.0.0
```

Codex 完成一个经过测试的任务后，应提交结构化工作报告。

建议字段：

```json
{
  "task_id": "task-001",
  "project_id": "LingJi",
  "title": "任务标题",
  "repository": "owner/repository",
  "branch": "feature/example",
  "summary": "完成内容",
  "status": "completed",
  "started_at": "2026-07-19T10:00:00",
  "completed_at": "2026-07-19T11:00:00",
  "changed_files": [],
  "tests": [],
  "test_result": "",
  "commits": [],
  "pull_requests": [],
  "errors": [],
  "decisions": [],
  "remaining_tasks": [],
  "artifacts": [],
  "notes": ""
}
```

### 6.1 输出路由

主报告：

```text
05-Operations/Work-Reports/<project>/YYYY/MM/
```

错误：

```text
05-Operations/Errors/<project>/YYYY/MM/
```

决策候选：

```text
05-Operations/Decisions/Candidates/<project>/YYYY/MM/
```

后续任务候选：

```text
05-Operations/Tasks/Inbox/<project>/YYYY/MM/
```

决策和任务默认：

```yaml
status: needs_review
owner_confirmed: false
```

它们不会被自动批准或直接变成核心记忆。

### 6.2 命令行

立即写回：

```powershell
python scripts/submit_codex_report.py examples/codex_work_report.example.json
```

从标准输入读取：

```powershell
Get-Content report.json | python scripts/submit_codex_report.py -
```

进入异步队列：

```powershell
python scripts/submit_codex_report.py report.json --queue
```

## 7. MCP 工具

新增工具：

```text
enqueue_chatgpt_export
submit_codex_work_report
extraction_job_status
extraction_queue_status
process_extraction_jobs
```

新增资源：

```text
lingji://extraction/queue
```

`submit_codex_work_report` 采用立即写回，便于 Codex 在任务结束前获得明确结果。ChatGPT 大型导出默认进入持久化队列，也可以指定立即处理。

## 8. 服务运行

`python run_service.py` 会在主服务启动后同时启动 Extraction Worker。

可通过 `.env` 调整：

```text
EXTRACTION_WORKER_ENABLED=true
EXTRACTION_POLL_SECONDS=5
EXTRACTION_BATCH_SIZE=5
EXTRACTION_MAX_ATTEMPTS=3
```

也可以单独运行：

```powershell
python run_extraction_worker.py
```

## 9. 测试

新增测试：

```text
tests/test_extraction_queue.py
tests/test_chatgpt_importer.py
tests/test_codex_writeback.py
tests/test_extraction_worker.py
```

覆盖内容：

- 队列幂等入队。
- 原子领取和完成。
- 重试和最终失败。
- 强制重跑。
- 僵尸任务释放。
- ChatGPT JSON 导入。
- ChatGPT ZIP 导入。
- 分支消息和模型信息。
- 原始快照。
- Codex 报告拆分。
- 重复写回不产生重复文件。
- Worker 启停和任务消费。

完整 GitHub Actions 验证：

```text
Ran 51 tests
OK
```

同时通过：

- Python 3.11 单元测试与编译检查。
- Python 3.12 单元测试与编译检查。
- MCP Server 创建 smoke test。

本机真实 Vault 合并前仍应执行：

```powershell
python -m unittest discover -s tests -v
python -m compileall -q main.py run_service.py run_mcp_server.py run_extraction_worker.py src tests scripts
```

## 10. 当前限制

- ChatGPT 附件目前保存元数据和原始导出快照，不主动复制每个附件到 Obsidian Attachments。
- ChatGPT 项目名称未必存在于导出数据，可通过 `--project` 显式指定。
- Codex 写回依赖 Codex 或调用方提交结构化报告，不通过猜测 Git diff 自动生成全部字段。
- 独立 MCP 进程写入后，主服务 Watchdog 或下次完整重建负责更新召回索引。
- 浏览器、微信、手机、GitHub 和视频适配器尚未开发，但可以复用同一框架。
