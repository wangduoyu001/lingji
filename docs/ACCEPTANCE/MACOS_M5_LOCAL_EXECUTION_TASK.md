# LingJi macOS M5 当前真机验收任务单

> **当前状态：ACTIVE / READY_FOR_M5_REACCEPTANCE。**
>
> 本轮只允许验收下面指定的新 Artifact。旧 `171091fe...` / Artifact `9102748834` 永久禁止重试。

## 0. 当前任务身份

```yaml
status: ACTIVE
task_id: MACOS-M5-OWNER-AUTOPILOT-REACCEPTANCE-041C5FC8
repository: wangduoyu001/lingji
product_commit: 041c5fc805d2280c4d84d78bca45799f131ad61b
product_branch: feature/owner-autopilot-ui-codexpp
pull_request: 88
platform: macOS Apple Silicon
target: aarch64-apple-darwin
artifact_name: lingji-macos-arm64
artifact_id: 9189896949
workflow_run_id: 31722145426
artifact_archive_sha256: dcb6945a1b6784d2d98b4994f1814dbcf3a8b279017278e4940dba398bfc8cee
dmg_name: 灵机_0.1.0_aarch64.dmg
dmg_size_bytes: 46307971
dmg_sha256: bef1da0fb2783a22462a5ca60ea64b3483352a3ff1dc60199bd4254b9c10ad3d
windows_artifact_id: 9189908712
windows_artifact_sha256: 027a59c6f0a03a452225578f506b5d0509b5b358b665e413e414fae97cf4a22d
verdict: PENDING_PHYSICAL_M5
retry_same_artifact: true
```

## 1. 开始前

先按 `docs/ACCEPTANCE/MACOS_M5_ACCEPTANCE_INSTRUCTIONS.md` 做只读环境预检：

- 确认 Apple Silicon / arm64；
- 确认 8765–8767 与 LingJi 残留进程；
- 记录旧 `/Applications/灵机.app` 状态；
- 创建本任务唯一临时根；
- 不碰 Production DataRoot、Vault 或其他正式数据。

本轮临时数据必须全部位于：

```text
~/Library/Caches/LingJiAcceptance/MACOS-M5-OWNER-AUTOPILOT-REACCEPTANCE-041C5FC8/
```

## 2. 安装包身份

Codex 自行下载 Artifact `9189896949`，并先验证：

```text
Artifact ZIP SHA256 = dcb6945a1b6784d2d98b4994f1814dbcf3a8b279017278e4940dba398bfc8cee
DMG SHA256 = bef1da0fb2783a22462a5ca60ea64b3483352a3ff1dc60199bd4254b9c10ad3d
DMG size = 46307971
```

必须完整替换旧 App，禁止 overlay copy。新 App 安装后先做签名与 release metadata 验证；metadata Commit 必须精确等于：

```text
041c5fc805d2280c4d84d78bca45799f131ad61b
```

不一致立即 FAIL，不继续启动。

## 3. Acceptance 隔离

启动前设置本任务专用：

```text
LINGJI_ACCEPTANCE_DATA_ROOT=<task-root>/runtime-data
HOME=<task-root>/isolated-home
```

必须验证：

- storage / logs / runtime / raw / qdrant 等只写入 task root；
- `~/Documents/acceptance` 不得因本轮产生；
- task root 外新增 Acceptance 数据路径数量 = 0；
- 首次退出后 Sidecar 与 8766 真实释放；
- 同一任务根第二次启动仍能正常进入 healthy；
- 第二次退出后同样无残留。

## 4. 主人体验检查

只有到必须肉眼判断时才请主人参与。重点不是逐个点按钮，而是确认：

1. 第一次打开无需理解 DataRoot、Qdrant、Embedding 或端口即可进入可用状态。
2. 首页能直接看懂灵机已经自动做了什么、正在做什么、当前是否真的需要主人决定。
3. Codex 工作记录数量有来源解释，不再像莫名出现的聊天窗口。
4. 自动发现和后台处理无需反复点击刷新。
5. 技术异常与“需要主人决定”明确分开。
6. 只有明确授权或高风险边界才要求主人操作。

## 5. 结束清理

验收结束后必须：

- 停止本轮 App / Sidecar；
- 确认 8765–8767 无本轮残留；
- 卸载 DMG；
- 删除本轮 task root、普通成功日志、截图、重复 ZIP/DMG、临时数据库和缓存；
- 只保留最终报告、必要失败证据摘要和后续确实复用的正式 App；
- 不删除 Production DataRoot、Vault 或其他正式数据。

## 6. 最终报告

最终报告路径：

```text
docs/TEST_REPORTS/MACOS_M5_PHYSICAL_ACCEPTANCE_041c5fc8.md
```

报告分支：

```text
acceptance/macos-m5-owner-autopilot-041c5fc8
```

报告必须记录：

- 最终 PASS / FAIL；
- 安装包身份；
- 首启 / 二启；
- Acceptance 隔离；
- UI/Autopilot 肉眼结论；
- 清理结果；
- 远程报告 Commit 与 PR #88 评论。

PR #88 在真实 M5 PASS 前继续 Draft / DO NOT MERGE。
