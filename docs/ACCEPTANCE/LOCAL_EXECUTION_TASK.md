# LingJi 本机执行任务单

> 本文件是 ChatGPT / 主开发代理向本机 Codex 下达当前任务的唯一权威入口。
>
> **当前状态：READY FOR M5 REACCEPTANCE。** PR #88 的产品代码已经锁定在 `2c96b3ec54b066204cad8db75455be24822852a9`；六道远程门禁全部 PASS，macOS / Windows 最终 Artifact 已由同一精确产品 Commit 生成并独立复核。
>
> 旧失败产品 `171091fe...` / Artifact `9102748834` 永久禁止重试。本轮只做 M5 真机复验、报告、远程回执和安全清理；**不得继续修改产品代码，不得为了让验收通过而放宽门禁。**

## 1. 当前任务元数据

```yaml
task_id: PR88-M5-REACCEPTANCE-2C96B3EC
status: ACTIVE
execution_mode: MACOS_M5_PHYSICAL_REACCEPTANCE
repository: wangduoyu001/lingji
product_pr: 88
product_branch: feature/owner-autopilot-ui-codexpp
product_commit: 2c96b3ec54b066204cad8db75455be24822852a9
artifact_name: lingji-macos-arm64
artifact_id: 9224368022
artifact_workflow_run_id: 31813880672
artifact_zip_sha256: 6d7b4b8155d5f98abf3ec66fd2b793b51bac39833b08a92984781a7a07ac926e
dmg_name: 灵机_0.1.0_aarch64.dmg
dmg_sha256: 95b72565a30ca86c1eee1c2b0dd4c8239fcce774f32e66e7f24b33fe6b986372
dmg_bytes: 46320432
windows_artifact_name: lingji-windows-0.1.0-2c96b3ec
windows_artifact_id: 9224405293
windows_artifact_workflow_run_id: 31813880675
windows_artifact_zip_sha256: 33e5090e3e7052c9b38514d7c1c3fc7538a58eed609494acfa810b66e04d4d95
windows_installer_sha256: 1fb1bb26b23521fa7726c054304bc0ffa63a694dc49d83b1685f38b7034e97e3
windows_portable_sha256: af32bb8b417ac3c2ae67ae74520be141c04a3ab6289a8ff8d56f4af00feae40a
report_branch: acceptance/pr88-m5-reacceptance-2c96b3ec
report_path: docs/TEST_REPORTS/MACOS_M5_PHYSICAL_ACCEPTANCE_2c96b3ec.md
public_summary_path: docs/TEST_REPORTS/evidence/PR88_M5_REACCEPTANCE_SUMMARY_2c96b3ec.json
public_hashes_path: docs/TEST_REPORTS/evidence/PR88_M5_REACCEPTANCE_HASHES_2c96b3ec.txt
result_receipt_path: docs/ACCEPTANCE/LOCAL_EXECUTION_RESULT.md
cleanup_before_required: true
cleanup_after_required: true
remote_verification_required: true
owner_confirmation_required: true
product_code_changes_forbidden: true
same_sha_artifacts_required: true
secret_export_count_required: 0
rejected_artifact_id: 9102748834
retry_rejected_artifact: false
```

## 2. 已锁定的远程证据，不得重新发包

同一产品 Commit `2c96b3ec54b066204cad8db75455be24822852a9` 已通过：

```text
local-execution-handoff       run 31813880612  PASS
acceptance-doc-sync           run 31813880621  PASS
tests                         run 31813880671  PASS
P0 Windows Gate               run 31813880659  PASS
macOS Desktop Gate            run 31813880672  PASS
Windows Desktop Release       run 31813880675  PASS
```

macOS Gate 已真实完成：精确源码身份、Apple Silicon、Rust tests、App bundle、内嵌 Commit、packaged Sidecar、鉴权 Control API、DMG 创建、最终 DMG 挂载验证、安装后 Acceptance 隔离、Sidecar 真实退出与 Artifact 上传。

Windows 同 SHA Release 已完成 packaged runtime、鉴权健康/managed stop、NSIS 安装器、Artifact 合同；`build-metadata.json` 内嵌 Commit 精确为 `2c96b3ec54b066204cad8db75455be24822852a9`。

