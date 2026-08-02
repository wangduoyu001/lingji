# LingJi 本机执行结果回执

> 本文件是本机 Codex 向 ChatGPT / 主开发代理提交结果的唯一固定回执。
>
> 当前任务由灵机和 Codex自动执行低风险步骤。主人只观察 UI、授权合成内容、决定测试候选以及许可 Windows 重启。

## 1. 当前回执

```yaml
task_id: PR60-MEMORY-QUALITY-TRIAL-24F35704
status: PENDING
verdict: PENDING
execution_mode: DAY0_THEN_REAL_DATA_TRIAL
repository: wangduoyu001/lingji
product_pr: 60
product_commit: 24f3570440437f57b6a62e54d409577ed40b6c14
task_instruction_commit: PENDING
report_branch: acceptance/pr60-memory-quality-trial-24f35704
report_commit: PENDING
report_path: docs/TEST_REPORTS/PR60_MEMORY_QUALITY_TRIAL_24f35704.md
public_summary_path: docs/TEST_REPORTS/evidence/PR60_MEMORY_QUALITY_TRIAL_SUMMARY_24f35704.json
public_hashes_path: docs/TEST_REPORTS/evidence/PR60_MEMORY_QUALITY_TRIAL_HASHES_24f35704.txt
cleanup_before: NOT_RUN
cleanup_after: NOT_RUN
remote_branch_verified: false
remote_commit_verified: false
remote_report_verified: false
remote_result_verified: false
pr_comment_verified: false
local_temp_root_absent: false
owner_observation: NOT_REQUIRED
started_at: PENDING
finished_at: PENDING
trial_protocol_path: docs/ACCEPTANCE/MEMORY_QUALITY_TRIAL.md
day0_result: NOT_RUN
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
artifact_name: lingji-windows-0.1.0-24f35704
artifact_id: 8832010437
artifact_zip_sha256: ac3c329e85e35b17fa35c92f68f415a58905e544b8325de42e557171f35fcd45
installer_sha256: e89a10c12d08d0ddb910233d6c7d366f50e509a975ce6506f0cf3b80772368ce
portable_exe_sha256: 5139cef2771124c6609c85acc154a10d9db1c77b06e0ed4deefd5fac16d8341f
sidecar_exe_sha256: 4cbf0a62a1f5667ec22e36c2e347f4a113c05eb4217eaa48801c960450061b03
manifest_sha256: 077e07851431d4eeece773a1734a98c0816fe62067dbe78487d1276e6b46e182
build_metadata_sha256: fd32179b943ed88fe6d3ebb09f345846913b2f7b956cb55fc9dedb26248fb6c0
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
产品 Head：24f3570440437f57b6a62e54d409577ed40b6c14
Artifact：lingji-windows-0.1.0-24f35704
Artifact ID：8832010437
Release run：30743102197
```

旧 `3739c42f / 8831573426`、`4161807c / 8821878623`、`b68711fd / 8830090726` 及更早身份禁止使用。

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
