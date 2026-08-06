# 统一 AI 记忆连接器实施与测试报告

日期：2026-07-29  
PR：#60  
分支：`feature/unified-ai-memory-connectors`  
目标：`master`  
稳定基线：`18b99a6909e929df432253686eeaeee3ed9f7024`

## 1. 当前状态

```text
COMBINED_GUIDED_UI_AND_CONNECTOR_CODE_COMPLETE
PRE_RETARGET_TESTS_PASSED
MASTER_TESTS_P0_AND_RELEASE_TRIGGERED
INSTALLED_ARTIFACT_PENDING
OWNER_MACHINE_ACCEPTANCE_PENDING
DO_NOT_MERGE
```

PR #60 现在同时包含 PR #56 的新手引导、AI 助手扫描与历史导入，以及统一 AI 记忆连接器。这样主人只需安装和验收一个精确 Windows Artifact。

PR #56 在组合版本通过完整 CI 并生成安装包前保持开放，之后按 superseded 关闭，不单独合并。

## 2. 产品目标

让第一次接触灵机的用户完成：

```text
扫描 AI 工具
→ 预览连接改动
→ 备份现有配置
→ 连接 LingJi Memory Gateway
→ 测试连接
→ 导入已有资料
→ 查看处理进度
→ 审核永久记忆
```

连接与历史导入必须保持分离：

```text
连接 = 今后的 AI 任务通过 MCP 使用灵机记忆
导入 = 把旧聊天、导出文件或工作报告放进采集队列
```

## 3. 新手 UI 与导入

已实现：

- 首页改为“开始使用”；
- 统一页面说明与全局使用说明；
- 扫描、连接、导入、审核四步首次使用流程；
- Codex、Claude Code、WorkBuddy 安全元数据扫描；
- 检测、连接、导入、同步状态分离；
- ChatGPT 官方 Export ZIP/JSON 导入；
- Codex Report JSON 导入；
- 导入复用 Capture、Extraction Queue、幂等、重试与审计；
- 导入成功只代表进入处理链，不代表成为永久记忆；
- AI 只能提交候选，主人审核仍是正式记忆唯一入口。

## 4. 安装版 MCP Runtime

- `lingji-core.exe` 新增 `--service mcp`；
- Control Runtime 以 hidden/no-window 子进程托管 MCP；
- MCP 只监听 `127.0.0.1:8767`；
- MCP 使用 Streamable HTTP `/mcp`；
- 所有 HTTP 请求需要 Bearer Token；
- MCP 与 Control Runtime 共享当前 Workspace，但 Production / Acceptance 物理隔离；
- 父 Runtime 退出时 MCP 子进程退出；
- `mcp-state.json` 记录运行身份；
- Token 保存在 owner DataRoot 的 `storage/mcp_http_token`；
- Runtime 合同保持 Schema 2，新增向后兼容 `mcp` 字段；
- `automatic_core_memory_write=false`。

## 5. 客户端连接器

### 5.1 Codex

- 读取 `CODEX_HOME/config.toml` 或 `~/.codex/config.toml`；
- 生成写入预览并隐藏 Token；
- 只管理带标记的 `lingji-memory` 区块；
- 保留模型、账号、审批、沙箱和其他 MCP 设置；
- 写入前验证完整 TOML；
- 发现非 LingJi 管理的同名配置时拒绝覆盖；
- 写入前备份；
- 支持 `codex mcp list` 连接测试；
- 回滚只移除 LingJi 管理区块。

### 5.2 Claude Code

- 只调用官方 `claude mcp` CLI；
- 使用 user scope；
- 使用 HTTP Transport 与 Bearer Header；
- 写入前备份 `~/.claude.json`；
- 发现非 LingJi 管理的同名配置时拒绝覆盖；
- 支持 `get` 测试和 `remove` 回滚；
- Windows 子进程隐藏运行。

### 5.3 WorkBuddy / CodeBuddy

- 生成可复制的 HTTP MCP JSON；
- 不修改未公开或不稳定的本地配置文件；
- 由主人粘贴到官方自定义连接器/MCP 页面；
- 由客户端执行官方连接测试；
- 预览 API 不返回完整 Token 配置；
- 只有精确确认复制后才返回完整本机配置。

## 6. MCP 记忆工具

连接后的 AI 可以使用：

```text
get_core_memory
search_memory
fetch_memory
build_context_pack
propose_memory
recent_changes
memory_health
```

写入边界：

```text
AI propose_memory
→ reviewable candidate
→ Human Memory Review
→ owner approval
→ formal permanent memory
```

AI 不能直接批准、覆盖或删除 Core Memory。

## 7. 当前不在范围

```text
Claude Code history adapter
WorkBuddy / CodeBuddy history adapter
ChatGPT live local connector
remote/public MCP access
per-AI Agent Scope UI
per-AI private-memory permission matrix
automatic permanent-memory approval
Qdrant / Embedding phase
```

