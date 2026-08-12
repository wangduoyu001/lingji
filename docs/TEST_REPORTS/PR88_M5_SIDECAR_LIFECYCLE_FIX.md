# PR #88 M5 Sidecar Lifecycle Closeout

## 状态

本报告记录 PR #88 单次收口阶段对 macOS 最终 DMG 隔离 Gate 与 Windows packaged Sidecar managed-stop 的完整生命周期修复。

- 最早失败候选：`94178f8ca06beb646ede5a64a09b829dceb388c0`
- macOS 原始失败：`hdiutil detach ... Resource busy`
- Windows 静态 smoke 失败候选：`b0f64bf6ce518666abc8fe6286bdc728a2568156`
- Windows managed-stop 失败候选：`9079ee88ae24353d6ce934e82d6c7861c42853c4`
- Windows stale-state 复验候选：`1d71d748870227caaac46419e5afa5668f229a69`
- PR 状态：`Draft / DO NOT MERGE`
- 旧 Artifact `9102748834`：永久拒绝，不得重试

## 已确认的三层问题

### 1. macOS：state 提前消失

旧停止顺序曾是：

```text
删除 stop request
→ 提前删除 sidecar-state.json
→ SIGTERM
```

Uvicorn 会优雅处理 SIGTERM，因此 state 已消失时进程可能仍占用 DMG。Gate 随后卸载镜像，得到 `Resource busy`。

第一层修复将 state 保留到服务退出。该行为已经在 `9079ee88...` 的真实 macOS Desktop Gate 中通过：最终 DMG identity、Rust、Sidecar、authenticated 8766、首启/二启、task-scoped DataRoot、`Documents/acceptance` 不存在和 DMG detach 全部 PASS。

### 2. Windows：静态 smoke 保护旧测试名

Windows Release 曾在 Desktop smoke 中寻找旧字符串 `matching_stop_request`，而生命周期回归已改为“state 直到真实退出才消失”。Smoke 已改为验证新语义，而不是恢复旧名称。

### 3. Windows：SIGTERM 会让冻结 Sidecar 直接结束

`1d71d748...` 的 Windows Release 已证明：匹配 stop request 能让 PyInstaller/Uvicorn 进程退出，但 `sidecar-state.json` 仍存在。即便 packaged `main()` 有 `finally`，Windows 冻结进程的 `os.kill(..., SIGTERM)` 路径也不能保证 Python finally/atexit 被执行。

因此不能继续依赖 OS signal 再补清理代码。

## 最终修复：进程内 Uvicorn shutdown bridge

packaged Runtime 现在使用一个 `threading.Event` 作为停止桥：

```text
RuntimeManager 写入匹配 instance_id 的 stop request
→ Sidecar lifecycle monitor 消费 stop request
→ shutdown_event.set()
→ run_control_api 内 watcher 观察 event
→ uvicorn.Server.should_exit = True
→ Uvicorn 正常 graceful shutdown
→ Autopilot / service 正常 close
→ packaged main finally 精确 cleanup_runtime_lifecycle(current instance)
→ sidecar-state.json 删除
→ 进程正常退出
```

只有没有提供 shutdown event 的旧/直接调用才保留 SIGTERM compatibility fallback。正式 packaged Desktop 不再依赖 OS SIGTERM 作为正常停止机制。

## 安全边界

- stop request 必须匹配当前 `instance_id`；
- `cleanup_runtime_lifecycle()` 只删除仍属于当前实例的 state/stop 文件；
- mismatched instance 不得被清理；
- 不使用全局 kill/killall 作为正常停止机制；
- 不放宽 `LINGJI_ACCEPTANCE_DATA_ROOT`；
- 不触碰 Production、Vault、正式凭据或第三方 AI 配置；
- 认证状态快照继续要求 `secret_export_count=0`。

## 自动回归

`tests/test_packaged_control_api.py` 必须验证：

1. packaged shutdown event 被匹配 stop request 设置；
2. 使用 event 时不调用 `os.kill`；
3. event 已设置但服务尚未返回时 state 仍存在；
4. 显式 lifecycle cleanup 后 state 消失；
5. mismatched instance / stop request 不会误清理；
6. legacy caller 仍保留 signal fallback。

`desktop/lingji-control/scripts/runtime-sidecar-smoke.mjs` 必须验证：

- packaged entrypoint 传递 `shutdown_event`；
- `run_control_api.py` 使用 `uvicorn.Config` + `uvicorn.Server`；
- watcher 在 event 后设置 `server.should_exit = True`；
- packaged `finally` 精确清理当前 lifecycle；
- 旧身份、DataRoot、Rust/RuntimeManager、安全边界继续存在。

## 最终门禁

新的精确产品 Head 必须同时通过：

```text
tests
P0 Windows Gate
Windows Desktop Release Baseline
macOS Desktop Gate
acceptance-doc-sync
local-execution-handoff
```

Windows Release 必须真正通过 authenticated health、managed stop、state 清理、NSIS 和 Artifact contract。macOS 必须继续通过最终 DMG 首启/二启、身份、隔离与 detach。

## 完成判定

本报告存在不代表真实 M5 已 PASS。只有统一最终 Head 的六条门禁全部 PASS、新 Windows/macOS Artifact 生成、独立哈希和最终 DMG metadata 复核完成后，开发回执才允许进入 `READY_FOR_M5_REACCEPTANCE`。
