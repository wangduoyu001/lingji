# PR #73 · 可启动 Codex 命令解析

- 产品分支：`fix/pr60-launchable-codex-resolution`
- 产品 Commit：`pending`
- 来源缺陷：`PR60-MEMORY-QUALITY-TRIAL-4161807C / WindowsApps codex.exe Access is denied`
- 影响模块：Codex客户端命令发现、Windows npm shim调用、真实 MCP注册验证、连接状态证据、验收同步治理
- 风险等级：P0
- 用户可感知变化：灵机不再因为 PATH第一个 Codex应用别名无法启动就停止；会继续检查后续可启动候选，并显示候选数、选中命令和失败尝试状态。
- 数据或安全边界变化：只检查确定性 PATH/PATHEXT/npm命令候选并执行固定 `--version`；不扫描磁盘、不读取 Codex历史、不修改 PATH、不执行主人提供的 shell片段。

## 自动验收

- [ ] `python -m pytest -q tests/test_executable_resolution.py`：验证 WindowsApps alias被拒绝后选择 npm `codex.cmd`，固定 COMSPEC调用和全候选阻塞状态。
- [ ] `python -m pytest -q tests/test_ai_connector_readiness.py tests/test_ai_memory_connectors.py`：验证配置、可启动命令和真实 `codex mcp list` 三层证据。
- [ ] `python -m pytest -q tests/test_acceptance_sync.py`：验证旧巨型日志和独立日期条目均可满足验收同步，普通验收文档不能冒充变更合同。
- [ ] Python 3.11、Python 3.12、Windows Python全量回归。
- [ ] Desktop smoke、React/TypeScript生产构建、MCP、浏览器和 Obsidian回归。
- [ ] 合入产品分支后执行 P0 Windows Gate、Rust/Tauri和 Windows Desktop Release Baseline。

## 真机验收

- [ ] PATH前部存在不可启动 `WindowsApps\codex.exe`、后部存在可启动 npm `codex.cmd` 时，灵机自动跳过前者并选择后者。
- [ ] UI分别显示候选存在、实际可启动命令和真实 MCP注册验证，不把路径存在显示成 ready。
- [ ] 选中命令执行 `codex mcp list` 并列出 `lingji-memory` 后才显示 ready。
- [ ] 所有候选都被拒绝时显示 `client_launch_blocked`，包含脱敏失败证据，不伪造成功。
- [ ] 新安装包首次 Runtime恢复仍需在 45秒预算内完成。

## 主人肉眼确认

- [ ] 主人无需选择 Codex命令路径；灵机自动解析并展示最终选中的命令类型。
- [ ] 页面能一眼区分“发现候选”“命令可启动”“真实 LingJi MCP可见”。
- [ ] 不出现“配置已完成”与“命令无法启动”同时绿色的矛盾状态。

## 回归项

- [ ] 不使用递归磁盘搜索。
- [ ] 不使用 `shell=True`。
- [ ] `.cmd/.bat` 命令行只由固定服务端参数经 `subprocess.list2cmdline`生成。
- [ ] 不读取 Codex Session/JSONL或主人配置正文。
- [ ] 不修改 PATH、不安装或下载 Codex。
- [ ] 配置冲突、授权、备份和回滚合同保持不变。
- [ ] PR #60 保持 Draft；旧 Artifact不得复用。

## 清理与回滚

- 本变更不创建永久数据；命令探测结果只保存在进程缓存和脱敏连接状态。
- 新 Day 0 使用任务专属 DataRoot、配置副本和临时环境。
- 回滚时删除解析模块并恢复旧状态实现，但不得把路径存在重新当成命令可用。

## 不在范围

- 不自动安装 Codex。
- 不读取或导入 Codex原始历史。
- 不绕过 Windows权限控制。
- 不新增远程/public MCP。
- 不放宽永久记忆授权。

## 最终报告

- 实施报告：`docs/TEST_REPORTS/PR60_LAUNCHABLE_CODEX_COMMAND_RESOLUTION.md`
- 真机报告：新精确产品 Head和 Artifact生成后写入独立 acceptance报告分支。
