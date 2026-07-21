# P2-05C Capture Center UI Test Report

## 状态

```text
IMPLEMENTED_NOT_TESTED
NOT_MERGED_AWAITING_COORDINATED_REVIEW
```

## Smoke Test

新增：

```text
desktop/lingji-control/scripts/capture-center-smoke.mjs
npm run test:capture
```

覆盖：

- 导航与页面入口。
- 规定的 Capture API 路径。
- 公共提交参数和 `process_later=true`。
- 文本和 URL 验证。
- 文件选择 `multiple=false/directory=false`。
- Web Snapshot、ChatGPT Export、Codex Report 扩展过滤。
- 媒体扩展过滤。
- 后端分页大小 30。
- status/source_type/q 筛选。
- queued/retrying 取消权限。
- failed/cancelled 重试权限。
- running 不可强制取消。
- completed 结果引用跳转。
- restricted 标识。
- 401、409、503 稳定错误映射。
- AbortController 与 requestId 竞态保护。
- 页面不引用 payload 或 lease_token。
- Tauri Dialog 初始化和 `dialog:default` 权限。

## 计划命令

```text
cd desktop/lingji-control
npm run test:capture
npm run test:smoke
npm run build
cargo check --manifest-path src-tauri/Cargo.toml
```

## 实际执行

当前执行环境无法解析 GitHub 域名，仓库只能通过 GitHub Connector 修改，无法建立本地 Node/Rust 工作树。因此以下命令未执行：

```text
npm run test:capture: NOT EXECUTED
npm run test:smoke:   NOT EXECUTED
npm run build:        NOT EXECUTED
cargo check:          NOT EXECUTED
passed:               NOT EXECUTED
failed:               NOT EXECUTED
skipped:              NOT EXECUTED
```

## 锁文件状态

```text
package.json: UPDATED
Cargo.toml: UPDATED
package-lock.json: NOT UPDATED
Cargo.lock: NOT UPDATED
```

原因：无法运行 npm/cargo 生成可信锁文件，且不手工伪造 integrity/checksum。协调审查必须先生成锁文件，再执行测试门禁。因为这一缺口，状态不得提升为 `IMPLEMENTED_FOCUSED_TESTED`。

## 边界

```text
Python 后端: NOT MODIFIED
数据库 Schema: NOT MODIFIED
监听: NOT DEVELOPED
手机端: NOT DEVELOPED
浏览器插件: NOT DEVELOPED
生产数据: NOT ACCESSED
生产后端: NOT STARTED
Qdrant: NOT STARTED
Ollama: NOT STARTED
正式分支: NOT MERGED
rebase: NOT USED
force push: NOT USED
```
