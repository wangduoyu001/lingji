# PR #60 · 自动记忆入口隔离修复

- 产品分支：`feature/unified-ai-memory-connectors`
- 产品 Commit：`pending`
- 影响模块：AI 助手元数据发现、受控导入计划、Codex 命令解析、连接器环境隔离、Assistant Hub。
- 风险等级：P0
- 用户可感知变化：自动扫描和命令状态在隔离运行中不再误用主机环境；找不到可启动 Codex 命令时，页面会如实显示“未找到”，不会误报权限问题或假装已连接。
- 数据与安全边界：只有调用方没有提供环境时才使用系统环境；显式 `env={}` 现在是严格隔离边界。修复不读取聊天、导出正文、凭据、浏览器配置、Vault 或永久记忆；不写第三方 AI 配置。

## 自动验收

- [ ] `python -m pytest -q tests/test_assistant_hub_imports.py tests/test_assistant_hub_discovery.py tests/test_ai_memory_connectors.py tests/test_ai_connector_readiness.py tests/test_executable_resolution.py`：验证空环境不继承主机 Profile/PATH/CODEX_HOME，且“未发现、不可启动、已验证”状态保持分层。
- [ ] `python -m pytest -q tests/test_assistant_hub_api.py tests/test_vector_truth_contract.py tests/test_memory_owner_lock.py`：验证一动作导入、显式授权和永久记忆所有权未回归。
- [ ] `python scripts/check_acceptance_sync.py`：验证变更条目与验收任务同步。
- [ ] `npm run test:smoke` 与 `npm run build`（`desktop/lingji-control`）：验证 Assistant Hub 页面与生产构建。

## 真机验收

- [ ] 使用隔离 fixture 数据启动 Desktop：进入 AI 助手中心即自动扫描；有候选时只有一次“授权并开始导入”，无候选时只有一次文件选择；不选真实文件。
- [ ] 检查连接器面板分别呈现配置、可启动命令和真实 MCP 验证；不存在矛盾的成功状态。

## 主人肉眼确认

- [ ] 只在用户决定读取真实资料或授权写入第三方 AI 配置前询问；本修复任务不触发这些动作。

## 回归项

- [ ] 显式空环境不得继承宿主 `USERPROFILE`、`CODEX_HOME`、`LOCALAPPDATA` 或 `PATH`。
- [ ] 不得自动导入原始 Codex Session/JSONL、Claude Code 或 WorkBuddy 历史。
- [ ] 永久记忆候选仍需人工批准。

## 清理与回滚

- 临时数据前缀：本地测试框架的临时目录。
- 覆盖安装或迁移方式：不涉及。
- 临时备份删除条件：本任务不创建备份或安装目录。
- 测试数据清理方式：pytest 自身临时目录；不执行任何手动删除。

## 不在范围

- 不新增“接管所有 AI 软件”的未经验证承诺。
- 不读取、导入或删除真实资料。
- 不运行发布、安装、Artifact、重启或历史 Day 0 验收。

## 最终报告

- 报告路径：`docs/TEST_REPORTS/PR60_AUTONOMOUS_MEMORY_REPAIR_1860fa1.md`
