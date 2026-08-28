# Task 7E — Runner Error Envelope and Executable Release Entry

日期：2026-08-28（Asia/Shanghai）  
工作树：`/Users/wuhanwangduoyu/Documents/ChatGPT/灵机/.worktrees/phase1-automatic-memory`  
基线：`0047d75795d255b2c9a36217784751ec8fde8f4d`

## 范围与结论

本轮只修复 Task 1 Repair Round 2 的 I4/I7：正式 quality runner 的阶段异常
回执，以及 `scripts/validate.ps1` release dispatch 的测试可观测性。未运行
4R2、100k、release、Artifact、Production/Vault、8766/8767 或主人验收。

代码实现为：

- `run_quality_gate()` 为 admission/root/sentinel/fixture/import/gateway/
  promotion/audit/scoring/evaluator/publication_pre 异常生成新的
  `QualityRunEnvelope`；`evaluation_report=None`，三种状态均为
  `NOT_EVALUATED`，reason code 仅来自 allowlist。
- Envelope 增加无路径的 machine cleanup inventory；异常文本、路径、token
  和 fixture 正文不会被序列化。临时输出使用原子写入；CLI 在 isolated root
  退出后再发布到固定 repository output，替换旧 PASS。
- CLI 捕获 setup/runner/cleanup/publication 边界；publication 写失败返回非零
  并仅输出稳定 `QUALITY_PUBLICATION_*` stderr code。
- PowerShell release entry 增加 opt-in `LINGJI_VALIDATE_TEST_HOOK`，记录
  `preflight`、`scale-env`、`scale-command` 顺序；当前 `BLOCKED_4R2_REQUIRED`
  在 preflight 退出，因此后两项计数为零。新增 launcher 只在发现真实
  `pwsh`/`powershell(.exe)` 时调用 `scripts/validate.ps1`，不安装或替代它。

## TDD / 自动化证据

RED：新增 stage-hook matrix 首次运行因 `run_quality_gate()` 不接受 stage hook
而失败；这是缺失异常边界的行为性失败。GREEN：

```text
./.venv/bin/python -m pytest -q tests/evaluation/test_task4_reset_runner.py
25 passed in 25.28s

./.venv/bin/python -m pytest -q tests/test_task4_reset_validation_guard.py tests/evaluation/test_task4_reset_runner.py
28 passed in 25.13s

./.venv/bin/python -m pytest -q tests/evaluation/test_task4_reset_readiness.py tests/test_task4_reset_validation_guard.py
112 passed in 1.00s
```

完整 Task4 reset/quality/validation 回归（含 ingestion/import/identity/readiness/
runner/end-to-end/historical rejection/promotion/acceptance gate）最终为：

```text
350 passed in 96.76s
```

Stage matrix 覆盖每个 runner stage 的注入异常、旧 PASS 原子替换、fresh
NOT_EVALUATED、allowlisted reason 与无敏感数据检查。已有 Task4 reset readiness
测试和 measured FAIL、cleanup override、API 兼容合同均保持通过。

## PowerShell 状态

按任务要求进行了只读搜索：

```text
command -v pwsh powershell powershell.exe: no matches
find /usr/local /opt/homebrew /Applications /Library ...: no matches
find /Users/wuhanwangduoyu ...: no matches
```

因此本机没有真实 PowerShell runtime，未执行或冒充执行 PowerShell release
dispatch；本轮状态严格为 `BLOCKED_POWERSHELL_RUNTIME_UNAVAILABLE`，Task 7
entry 不能标记 READY。Windows CI/具备 PowerShell 的主机可运行：

```text
python scripts/run_powershell_validation.py --mode release --hook <test-file>
```

这会直接调用真实 `scripts/validate.ps1`，并在 preflight 阻塞时验证 scale
environment/command marker 为零。

## 限制与清理

- `LOCAL_EXECUTION_TASK.md` 保持 `IDLE`；未执行本机验收任务。
- 未运行 full/release/4R2/100k、Artifact、Production/Vault、真实服务、UI 或
  owner acceptance。
- 测试仅使用 pytest temporary roots；不得据此宣称 Task 7/Phase 1 或 release
  acceptance 已通过。PowerShell 真实执行证据留待具备 runtime 的 Windows CI/主机。
