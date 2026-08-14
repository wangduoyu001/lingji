# PR #88 文档权威清理报告

日期：2026-08-15

## 目标

在 PR #88 的 M5 真机复验已经 `FAIL / DO NOT MERGE` 后，清理仓库中互相冲突的“当前任务”“当前状态”和旧总控计划，确保 Codex 只存在一个可判断是否执行的本机任务入口。

## 已确认的当前事实

```text
Product PR: #88
Product commit: 2c96b3ec54b066204cad8db75455be24822852a9
M5 task: PR88-M5-REACCEPTANCE-2C96B3EC
M5 verdict: FAIL / DO NOT MERGE
Report branch: acceptance/pr88-m5-reacceptance-2c96b3ec
Report commit: 9fdbacf52c22ecaac7eab3a4676f80a81e0dfa95
Cleanup receipt commit: 33982e1d5d3d567369e56484ade733a8b7228408
```

技术侧通过，主人体验侧阻塞为 `M5-UX-003`、`M5-UX-004`、`M5-UX-005`；“找回主窗口”和 Memory Progress Dashboard 未通过。

## 清理内容

### 保留并更新为当前权威

- `docs/PROJECT_STATUS.md`
  - 更新到 2026-08-15 当前状态；
  - 明确 PR #88 真机 FAIL；
  - 明确下一步必须先做产品 UI / 信息架构修复。

- `docs/ACCEPTANCE/README.md`
  - 取消“当前为 MEMORY_QUALITY_TRIAL”一类阶段绑定；
  - 规定只有 `LOCAL_EXECUTION_TASK.md` 是唯一当前任务；
  - 专项文档只作为协议，不再充当任务单。

- `docs/ACCEPTANCE/LOCAL_EXECUTION_TASK.md`
  - 从 `ACTIVE` 转为 `IDLE`；
  - 记录最近失败候选与禁止重跑边界；
  - 明确新 Commit + 新 Artifact + 新 ACTIVE task 之前不得执行。

- `docs/ACCEPTANCE/LOCAL_EXECUTION_RESULT.md`
  - 同步真实 M5 回执为 `COMPLETED / FAIL`；
  - 保留技术 PASS、主人 FAIL、清理与远程证据。

- `docs/ACCEPTANCE/MACOS_M5_ACCEPTANCE_INSTRUCTIONS.md`
  - 改成纯平台协议；
  - 不再引用另一份 M5“当前任务单”；
  - 具体身份和路径只读取 canonical task。

### 删除的冲突文档

- `docs/ACCEPTANCE/MACOS_M5_LOCAL_EXECUTION_TASK.md`
  - 原内容仍宣称自己是“当前唯一执行入口”，且绑定旧 Commit `041c5fc8`，与 canonical task 冲突；删除后由 Git 历史保留追踪。

- `docs/ACCEPTANCE/LOCAL_FINAL_CLOSEOUT_PLAN.md`
  - 原内容仍宣称 `ACTIVE GOVERNANCE`，绑定 PR #60 与旧产品提交；已经失去当前治理职责，删除后由 Git 历史保留追踪。

## 保留的历史文档

以下文件保留，因为它们承担专项协议或历史验收合同职责，只要不宣称自己是当前任务即可：

- `AUTOPILOT_PHASE4_ACCEPTANCE.md`
- `MEMORY_QUALITY_TRIAL.md`
- `CHANGE_ACCEPTANCE_LOG.md`
- `docs/TEST_REPORTS/` 历史报告

`CHANGE_ACCEPTANCE_LOG.md` 的历史条目不删除，避免破坏验收追踪链。

## 清理后的读取模型

```text
README.md
→ AGENTS.md
→ docs/PROJECT_STATUS.md
→ docs/ACCEPTANCE/README.md
→ docs/ACCEPTANCE/LOCAL_EXECUTION_TASK.md
→ docs/ACCEPTANCE/LOCAL_EXECUTION_RESULT.md
→ 当前任务明确引用的专项协议
```

当 task 为 `IDLE` 时，本机 Codex 必须停止，不得从历史文档自行拼出下一任务。

## 验证要求

本次仅文档治理，不改变产品 Runtime。合并前必须由 GitHub 验证：

```text
python scripts/check_local_execution_handoff.py
python -m pytest -q tests/test_local_execution_handoff.py
acceptance-doc-sync
完整 tests workflow
```

预期：canonical task/result 在 `IDLE + COMPLETED/FAIL` 状态下仍满足 handoff schema；删除重复旧任务不会影响机器验收入口。
