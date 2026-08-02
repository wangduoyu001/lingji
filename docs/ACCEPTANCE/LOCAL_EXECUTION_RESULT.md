# LingJi 本机执行结果回执

> 本文件是本机 Codex 向 ChatGPT / 主开发代理提交结果的唯一固定回执。
>
> 当前任务由灵机和 Codex自动执行低风险步骤。主人只观察 UI、授权合成内容、决定测试候选以及许可 Windows 重启。

## 1. 当前回执

```yaml
task_id: PR60-MEMORY-QUALITY-TRIAL-3739C42F
status: COMPLETED
verdict: FAIL
execution_mode: DAY0_THEN_REAL_DATA_TRIAL
repository: wangduoyu001/lingji
product_pr: 60
product_commit: 3739c42ffc44b5524a3231bc2fd7279ae43c11b1
task_instruction_commit: 56c8de00d1a9bf2c5b1c92e73683577dc88de75f
report_branch: acceptance/pr60-memory-quality-trial-3739c42f
report_commit: 067cdf31d7a47d5a4a2419a097a3eb78c22738a2
report_path: docs/TEST_REPORTS/PR60_MEMORY_QUALITY_TRIAL_3739c42f.md
public_summary_path: docs/TEST_REPORTS/evidence/PR60_MEMORY_QUALITY_TRIAL_SUMMARY_3739c42f.json
public_hashes_path: docs/TEST_REPORTS/evidence/PR60_MEMORY_QUALITY_TRIAL_HASHES_3739c42f.txt
cleanup_before: PASS
cleanup_after: PASS
remote_branch_verified: true
remote_commit_verified: true
remote_report_verified: true
remote_result_verified: true
pr_comment_verified: true
local_temp_root_absent: true
owner_observation: NOT_REQUIRED
started_at: 2026-08-02T09:41:00Z
finished_at: 2026-08-02T09:47:00Z
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
owner_config_preserved: PASS
artifact_name: lingji-windows-0.1.0-3739c42f
artifact_id: 8831573426
artifact_zip_sha256: 96c106cd2107b6247d53ceaa6305499af9d0c185a0086a2d2cb1020c6246d387
installer_sha256: 4faa7b2bc558870fa5b864603a7d44db706ee4fdf7ac853084ac003b70e79823
portable_exe_sha256: 38f2324be22dcaaaa5c4cb9e57ce5fb53dd4eb2656a6907a303405dcf55dda26
sidecar_exe_sha256: 2a45a7217cd5c55fda05ef7de80dc9c6057e66da5d649ec0a11828eafd672311
manifest_sha256: 25ca10303b881bc44547a3185c3361ea8239358a799e3f227c0ec542dd89d290
build_metadata_sha256: 33dcaefe4b1eac885fa692ba0529f459fada105532cbf793e80a638576c8a7d5
```

## 2. 当前阶段

```text
代码与发布链：PASS
正式 Artifact：READY
Day 0：NOT_RUN
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
产品 Head：1860fa17c5de26b0ff4d54ace48158a6e343505a
Artifact：lingji-windows-0.1.0-1860fa17
Artifact ID：8830371064
Release run：30738090397
```

旧 `4161807c / 8821878623`、`b68711fd / 8830090726` 及更早身份禁止使用。

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
最终报告：PENDING
公开摘要：PENDING
公开哈希：PENDING
PR #60评论：PENDING
报告分支最终 HEAD：PENDING
```

禁止提交安装包、数据库、Token、私人正文、完整主人路径清单、node_modules、dist或未脱敏日志。
