# P2-04 Memory Inspector Desktop UI

状态：`IMPLEMENTED_NOT_TESTED`

## 目标

在正式 Tauri + React 控制中心中提供只读 Memory Inspector（记忆检查器），展示 Source → Conversation → Message → Memory → Chunk → Vector 的真实关系。不修改后端 Schema、SourceReadModel、采集 Pipeline 或 Qdrant。

## 页面入口

- 导航：`记忆检查器`
- PageId：`memory_inspector`
- 页面：`desktop/lingji-control/src/pages/MemoryInspectorPage.tsx`
- 样式：`MemoryInspectorPage.css`

## 页面结构

1. 顶部状态条：Source、Conversation、Message、Memory、Chunk、Vector 覆盖、读取模型状态、三态重建状态、最后更新时间。
2. 筛选区：来源类型、项目、隐私、状态、角色、关键词、开始时间、结束时间、刷新。
3. 三栏主视图：Source 列表、Conversation 列表、Message 时间线。
4. 右侧抽屉：Message 正文、关联 Memory、来源关系、Chunk/Vector 返回数据。

## API 映射

仅调用既有只读接口：

- `/api/memory/inspector/status`
- `/api/memory/inspector/sources`
- `/api/memory/inspector/conversations`
- `/api/memory/inspector/messages`
- `/api/memory/inspector/messages/{message_id}`
- `/api/memory/inspector/memories/{memory_id}`
- `/api/memory/inspector/memories/{memory_id}/source`
- `/api/memory/inspector/memories/{memory_id}/vector`

未发明新接口。字段存在差异时使用真实响应字段，并对缺失关系显示明确空状态。

## API Client

`LingJiApi` 增加：

- `ApiError(status, code, message)` 统一错误。
- `AbortSignal` 取消请求。
- 默认 15 秒超时。
- 复用现有 Base URL 与 Token。
- 不在组件内直接调用 `fetch`。

## 状态机

- Loading：刷新按钮显示“读取中”。
- Empty：区分“系统正常但未导入”和“筛选后没有结果”。
- Unauthorized：401 显示本地授权或 Token 配置提示。
- Unavailable：503/READ_MODEL_UNAVAILABLE 显示结构化读取模型暂不可用。
- Network unavailable：显示本机控制服务不可用。
- Partial Data：Memory 的 source/vector 子请求采用 `Promise.allSettled`，部分失败不伪造状态。
- Configuration Required：由 status state 原样显示。

## 筛选合同

分页大小固定为 30，小于后端最大 200。分页通过 `limit` 与 `offset` 发送到后端。筛选、关键词和时间范围作为 Query 参数发送，未在前端加载全量数据伪造分页。关键词采用 300ms 防抖。筛选变化会中止旧请求，并使用递增 request id 防止旧结果覆盖新结果。

## 隐私处理

- `restricted` 条目有橙色左边界。
- 列表不主动展示完整敏感正文。
- restricted Message 正文必须通过 `<details>` 主动展开。
- 页面不把本地路径、Token、Cookie 或 API Key放入标题、通知和日志摘要。
- 后端错误仅转换为稳定用户提示。

## 三态处理

`rebuild_required`：

- `true`：需要重建
- `false`：无需重建
- `null/undefined`：未知

未知计数统一显示“未知”，不显示为 0。

## 后续 Capture Center 接入位置

Capture Center 后续只能在已有采集后端完成后，通过 Source 列表的 `source_id` 跳转到 Inspector。P2-04 不新增信息入口后端，也不修改 Capture Pipeline。

## 未实现内容

- 未新增后端 Message → Memory 字段。接口未返回关系时显示明确空状态。
- 未开发 Capture Center UI。
- 未运行本地 npm、Tauri、生产后端、Qdrant 或 Ollama。
