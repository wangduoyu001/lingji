# P2-07C Local UI Memory Loop Test Report

## 结论

```text
IMPLEMENTED_NOT_TESTED
NOT_MERGED_AWAITING_COORDINATED_REVIEW
```

## 范围

仅修改 `desktop/lingji-control/` 并新增本报告和模块文档。未修改 Python、数据库 Schema、共享状态文档、监听、移动端或浏览器插件。

## Smoke 合同

### Codex Workspace

覆盖：导航、冻结 API 路径、当前项目、Unassigned、Session 列表与详情、不显示 Transcript、不显示完整路径、Activity after_id、1 秒/5 秒轮询、inactive/hidden 停止、Context Pack Markdown 与复制、AbortController、requestId。

### Memory Review

覆盖：Candidate 列表和详情、approve、edit-approve、reject、owner_confirmed、expected_content_hash、409 冲突、手动新增 Core Memory、归档提示、无永久删除按钮、external_modified、missing、401、503、AbortController、requestId。

### Obsidian Operations

覆盖：相对路径读取、手动笔记、允许目录、禁止 Core/08-Private/00-System 入口、扫描变化、当前项目和当前 Session 快捷入口、401、404、422、503、AbortController、requestId。

## 计划命令

```bash
cd desktop/lingji-control
npm run test:codex-loop
npm run test:memory-review
npm run test:obsidian-operations
npm run test:smoke
npm run build
cargo check --manifest-path src-tauri/Cargo.toml
```

## 实际执行

当前会话只有 GitHub Connector，没有可联网克隆的本地工作树，因此上述命令均未执行。没有把“源码字符串检查已编写”冒充成“构建已通过”，这种习惯虽然在人类项目报告里常见，但依然不正确。

```text
test:codex-loop: NOT EXECUTED
test:memory-review: NOT EXECUTED
test:obsidian-operations: NOT EXECUTED
test:smoke: NOT EXECUTED
build: NOT EXECUTED
cargo check: NOT EXECUTED
```

## 协调审查门禁

1. 在真实工作树执行 `npm ci`。
2. 依次执行三个 focused smoke。
3. 执行全量 `test:smoke`。
4. 执行 TypeScript/Vite build。
5. 有 Rust 环境时执行 cargo check。
6. 若 DTO 与 1号/2号最终实现不同，只调整前端合同映射，不修改 Python 迁就 UI。

## 生产数据

未连接本地生产 API，未读取 Vault、SQLite、Qdrant、Obsidian 实际笔记或 Codex Transcript。