第一版本机客户端使用同一 `lingji-local` owner-approved 记忆视图。不得提前宣称已经完成逐 AI 权限隔离。

## 8. 安全审查

已落实：

- Connector ID allowlist；
- 固定客户端命令；
- 固定配置目标；
- 无 `shell=True`；
- 无任意路径 API；
- 8766 管理路由需要 `X-LingJi-Token`；
- 8767 MCP 请求需要 Bearer Token；
- 8766 与 8767 均为 loopback-only；
- 写入前精确 confirmation；
- 写入前备份；
- Token 不在 UI 和预览 API 显示；
- Production / Acceptance Token 和 DataRoot 隔离；
- Core Memory 自动写入关闭。

真机仍需验证：

- Codex 对新配置的实际识别；
- Claude Code CLI 实际写入与连接；
- WorkBuddy 自定义连接器接受 HTTP + Header 配置；
- MCP 子进程真实启动；
- Core 重启和 Windows 重启后的 MCP 恢复；
- 没有 PowerShell、CMD 或黑窗；
- MCP 工具真实调用；
- Token 未进入公开诊断、日志或截图。

## 9. 自动测试

Python：

```text
tests/test_ai_memory_connectors.py
tests/test_assistant_hub_api.py
tests/test_mcp_http_auth.py
tests/test_packaged_mcp_runtime.py
```

Desktop：

```text
desktop/lingji-control/scripts/assistant-hub-smoke.mjs
desktop/lingji-control/scripts/assistant-memory-connectors-smoke.mjs
desktop/lingji-control/scripts/runtime-sidecar-smoke.mjs
```

覆盖：

- Codex 配置保留与 TOML 解析；
- 同名冲突拒绝；
- 备份和回滚；
- 精确确认；
- WorkBuddy copy-only 配置；
- Claude 官方 CLI 命令；
- 未知 Connector 拒绝；
- 8766 管理接口认证；
- 8767 Bearer 认证；
- 预览秘密脱敏；
- 非 loopback 拒绝；
- Runtime 合同、Token 与 MCP 状态；
- 四步用户流程；
- 预览、应用、测试和回滚入口；
- 安装版 MCP 子进程与打包依赖；
- PyInstaller 收集 MCP 包；
- 发布合同禁止自动 Core Memory 写入。

## 10. 已通过的预重定向验证

精确 Head：

```text
1936f5842e61f7c7bfecb47fa9561e9f72bc0617
tests #1062: SUCCESS
```

通过：

- Python 3.11 full suite；
- Python 3.12 full suite；
- Windows Python full suite；
- Desktop 22-script Smoke suite；
- React/Vite production build；
- Tauri configuration validation；
- MCP server creation；
- Browser capture smoke；
- Obsidian plugin smoke。

## 11. 组合版本最终 CI 门槛

本次报告更新提交用于触发目标为 `master` 的完整门禁。

必须在同一最终 Head 上通过：

```text
tests
P0 Windows Gate
Windows Desktop Release Baseline
```

Windows Release 必须生成唯一 Artifact 并验证：

- `lingji-core.exe` GUI subsystem；
- MCP Python 依赖已打包；
- 8766 authenticated health；
- managed stop；
- Runtime contract 的 `mcp` 字段；
- NSIS 安装包；
- SHA256SUMS；
- Artifact 与 Head 对应。

## 12. 主人真机验收

### 新手理解

1. 第一次打开能找到“开始连接 AI”；
2. 能理解扫描、连接、导入和审核的区别；
3. 不看源码或开发文档即可走完整流程；
4. 页面不会把“检测到”显示成“已连接”。

### Codex

1. 预览只修改 LingJi 区块；
2. 设置并新开 Codex 会话；
3. 调用 `get_core_memory`、`search_memory`、`build_context_pack`；
4. 调用 `propose_memory`；
5. 候选进入人工审核；
6. 断开和回滚保留其他设置。

### Claude Code

执行与 Codex 相同的读取、候选提交与回滚测试。

### WorkBuddy / CodeBuddy

1. 复制配置；
2. 粘贴到官方自定义连接器页面；
3. 执行官方连接测试；
4. 在对话中调用 LingJi 工具；
5. 确认主人审核边界。

### 生命周期

1. 重启 Core 后 MCP 恢复；
2. Windows 重启后 MCP 恢复；
3. Production / Acceptance Token 和数据隔离；
4. 启动和重启没有 PowerShell、CMD 或黑色控制台窗口。

## 13. 当前结论

```text
CODE COMPLETE: YES
PRE_RETARGET TESTS: PASS
MASTER GATES: RUNNING / PENDING
INSTALLED ARTIFACT: NOT YET
OWNER ACCEPTANCE: NOT YET
MERGE ALLOWED: NO
```
