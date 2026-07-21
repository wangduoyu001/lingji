# P2-05C Capture Center Desktop UI

## 状态

```text
IMPLEMENTED_NOT_TESTED
NOT_MERGED_AWAITING_COORDINATED_REVIEW
```

## 页面

- PageId：`capture_center`
- 导航：`手动投喂中心`
- 描述：`提交文本、网页、文件和媒体`
- 页面：`desktop/lingji-control/src/pages/CaptureCenterPage.tsx`

Capture Center 只负责手动提交和用户任务操作。`JobsPage` 保持通用任务诊断职责，`MemoryInspectorPage` 继续负责结果关系查看。

## 组件与合同

- `captureCenterTypes.ts`：Capture DTO、分页、状态、Capabilities 和结果引用。
- `captureCenterContract.ts`：提交公共字段、校验、分页、操作权限、脱敏文件名和错误映射纯函数。
- `captureCenterApi.ts`：统一使用既有 `LingJiApi`，没有组件级重复 fetch。
- `CaptureCenterPage.tsx`：状态、提交 Tab、任务列表、详情、取消、重试和结果跳转。

## API

仅使用：

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
```

所有提交默认 `process_later=true`。任务分页大小固定为 30，并通过后端 `status/source_type/q/limit/offset` 查询。

## 提交表单

Tab：文本、网页、文件、媒体、ChatGPT Export、Codex Report。

公共字段：标题、项目、标签、隐私、优先级。隐私默认 `private`，支持 `restricted`。

文件模式：Web Snapshot、ChatGPT Export、Codex Report。媒体选项：OCR、转写、关键帧、提取音频。Capabilities 明确返回不支持时禁用对应控件并显示原因。

## Tauri Dialog

前端使用 `@tauri-apps/plugin-dialog` 的 `open()`：

```text
multiple: false
directory: false
```

Rust 注册：

```rust
.plugin(tauri_plugin_dialog::init())
```

权限仅增加：

```text
dialog:default
```

没有增加广泛 fs 权限、目录监听或文件常驻 scope。用户取消返回空值，不显示错误。

## 状态与竞态

- Loading、Empty、Filtered Empty、Unauthorized、Unavailable、Configuration Required、Paused、Partial Data、Submission Error 和 Job Conflict 均有稳定界面。
- 列表请求使用 `AbortController` 和 requestId。
- 页面 inactive 时停止轮询。
- 有活动任务时 2 秒轮询；无活动任务时降为 10 秒。
- 提交中禁用重复提交，成功后刷新列表。
- 取消和重试操作中禁用，409 显示稳定冲突提示。

## 任务操作

- queued/retrying：允许取消。
- failed/cancelled：允许重试。
- running：显示“处理中，当前版本不支持强制终止”。
- completed：有 result_refs 时显示“查看结果”，跳转 Memory Inspector。

结果引用只保存在 React 内存状态，不写入 localStorage。

## 隐私

任务列表和详情只显示 basename/title、稳定错误摘要、状态和 result_refs。不会渲染完整路径、payload、Token、Cookie、API Key、异常堆栈或 lease_token。restricted 任务有明确视觉标记。

## 已知限制

当前连接工具无法运行 npm/cargo，也无法自动生成 `package-lock.json` 和 `Cargo.lock`。依赖声明和插件接线已实现，但锁文件需在协调审查工作树执行 `npm install --package-lock-only` 与 `cargo check` 后提交。未将这一缺口伪装成已完成。

## 回滚

回滚本分支的 P2-05C 提交即可移除页面、Dialog Plugin 和 Smoke Test，不涉及 Python、数据库或生产数据。
