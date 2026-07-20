# P2-04 Memory Inspector UI Test Report

## 状态

```text
IMPLEMENTED_NOT_TESTED
NOT_MERGED_AWAITING_COORDINATED_REVIEW
```

## 范围

- 正式桌面导航与页面接线。
- 只读 Inspector API Client。
- Source / Conversation / Message 三栏视图。
- Message / Memory / Chunk / Vector 关系抽屉。
- 后端分页、筛选、搜索防抖、取消请求和竞态保护。
- 401、503、网络不可用、正常空数据、筛选空数据状态。
- restricted 内容默认折叠。
- rebuild_required true / false / null 三态显示。
- 未知数值显示“未知”，不伪造为 0。

## 代码检查

实现包含以下可审查合同：

- `LIMIT = 30`，后端合同最大值为 200。
- 关键词防抖 300ms。
- `AbortController` 中止旧请求。
- `requestId` 阻止旧请求覆盖新结果。
- `ApiError` 保留 HTTP status 与稳定 code。
- 503 `READ_MODEL_UNAVAILABLE` 不显示后端路径或堆栈。
- Memory 子关系请求使用 `Promise.allSettled`，允许部分数据。

## 计划测试用例

1. API Client 错误转换、Token、超时和取消。
2. limit/offset 与筛选 Query 参数。
3. 300ms 搜索防抖。
4. Loading 与刷新状态。
5. 正常空数据与筛选空数据。
6. 401 授权状态。
7. 503 结构化读取模型不可用。
8. Source、Conversation、Message 选择链路。
9. Message 时间线与详情读取。
10. Memory 关系与 Vector 三态。
11. restricted 正文默认折叠。
12. 旧请求返回晚于新请求时不覆盖新状态。

## 实际执行

当前执行环境无法解析 `github.com`，无法把仓库物化到本地，也无法运行 Node/npm/Tauri 命令。没有使用“代码看起来没问题”冒充测试通过。

```text
npm run typecheck: NOT AVAILABLE IN package.json / NOT EXECUTED
npm run test:      NOT AVAILABLE IN package.json / NOT EXECUTED
npm run build:     NOT EXECUTED
npm run test:smoke: NOT EXECUTED
passed:  NOT EXECUTED
failed:  NOT EXECUTED
skipped: NOT EXECUTED
```

## 环境与数据边界

```text
生产后端: NOT STARTED
生产数据: NOT ACCESSED
Qdrant: NOT STARTED
Ollama: NOT STARTED
数据库 Schema: NOT MODIFIED
src/extraction: NOT MODIFIED
src/sources: NOT MODIFIED
src/gateway: NOT MODIFIED
src/control Python: NOT MODIFIED
second_brain: NOT MODIFIED
正式分支: NOT MERGED
force push: NOT USED
rebase: NOT USED
```

## 审查建议

协调者应在可用工作树中运行：

```text
cd desktop/lingji-control
npm run test:smoke
npm run build
```

package.json 当前没有独立 `typecheck` 和通用 `test` 脚本。若协调者要求自动化组件测试，应在统一审查后决定是否引入 Vitest/jsdom，避免本任务擅自安装大量依赖。
