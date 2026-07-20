# P2-04 Memory Inspector UI Test Report

## 状态

```text
IMPLEMENTED_NOT_TESTED
COORDINATED_REVIEW_FIXES_IMPLEMENTED
NOT_MERGED
```

## 本轮返工范围

- 修复 `q/from_time/to_time` Query 参数。
- 为 Source、Conversation、Message 分别限制允许参数。
- 修复嵌套 Status 响应映射。
- 保留 Message detail 顶层 `memory_links`。
- 优先使用 `display_name/projects/occurred_at/content_preview/metadata.model/metadata.is_branch`。
- restricted 状态按当前 Message row 判断。
- Vector 从 `response.vector` 解包。
- Memory Source 从 `canonical/links` 解包。
- 为 Message 与 Memory 详情请求增加独立取消和 request id。
- 恢复 `App.tsx`、`types.ts`、`MemoryInspectorPage.css` 可读格式。
- 增加不依赖生产后端的纯函数合同测试。

## 纯函数合同测试

`desktop/lingji-control/scripts/memory-inspector-smoke.mjs` 直接加载并执行 `memoryInspectorContract.ts` 中无 TypeScript 专属语法的纯函数，验证：

1. Source Query 只包含 `source_type/privacy/project/status/q/limit/offset`。
2. Conversation Query 只包含 `source_id/source_type/privacy/project/from_time/to_time/q/limit/offset`。
3. Message Query 只包含 `conversation_id/source_id/role/from_time/to_time/q/limit/offset`。
4. Message Query 不携带 `project/privacy/status/source_type`。
5. Status 从 `sources/memory/vector` 嵌套结构映射。
6. 缺失计数保持 `null` 并显示“未知”。
7. Message detail 同时保留 `item` 与 `memory_links`。
8. `occurred_at/content_preview/metadata.model/metadata.is_branch` 合同。
9. 数组字段格式化。
10. restricted 按当前 row 判断。
11. Vector 从 `response.vector` 解包。
12. Memory Source 从 `canonical/links` 解包。
13. `rebuild_required` true/false/null 三态。
14. 页面具备列表、Message、Memory 三组独立竞态保护。

## 计划执行命令

```text
cd desktop/lingji-control
npm run test:inspector
npm run test:smoke
npm run build
```

## 实际执行

当前工具只能修改远程 GitHub 分支，不能在仓库工作树中运行 Node/npm/Tauri。没有把源码审查冒充测试通过。

```text
npm run test:inspector: NOT EXECUTED
npm run test:smoke:     NOT EXECUTED
npm run build:          NOT EXECUTED
passed:                  NOT EXECUTED
failed:                  NOT EXECUTED
skipped:                 NOT EXECUTED
```

## 环境与数据边界

```text
生产后端: NOT STARTED
生产数据: NOT ACCESSED
Qdrant: NOT STARTED
Ollama: NOT STARTED
数据库 Schema: NOT MODIFIED
Python 后端: NOT MODIFIED
src/extraction: NOT MODIFIED
src/sources: NOT MODIFIED
src/gateway: NOT MODIFIED
src/control Python: NOT MODIFIED
second_brain: NOT MODIFIED
正式分支: NOT MERGED
force push: NOT USED
rebase: NOT USED
```

## 审查重点

协调审查应重点运行 `npm run build`，确认 TypeScript 对 `memoryInspectorContract.ts` 的导入和既有页面类型没有回归。若失败，应只修复前端类型或格式问题，不得修改后端合同绕过错误。
