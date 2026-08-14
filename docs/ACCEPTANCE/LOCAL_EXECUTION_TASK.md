# LingJi 本机执行任务单

> **当前状态：IDLE / NO ACTIVE LOCAL TASK。**
>
> PR #88 对产品 Commit `2c96b3ec54b066204cad8db75455be24822852a9` 的 M5 真机复验已经完成，最终结论为 `FAIL / DO NOT MERGE`。
>
> 本文件仍是本机 Codex 的唯一任务入口。只有下面 YAML 的 `status` 被明确改为 `ACTIVE` 后才允许执行；`IDLE` 时不得根据旧报告、聊天、本机残留目录或历史任务自行重跑。

## 1. 最近一次任务身份

```yaml
task_id: PR88-M5-REACCEPTANCE-2C96B3EC
status: IDLE
execution_mode: MACOS_M5_PHYSICAL_REACCEPTANCE
repository: wangduoyu001/lingji
product_pr: 88
product_branch: feature/owner-autopilot-ui-codexpp
product_commit: 2c96b3ec54b066204cad8db75455be24822852a9
artifact_name: lingji-macos-arm64
artifact_id: 9224368022
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
```

## 2. 最近一次结论

远程回执已经完成：

```text
status: COMPLETED
verdict: FAIL
report commit: 9fdbacf52c22ecaac7eab3a4676f80a81e0dfa95
cleanup receipt commit: 33982e1d5d3d567369e56484ade733a8b7228408
```

技术侧已通过：

- Artifact / DMG / 内嵌产品 Commit 身份；
- Apple Silicon arm64；
- whole-bundle 安装与 codesign；
- task-scoped Acceptance 数据隔离；
- Secret 不导出，`secret_export_count=0`；
- 第二次启动与精确停止；
- 失败后的旧 App 恢复与本轮临时数据清理。

主人验收阻塞：

- `M5-UX-003`：首页看不出系统自动执行了什么；
- `M5-UX-004`：新 UI 与旧版没有形成明显、可感知的产品差异；
- `M5-UX-005`：信息层级不友好，重点、进度、下一步不清楚；
- “找回主窗口”和 Memory Progress Dashboard 未获得主人通过。

因此 Artifact `9224368022` **不得再次作为验收候选重跑**。更早的失败 Artifact `9102748834` 同样永久禁止重试。

## 3. 下一轮开始条件

当前没有本机任务。下一轮必须先由产品开发修复上述 P1 UX 问题，然后：

```text
新产品 Commit
→ 同一精确 SHA 的完整自动门禁
→ 新 macOS / Windows Artifact
→ 新 Artifact 哈希锁定
→ 更新本文件为新的 task_id + status: ACTIVE
→ 才允许再次进入 M5 真机验收
```

新的首页至少必须做到：

1. 置顶显示“是否有必须由主人决定的事项”；
2. 清楚显示系统已经自动完成、正在执行、失败/重试、下一步；
3. 用真实事件串起来源发现、收纳、解析、候选、确认、索引、取回、更新；
4. 技术指标下沉到高级诊断，不再用统计卡片冒充自动化体验；
5. 新 UI 必须在首屏结构和日常操作路径上形成明显差异，而不是旧页面追加几个块。

## 4. Codex 硬规则

当 `status: IDLE` 时：

- 不下载 Artifact；
- 不安装或启动 LingJi；
- 不新建验收分支；
- 不修改产品代码；
- 不把历史任务恢复成 ACTIVE；
- 只向调用方报告：当前没有可执行的本机任务。

历史验收细节以对应 `docs/TEST_REPORTS/` 报告为证据，不得覆盖本文件的当前状态。
