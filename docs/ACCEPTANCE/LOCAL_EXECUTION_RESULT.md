# LingJi 本机执行结果回执

> 本文件是本机 Codex 向 ChatGPT / 主开发代理提交结果的唯一固定回执。
>
> 当前任务由灵机和 Codex自动执行低风险步骤。主人只观察 UI、授权合成内容、决定测试候选以及许可 Windows 重启。

## 1. 当前回执

```yaml
task_id: PR60-MEMORY-QUALITY-TRIAL-05376996
status: RUNNING
verdict: FAIL
execution_mode: DAY0_THEN_REAL_DATA_TRIAL
repository: wangduoyu001/lingji
product_pr: 60
product_commit: 053769965cf767cfe5221ffa4334b189bedb4d7d
task_instruction_commit: 03b8b27ac2e79923ad4001b49b4345cda726f588
report_branch: acceptance/pr60-memory-quality-trial-05376996
report_commit: 215b917b15859a2841c752c1d8c293359c04410b
report_path: docs/TEST_REPORTS/PR60_MEMORY_QUALITY_TRIAL_05376996.md
public_summary_path: docs/TEST_REPORTS/evidence/PR60_MEMORY_QUALITY_TRIAL_SUMMARY_05376996.json
public_hashes_path: docs/TEST_REPORTS/evidence/PR60_MEMORY_QUALITY_TRIAL_HASHES_05376996.txt
cleanup_before: PASS
cleanup_after: NOT_RUN
remote_branch_verified: true
remote_commit_verified: true
remote_report_verified: true
remote_result_verified: true
pr_comment_verified: true
local_temp_root_absent: false
owner_observation: NOT_REQUIRED
started_at: 2026-08-02T12:26:47Z
finished_at: NOT_FINISHED
trial_protocol_path: docs/ACCEPTANCE/MEMORY_QUALITY_TRIAL.md
day0_result: FAIL
stage1_result: NOT_RUN
stage2_result: NOT_RUN
real_data_authorized: false
quality_questions_total: 0
owner_sample_questions: 0
quality_score_percent: 0
source_accuracy_percent: 0
false_positive_percent: 0
codex_mcp_success_percent: 0
duplicate_formal_content_count: 0
production_pollution_count: 0
owner_config_preserved: NOT_RUN
artifact_name: lingji-windows-0.1.0-05376996
artifact_id: 8832376546
artifact_zip_sha256: abb116cbca8e7ccc2d23e206ed3fdc1a764f5b36bd4209864c628539bda33b4b
installer_sha256: 8f4719e610ddab037044dee364de6e3b4990c37c18a56da8f3fca6e6480b3b4e
portable_exe_sha256: a28169265e3f6eb16f9cb6102d4142b5e5c6d82a97e9c0bd7778e16571caae5e
sidecar_exe_sha256: 8be47b40acf703454ffbec315c58f7a0f9c0d5250ab2156f554fb5b4a1025fb2
manifest_sha256: c9778ddd6f4f782be2bcc43aa6d573b3a76518416aa718529f17fa2a627f73a5
build_metadata_sha256: 167cd2dadddf8d2e3f822729d5d08a1f81080f0fb37a3da9d23b353c5b76721e
```

## 2. 当前阶段

```text
代码与发布链：PASS
正式 Artifact：READY
Day 0：FAIL（全新独立复跑已复现 LJ-05376996-P0-NONEMPTY-DAY0-STORE）
主人检查点 A-F：NOT_RUN
真实资料授权：false
Stage 1：NOT_RUN
Stage 2：NOT_RUN
```

## 3. 本轮必须证明

```text
首次恢复 <= 45 秒
精确 DataRoot / workspace / binding
合成导出包自动发现
一次授权后立即入队，无路径输入和二次提交
Codex跳过不可启动WindowsApps别名并选择可启动命令
真实 codex mcp list 列出 lingji-memory
真实 Codex MCP调用命中验收 Runtime
MCP独占 SQLite/Qdrant，Control只读快照
empty / locked / stale / healthy状态一致
合成候选批准一个、拒绝一个
Windows重启恢复
清理 dry-run = DRY_RUN_READY，execute后目标不存在
Production污染 = 0
真实资料读取 = 0
```

## 4. 自动化与主人边界

Codex负责安装、启动、扫描、UI/API操作、状态刷新、重试、生命周期、截图、报告、Git提交、远程复读和清理。

主人只在以下检查点给出结论或授权：

```text
A：首启、DataRoot和UI观察
B：授权读取任务生成的合成导出包
C：一键导入、Codex MCP和Qdrant证据确认
D：指定一个合成候选批准、一个拒绝
E：允许 Windows重启
F：重启、清理和远程报告最终确认
```

主人未确认全部检查点前，`day0_result`不得为 `PASS`。

## 5. 固定身份

```text
产品 Head：053769965cf767cfe5221ffa4334b189bedb4d7d
Artifact：lingji-windows-0.1.0-05376996
Artifact ID：8832376546
Release run：30744178349
```

旧 `24f35704 / 8832010437`、`3739c42f / 8831573426`、`4161807c / 8821878623`、`b68711fd / 8830090726` 及更早身份禁止使用。

## 6. 最终状态规则

允许：

```text
status: PENDING / RUNNING / COMPLETED / BLOCKED_SUBMISSION
verdict: PENDING / PASS / FAIL / BLOCKED
```

Day 0失败时：

```text
stage1_result = NOT_RUN
stage2_result = NOT_RUN
real_data_authorized = false
```

整个任务最终 PASS仍须满足 Day 0、明确真实资料授权、Stage 1、质量阈值、主人抽查、零重复、零Production污染、主人配置保留、清理和远程复读全部通过。

## 7. 证据索引

```text
最终报告：docs/TEST_REPORTS/PR60_MEMORY_QUALITY_TRIAL_05376996.md
公开摘要：docs/TEST_REPORTS/evidence/PR60_MEMORY_QUALITY_TRIAL_SUMMARY_05376996.json
公开哈希：docs/TEST_REPORTS/evidence/PR60_MEMORY_QUALITY_TRIAL_HASHES_05376996.txt
PR #60本轮独立复跑评论：https://github.com/wangduoyu001/lingji/pull/60#issuecomment-5157925567
报告分支报告内容 HEAD：215b917b15859a2841c752c1d8c293359c04410b
```

禁止提交安装包、数据库、Token、私人正文、完整主人路径清单、node_modules、dist或未脱敏日志。
