# PR #88 M5 macOS Gate 真实退出验证修复

## 任务目标

修复最终 DMG 首启/二启隔离 Gate 的退出竞态。旧 Gate 在发送 instance-scoped stop request 后只等待 `sidecar-state.json` 消失，最多 10 秒，没有验证真实 Sidecar PID 是否退出，也没有验证 8766 是否释放，因此可能在进程仍占用 DMG 时继续二启或卸载，最终出现 `hdiutil detach ... Resource busy`。

## 根因证据

最终候选 `d83c8111cf499aab82b87d74673afadeba01674d` 的 macOS Gate 已通过 exact source identity、Apple Silicon、frontend build、Rust unit tests、embedded release metadata、packaged Sidecar contract、authenticated 8766 boot、DMG 创建以及最终 DMG metadata / arm64 / codesign，最终仅在 `Verify installed App acceptance isolation` 结束时失败：

```text
hdiutil: couldn't unmount "disk6" - Resource busy
```

该步骤当前 cleanup 仅循环检查 state 文件是否消失，没有确认记录的 Sidecar PID 和 8766 listener 已消失。

## 修复设计

每次首启/二启停止流程必须：

```text
读取 sidecar-state.json 中 instance_id + pid
→ 原子写入匹配 instance_id 的 sidecar-stop-request.json
→ 退出 Desktop 主进程
→ 最多等待 30 秒
→ sidecar-state.json 不存在
→ captured Sidecar PID 不存在
→ 8766 无 LISTEN
→ 三项同时成立才视为真实停止
→ 才允许二次启动或 DMG detach
```

超时必须输出当前 state、captured PID 的 `ps`、`lsof -nP -iTCP:8766 -sTCP:LISTEN` 和 Desktop launch log，然后 FAIL。

## 安全边界

- 不使用 `killall`。
- 不把主动 kill Sidecar PID 当正常成功路径。
- 仅发送当前 task-scoped runtime 的精确 `instance_id` stop request。
- 不放宽 `LINGJI_ACCEPTANCE_DATA_ROOT`。
- 不触碰 Production、Vault 或系统凭据。

## 回归要求

- 首次启动 authenticated 8766 PASS。
- 第一次真实退出三条件 PASS。
- 第二次启动 authenticated 8766 PASS。
- 第二次真实退出三条件 PASS。
- `~/Documents/acceptance` 不得出现。
- 最终 DMG detach PASS。
- Windows 已通过的 graceful managed-stop 不得回退。

## 回滚

仅回滚 macOS Gate 的等待与诊断逻辑；不得回退 Sidecar 的 Uvicorn graceful shutdown bridge，也不得恢复“state 消失即代表进程退出”的错误语义。
