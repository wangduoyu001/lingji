# LingJi 本机执行任务单

> 本文件是 ChatGPT / 主开发代理向本机 Codex 下达任务的唯一权威入口。
>
> Codex 只执行第一段 YAML 中 `status: ACTIVE` 的任务，不得从聊天、旧报告、本机残留目录或旧 Artifact 推断任务。

## 1. 当前任务元数据

```yaml
task_id: PR60-CODE-RELEASE-VALIDATION-A90A18A6
status: ACTIVE
execution_mode: CODE_RELEASE_VALIDATION
repository: wangduoyu001/lingji
product_pr: 60
product_branch: feature/unified-ai-memory-connectors
product_commit: a90a18a66ffba157c01367ba70bfec98f58798e2
artifact_name: NOT_APPLICABLE_PENDING_NEW_ARTIFACT
artifact_id: NOT_APPLICABLE
report_base: master
report_branch: acceptance/pr60-code-release-validation-a90a18a6
report_path: docs/TEST_REPORTS/PR60_CODE_RELEASE_VALIDATION_a90a18a6.md
public_summary_path: docs/TEST_REPORTS/evidence/PR60_CODE_RELEASE_VALIDATION_SUMMARY_a90a18a6.json
public_hashes_path: docs/TEST_REPORTS/evidence/PR60_CODE_RELEASE_VALIDATION_HASHES_a90a18a6.txt
result_receipt_path: docs/ACCEPTANCE/LOCAL_EXECUTION_RESULT.md
cleanup_before_required: true
cleanup_after_required: true
remote_verification_required: true
owner_confirmation_required: true
```

## 2. 任务性质

本任务只验证导致 `D0-AUTO-001` 的代码修复和完整发布链。

```text
不安装灵机
不启动桌面 UI
不启动 Production Runtime
不读取或导入真实资料
不修改 Vault、正式数据库、Qdrant 或用户 AI 客户端配置
```

旧身份继续禁止执行：

```text
d69874afd8def42a40c4a5cc5e678a71921d44b5
Artifact 8762312712
```

## 3. 验证目标

必须证明：

1. `tests/test_brain_status_e2e.py` 不再依赖仓库残留 `dist`；
2. 合法的单 JavaScript bundle 可以通过；
3. 缺失、空文件、远程脚本和越界路径必须失败；
4. `npm run build` 每次都验证本次刚生成的 `dist`；
5. 干净构建和已有 `dist` 的重复构建结果一致；
6. 完整 Python、Desktop、Rust/Tauri 和 Windows release 链通过；
7. 本地 release 产物的 Commit 必须精确为 `a90a18a66ffba157c01367ba70bfec98f58798e2`。

实现依据：

```text
docs/TEST_REPORTS/PR60_FRONTEND_DIST_GATE_FIX.md
scripts/validate_frontend_dist.py
tests/test_validate_frontend_dist.py
tests/test_brain_status_e2e.py
desktop/lingji-control/package.json
```

## 4. 开始前门禁

Codex 必须：

1. 拉取远程最新 `master` 并读取本任务单和结果回执；
2. 确认 PR #60 远程 Head 精确等于 `product_commit`；
3. 从精确 Commit 创建隔离 product worktree；
4. 使用唯一临时根：

```text
D:\codex\LingJiValidation\PR60-CODE-a90a18a6
```

5. 只清理该目录和本任务创建的 worktree、构建缓存、测试日志及本地 release 产物；
6. 不删除或修改任何主人数据、正式 Acceptance 数据和旧失败报告；
7. 若身份不一致、目录清理被拒绝或依赖无法安装，立即 BLOCKED，不得绕过。

## 5. 必跑验证

### A. 精确修复测试

```powershell
python -m pytest -q tests/test_brain_status_e2e.py tests/test_validate_frontend_dist.py
```

预期：全部 PASS，不允许 skip。

### B. Python 全量回归

