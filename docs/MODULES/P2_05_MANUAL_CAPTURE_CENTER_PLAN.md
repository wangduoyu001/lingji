# P2-05 Manual Capture Center Plan

> Updated: 2026-07-21  
> Formal Branch: `feature/second-brain-memory`  
> Planning Base Commit: `21fd3ed8093fd2cf06c774682127a0377fae034e`  
> Status: `PLANNED_AWAITING_PARALLEL_IMPLEMENTATION`

## 1. 目标

P2-05 建立 Manual Capture Center（手动信息入口中心）。

用户通过 LingJi Desktop 主动提交内容，并看到完整任务状态：

```text
手动提交
-> CaptureService
-> ExtractionPipeline.enqueue()
-> SQLiteExtractionQueue
-> ExtractionWorker
-> Vault / Raw
-> Memory / Structured Read Model
-> Memory Inspector
```

本阶段优先形成稳定可用闭环，不追求自动监听所有设备和平台。

## 2. 明确不做

用户已明确暂不开发：

```text
系统监听
剪贴板监听
文件夹监听
手机分享客户端
浏览器插件
抖音、小红书、公众号等平台专用客户端
```

P2-05 不注册操作系统 Watcher，不接入全局键盘，不读取浏览器 Cookie，不实现移动端分享扩展。

## 3. 当前代码事实

### 3.1 已有 CaptureService

正式位置：

```text
src/capture/service.py::CaptureService
```

已具备：

- 文本、网页、文件、媒体提交方法。
- CapturePolicy。
- 两阶段去重 `probe -> success -> commit`。
- Metadata 敏感字段递归检查。
- `process_later` 强制排队。

当前限制：

- 尚未接入 LocalControlService。
- `status()` 和 pause/resume 仅为进程内状态。
- 部分 helper 默认仍使用 `clipboard`、`browser_extension` 等历史 capture_method，需要手动入口语义收口。

### 3.2 已有持久化队列

正式位置：

```text
src/extraction/queue.py::SQLiteExtractionQueue
```

现有 `extraction_jobs` 已包含：

- queued/running/retrying/completed/failed/cancelled 状态。
- attempts/max_attempts。
- progress_current/progress_total/progress_message。
- last_error/result。
- idempotency_key。
- lease、heartbeat 和 stale recovery。

P2-05 禁止创建第二套 Capture 任务表或第二套队列。

当前缺口：

- 没有正式的用户取消方法。
- 没有正式的用户手动重试方法。
- list 仅支持 status 和 limit，缺少分页、来源、关键词等 UI 查询合同。
- Queue Row 包含内部 payload/input_path，不能未经脱敏直接暴露给 Desktop。

### 3.3 已有 Local Control API

正式位置：

```text
src/control/api.py
src/control/service.py::LocalControlService
```

已有：

- `GET /api/jobs`
- `GET /api/jobs/{job_id}`
- `POST /api/share`

当前 `/api/share` 直接调用 ExtractionPipeline，绕过 CaptureService；文件路径任务排队，纯文本和网页会立即执行。

P2-05 必须让手动投喂统一经过 CaptureService，并默认进入持久化队列。

### 3.4 已有 Desktop JobsPage

正式位置：

```text
desktop/lingji-control/src/pages/JobsPage.tsx
```

当前只提供简单任务表和状态筛选。P2-05 新建独立 Capture Center 页面；JobsPage 保留为通用诊断页，不承担提交表单和 Memory 结果关系。

### 3.5 Tauri 文件选择现状

当前 Tauri 仅注册 `control_credentials` command，未安装文件对话框插件：

```text
desktop/lingji-control/src-tauri/Cargo.toml
desktop/lingji-control/src-tauri/src/main.rs
desktop/lingji-control/src-tauri/capabilities/default.json
```

P2-05 使用官方 Tauri 2 Dialog Plugin 选择本地文件路径：

```text
@tauri-apps/plugin-dialog
tauri-plugin-dialog
```

只授予主窗口对话框所需最小权限，不引入全文件系统常驻权限，不实现目录监听。

## 4. 设计原则

1. **手动提交全部排队**  
   文本和网页也默认 enqueue，避免 UI 请求阻塞，并确保状态、重试和审计统一。

2. **只复用现有队列**  
   Capture Job 就是 Extraction Job 的用户可见投影，不创建第二套状态机。

3. **API 返回脱敏 DTO**  
   默认不返回完整正文、绝对路径、Token、Cookie、内部 payload 或异常堆栈。

4. **Memory Inspector 负责结果查看**  
   Capture Center 只显示任务和结果引用；完成后通过 Memory/Source ID 跳转到 Memory Inspector。

5. **不伪造进度**  
   Worker 没有发布精确进度时显示步骤状态或“未知”，不能用定时器假装百分比增长。

6. **取消边界明确**  
   queued/retrying/failed 可取消或重试；running 本阶段不做强制终止，只返回稳定冲突提示。

