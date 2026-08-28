# Task 7E 独立审查：Runner envelope 与 Windows PowerShell 入口

日期：2026-08-28（Asia/Shanghai）  
审查工作树：`/Users/wuhanwangduoyu/Documents/ChatGPT/灵机/.worktrees/phase1-automatic-memory`  
审查基线：`6ae95dd`  
审查 HEAD：`215554e8bc773e711723d85594907fe001b4806f`

## 结论

```text
Spec Compliance: PASS
Task Quality: ACCEPT
Disposition: ACCEPTED_FOR_TASK7_ENTRY
Critical: 0
Important: 0
Minor: 0
```

Task7E 的两个入口阻断均已关闭。该结论只允许 Task7 进入既有质量/规模门禁，
不代表 4R2、100k、release、Artifact、macOS、Phase 1 或主人验收通过。

## 独立核查

### 1. Runner 异常 envelope

- `run_quality_gate()` 在 admission、root、sentinel、fixture、import、gateway、
  promotion、audit、scoring、evaluator、publication_pre 阶段异常时返回新的
  `QualityRunEnvelope`。
- 异常 envelope 的 `evaluation_report` 为 `None`，functional/phase/windows 均为
  `NOT_EVALUATED`；reason 经过固定 allowlist 规范化为 `RUNNER_<STAGE>_FAILED`，
  不序列化原始异常、路径、token 或 fixture 正文。
- 临时报告和最终 repository output 使用既有原子 JSON 发布路径。阶段异常会替换
  旧 PASS；cleanup 异常由 CLI 转为 cleanup envelope，publication 异常返回稳定的
  `QUALITY_PUBLICATION_*` 非零错误，不伪报成功。
- 独立运行 runner 与 guard 聚焦矩阵：`31 passed`。其中 stage matrix 覆盖上述
  阶段、fresh envelope、旧 PASS 替换和敏感内容不泄漏。

### 2. PowerShell release entry

- `scripts/run_powershell_validation.py` 只搜索并调用真实 `pwsh`、`powershell` 或
  `powershell.exe`，不安装 runtime，也不以 Python 重实现 PowerShell。
- `--entry-only` 同时要求 release mode、hook、进程环境 marker 和 PowerShell switch；
  默认 focused/full/release 路径保持原行为。
- `scripts/validate.ps1` 的 entry-only 只跳过重复的 full 阶段，仍真实进入
  `Invoke-ReleaseValidation`；preflight 失败后不会构造或调用 scale environment/
  command。
- 无 PowerShell 的本机运行结果为稳定的
  `BLOCKED_POWERSHELL_RUNTIME_UNAVAILABLE`，没有伪造 marker。

### 3. Windows 远程证据

已通过 GitHub API、run log、artifact 和远程分支复读：

- Workflow run `33153622216` 的 Python job `98791162437` checkout head 为
  `e145dbe4b6642723d0e63821dcb137af83a5fe1b`。
- artifact `p0-windows-pytest-log`（artifact ID `9678758558`）包含原文：

  ```text
  TASK7E_REAL_POWERSHELL_RELEASE_ENTRY PASS events=preflight scale-env=0 scale-command=0
  ```

- marker 来自 `test_release_entry_executes_real_powershell_when_available`，该测试
  通过 launcher 进入真实 `scripts/validate.ps1`，收到非零
  `BLOCKED_4R2_REQUIRED`，hook 只记录 `preflight`。
- `codex/phase1-automatic-memory` 远程 HEAD 已复读为
  `215554e8bc773e711723d85594907fe001b4806f`，报告文件可远程读取。
- P0 run 总体为 failure，但失败来自既有 Windows full-suite 测试和 Desktop smoke
  （日志中的 `Navigation is missing 主动投喂`），不是 Task7E entry 测试；该失败不
  得改写成 Task7E 修复失败，也不得改写成 P0 通过。

### 4. 范围与回归

- 相对 `6ae95dd` 没有 workflow 文件变化；`c47911e`、`e145dbe`、`215554e` 的
  修改保持在 launcher、测试 guard 和证据文档范围内。
- 测试按 `test_00_...` 提前收集，但只增加真实 Windows runtime guard，不改变其他
  测试的判定；Windows 无 runtime 时仅在非 Windows 主机返回 blocked 事实，在
  Windows 主机则要求 runtime 存在并 fail closed。
- 本地未运行 release、4R2、100k、Artifact、live 8766/8767、Production/Vault 或
  owner acceptance，符合本轮边界。

## 验证回执

```text
./.venv/bin/python -m pytest -q \
  tests/evaluation/test_task4_reset_runner.py \
  tests/test_00_task4_reset_validation_guard.py --tb=short
31 passed in 25.73s

compileall: PASS
git diff --check 6ae95dd..HEAD: PASS
python scripts/check_acceptance_sync.py: PASS (product-impacting files 0)
python scripts/check_local_execution_handoff.py: PASS
```

工作树在报告提交前保持 clean；本报告为 docs-only 审查产物，未修改产品代码或
测试。
