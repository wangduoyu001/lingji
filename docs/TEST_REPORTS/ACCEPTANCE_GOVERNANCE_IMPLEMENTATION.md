# 验收治理实施与测试报告

日期：2026-07-29  
分支：`docs/acceptance-governance`  
目标：`master`

## 1. 目标

将灵机验收要求从聊天记录迁移为仓库内的持续权威，使 Codex 每次拉取代码后能够直接读取当前验收指令，并强制每次产品优化、开发、修复、依赖或发布流程变化同步更新验收要求。

## 2. 新增权威

```text
docs/ACCEPTANCE/README.md
docs/ACCEPTANCE/CODEX_ACCEPTANCE_INSTRUCTIONS.md
docs/ACCEPTANCE/CHANGE_ACCEPTANCE_LOG.md
docs/ACCEPTANCE/REPORT_TEMPLATE.md
```

职责：

- `README.md`：验收治理和读取顺序；
- `CODEX_ACCEPTANCE_INSTRUCTIONS.md`：Codex 通用真机验收执行基线；
- `CHANGE_ACCEPTANCE_LOG.md`：每次代码变化对应的增量验收要求；
- `REPORT_TEMPLATE.md`：最终验收报告格式。

## 3. 自动同步门禁

新增：

```text
scripts/check_acceptance_sync.py
tests/test_acceptance_sync.py
.github/workflows/acceptance-doc-sync.yml
```

门禁识别以下产品相关变化：

- `src/`；
- `second_brain/`；
- Desktop React、Tauri 和 Smoke；
- Browser Extension；
- Obsidian Plugin；
- `scripts/`；
- GitHub Workflows；
- constraints 和根依赖文件；
- 正式 Python 启动入口。

出现上述变化时，同一变更必须包含：

```text
docs/ACCEPTANCE/CHANGE_ACCEPTANCE_LOG.md
```

只修改其他验收文件不能替代增量验收记录。

## 4. 仓库入口和治理

更新：

```text
AGENTS.md
docs/DEVELOPMENT_RULES.md
.github/pull_request_template.md
```

Codex 的最小读取顺序现在明确包含验收权威。PR 模板要求开发者填写自动测试、真机测试、主人观察、回归、清理、回滚和不在范围。

## 5. 磁盘和安装规则

统一规则：

```text
清理旧验收目录
→ 关闭 LingJi 残留进程
→ 释放 8766 / 8767
→ 直接覆盖安装
→ 完整验收
→ 提交报告
→ 删除临时 Artifact、日志、截图、fixture 和配置副本
```

默认不卸载，不删除主人 DataRoot、Vault、正式记忆或 AI 客户端原配置。不长期保留重复 ZIP、安装包和备份。

## 6. 测试覆盖

`tests/test_acceptance_sync.py` 覆盖：

- 纯文档变化不触发门禁；
- 产品代码变化但未更新增量验收记录时失败；
- 产品代码与增量验收记录同步时通过；
- 只更新其他验收文件不能绕过；
- Workflow 和依赖变化触发门禁；
- Windows 路径标准化；
- 纯测试变化不强制新增产品验收记录。

## 7. 预期验证命令

```powershell
python -m pytest -q tests/test_acceptance_sync.py
python scripts/check_acceptance_sync.py
.\scripts\validate.ps1 -Mode focused -Area docs
```

GitHub：

```text
acceptance-doc-sync
现有 tests workflow
```

## 8. 安全边界

- 不读取或提交 Token、配置正文、私人聊天或数据库；
- 不改变 LingJi Runtime、数据模型或产品行为；
- 不修改 PR #60 产品 Head；
- 不自动合并产品 PR；
- 报告与产品 Artifact 继续使用独立分支。

## 9. 当前结论

```text
DOCUMENT AUTHORITY: IMPLEMENTED
SYNC CHECKER: IMPLEMENTED
UNIT TESTS: ADDED
CI WORKFLOW: ADDED
LOCAL EXECUTION: NOT RUN IN GITHUB CONNECTOR ENVIRONMENT
PR CI: PENDING
MERGE: PENDING CI AND REVIEW
```
