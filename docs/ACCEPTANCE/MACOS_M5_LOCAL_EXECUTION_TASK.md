# LingJi macOS M5 当前真机验收任务单

> **这是当前 M5 真机验收的唯一执行入口。**
>
> 用户只需要把本文件链接交给 Codex。Codex 必须自行读取任务身份、Artifact、验收协议、安装替换规则、隔离规则、Autopilot 专项门禁、清理规则和报告路径；禁止再次向用户索要已经写在这里的信息。
>
> 本文件采用原地更新策略，每轮新的 M5 验收覆盖当前任务身份，不重复创建任务单。

## 0. 当前唯一任务身份

```yaml
status: ACTIVE
task_id: MACOS-M5-AUTOPILOT-PHASE4-171091FE
execution_mode: FRESH_ENVIRONMENT_THEN_LOCAL_ACCEPTANCE
repository: wangduoyu001/lingji
product_commit: 171091fe764c6653cdc7325b4a1a71e0b7800822
product_branch: feature/owner-autopilot-ui-codexpp
pull_request: 88
platform: macOS Apple Silicon
target: aarch64-apple-darwin
app_version: 0.1.0
bundle_format: dmg
artifact_name: lingji-macos-arm64
artifact_id: 9102748834
workflow_run_id: 31495013820
workflow_name: macOS Desktop Gate
workflow_result: success
artifact_archive_size_bytes: 46064302
artifact_archive_sha256: 701680b5d89ef3dc1fa669afd038a13779cb755b3adc5d104df6a1fbee36e306
dmg_name: 灵机_0.1.0_aarch64.dmg
dmg_size_bytes: 46271781
dmg_sha256: 78c1b01abbe44b2800f4cfc3af5020f96d66feaa0682f909c4e2fc86d35fed9f
base_protocol: docs/ACCEPTANCE/MACOS_M5_ACCEPTANCE_INSTRUCTIONS.md
phase4_protocol: docs/ACCEPTANCE/AUTOPILOT_PHASE4_ACCEPTANCE.md
implementation_report_on_product_commit: docs/TEST_REPORTS/AUTOPILOT_ENGINE_PHASE4_IMPLEMENTATION.md
report_path: docs/TEST_REPORTS/MACOS_M5_PHYSICAL_ACCEPTANCE_171091fe.md
report_branch: acceptance/macos-m5-autopilot-phase4-171091fe
```

被测产品身份始终是：

```text
171091fe764c6653cdc7325b4a1a71e0b7800822
```

本任务单及验收协议后续产生的 master 文档 Commit **不改变被测产品 Commit**。

GitHub Actions：

```text
https://github.com/wangduoyu001/lingji/actions/runs/31495013820
```

Artifact：

```text
https://github.com/wangduoyu001/lingji/actions/runs/31495013820/artifacts/9102748834
```

PR：

```text
https://github.com/wangduoyu001/lingji/pull/88
```

---

# 1. Codex 固定读取顺序

```text
本文件
→ docs/ACCEPTANCE/MACOS_M5_ACCEPTANCE_INSTRUCTIONS.md
→ docs/ACCEPTANCE/AUTOPILOT_PHASE4_ACCEPTANCE.md
→ PR #88 当前说明
→ feature/owner-autopilot-ui-codexpp @ 171091fe 的相关代码
→ 产品 Commit 上 docs/TEST_REPORTS/AUTOPILOT_ENGINE_PHASE4_IMPLEMENTATION.md
```

优先级：

```text
MACOS_M5_LOCAL_EXECUTION_TASK.md
→ AUTOPILOT_PHASE4_ACCEPTANCE.md
→ MACOS_M5_ACCEPTANCE_INSTRUCTIONS.md
→ 其他通用验收文档
```

读完直接执行，不再询问 task_id、commit、Artifact、DMG、临时目录、协议或报告路径。

---

# 2. 已通过的远程门禁

精确产品 Commit `171091fe...` 已完成：

```text
acceptance-doc-sync #280: PASS
local-execution-handoff #227: PASS
tests #1295: PASS
P0 Windows Gate #283: PASS
Windows Desktop Release Baseline #165: PASS
macOS Desktop Gate #22: PASS
```