因此本机 Codex **不得**：

```text
重新生成 Artifact
切换到较旧 SHA
使用 90398fd8 / 041c5fc8 / 171091fe 的包代替本轮包
提交产品修复
force push / reset --hard / clean -fdx
为了验收绿灯降低身份、隔离、Secret 或生命周期要求
```

如果真机发现产品缺陷，直接 `FAIL / DO NOT MERGE`，保留最小证据并回传；不要在本轮 M5 分支上继续开发。

## 3. M5 任务根与安装规则

在 M5 上创建唯一任务根：

```text
ACCEPTANCE_ROOT="$HOME/LingJiAcceptance/PR88-M5-REACCEPTANCE-2c96b3ec"
LINGJI_ACCEPTANCE_DATA_ROOT="$ACCEPTANCE_ROOT/runtime-data"
ISOLATED_HOME="$ACCEPTANCE_ROOT/isolated-home"
APP_BACKUP="$ACCEPTANCE_ROOT/app-backup/灵机.app"
```

开始前必须：

1. 确认机器为 Apple Silicon / arm64，Gatekeeper 开启；
2. 确认 8766 / 8767 没有 LingJi 遗留 listener；只处理本轮 LingJi 精确实例，不得全局 kill AI/Codex 进程；
3. 记录 `/Applications/灵机.app` 当前状态与签名；
4. 检查 `~/Documents/acceptance`。若开始前已存在，不得擅自删除，先记录为环境阻断；若开始前不存在，本轮结束时必须仍不存在；
5. 下载 Artifact `9224368022`，先校验 ZIP 与 DMG SHA256，任何一个不一致立即 FAIL；
6. 挂载 DMG，复核 App 内嵌产品 Commit 必须精确等于 `2c96b3ec54b066204cad8db75455be24822852a9`，主程序与 Sidecar 必须 arm64；
7. 旧 `/Applications/灵机.app` 必须整体移动到 `$APP_BACKUP`；完整复制新 App 后执行严格 codesign 验证。**禁止 overlay copy。**

若新版本 FAIL：停止本轮精确 Runtime，释放 8766/8767，移除失败 App，整体恢复 `$APP_BACKUP` 并复核签名。若 PASS：保留新 App，报告远程确认后删除临时备份与任务根。

## 4. 真机必须关闭的原始三个 Blocker

### M5-IDENTITY-002

必须证明：

```text
Artifact ID / ZIP / DMG hash 全部与任务单一致
最终 DMG 内 App metadata.commit == 2c96b3ec54b066204cad8db75455be24822852a9
安装后的 /Applications/灵机.app 诊断仍指向同一 Commit
Desktop 主程序 arm64
Sidecar arm64
codesign --verify --deep --strict PASS
```

任何“看起来像同版本”、短 SHA 推断或字符串猜测都不算 PASS。

### M5-UX-003

首次正常打开必须：

```text
不要求主人理解或选择 DataRoot / Workspace / Qdrant / SQLite / 端口 / acceptance
自动准备并进入可用首页
手动目录选择只能在自动准备失败后的高级兜底出现
首页首先说明：有没有必须由主人决定的事、系统正在做什么、已自动处理什么
无主人事项时界面应安静明确，不靠技术指标堆满屏幕证明“系统活着”
```

主人肉眼确认失败即 FAIL，不允许用自动测试代替。

### M5-ISOLATION-002

以 task-scoped Acceptance 环境启动真实安装 App：

```text
HOME="$ISOLATED_HOME"
LINGJI_ACCEPTANCE_DATA_ROOT="$ACCEPTANCE_ROOT/runtime-data"
```

必须证明所有本轮 SQLite、Qdrant、logs、raw、vault、backup、runtime state、token 均在 `$ACCEPTANCE_ROOT` 范围内；不得创建 `~/Documents/acceptance` 或其他任务根外 Acceptance 数据。

## 5. Phase 4 / Phase 5 新功能真机检查

### 找回主窗口

