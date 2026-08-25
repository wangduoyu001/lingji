# P2-07C Local UI Usable Memory Loop

> 文档角色：历史实施/验证快照，不是当前进度或当前架构权威。
> 当前状态看 `docs/PROJECT_STATUS.md`；当前代码入口看 `docs/MODULES/CODE_MAP.md`。

## 状态

`IMPLEMENTED_NOT_TESTED`

分支：`work/p2-07c-local-ui-loop`
基础提交：`8b033eba1be6d4e7509a763b8333299672d2161b`

## 页面

- Dashboard：扩展现有总览，增加当前项目、Session、分支、Worktree、MCP、Obsidian、Memory Index、最近检查点、待审核数量和 Activity。
- 项目与对话：项目识别、目录选择、Session 列表和详情、增量 Activity、Context Pack。
- 记忆审核：Candidate 列表和详情、批准、编辑批准、拒绝、主人手动新增、归档与 Integrity。
- Obsidian：保留原配置，增加测试读取、受限目录手动笔记和显式扫描。
- Memory Inspector：增加当前项目、Codex、当前 Session、关联 Memory、Core Memory 快捷导航状态。

## 组件

- `CurrentWorkPanel`
- `CodexWorkspacePage`
- `MemoryReviewPage`
- `ObsidianOperations`
- `ObsidianLoopPage`
- `MemoryInspectorLoopPage`

## API

严格使用任务冻结的 `/api/codex/*`、`/api/activity`、`/api/context/project`、`/api/memory/review/*`、`/api/memory/core/*` 和 `/api/obsidian/*` 路径。请求继续通过现有 `LingJiApi` 发送 `X-LingJi-Token`。

## 状态管理

- 列表、详情、当前工作和读取操作使用 `AbortController`。
- 使用递增 `requestId` 阻止旧请求覆盖新状态。
- 页面 inactive 或浏览器窗口隐藏时停止 Activity 请求。
- 活动 Session 使用 1 秒轮询；无活动 Session 使用 5 秒轮询。
- 没有后端 progress_current/progress_total 时只显示阶段，不伪造百分比。

## Activity Polling

`GET /api/activity?after_id=<last_event_id>`，仅保留最近 100 条 UI 事件。没有引入 WebSocket 或 SSE。

## 记忆审核交互

批准和编辑批准提交：

```json
{
  "owner_confirmed": true,
  "expected_content_hash": "..."
}
```

编辑冲突 409 显示固定提示并保留编辑内容。拒绝理由可选。没有永久删除、HMAC、Tombstone 或复杂 Merge UI。

## Obsidian 操作

允许手动写入目录：

- `01-Inbox/Manual`
- `03-Knowledge/Notes`
- `05-Operations/Tasks`

UI 不提供 Core-Memory、08-Private、00-System 或任意绝对路径写入入口。扫描只能由用户点击触发，不启动监听。

## 快捷筛选与隐私

快捷导航仅传递 ID、source_type 和布尔筛选标志，不把正文写入 URL 或 localStorage。项目路径通过 `path_display` 截断显示，不渲染完整 Transcript。

## 测试

新增：

- `scripts/codex-workspace-smoke.mjs`
- `scripts/memory-review-smoke.mjs`
- `scripts/obsidian-operations-smoke.mjs`

对应 npm scripts 已加入 `test:smoke`。

## 已知限制

- 并行期间使用前端 Mock DTO，未连接生产数据。
- 当前环境无法运行 npm、Vite、TypeScript 或 Cargo，因此未验证 build/cargo。
- Memory Inspector 快捷状态由内存导航和 URL ID 参数承载；精确实体自动展开仍依赖后续协调阶段确认后端 DTO 与 Inspector 选择合同。

## 回滚

按提交逆序回滚 P2-07C 的最多五个逻辑提交即可；不涉及 Python、数据库 Schema 或生产数据迁移。