macOS Gate #22 已验证 exact-head source、Apple Silicon、ARM64 Sidecar、Rust tests、`.app`、embedded identity、packaged Sidecar、packaged 8766 boot、DMG build 和 final DMG mount。

本轮真机不重复证明 CI 已经证明的编译事实；重点验证真实 M5 生命周期、隔离、Autopilot 行为和主人体验。

---

# 3. 创建唯一任务根并取得 Artifact

```bash
export ACCEPTANCE_ROOT="$HOME/Library/Caches/LingJiAcceptance/MACOS-M5-AUTOPILOT-PHASE4-171091FE-171091fe"
```

开始前确认该字符串精确匹配当前 task_id，只清理这个任务根，不允许通配符或扩大删除范围。

创建：

```bash
mkdir -p \
  "$ACCEPTANCE_ROOT/artifact" \
  "$ACCEPTANCE_ROOT/logs" \
  "$ACCEPTANCE_ROOT/app-backup" \
  "$ACCEPTANCE_ROOT/runtime-data" \
  "$ACCEPTANCE_ROOT/fixtures" \
  "$ACCEPTANCE_ROOT/evidence-public" \
  "$ACCEPTANCE_ROOT/evidence-private"
```

下载：

```bash
gh run download 31495013820 \
  -R wangduoyu001/lingji \
  -n lingji-macos-arm64 \
  --dir "$ACCEPTANCE_ROOT/artifact"
```

必须得到：

```text
$ACCEPTANCE_ROOT/artifact/灵机_0.1.0_aarch64.dmg
```

校验：

```bash
shasum -a 256 "$ACCEPTANCE_ROOT/artifact/灵机_0.1.0_aarch64.dmg"
stat -f '%z' "$ACCEPTANCE_ROOT/artifact/灵机_0.1.0_aarch64.dmg"
```

期望：

```text
sha256 = 78c1b01abbe44b2800f4cfc3af5020f96d66feaa0682f909c4e2fc86d35fed9f
size   = 46271781 bytes
```

禁止使用任何旧 DMG。无法取得 Artifact ID `9102748834` 时才允许标记 `BLOCKED_ARTIFACT_DOWNLOAD_AUTH`。

---

# 4. 真机预检

严格执行 `MACOS_M5_ACCEPTANCE_INSTRUCTIONS.md`，至少只读记录：

```text
macOS version
uname -m == arm64
Gatekeeper 状态
磁盘空间
已有 /Applications/灵机.app
旧 DMG 挂载
LingJi / lingji-core / MCP 残留进程
8765 / 8766 / 8767 端口
~/Library/Application Support/LingJi 现状
~/Documents/acceptance 验收前是否存在
Obsidian / Ollama / Git / Vault 现状
主人 Production DataRoot
```

禁止为了制造“干净环境”删除 Production DataRoot、Vault、正式记忆、个人模型或第三方 AI 配置。

---

# 5. 强制物理隔离

本轮 Runtime 必须使用：

```bash
export LINGJI_ACCEPTANCE_DATA_ROOT="$ACCEPTANCE_ROOT/runtime-data"
mkdir -p "$LINGJI_ACCEPTANCE_DATA_ROOT"
```

必须在 Runtime 启动前注入。

本轮 `storage/logs/snapshots/backups/raw/qdrant/vault/runtime`、SQLite、token 和派生数据只能位于这个 task-scoped root。

以下任一情况直接：

```text
FAIL_ACCEPTANCE_ISOLATION
```

- 新增任务根外 Runtime 数据；
- 本轮创建新的 `~/Documents/acceptance`；
- 写入主人 Production DataRoot；
- 普通启动继续复用历史 Acceptance workspace。

报告必须记录：

```text
unexpected_write_count
unexpected_paths
production_pollution_count
```

---

# 6. 安装必须 whole-bundle replace

禁止 overlay copy。

固定流程：

