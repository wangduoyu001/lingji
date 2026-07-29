# 验收要求变更记录

> 每个包含产品代码、运行时、UI、连接器、数据链路、脚本、依赖或发布流程变化的 PR，都必须在本文件顶部追加一条记录。
>
> 记录描述“本次代码变化后，验收必须新增、修改或回归什么”。历史记录不得删除，只能更正明显错误并说明原因。

## 填写模板

```markdown
## YYYY-MM-DD · <PR/任务> · <短标题>

- 产品分支：`<branch>`
- 产品 Commit：`<sha 或 pending>`
- 影响模块：
- 风险等级：P0 / P1 / P2 / P3
- 用户可感知变化：
- 数据或安全边界变化：

### 新增或修改的自动验收

- [ ] `<测试命令或测试文件>`：验证什么

### 新增或修改的真机验收

- [ ] `<步骤>`：预期结果

### 主人肉眼确认

- [ ] `<必须人工观察的行为>`

### 回归项

- [ ] `<历史 Bug 或兼容承诺>`

### 清理与回滚

- 临时数据前缀：
- 覆盖安装或迁移方式：
- 临时备份删除条件：
- 测试数据清理方式：

### 不在范围

- `<本次没有实现且不得宣称已完成的能力>`

### 最终报告

- 报告路径：`docs/TEST_REPORTS/<REPORT>.md`
- 报告分支：`acceptance/<task>-<short-sha>`
```

---

## 2026-07-29 · PR #62 · 建立统一 Codex 验收权威

- 产品分支：`docs/acceptance-governance`
- 治理实现与门禁验证基线：`e43da870bc755321f5bd0db4a40aca31df91124d`
- 影响模块：仓库治理、Codex 执行入口、CI 文档同步门禁
- 风险等级：P1
- 用户可感知变化：Codex 拉取代码后可直接从仓库读取当前验收指令，不再依赖聊天中复制的旧指令。
- 数据或安全边界变化：没有产品数据变更；新增规则要求临时证据和配置副本在报告提交后清理。

### 新增或修改的自动验收

- [x] `python scripts/check_acceptance_sync.py`：产品相关文件变化时必须同步修改 `docs/ACCEPTANCE/CHANGE_ACCEPTANCE_LOG.md`。
- [x] `python -m pytest -q tests/test_acceptance_sync.py`：覆盖无代码变化、代码未同步文档、代码已同步文档、隐藏 GitHub 路径、Windows 路径和依赖/Workflow 变化。
- [x] GitHub Workflow `acceptance-doc-sync #1`：精确基线成功。
- [x] GitHub Workflow `tests #1082`：精确基线成功。
- [x] GitHub Workflow `P0 Windows Gate #241`：精确基线成功。

### 新增或修改的真机验收

- [x] Codex 拉取仓库后读取 `AGENTS.md`，能够定位本目录和通用验收指令。
- [x] 使用当前变更记录生成对应验收清单，不依赖聊天历史。
- [x] 验收规则明确要求报告提交后删除临时 Artifact、日志、截图、fixture 和配置临时副本。

### 主人肉眼确认

- [x] 主人明确要求仓库成为验收指令权威，并要求 Codex 拉取后直接读取。

### 回归项

- [x] 不允许代码变更后遗漏验收标准更新。
- [x] 不允许为了补报告移动已打包的产品 Head。
- [x] 不允许长期堆积重复安装包、日志、截图和配置备份。

### 清理与回滚

- 临时数据前缀：`ACCEPTANCE_GOVERNANCE_`
- 覆盖安装或迁移方式：不涉及产品安装。
- 临时备份删除条件：测试完成立即删除。
- 测试数据清理方式：删除测试临时 Git 仓库和输出目录。

### 不在范围

- 不改变 LingJi 产品功能。
- 不替代模块测试报告。
- 不自动合并任何产品 PR。

### 最终报告

- 报告路径：`docs/TEST_REPORTS/ACCEPTANCE_GOVERNANCE_IMPLEMENTATION.md`
- 治理 PR：`#62`
