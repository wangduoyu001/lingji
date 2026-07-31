# LingJi 本机执行任务单

> 本文件是 ChatGPT / 主开发代理向本机 Codex 下达任务的唯一权威入口。
>
> Codex 只执行 `status: ACTIVE` 的任务。`status: IDLE` 表示当前没有可执行任务，不得根据旧聊天、旧报告、本机残留目录或旧 Artifact 自行继续。

## 1. 当前任务元数据

```yaml
task_id: PR60-MEMORY-QUALITY-TRIAL-D69874AF
status: IDLE
execution_mode: DAY0_THEN_REAL_DATA_TRIAL
repository: wangduoyu001/lingji
product_pr: 60
product_branch: feature/unified-ai-memory-connectors
product_commit: d69874afd8def42a40c4a5cc5e678a71921d44b5
artifact_name: lingji-windows-0.1.0-d69874af
artifact_id: 8762312712
artifact_zip_sha256: 6bf1f591502617c400ce482f6beb0d5e430a172cd036137bb4a39cae2cbf4cb4
installer_name: LingJi_0.1.0_windows_x64_setup.exe
installer_sha256: d62867b7b7c90bee8273b3cf5720f53099c266897ce95d0e42224deae31bf262
portable_exe_sha256: a852079b43b2f4020cb66942f44f1a5035633b65d3ff4122c2613c5ea7440a69
sidecar_exe_sha256: 20fe548e1be5cff5d1a34852f4fc0e223abb218eef1e51418724a6723e180599
manifest_sha256: d78a91153b62bcf641bcbbdbc41819283fe0dbc5deff2cdab64cdffcea3e6c87
trial_protocol_path: docs/ACCEPTANCE/MEMORY_QUALITY_TRIAL.md
report_base: master
report_branch: acceptance/pr60-memory-quality-trial-d69874af
report_path: docs/TEST_REPORTS/PR60_MEMORY_QUALITY_TRIAL_d69874af.md
public_summary_path: docs/TEST_REPORTS/evidence/PR60_MEMORY_QUALITY_TRIAL_SUMMARY_d69874af.json
public_hashes_path: docs/TEST_REPORTS/evidence/PR60_MEMORY_QUALITY_TRIAL_HASHES_d69874af.txt
result_receipt_path: docs/ACCEPTANCE/LOCAL_EXECUTION_RESULT.md
day0_required: true
real_data_requires_day0_pass: true
real_data_authorization_required: true
minimum_quality_questions: 20
minimum_owner_sample_questions: 10
minimum_quality_score_percent: 90
minimum_source_accuracy_percent: 95
maximum_false_positive_percent: 5
cleanup_before_required: true
cleanup_after_required: true
remote_verification_required: true
owner_confirmation_required: true
```

## 2. 当前状态

本任务已暂停，禁止执行。

原因：

```text
产品提交 d69874afd8def42a40c4a5cc5e678a71921d44b5
Artifact 8762312712
在本机 release 门禁中触发 D0-AUTO-001，已形成远程 FAIL 报告。
```

该产品提交、安装包、报告分支和所有哈希仅作为历史失败身份保留，不得再次下载、安装或验收。

## 3. 正在准备的新身份

PR #60 当前代码修复方向：

```text
移除依赖残留 dist 的顺序相关 Python 断言
增加独立 frontend dist 验证器
允许合法的单 bundle 或多 bundle 输出
拒绝缺失、空文件、远程脚本和越界路径
在 Vite build 后立即验证本次真实产物
```

实现记录：

```text
docs/TEST_REPORTS/PR60_FRONTEND_DIST_GATE_FIX.md
```

候选代码 Head：

```text
a90a18a66ffba157c01367ba70bfec98f58798e2
```

候选 Head 不是本机验收身份。只有完成以下全部条件后，才允许重新把本文件改为 `ACTIVE`：

1. 精确 Head 的完整 Python、Desktop、Rust/Tauri 和 Windows P0 检查通过；
2. 本地或 CI `scripts/validate.ps1 -Mode release` 从干净环境通过；
3. 生成新的 Windows Artifact；
4. Artifact 名称、ID、ZIP、Installer、Portable、Sidecar 和 Manifest 哈希全部固定；
5. `CHANGE_ACCEPTANCE_LOG.md`、本任务单和结果回执身份完全一致；
6. 新报告分支和路径使用新短 SHA，不复用 `d69874af`。

## 4. Codex 当前行为

Codex读取本文件后只能回复：

```text
当前没有 ACTIVE 本机任务。
旧 d69874af / Artifact 8762312712 已暂停并禁止执行。
等待新 Artifact 和新的 ACTIVE 任务单。
```

Codex不得：

- 下载或安装 Artifact 8762312712；
- 继续旧 Day 0；
- 读取真实资料；
- 使用旧报告分支补写新结论；
- 根据 PR Head 自行构建并替代固定 Artifact；
- 修改 Production DataRoot、Vault、Qdrant、正式记忆或用户 AI 客户端配置。

## 5. 下一次激活要求

新任务激活时必须同时更新：

```text
docs/ACCEPTANCE/LOCAL_EXECUTION_TASK.md
docs/ACCEPTANCE/LOCAL_EXECUTION_RESULT.md
docs/ACCEPTANCE/CHANGE_ACCEPTANCE_LOG.md
PR #60 精确身份与 Artifact 评论
```

在上述身份全部远程可读前，不进行本机安装和真实数据试运行。