1. 正常退出旧 LingJi；
2. 确认 Core 与 8766 已释放；
3. 挂载已验哈希 DMG；
4. 若 `/Applications/灵机.app` 已存在，把整个旧 App 移到 `$ACCEPTANCE_ROOT/app-backup/灵机.app`；
5. 从 DMG 完整复制新 `.app` 到 `/Applications`；
6. 执行 `codesign --verify --deep --strict /Applications/灵机.app`；
7. PASS 才允许启动；
8. 新 App 复制/签名失败则完整回滚旧 App，并复验旧 App 签名。

报告：

```text
install_mode=whole_bundle_replace
post_install_codesign=PASS|FAIL
rollback_required=true|false
```

---

# 7. 使用 task-scoped 环境启动已安装 App

不要用可能丢失本轮环境变量的 Finder 双击作为技术隔离结论。

从已安装 App 主二进制启动：

```bash
APP_BIN="$(find /Applications/灵机.app/Contents/MacOS -maxdepth 1 -type f -perm -111 | head -n 1)"
test -n "$APP_BIN"
LINGJI_ACCEPTANCE_DATA_ROOT="$LINGJI_ACCEPTANCE_DATA_ROOT" \
  "$APP_BIN" >"$ACCEPTANCE_ROOT/logs/desktop-launch.log" 2>&1 &
```

主人只观察 GUI，不需要操作终端。

---

# 8. 基线验收

必须确认：

```text
Release Metadata commit == 171091fe764c6653cdc7325b4a1a71e0b7800822
UI/诊断产品 commit == 171091fe764c6653cdc7325b4a1a71e0b7800822
connection_state=connected
control_service=connected
runtime_state=healthy
runtime_healthy=true
runtime_managed=true
runtime_binary_available=true
8766 only 127.0.0.1
```

并验证正常首次启动不要求主人先选择 DataRoot。手动选择位置只能是自动准备真实失败后的兜底。

完成：

```text
启动 → healthy → 正常退出 → Core 退出 → 8766/8767 释放
→ 同 task-scoped root 再启动 → healthy
```

---

# 9. Phase 4 Autopilot 真机专项

## 9.1 Engine 真正在运行

从当前 task-scoped Runtime 的 token 文件读取 token，但不得打印或写入公开报告：

```bash
TOKEN_FILE="$LINGJI_ACCEPTANCE_DATA_ROOT/storage/control_api_token"
test -s "$TOKEN_FILE"
TOKEN="$(cat "$TOKEN_FILE")"
```

调用：

```bash
curl -fsS \
  -H "X-LingJi-Token: $TOKEN" \
  http://127.0.0.1:8766/api/autopilot/status
```

必须确认：

```text
enabled=true
running=true
cycle_count >= 1
last_success_at 非空
```

继续轮询到下一轮，`cycle_count` 必须自然增长。不得手工调用隐藏 repair 命令伪造结果。

## 9.2 真实安全修复 + 自动复验

只操作本轮 task root。

选择本轮自动创建、可重建且位于 `$LINGJI_ACCEPTANCE_DATA_ROOT` 内的 `backups` 目录作为 fixture。执行前确认：

```text
真实路径位于 ACCEPTANCE_ROOT 内
不是 symlink
不含主人文件
```

删除该测试目录后等待 Autopilot 下一轮自然巡检。

必须观察到：

```text
backups 目录自动恢复
recent_actions 出现 create_backup_directory
verified=true
automatic_repair_count 增长
任务根外文件变化 = 0
```

这一步是 Phase 4 的关键证明：不是 UI 写“自动处理”，而是 Runtime 真正发现、修复并复验。

## 9.3 stale extraction lease

只用本轮 fixture，在 task-scoped `lingji_state.db` 构造一个未超过 max_attempts 的 stale running extraction job。

必须验证：

```text
Autopilot 通过现有 release_stale 合同恢复任务
不创建重复 job
不绕过 max_attempts
```

再构造最终 failed/cancelled fixture，必须保持：

```text
不会被 Autopilot 自动 queue.retry()
不会无限重新排队
```

不得使用主人真实任务做该测试。

## 9.4 高风险状态必须停止自动写

仅在隔离 fixture / 测试副本制造以下状态，不损坏真实运行数据库：

```text
SQLite integrity error
vector rebuild_required=true
```

验证策略结果：

