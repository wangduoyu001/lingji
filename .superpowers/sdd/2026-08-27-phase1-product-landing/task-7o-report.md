# Task 7O — Measurement Contract Closure

日期：2026-08-28（Asia/Shanghai）

## 范围

本轮只处理 Task7N combined review 的 C1/C2/I1/I2/M1：统一 functional evidence
artifact、保持 automatic activation quarantine、补全 promotion orphan/audit 观测、迁移
过时 readiness 断言并删除未调用的旧编排实现。未修改 retrieval/ranking/vector/model、
自动晋级策略、100k、release、UI、真实数据或本机任务单。

## RED / GREEN

- RED：新增 Task7O contract tests 首次 `4 failed, 1 passed`，分别暴露 canonical artifact
  缺失、quarantine measurement 缺失和 orphan/audit 合同缺口。
- GREEN：Task7O contract closure `9 passed, 1 warning`；Task7M/N1/N2/N3、Task4 reset
  readiness/runner 直接矩阵 `154 passed, 1 warning`；Task4 reset end-to-end compatibility
  `20 passed, 1 warning`。
- `python -m compileall -q src tests`：PASS。
- `git diff --check`：PASS。
- `python3 scripts/check_acceptance_sync.py`：PASS。
- `python3 scripts/check_local_execution_handoff.py`：PASS（LOCAL_EXECUTION_TASK 仍 IDLE）。

## 收口内容

1. `CanonicalFunctionalEvidence` 位于 `src/automatic_memory/quality_evidence.py`，以严格
   typed immutable boundary 统一 runner 序列化与 scale loader 反序列化。它包含 run/code/
   fixture identity、import、promotion、Gateway、MCP、Qdrant、corruption、baseline、
   nullable production、measured quality/status/readiness。未知/缺失字段、错误类型、布尔
   数值、NaN 与状态矛盾均返回 `BLOCKED_4R2_REQUIRED`。真实 runner FAIL artifact 已直接
   交给 loader 并被阻断；完整一致 test artifact 通过同一类 round-trip 并可到达 scale
   callback。
2. 当前 automatic activation quarantine 下，所有 category 的 expected/actual 以
   `pending_owner_review` 为合同，accuracy 为 `not_applicable`，correct/total/accuracy
   保持 null；没有恢复自动 approve，也没有用 NA 掩盖事实、引用或 MCP 失败。
3. Promotion measurement 从本次所有 imported message 的 relationship 查询收集 link，
   不再只从 projection 反查；审计纳入 owner-rejected 与 projection-error 等正式终态，
   pending/rejected/error 的 projection/link、缺失/额外/重复 audit 都 fail closed。
4. 过时的 Task4 runner readiness 测试已迁移到当前 MCP measured failure 与 nullable
   selection-before-bound baseline 合同；`quality_gate` 不再保留未调用的旧编排副本，历史
   `_promote_fixtures` 仅保留薄兼容 shim，不参与正式 runner。

## 质量 CLI（一次复算）

质量 CLI 仍诚实失败：`functional_status=FAIL`、facts `0/106`、citations `0/106`、strict
MCP `0/100`、context baseline `NOT_MEASURED`、activation `NOT_APPLICABLE`（null counters）、
production `null`。因此 Task7 质量、100k、release、Artifact、live 8766/8767、Production/Vault
和主人验收仍未通过；本轮不授权 retrieval diagnosis。

## 交付身份

- 产品/测试 Commits：`5b5a22a094d328561ef4636e751aad6de6201840`,
  `7bdd0b408ff1b6c884ac72acaa59caa3e1feacb0`
- 初始证据/文档 Commit：`214b717c9920dfb44ca2290aaa593e78abdaf9ab`
- 本报告不声明 Task7O accepted，须由全新
  独立审查确认 Critical=0、Important=0 后才能进入下一步。