1. 正常启动后，把主窗口最小化或移动到不可见区域；
2. 从 macOS 菜单栏使用 **“找回主窗口”**；
3. 主窗口必须重新可见、回到当前屏幕合理位置并获得焦点；
4. 不得重置其他用户设置，不得影响 Runtime。

主人必须肉眼确认入口容易发现且确实能找回窗口。

### 记忆进度看板

首页必须能直接看出：

```text
正在收纳什么
正在更新什么
当前可取回/检索的覆盖状态
有没有必须由主人决定的授权或异常
```

若没有已验证质量样本，界面不得把向量数量、覆盖率或“可检索”包装成“准确率”。高级诊断信息应留在高级工具/健康细节，不占据日常首页主流程。

## 6. 认证状态与 Secret 边界

必须回归：

```text
Credential Secret 只在 macOS Keychain / 系统安全凭据存储
Overview / Autopilot / 报告只读取脱敏 AuthStatus
Token、Cookie、Authorization Header、Secret 长度、Secret 文件路径不得进入 UI、日志、JSON、Markdown 或 Git
public auth evidence 只能使用 allowlist 字段
secret_export_count = 0
```

若某 Provider 未配置，可以显示未配置；不得伪造 verified。

## 7. Runtime 生命周期

至少完成：

```text
第一次启动 -> authenticated 8766 healthy
精确 instance stop -> sidecar-state.json 消失 + 记录的 Sidecar PID 退出 + 8766 无 LISTEN
同一任务根第二次启动 -> authenticated 8766 healthy
再次精确 stop -> 三重退出条件再次 PASS
```

禁止把“state 文件消失”单独当成 Runtime 已退出；禁止 `killall` 作为正常成功路径。

## 8. 主人只需要确认的内容

Codex 负责安装、命令、日志、哈希、端口、进程、报告、Git 和清理。主人只确认：

```text
A 首次打开是否无需技术配置即可理解并使用
B 首页是否清楚告诉自己系统正在做什么、有没有必须决定的事
C “找回主窗口”是否容易发现且有效
D 记忆进度看板是否清楚，并且没有伪造“准确率”
E 真正需要授权时，动作是否清晰且只有必要选择
```

除上述肉眼判断外，不要求主人填写路径、执行命令、上传文件、清理目录或解释技术日志。

## 9. PASS / FAIL 判定

只有以下全部成立才允许 `PASS`：

```text
精确 Artifact 身份 PASS
整体替换与 codesign PASS
首次体验主人确认 PASS
Acceptance 物理隔离 PASS
主窗口找回 PASS
记忆进度看板 PASS
Credential/AuthStatus/secret_export_count=0 PASS
首启 -> 停止 -> 二启 -> 停止生命周期 PASS
Production / 主人真实数据污染 = 0
8766 / 8767 本轮结束后释放
远程报告、结果回执、PR #88 评论均复读确认
本轮临时数据与备份按 PASS/FAIL 规则完成安全清理或恢复
```

任一 P0/P1 项失败：

```text
Verdict = FAIL
PR #88 = Draft / DO NOT MERGE
不继续使用当前 Artifact
不在 M5 验收分支自行修产品
```

## 10. 报告与远程回执

报告分支：

```text
acceptance/pr88-m5-reacceptance-2c96b3ec
```

必须提交：

```text
docs/TEST_REPORTS/MACOS_M5_PHYSICAL_ACCEPTANCE_2c96b3ec.md
docs/TEST_REPORTS/evidence/PR88_M5_REACCEPTANCE_SUMMARY_2c96b3ec.json
docs/TEST_REPORTS/evidence/PR88_M5_REACCEPTANCE_HASHES_2c96b3ec.txt
docs/ACCEPTANCE/LOCAL_EXECUTION_RESULT.md
```

报告中不得提交真实 Secret、绝对私人资料路径、对话正文或不必要截图原件。只保留判定所需的最小脱敏证据和哈希。

第一次 push 后必须远程复读分支、Commit、报告和结果回执；清理本轮临时垃圾后更新回执，再 push 并再次远程复读；最后把 PASS/FAIL 结论与报告 Commit 写入 PR #88 评论。

**PR #88 在主人真机 PASS 之前始终保持 Draft / DO NOT MERGE。**
