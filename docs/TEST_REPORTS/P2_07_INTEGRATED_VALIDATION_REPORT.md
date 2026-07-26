# P2-07 Integrated Validation Report

> Status: `VALIDATED_READY_FOR_FORMAL_MERGE`  
> Integration Branch: `work/p2-07-integrated-validation`  
> Functional Integration Head: `2b4ce6680564b06d86000325f75cc6874a8ccd63`  
> Validation Contract Head: `56819e1dca5d14e9a3b55f506784312089a0a2db`  
> Formal PR: `#22`  
> Test Date: `2026-07-21`

## 1. 验证范围

本报告验证 P2-07A、P2-07B、P2-07C 和协调集成代码处于同一棵树时的完整行为：

- Project Resolver 和 Worktree 归一化。
- Codex Session JSONL 生命周期、幂等、恢复和脱敏。
- Structured Source / Conversation / Message 映射。
- Project Context Pack、权限、引用和字符预算。
- Candidate 审核、Hash 冲突、主人手动记忆和归档。
- Core Memory Integrity。
- Obsidian 安全读写和扫描变化。
- 8766 懒加载路由装配和 Token 认证。
- MCP Codex Session 与 Project Context Tool。
- Desktop Current Work、项目与对话、Activity、Context Pack、记忆审核、Obsidian 操作和 Inspector 快捷目标。
- Tauri Rust 工程编译检查。

## 2. 最终结果

```text
Linux Python 3.12:
437 passed / 11 skipped / 0 failed / 2 warnings / 11.68s

Windows Python 3.12:
437 passed / 11 skipped / 0 failed / 2 warnings / 67.29s

Linux Python 3.11:
PASS / 0 failed

Clean-install validation:
PASS

compileall:
PASS

npm ci:
PASS

Desktop named smoke suite:
PASS (11 scripts)

TypeScript / Vite build:
PASS

cargo check --manifest-path src-tauri/Cargo.toml:
PASS

MCP smoke:
PASS

Browser capture smoke:
PASS

Obsidian plugin smoke:
PASS

GitHub tests workflow:
SUCCESS

GitHub P0 Windows Gate:
SUCCESS
```

最终状态：

```text
P2_07_INTEGRATED_VALIDATED
READY_FOR_FORMAL_MERGE
```

## 3. Python 门禁

执行：

```bash
python -m pip check
python scripts/validate_clean_install.py --root . --import-check
python -m compileall -q \
  main.py \
  run_service.py \
  run_control_api.py \
  run_mcp_server.py \
  run_extraction_worker.py \
  src \
  second_brain \
  tests \
  scripts
python -m pytest -q --tb=short
```

Linux 与 Windows 都使用完整仓库测试，不使用 15 个或 43 个新增测试冒充全仓回归。

## 4. Desktop 与 Rust 门禁

执行：

```bash
cd desktop/lingji-control
npm ci
npm run test:smoke
npm run build
cargo check --manifest-path src-tauri/Cargo.toml
```

Named smoke suite：

```text
acceptance-smoke.mjs
ui-modular-smoke.mjs
vector-center-smoke.mjs
hardware-smoke.mjs
models-smoke.mjs
memory-inspector-smoke.mjs
capture-center-smoke.mjs
obsidian-smoke.mjs
codex-workspace-smoke.mjs
memory-review-smoke.mjs
obsidian-operations-smoke.mjs
```

CI 会保存具名 Smoke 和 Build 日志，失败时可以定位到具体脚本。

## 5. 协调审查发现并修复的问题

### 5.1 A/B/C API 合同错位

修复：

- Project Resolve 使用 `workspace_path`。
- Context Pack 使用 `query`。
- Reject 提交 `owner_confirmed`、`expected_content_hash` 和 `reason`。
- Owner Memory 和 Archive 提交主人确认。
- Core Integrity 使用 `current_hash`。

### 5.2 Markdown 正文 Hash

