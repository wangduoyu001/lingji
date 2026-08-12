# PR #88 M5 Sidecar Lifecycle Closeout

## 状态

本报告记录 PR #88 单次收口阶段对 macOS 最终 DMG 隔离 Gate 与 Windows Release smoke 的生命周期修复。

- 原始失败候选：`94178f8ca06beb646ede5a64a09b829dceb388c0`
- 原始 macOS Gate：`#26`
- 原始失败步骤：`Verify installed App acceptance isolation`
- 原始失败：`hdiutil: couldn't unmount ... Resource busy`
- 后续 Windows Release 失败候选：`b0f64bf6ce518666abc8fe6286bdc728a2568156`
- Windows Release 失败步骤：`Run Desktop smoke tests`
- PR 状态：`Draft / DO NOT MERGE`
- 旧 Artifact `9102748834`：永久拒绝，不得重试

## macOS 根因

隔离 Gate 已向当前 Sidecar 的 `sidecar-stop-request.json` 写入精确 `instance_id`，但旧 `install_runtime_lifecycle()` 在收到匹配 stop request 后执行：

```text
删除 stop request
→ 提前删除 sidecar-state.json
→ 给自身发送 SIGTERM
```

Uvicorn 会处理 SIGTERM 并优雅退出，因此 state 消失时进程仍可能存活并占用 DMG 内 Sidecar。Gate 将“state 消失”误判成“进程已真实退出”，随后 `hdiutil detach` 以 `Resource busy` 失败。

## macOS 修复

生命周期改为：

```text
删除匹配 stop request
→ 给自身发送 SIGTERM
→ sidecar-state.json 保持存在
→ Uvicorn / Python 真实退出
→ atexit cleanup 删除当前 instance_id 的 state
```

因此 `sidecar-state.json` 重新代表真实活进程，而不是“已收到停止请求”。

## Windows Release 二次根因

`b0f64bf...` 已包含正确的新生命周期实现，但 Windows Desktop Release 在静态 smoke 阶段失败。根因不是 Runtime，而是 `desktop/lingji-control/scripts/runtime-sidecar-smoke.mjs` 仍断言旧测试名：

```text
matching_stop_request
```

生命周期回归已经重命名并强化为：

```text
test_runtime_lifecycle_keeps_identity_until_process_really_exits
```

旧 smoke 因此在正确代码上制造假红灯。

## Windows smoke 修复

静态 smoke 改为验证新语义，而不是恢复旧名字：

1. Python 回归必须包含 `keeps_identity_until_process_really_exits`；
2. 仍验证 mismatched stop request 被忽略；
3. packaged entrypoint 必须明确保留 `sidecar-state.json` 直到真实退出；
4. 必须继续由 `atexit.register(cleanup)` 在真实退出阶段清理 state。

不得通过把测试重命名回旧字符串来“修绿” CI。

## 必须通过的统一远程门禁

最终候选必须由同一个精确产品 Head 完成：

```text
tests
P0 Windows Gate
Windows Desktop Release Baseline
macOS Desktop Gate
acceptance-doc-sync
local-execution-handoff
```

macOS Gate 必须重新跑最终 DMG App 首启 + 二启，确认 authenticated 8766 ping、task-scoped 数据根、`Documents/acceptance` 不存在，并在 Sidecar 真实退出后成功卸载 DMG。

Windows Release 必须完整通过 Desktop smoke、Rust、packaged runtime、authenticated health/managed stop、NSIS 与 Artifact contract。

## 安全边界

- 不使用全局 kill/killall 清理 Sidecar；停止请求继续绑定当前 `instance_id`。
- 不放宽 `LINGJI_ACCEPTANCE_DATA_ROOT` 精确匹配。
- 不删除 Production、Vault、正式凭据或第三方应用配置。
- Secret 同步规则不变，认证状态快照必须保持 `secret_export_count=0`。

## 完成判定

本报告存在不代表 `M5-ISOLATION-002` 已关闭。只有统一最终 Head 上 macOS Desktop Gate、Windows Release、完整回归、认证状态门禁和新 Artifact 全部 PASS，才允许开发回执进入 `READY_FOR_M5_REACCEPTANCE`。