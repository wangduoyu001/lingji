# LingJi 本机执行结果回执

> 本文件是本机 Codex 向 ChatGPT / 主开发代理提交结果的唯一固定回执。
>
> 当前任务由灵机和 Codex自动执行低风险步骤。主人只观察 UI、授权真实内容、决定永久记忆以及许可 Windows 重启。

## 1. 当前回执

```yaml
task_id: PR60-MEMORY-QUALITY-TRIAL-4161807C
status: PENDING
verdict: PENDING
execution_mode: DAY0_THEN_REAL_DATA_TRIAL
repository: wangduoyu001/lingji
product_pr: 60
product_commit: 4161807ce4598cc1696093da4a703de101648280
task_instruction_commit: bc9aead956e363405c39ae784d9beb9ba5bc5dff
report_branch: acceptance/pr60-memory-quality-trial-4161807c
report_commit: PENDING
report_path: docs/TEST_REPORTS/PR60_MEMORY_QUALITY_TRIAL_4161807c.md
public_summary_path: docs/TEST_REPORTS/evidence/PR60_MEMORY_QUALITY_TRIAL_SUMMARY_4161807c.json
public_hashes_path: docs/TEST_REPORTS/evidence/PR60_MEMORY_QUALITY_TRIAL_HASHES_4161807c.txt
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
artifact_name: lingji-windows-0.1.0-4161807c
artifact_id: 8821878623
artifact_zip_sha256: c1019006509033a45debf24fd5530133cda2a804d051424a66a0c3d122c680ab
installer_sha256: 219c5866ad22b5a1b6e6ea0d78c02fb2b4a392548d3cb9b360a236d9d6bdf931
portable_exe_sha256: c49c46f32d9b4e52c0e32754c16b4bf8f67cfb9a7d61d90ea782a2a524508210
sidecar_exe_sha256: 76c36cd02735afd556ebdfd9a0af4ebf0a8879eaccb56dc1252f1ea8466b9d20
manifest_sha256: 50168354b918f318a71677892c4d5fd6e6dc85cbdf18ae0599d31bf12d61f368
build_metadata_sha256: 73726765d1293d0a4ef7b3e72150208da98919abfaf53c7a681b35181c1a75a2
binding_contract_version: 1
binding_id: PR60-MEMORY-QUALITY-TRIAL-4161807C
expected_data_root: D:\codex\LingJiAcceptance\PR60-MEMORY-TRIAL-4161807c\product
expected_workspace: acceptance
actual_data_root: PENDING
actual_workspace: PENDING
binding_verified: false
automatic_scan_result: NOT_RUN
automatic_model_refresh_result: NOT_RUN
automatic_hardware_refresh_result: NOT_RUN
automatic_recovery_result: NOT_RUN
owner_global_bootstrap_preserved: NOT_RUN
```

## 2. 当前阶段

```text
Day 0自动执行：NOT_RUN
主人观察 A-D：NOT_RUN
候选决定 E：NOT_RUN
Windows重启许可与恢复 F：NOT_RUN
真实资料授权：false
Stage 1：NOT_RUN
Stage 2：NOT_RUN
```

真实资料正文读取必须保持0，直到 Day 0 与主人观察全部 PASS并获得具名授权。

## 3. 固定身份

```text
产品 Head：4161807ce4598cc1696093da4a703de101648280
Artifact：lingji-windows-0.1.0-4161807c
Artifact ID：8821878623
Artifact ZIP：c1019006509033a45debf24fd5530133cda2a804d051424a66a0c3d122c680ab
Installer：219c5866ad22b5a1b6e6ea0d78c02fb2b4a392548d3cb9b360a236d9d6bdf931
Portable：c49c46f32d9b4e52c0e32754c16b4bf8f67cfb9a7d61d90ea782a2a524508210
Sidecar：76c36cd02735afd556ebdfd9a0af4ebf0a8879eaccb56dc1252f1ea8466b9d20
Manifest：50168354b918f318a71677892c4d5fd6e6dc85cbdf18ae0599d31bf12d61f368
Build metadata：73726765d1293d0a4ef7b3e72150208da98919abfaf53c7a681b35181c1a75a2
```

旧 Artifact `8723868744`、`8762312712`、`8820695386` 禁止使用。

## 4. Day 0自动验证状态

```text
前置清理：NOT_RUN
Artifact下载与哈希：NOT_RUN
任务启动契约：NOT_RUN
任务专属LOCALAPPDATA/APPDATA：NOT_RUN
覆盖安装：NOT_RUN
Runtime实际DataRoot自证：NOT_RUN
Runtime workspace自证：NOT_RUN
旧bootstrap回退防护：NOT_RUN
无黑窗：NOT_RUN
自动AI元数据扫描：NOT_RUN
自动模型刷新：NOT_RUN
自动硬件刷新：NOT_RUN
自动状态轮询/重试/恢复：NOT_RUN
UI观察台与菜单定位：NOT_RUN
Codex配置/命令/真实MCP三层状态：NOT_RUN
真实Codex MCP调用：NOT_RUN
Embedding/Qdrant详细状态：NOT_RUN
合成候选生成：NOT_RUN
候选批准/拒绝执行：NOT_RUN
Core/Sidecar三轮重启：NOT_RUN
Desktop同环境重启：NOT_RUN
Windows重启恢复：NOT_RUN
主人全局bootstrap保留：NOT_RUN
Production污染：0
真实资料正文读取：0
```

## 5. 主人只需观察与决定

```text
Checkpoint A：UI主动运行、DataRoot/workspace/binding验证清楚，未要求逐项启动和扫描：NOT_RUN
Checkpoint B：自动扫描和进度可见，真实正文前停在授权边界：NOT_RUN
Checkpoint C：Codex三层状态一致，真实MCP调用成功：NOT_RUN
Checkpoint D：Embedding/Qdrant原因、影响和处理进度可懂：NOT_RUN
Checkpoint E：主人给出候选A/B决定，Codex代为执行且结果正确：NOT_RUN
Checkpoint F：主人许可Windows重启，灵机自动恢复且绑定不漂移：NOT_RUN
```

主人未明确确认 A-F 前：

```text
day0_result != PASS
real_data_authorized = false
stage1_result = NOT_RUN
stage2_result = NOT_RUN
```

## 6. Stage 1质量指标

仅在具名真实资料授权后填写：

```text
质量题总数：0 / >=20
主人抽查：0 / >=10
质量分：0 / >=90%
来源准确率：0 / >=95%
误报率：0 / <=5%
Codex MCP成功率：0 / >=95%
重复正式内容：0
Production污染：0
主人配置保留：NOT_RUN
```

## 7. 最终状态规则

允许：

```text
status: PENDING / RUNNING / COMPLETED / BLOCKED_SUBMISSION
verdict: PENDING / PASS / FAIL / BLOCKED
```

整个任务最终 PASS 必须同时满足：

- Day 0与主人观察 A-F PASS；
- 具名真实资料范围获得明确授权；
- Stage 1与质量阈值PASS；
- Production污染为0；
- 主人配置保留；
- 报告、远程复读和安全清理PASS。

Day 0 PASS但尚未授权 Stage 1时，只能保持 `RUNNING / PENDING`。

## 8. 证据索引

```text
最终报告：PENDING
公开摘要：PENDING
公开哈希：PENDING
PR #60评论：PENDING
报告分支最终HEAD：PENDING
```

禁止提交安装包、数据库、Token、私人正文、真实路径全集、node_modules、dist或未脱敏日志。