原问题：

```text
创建时 Hash 正文
读取时 Hash Frontmatter 分隔后的正文
-> 首个空行差异
-> 刚创建即 external_modified
```

修复：

```text
src/project_memory/body_hash.py
canonical_body()
body_content_hash()
```

兼容既有 approved hash，同时使用稳定 canonical hash 返回当前状态。

### 5.3 Context Session Status

原问题：Recent Session 使用默认 Active-only 过滤，已完成 Codex Session 无法进入 Context Pack。

修复：Recent Sessions 接受 `active / completed / failed / abandoned`，仍要求 Project、Privacy、Agent Scope 和稳定引用。

### 5.4 Memory Index Sync

原问题：把 `PEMISIndex.build_index()` 的统计返回值直接传给 Gateway rebuild。

修复：先执行 `build_index(force=False)`，再使用 `indexer.get_all()` 的正式条目重建 Gateway。

### 5.5 8766 Runtime

修复：

- P2-07 Service 使用懒加载。
- 未授权请求在 Runtime 构造前返回 401。
- 复用现有 Memory Gateway、Extraction Pipeline、StateDatabase 和 Obsidian Service。
- 没有第二套 Queue 或 Lifecycle。

### 5.6 MCP Pipeline

修复：MCP 的既有采集工具、Codex Session Bridge 和 Project Context 使用同一个 Extraction Pipeline。

### 5.7 Inspector Shortcut

原问题：快捷参数只传到 Wrapper 和 URL，MemoryInspectorPage 未消费。

修复：Project / Source Type 进入筛选状态，Source / Conversation / Message / Memory ID 直接读取并展开目标详情。

### 5.8 Smoke 与 CI

修复：

- Wrapper Page 断言改为验证 Wrapper 内包含正式页面和扩展面板。
- Review Hash 在 API Client 边界验证。
- Workspace 分别验证 list/activity request ID。
- Mock 使用 `current_hash`。
- 新增具名 Smoke Runner 和 Artifact。
- P0 Windows Gate 新增真实 Tauri `cargo check`。

## 6. 安全边界验证

```text
Codex 私有 SQLite 读取: NO
Codex 私有缓存扫描: NO
完整 Transcript 写入 Obsidian: NO
Project/Session 数据库表: NO
数据库 Schema 修改: NO
第二套 Extraction Pipeline: NO
第二套 Memory Lifecycle: NO
自动 Core Memory 晋升: NO
永久删除: NO
跨项目 Codex Context: NO
系统监听: NO
剪贴板监听: NO
文件夹监听: NO
WebSocket / SSE: NO
生产 Vault 访问: NO
生产 SQLite 访问: NO
生产 Qdrant 访问: NO
生产 Ollama 访问: NO
rebase: NO
force push: NO
```

## 7. 警告

全仓仍有两个既有警告：

```text
Pydantic class-based config deprecation
Starlette TestClient httpx deprecation
```

它们没有造成 P2-07 测试失败，但应在后续工程维护阶段处理。

## 8. 已知限制

- `/api/codex/current` 的 Obsidian、Memory Index 和待审核数量允许返回未知，不伪装为 0。
- Activity 使用轮询，不使用 WebSocket/SSE。
- UI 不显示完整 Transcript。
- 自动审查不属于 P2-07。
- 自动监听、手机端和平台专用采集客户端仍未开发。
- Production `bge-m3` 切换和生产 Qdrant Collection 重建仍未执行。

## 9. 审查结论

P2-07A/B/C 单独交付时均存在“独立测试无法发现的组合合同问题”。经过协调修复后，最终 A+B+C 集成树已经通过 Linux、Windows、Desktop、MCP 和 Rust 门禁。

结论：

```text
可以合并到 feature/second-brain-memory
不得把未审查的独立自动审查包混入本次合并
P2-08 必须另开阶段并从 SHADOW 模式开始
```
