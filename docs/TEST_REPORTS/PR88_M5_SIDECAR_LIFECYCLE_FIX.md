# PR #88 M5 Sidecar Lifecycle Closeout

## 状态

本报告记录 PR #88 单次收口阶段对 macOS 最终 DMG 隔离 Gate 的生命周期修复。

- 来源候选：`94178f8ca06beb646ede5a64a09b829dceb388c0`
- 来源 macOS Gate：`#26`
- 来源失败步骤：`Verify installed App acceptance isolation`
- 来源失败：`hdiutil: couldn't unmount ... Resource busy`
- PR 状态：`Draft / DO NOT MERGE`
- 旧 Artifact `9102748834`：永久拒绝，不得重试

## 根因

隔离 Gate 已经向当前 Sidecar 的 `sidecar-stop-request.json` 写入精确 `instance_id`，但 `run_packaged_control_api.install_runtime_lifecycle()` 在收到匹配 stop request 后执行顺序为：

```text
删除 stop request
→ 删除 sidecar-state.json
→ 给自身发送 SIGTERM
```

Uvicorn 会处理 SIGTERM 并进行优雅退出，因此 `sidecar-state.json` 消失时进程可能仍然存活并继续占用 DMG 内的 Sidecar 可执行文件。Gate 把“state 消失”误当作“进程已真实退出”，随后执行 `hdiutil detach`，最终以 `Resource busy` 失败。

## 修复

Sidecar 生命周期改为：

```text
删除匹配的 stop request
→ 给自身发送 SIGTERM
→ sidecar-state.json 保持存在
→ Uvicorn / Python 真实退出
→ atexit cleanup 删除属于当前 instance_id 的 state
```

因此 `sidecar-state.json` 重新恢复为“真实活进程身份”的可信信号，而不是“已经收到停止请求”的提前信号。

## 回归测试

`tests/test_packaged_control_api.py` 的生命周期测试同步改为验证：

1. 匹配 stop request 被消费；
2. SIGTERM 被发送；
3. 在测试模拟的进程仍未真实退出时，`sidecar-state.json` 必须继续存在；
4. 不再保护旧的“收到停止请求即删除 state”错误行为。

最终远程验收仍必须由同一个精确产品 Head 完成：

```text
Python / Desktop / Rust / MCP
P0 Windows Gate
Windows Desktop Release Baseline
macOS Desktop Gate
acceptance-doc-sync
local-execution-handoff
```

其中 macOS Gate 必须重新跑最终 DMG App 首启 + 二启，确认 authenticated 8766 ping、task-scoped 数据根、`Documents/acceptance` 不存在，并在 Sidecar 真实退出后成功卸载 DMG。

## 安全边界

- 不使用全局 kill/killall 清理 Sidecar；停止请求仍绑定当前 `instance_id`。
- 不放宽 `LINGJI_ACCEPTANCE_DATA_ROOT` 精确匹配。
- 不删除 Production、Vault、正式凭据或第三方应用配置。
- 本修复不改变 Secret 同步规则；认证状态快照仍要求 `secret_export_count=0`。

## 完成判定

本报告存在不代表 `M5-ISOLATION-002` 已关闭。只有新的统一候选 Head 上 macOS Desktop Gate、Windows Release、完整回归和新 Artifact 全部 PASS 后，才允许开发回执进入 `READY_FOR_M5_REACCEPTANCE`。