```powershell
python -m pytest -q --tb=short
python -m compileall -q main.py run_service.py run_control_api.py run_packaged_control_api.py run_mcp_server.py run_extraction_worker.py src second_brain tests scripts
```

### C. Desktop 干净构建

```powershell
Set-Location desktop\lingji-control
npm ci --no-audit --no-fund
if (Test-Path dist) { Remove-Item dist -Recurse -Force }
npm run test:smoke
npm run build
```

必须记录 `validate:dist` 的 PASS 输出和实际 JavaScript 入口数量。

### D. 重复构建回归

不得删除第一次构建生成的 `dist`，直接再次执行：

```powershell
npm run build
```

预期仍为 PASS。随后回到仓库根目录。

### E. Rust/Tauri

```powershell
cargo test --manifest-path desktop/lingji-control/src-tauri/Cargo.toml --target x86_64-pc-windows-msvc
```

### F. 完整本地发布门禁

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/validate.ps1 -Mode release
```

必须从头执行完整 full + release，不允许只重跑失败测试，不允许修改断言、skip、mock 或关闭校验。

### G. 本地 release 身份

验证本地生成的：

```text
Installer
Portable EXE
Sidecar
build-metadata.json
lingji-core-manifest.json
SHA256SUMS.txt
```

要求：

- 文件存在且非空；
- metadata Commit 精确等于任务 Commit；
- 计算并记录全部 SHA256；
- 不把本地产物当作正式 GitHub Artifact；
- 不安装、不启动 UI。

## 6. 判定

PASS 必须同时满足：

```text
精确修复测试 PASS
Python 全量 PASS
Desktop smoke PASS
干净 build PASS
重复 build PASS
frontend dist validator PASS
Rust/Tauri PASS
validate.ps1 -Mode release PASS
本地 release 身份与哈希 PASS
无真实数据读取
清理 PASS
远程报告可读
```

任一失败，结论为 FAIL；环境或远程提交无法完成，结论为 BLOCKED。

## 7. 报告与回执

Codex 从最新 `master` 创建：

```text
acceptance/pr60-code-release-validation-a90a18a6
```

提交：

```text
docs/TEST_REPORTS/PR60_CODE_RELEASE_VALIDATION_a90a18a6.md
docs/TEST_REPORTS/evidence/PR60_CODE_RELEASE_VALIDATION_SUMMARY_a90a18a6.json
docs/TEST_REPORTS/evidence/PR60_CODE_RELEASE_VALIDATION_HASHES_a90a18a6.txt
docs/ACCEPTANCE/LOCAL_EXECUTION_RESULT.md
```

报告必须包含：

- 环境和精确 Commit；
- 每条命令、退出码、通过/失败数量；
- 两次 build 结果；
- validator 入口数量；
- release 汇总；
- 本地产物哈希；
- 失败日志尾部；
- 数据安全声明；
- 清理结果。

不得提交安装包、node_modules、target、dist、数据库、Token、私人资料、完整本机路径或未脱敏日志。

## 8. 结束清理

远程报告和回执复读成功后：

- 删除本任务 product/report worktree；
- 删除 npm 缓存副本、dist、target、本地 release 产物和普通成功日志；
- 删除 `D:\codex\LingJiValidation\PR60-CODE-a90a18a6`；
- 确认没有启动 LingJi、8766/8767 进程或孤儿 MCP；
- 安全策略拒绝删除时写 BLOCKED_POST_CLEANUP，不得强制绕过。

## 9. 最终回复

```text
代码发布链验证完成
task_id: PR60-CODE-RELEASE-VALIDATION-A90A18A6
结论: PASS / FAIL / BLOCKED
产品 Commit: a90a18a66ffba157c01367ba70bfec98f58798e2
完整 release: PASS / FAIL / BLOCKED
报告分支: acceptance/pr60-code-release-validation-a90a18a6
报告 Commit: <40位 SHA>
远程确认: PASS
本地清理: PASS
```