7. **保持兼容**  
   `/api/share` 保留为兼容入口，但内部转发到新的 Capture Control Service，不保留第二条执行链。

## 5. 正式架构

```text
CaptureCenterPage
  -> Capture API Client
       -> /api/capture/*
            -> LocalControlService
                 -> CaptureControlService
                      -> CaptureService
                           -> ExtractionPipeline.enqueue()
                                -> SQLiteExtractionQueue
                                     -> ExtractionWorker
                                          -> Vault / Raw
                                          -> Memory Index
                                          -> Structured Read Model
                                          -> Audit Event
```

建议新增：

```text
src/control/capture.py::CaptureControlService
```

职责：

- 组装长生命周期 CaptureService。
- 从 RuntimeSettingsStore 构建 CapturePolicy。
- 统一手动提交模型。
- 将 Queue Row 转换为脱敏 CaptureJob DTO。
- 提供列表、详情、取消、重试、暂停和恢复。
- 解析完成结果中的 Memory、Source、Conversation 引用。

不得把平台解析逻辑写进 CaptureControlService。

## 6. Capture Method 收口

P2-05 正式使用：

```text
manual_text
manual_web
manual_file
manual_media
manual_chatgpt_export
manual_codex_report
local_control_share
```

保留旧 method 仅用于兼容已有输入合同，但 Desktop 不再使用：

```text
clipboard
folder_watch
browser_extension
mobile_share
```

## 7. 手动输入类型

### 第一批正式支持

```text
文本粘贴
网页 URL + 可选正文/选中文字
ChatGPT Export ZIP/JSON
Codex Work Report JSON
普通 Web Capture JSON/HTML/TXT
媒体文件路径
```

### 文件分类

提交文件时根据用户选择或扩展名映射：

```text
.zip/.json + ChatGPT 模式 -> chatgpt_export
.json + Codex 模式       -> codex_report
媒体扩展名               -> media
网页快照/文本             -> web
```

P2-05 不新增通用 PDF、DOCX 解析器。若现有 Adapter 不能处理，UI 必须明确显示“当前版本暂不支持”，不得把文件塞给错误 Adapter。

## 8. API 合同

### 8.1 提交

```text
POST /api/capture/text
POST /api/capture/web
POST /api/capture/file
POST /api/capture/media
```

公共字段：

```text
title
project_ids
tags
privacy
priority
process_later
metadata
```

文本：

```text
text
source_type（默认 web）
```

网页：

```text
url
text
html
author
published_at
platform
```

文件：

```text
input_path
source_type
adapter_name（可选）
```

媒体：

```text
input_path
allow_ocr
allow_transcription
extract_keyframes
```

所有 Desktop 提交默认：

```text
process_later = true
```

### 8.2 查询

```text
GET /api/capture/status
GET /api/capture/capabilities
GET /api/capture/jobs
GET /api/capture/jobs/{job_id}
```

Jobs Query：

```text
status
source_type
q
limit（1-200）
offset
```

返回统一分页：

```json
{
  "items": [],
  "pagination": {
    "limit": 30,
    "offset": 0,
    "total": 0
  },
  "stats": {}
}
```

### 8.3 操作

```text
POST /api/capture/jobs/{job_id}/retry
POST /api/capture/jobs/{job_id}/cancel
POST /api/capture/pause
POST /api/capture/resume
```

状态规则：

```text
queued/retrying -> cancel allowed
failed/cancelled -> retry allowed
running          -> cancel/retry returns 409
completed        -> retry returns 409；用户可重新提交原内容
```

## 9. 脱敏 CaptureJob DTO

列表默认字段：

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
```

禁止默认返回：

```text
payload
options
input_path 绝对路径
last_error 原文
lease_token
locked_by
heartbeat 内部细节
正文全文
```

文件名可返回 basename，完整路径只允许后端日志使用。

## 10. 错误合同

稳定错误码至少包括：

```text
CAPTURE_PAUSED
CAPTURE_UNSUPPORTED_TYPE
CAPTURE_FILE_NOT_FOUND
CAPTURE_FILE_TOO_LARGE
CAPTURE_DUPLICATE
CAPTURE_JOB_NOT_FOUND
CAPTURE_JOB_RUNNING
CAPTURE_JOB_NOT_RETRYABLE
CAPTURE_JOB_NOT_CANCELLABLE
CAPTURE_SERVICE_UNAVAILABLE
```

完整异常只写 logger。

## 11. Queue 扩展

允许在现有 `SQLiteExtractionQueue` 增加：

```text
cancel(job_id)
retry(job_id)
list_page(status, source_type, q, limit, offset)
count(...)
```

禁止新增任务表。

`cancel()`：

- queued/retrying -> cancelled。
- failed -> cancelled 可保持 terminal。
- running -> 拒绝，不做进程强杀。

`retry()`：

- failed/cancelled -> queued，清理 error、lease、progress 和 completed_at。
- attempts 重置为 0。
- completed/running/queued/retrying -> 拒绝。

所有状态变化写 Audit Event。

## 12. Pause/Resume 持久化

在 RuntimeSettingsStore 增加：

```text
capture_mode
```

允许值：

```text
normal
low_power
paused
```

默认：

```text
low_power
```

P2-05 不启用 watcher，因此该设置只控制手动任务是否接收，以及重媒体任务策略。

## 13. Desktop 页面

新增：

```text
CaptureCenterPage
手动投喂中心
```

页面结构：

### 顶部状态

- Capture Mode。
- 待处理、处理中、重试中、完成、失败、取消数量。
- Worker 是否可用。
- 最近更新时间。

### 提交区

Tab：

```text
文本
网页
文件
媒体
ChatGPT Export
Codex Report
```

字段：

- 标题。
- 项目。
- 标签。
- 隐私。
- 优先级。
- 文本/URL/文件路径。
- 处理选项。

### 任务区

- 状态筛选。
- 来源筛选。
- 搜索。
- 后端分页。
- 刷新。
- 取消。
- 重试。
- 查看详情。
- 完成后跳转 Memory Inspector。

### 详情抽屉

- 当前步骤。
- 尝试次数。
- 稳定错误摘要。
- 结果引用。
- 时间信息。

不得显示原始绝对路径和完整 payload。

## 14. Tauri 文件选择

使用官方 Tauri 2 Dialog Plugin：

```text
Cargo:
tauri-plugin-dialog

