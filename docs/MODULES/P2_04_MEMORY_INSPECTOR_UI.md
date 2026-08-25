# P2-04 Memory Inspector Desktop UI

> 文档角色：历史实施/验证快照，不是当前进度或当前架构权威。
> 当前状态看 `docs/PROJECT_STATUS.md`；当前代码入口看 `docs/MODULES/CODE_MAP.md`。

状态：

```text
IMPLEMENTED_NOT_TESTED
COORDINATED_REVIEW_FIXES_IMPLEMENTED
NOT_MERGED
```

## 目标

在正式 Tauri + React 控制中心中提供只读 Memory Inspector（记忆检查器），展示 Source → Conversation → Message → Memory → Chunk → Vector 的真实关系。不修改后端 Schema、SourceReadModel、采集 Pipeline、Qdrant 或任何 Python 业务实现。

## 页面入口

- 导航：`记忆检查器`
- PageId：`memory_inspector`
- 页面：`desktop/lingji-control/src/pages/MemoryInspectorPage.tsx`
- 类型：`memoryInspectorTypes.ts`
- Query 与响应映射：`memoryInspectorContract.ts`
- 样式：`MemoryInspectorPage.css`

## 页面结构

1. 顶部状态条：Source、Conversation、Message、Memory、Chunk、Vector 覆盖、Vector 状态、三态重建状态、最后更新时间。
2. 筛选区：来源类型、项目、隐私、状态、角色、关键词、开始时间、结束时间、刷新。
3. 三栏主视图：Source 列表、Conversation 列表、Message 时间线。
4. 右侧抽屉：Message 正文、Memory Link、Memory 详情、Canonical 来源、Message Links、Vector Chunks。

## API 映射

仅调用现有只读接口：

- `/api/memory/inspector/status`
- `/api/memory/inspector/sources`
- `/api/memory/inspector/conversations`
- `/api/memory/inspector/messages`
- `/api/memory/inspector/messages/{message_id}`
- `/api/memory/inspector/memories/{memory_id}`
- `/api/memory/inspector/memories/{memory_id}/source`
- `/api/memory/inspector/memories/{memory_id}/vector`

未发明新接口。

## Query 参数合同

Source：

```text
source_type privacy project status q limit offset
```

Conversation：

```text
source_id source_type privacy project from_time to_time q limit offset
```

Message：

```text
conversation_id source_id role from_time to_time q limit offset
```

Message 不发送 `project/privacy/status/source_type`。所有接口使用真实参数 `q/from_time/to_time`，不再发送 `keyword/start_time/end_time`。

## Status 嵌套映射

`/status` 使用正式嵌套结构：

- `sources.sources`
- `sources.conversations`
- `sources.messages`
- `memory.documents`
- `memory.chunks`
- `vector.coverage`
- `vector.state`
- `vector.rebuild_required`

缺失字段保持 `null`，UI 显示“未知”，不伪造 0。

## 正式字段优先级

- Source：`display_name`、`projects`
- Conversation：`participants`、`projects`
- Message：`occurred_at`、`content_preview`、`metadata.model`、`metadata.is_branch`

数组字段通过 `formatList()` 转换为可读文本，不直接渲染对象或默认逗号字符串。

## Message → Memory

Message 详情同时保存：

```text
item
memory_links
```

Memory Link 显示：

- `memory_id`
- `relation_type`
- `confidence`

点击后读取现有三个 Memory 接口。

## Memory Source 与 Vector 解包

Vector 从 `response.vector` 读取：

- `state`
- `rebuild_required`
- `chunks`

Memory Source 从以下字段读取：

- `canonical.relative_path`
- `canonical.citation`
- `links[]`

不再尝试读取不存在的顶层 `source_id`。

## 请求竞态

三类请求均具备独立取消和 request id：

- 主列表
- Message 详情
- Memory 详情、Source 和 Vector

快速连续选择时，旧请求不会覆盖新选择。详情失败显示稳定错误提示，不再使用空 `catch` 静默吞掉异常。

## 隐私处理

- 每条 Message 使用当前 `row` 判断 `restricted`。
- restricted 列表不显示正文摘要。
- restricted 正文只在用户主动展开 `<details>` 后显示。
- 页面不把 Token、Cookie、API Key、本地绝对路径或堆栈写入标题和通知。

## 三态处理

- `true`：需要重建
- `false`：无需重建
- `null/undefined`：未知

## 后续 Capture Center 接入位置

Capture Center 后续只能通过现有采集后端和 `source_id` 跳转到 Inspector。本轮未开发 Capture Center UI。