```text
owner_action_count > 0
自动写修复 = 0
自动 Qdrant rebuild/delete = 0
```

如果无法在不损坏当前真机运行环境的前提下安全构造，使用产品 Commit 上的定向测试作为技术证据，并在报告明确标记 `fixture_simulated=true`；禁止为了验收故意破坏真实数据库。

---

# 10. Owner-first UI 肉眼验收

主人只需要判断这些：

1. App 正常出现，无异常黑窗；
2. 首次启动无需理解 DataRoot/Qdrant/Embedding/MCP/端口即可进入可用状态；
3. 没有主人事项时，首页明确“无需操作”或同等清楚结论；
4. 普通后台异常不会冒充“需要我决定”；
5. 发生 9.2 的真实自动修复后，首页能看到类似“刚自动处理 / 已自动复验”的真实结果；
6. 技术细节仍留在高级诊断，不重新占满首页；
7. 主人能明显感知：

```text
灵机自己发现问题
→ 自己修安全可修的问题
→ 自己确认修好没有
→ 只有不该替主人决定的事情才找主人
```

这一步必须由主人真实观察，Codex 不得代写 PASS。

---

# 11. 强制安全门禁

本轮最终必须全部为 0：

```text
unauthorized_content_read_count = 0
auto_permanent_memory_approval_count = 0
auto_qdrant_destructive_action_count = 0
third_party_ai_config_modify_count = 0
production_pollution_count = 0
unexpected_write_count = 0
```

任一不为 0：`FAIL / DO NOT MERGE`。

Ollama/ffmpeg 等可选能力缺失只允许后台降级，不得为了验收擅自安装。

---

# 12. 失败处理

任一步失败：

```text
保存最小失败证据
→ 继续不受影响的只读检查
→ 判断是否污染正式数据
→ 正常退出
→ 清理本轮临时内容
→ 生成 FAIL/BLOCKED 报告
```

产品缺陷则：

```text
停止本轮验收
→ 回传根因/复现/证据
→ 开发代理修复
→ 新产品 Commit
→ 新 Artifact
→ 原地更新本任务单
→ 再验收
```

禁止拿同一个已确认失败的 DMG 让主人反复测试。

---

# 13. 结束清理

无论 PASS/FAIL/BLOCKED：

```text
正常退出 LingJi
→ 确认 Autopilot/Core 退出
→ 8766/8767 释放
→ 卸载 DMG
```

然后清理本轮：

```text
ACCEPTANCE_ROOT
Artifact/DMG 重复副本
fixture
checkpoint
临时 SQLite/Qdrant
测试 DataRoot
普通成功日志/截图
临时 App 备份（新版本 PASS 后）
临时 worktree
```

只保留：

```text
/Applications/灵机.app 当前有效版本
主人 Production DataRoot
Vault
正式仓库
最终 Markdown 验收报告
必要脱敏证据摘要
```

禁止删除主人正式数据和第三方配置。

---

# 14. 最终报告与回传

报告写入：

```text
docs/TEST_REPORTS/MACOS_M5_PHYSICAL_ACCEPTANCE_171091fe.md
```

报告分支：

```text
acceptance/macos-m5-autopilot-phase4-171091fe
```

至少包含：

```text
task_id
product_commit
artifact_id
dmg_sha256
macOS_version
machine_architecture
artifact_integrity
install_result
post_install_codesign
runtime_result
restart_result
autopilot_running
autopilot_cycle_growth
auto_repair_fixture_result
auto_repair_verified
stale_lease_result
final_failed_job_not_retried
owner_escalation_result
auto_write_on_integrity_error_count
auto_qdrant_destructive_action_count
unauthorized_content_read_count
auto_permanent_memory_approval_count
third_party_ai_config_modify_count
production_pollution_count
unexpected_write_count
ui_owner_observation
cleanup_after
local_temp_root_absent
failed_step
root_cause_if_known
verdict
```

结论只允许：

```text
PASS
FAIL
BLOCKED
```

报告提交后必须远程复读，确认 GitHub 上的分支、Commit 和报告正文确实存在，再向用户汇报完成。

PR #88 在主人真实 M5 体验确认前继续保持 Draft，不得合并。