npm:
@tauri-apps/plugin-dialog
```

接线：

```text
src-tauri/src/main.rs
  -> .plugin(tauri_plugin_dialog::init())

src-tauri/capabilities/default.json
  -> dialog:default
```

Frontend 使用 `open()` 返回用户主动选择的文件路径。

边界：

- 不增加目录 watcher。
- 不申请广泛文件系统常驻权限。
- 不保存文件选择 scope。
- 不读取未被用户选择的文件。

## 15. 三工程师边界

### 1号：P2-05A Capture Control API

负责：

```text
src/control/capture.py
src/control/api.py
src/control/service.py
src/control/runtime_settings.py
src/extraction/queue.py
相关 Python tests
```

不得修改 Desktop。
不得修改 Adapter 解析逻辑。

### 2号：P2-05B Manual Import Wiring

负责：

```text
src/capture/
src/extraction/adapters/
src/extraction/bootstrap.py
手动导入映射和测试
```

主要任务：

- Manual capture_method 收口。
- ChatGPT/Codex/Web/Media 手动提交适配。
- 文件类型和 Adapter 映射。
- 不支持类型稳定拒绝。
- 保持旧 Markdown 和结构化输出兼容。

不得修改 Control API。
不得修改 Desktop。

### 3号：P2-05C Capture Center Desktop UI

负责：

```text
desktop/lingji-control/
```

主要任务：

- CaptureCenterPage。
- Capture API Client 和类型。
- Tauri Dialog Plugin。
- 提交表单、任务状态、重试取消和 Memory Inspector 跳转。

不得修改 Python 后端。

## 16. 并行开发规则

1. 三人从同一个正式基础提交创建分支。
2. 1号先冻结 API DTO 文档，3号用 Mock 合同并行开发。
3. 2号不得新增 API；只实现 CaptureService 和 Adapter 输入合同。
4. 共享文档只由协调者在集成阶段更新。
5. 三人不得修改 `docs/PROJECT_STATUS.md`、`docs/CHANGELOG.md`、`docs/MODULES/CODE_MAP.md`。
6. 每个任务必须新增模块文档和测试报告。
7. 未执行测试必须保持 `IMPLEMENTED_NOT_TESTED`。

## 17. 测试门禁

### 1号

- Queue cancel/retry 状态合同。
- Capture API 认证、分页、脱敏、409、404。
- `/api/share` 兼容转发。
- Runtime capture mode 持久化。

### 2号

- Manual method 映射。
- ChatGPT/Codex/Web/Media 正确 Adapter。
- 不支持文件稳定拒绝。
- 路径和敏感信息脱敏。
- 旧输出兼容。

### 3号

- 表单验证。
- 文件选择取消。
- API 错误状态。
- 后端分页。
- 取消/重试按钮状态。
- restricted/privacy 显示。
- Memory Inspector 跳转。
- `npm run build`。

### 集成门禁

```text
python -m compileall src tests
P2-05 Python focused pytest
P2-03 → P2-04 regression pytest
npm run test:smoke
npm run build
```

## 18. 完成定义

P2-05 完成时，用户能够：

1. 在 Desktop 主动提交文本、网页、已支持文件和媒体。
2. 关闭并重开 Desktop 后仍能看到持久化任务。
3. 查看排队、运行、重试、完成、失败和取消状态。
4. 对失败任务进行手动重试。
5. 对尚未运行的任务执行取消。
6. 查看稳定错误摘要，不泄漏本机敏感路径。
7. 从完成任务跳转到 Memory Inspector 查看最终关系。
8. 全流程不依赖系统监听、手机客户端或浏览器插件。
