# PR60 d69874af 前置验收门禁修复

## 问题

本机 Codex 在执行 `PR60-MEMORY-QUALITY-TRIAL-D69874AF` 前正确停止，原因有两个：

```text
BLOCKED_PRE_CLEANUP
BLOCKED_WRONG_IDENTITY
```

具体为：

1. 历史验收目录 `D:\codex\LingJiAcceptance\PR60-MEMORY-TRIAL-1c514877` 仍存在，通用删除命令被宿主策略拒绝；
2. `LOCAL_EXECUTION_TASK.md` 和 `LOCAL_EXECUTION_RESULT.md` 已切换到 `d69874af / Artifact 8762312712`，但 `CHANGE_ACCEPTANCE_LOG.md` 顶部当前 PR #60 条目仍指向旧的 `1c514877 / Artifact 8723868744`。

Codex 未下载、安装、启动 UI 或读取真实资料，处理符合硬门禁。

## 修复

### 验收身份统一

`docs/ACCEPTANCE/CHANGE_ACCEPTANCE_LOG.md` 的当前 PR #60 条目已统一为：

```text
Product Commit: d69874afd8def42a40c4a5cc5e678a71921d44b5
Artifact: lingji-windows-0.1.0-d69874af
Artifact ID: 8762312712
Report branch: acceptance/pr60-memory-quality-trial-d69874af
Report: docs/TEST_REPORTS/PR60_MEMORY_QUALITY_TRIAL_d69874af.md
```

旧 `1c514877` 条目保留为历史失败记录，并明确禁止重跑。

### 安全清理工具

新增：

```text
scripts/cleanup_acceptance_workspace.py
tests/test_cleanup_acceptance_workspace.py
```

工具的安全边界：

- 默认只允许 `D:\codex\LingJiAcceptance`；
- 拒绝删除验收根目录本身；
- 目标必须是根目录的直接子目录；
- 只允许任务单列出的精确目录名；
- 必须提供匹配的 `task_id`；
- 默认仅 dry-run；
- 只有显式 `--execute` 才删除；
- 不跟随符号链接或 Windows reparse point；
- 逐项删除并输出 JSON 结果；
- 不使用模糊通配符；
- 不接触 Production DataRoot、正式 Acceptance 数据、Vault、正式记忆或用户 AI 配置。

推荐执行顺序：

```powershell
python scripts/cleanup_acceptance_workspace.py `
  --task-id PR60-MEMORY-QUALITY-TRIAL-D69874AF `
  --target D:\codex\LingJiAcceptance\PR60-MEMORY-TRIAL-1c514877

python scripts/cleanup_acceptance_workspace.py `
  --task-id PR60-MEMORY-QUALITY-TRIAL-D69874AF `
  --target D:\codex\LingJiAcceptance\PR60-MEMORY-TRIAL-1c514877 `
  --execute
```

若仓库批准的精确工具仍被宿主策略拒绝，Codex必须继续报告 `BLOCKED_PRE_CLEANUP`，不得绕过安全策略；这时阻塞属于宿主权限而非产品代码。

## 自动测试

```text
python -m pytest -q tests/test_cleanup_acceptance_workspace.py
python scripts/check_local_execution_handoff.py --ref-name master
python scripts/check_acceptance_sync.py
```

覆盖：

- 拒绝删除验收根目录；
- 拒绝根目录外路径；
- 拒绝非白名单目录；
- dry-run 不删除；
- execute 只删除目标目录并保留相邻数据；
- 当前任务身份与当前目标必须一致。

## 结论

```text
WRONG_IDENTITY: FIXED
GUARDED_CLEANUP ENTRYPOINT: ADDED
OWNER DATA ACCESS: NONE
PRODUCT ARTIFACT: UNCHANGED
RE-ACCEPTANCE: MAY RESUME AFTER CI AND MERGE
```
