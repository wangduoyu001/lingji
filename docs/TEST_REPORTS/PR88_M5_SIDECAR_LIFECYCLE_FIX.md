# PR #88 M5 Sidecar Lifecycle Closeout

## 状态

本报告记录 PR #88 单次收口阶段对 macOS 最终 DMG 隔离 Gate 与 Windows Release managed-stop 的生命周期修复。

- 原始失败候选：`94178f8ca06beb646ede5a64a09b829dceb388c0`
- 原始 macOS Gate：`#26`
- 原始失败：`hdiutil: couldn't unmount ... Resource busy`
- Windows Release 静态 smoke 失败候选：`b0f64bf6ce518666abc8fe6286bdc728a2568156`
- Windows Release managed-stop 失败候选：`9079ee88ae24353d6ce934e82d6c7861c42853c4`
- PR 状态：`Draft / DO NOT MERGE`
- 旧 Artifact `9102748834`：永久拒绝，不得重试

## 第一层根因：macOS state 提前消失

旧 `install_runtime_lifecycle()` 在收到匹配 stop request 后执行：

```text
删除 stop request
→ 提前删除 sidecar-state.json
→ 给自身发送 SIGTERM
```

Uvicorn 会处理 SIGTERM 并优雅退出，因此 state 消失时进程仍可能存活并占用 DMG 内 Sidecar。Gate 将“state 消失”误判成“进程已真实退出”，随后 `hdiutil detach` 以 `Resource busy` 失败。

第一层修复改为：

```text
删除匹配 stop request
→ 给自身发送 SIGTERM
→ sidecar-state.json 保持存在
→ 等待真实服务退出
```

该修复已在 `9079ee88...` 的真实 macOS Desktop Gate 中验证：最终 DMG identity、Rust、Sidecar、authenticated 8766、首启/二启、task-scoped 数据根、`Documents/acceptance` 不存在和 DMG detach 全部 PASS。

## 第二层根因：Windows 冻结进程退出后 state 残留

`9079ee88...` 的 Windows Desktop Release 已通过 Desktop smoke、前端构建、Rust RuntimeManager、packaged Python contract 与 Sidecar build，随后在 `Verify authenticated health and managed stop` 失败：

```text
Packaged runtime left stale identity after managed stop
```

日志证明匹配 stop request 已使 PyInstaller/Uvicorn 进程真实退出，但 `sidecar-state.json` 仍存在。原因是第一层修复只依赖 `atexit` 做最终 state 清理，而冻结的 Windows Sidecar 退出路径不能把 `atexit` 作为唯一可靠清理机制。

## 第二层修复：显式 finally + atexit 双保险

新增 `cleanup_runtime_lifecycle(data_root, instance_id)`：

- 只删除仍属于当前 `instance_id` 的 state / stop request；
- 不会误删新实例或其他 Runtime 的 lifecycle 文件；
- 可由正常服务退出路径显式调用。

packaged Sidecar 主链调整为：

```text
install_runtime_lifecycle
→ run_control_api / Uvicorn
→ Uvicorn 完成 graceful shutdown 并返回
→ finally: cleanup_runtime_lifecycle(current instance)
→ 进程退出
```

`atexit` 保留为普通退出兜底，但不再承担唯一的最终清理责任。

这样同时满足两个互相容易打架的要求：

1. 收到 SIGTERM 时不能提前删 state，避免 macOS 错把“正在退出”当成“已经退出”；
2. 服务真正完成 shutdown 后必须显式删 state，避免 Windows 已退出却残留陈旧 identity。

## 回归测试

`tests/test_packaged_control_api.py`：

- 匹配 stop request 被消费且 SIGTERM 已发送时，模拟进程仍活着，state 必须继续存在；
- 显式 `cleanup_runtime_lifecycle()` 后 state 必须消失；
- mismatched instance 不得被清理；
- mismatched stop request 继续被忽略。

`desktop/lingji-control/scripts/runtime-sidecar-smoke.mjs`：

- 必须存在 `cleanup_runtime_lifecycle`；
- 必须存在 `keeps_identity_until_process_really_exits`；
- 必须存在 `cleanup_only_removes_matching_instance`；
- packaged entrypoint 必须保留 `atexit` 兜底；
- 主函数必须通过 `finally` 显式调用 lifecycle cleanup。

不得通过恢复旧测试名或放宽 managed-stop 断言来让 CI 变绿。

## 最终统一远程门禁

新的精确产品 Head 必须同时通过：

```text
tests
P0 Windows Gate
Windows Desktop Release Baseline
macOS Desktop Gate
acceptance-doc-sync
local-execution-handoff
```

Windows Release 必须完整通过 authenticated health / managed stop、state 清理、NSIS 与 Artifact contract。macOS 必须继续通过最终 DMG 首启/二启、身份、隔离和 detach。

## 安全边界

- 不使用全局 kill/killall 清理 Sidecar；停止请求继续绑定当前 `instance_id`。
- lifecycle cleanup 只允许删除匹配 instance 的文件。
- 不放宽 `LINGJI_ACCEPTANCE_DATA_ROOT` 精确匹配。
- 不删除 Production、Vault、正式凭据或第三方应用配置。
- Secret 同步规则不变，认证状态快照必须保持 `secret_export_count=0`。

## 完成判定

本报告存在不代表真实 M5 已 PASS。只有统一最终 Head 的六条远程门禁全部 PASS、新 Windows/macOS Artifact 生成、独立哈希与最终 DMG metadata 复核完成后，开发回执才允许进入 `READY_FOR_M5_REACCEPTANCE`。