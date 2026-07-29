# 统一 AI 记忆连接器实施与测试报告

日期：2026-07-29  
分支：`feature/unified-ai-memory-connectors`  
基线：PR #56 Head `8c69dfa3bc9562f80f190701244ece82896c7e17`

## 1. 状态

```text
IMPLEMENTED
AUTOMATED_VALIDATION_PENDING
OWNER_MACHINE_ACCEPTANCE_PENDING
DO_NOT_MERGE
```

本报告记录代码和测试合同，不在 CI 与主人真机验收完成前宣称功能通过。

## 2. 本轮目标

将现有 LingJi MCP Memory Gateway 产品化为安装版可使用的统一 AI 记忆连接器：

```text
Codex / Claude Code / WorkBuddy
→ owner-confirmed connector setup
→ authenticated packaged MCP
→ approved memory read + candidate memory proposal
```

## 3. 已实现

### 3.1 安装版 MCP Runtime

- `lingji-core.exe` 新增 `--service mcp`；
- Control Runtime 以 hidden/no-window 子进程托管 MCP；
- MCP 只监听 `127.0.0.1:8767`；
- MCP 使用 Streamable HTTP `/mcp`；
- 所有 HTTP 请求需要 Bearer Token；
- MCP 与 Control Runtime 共享当前 Workspace，但保留 Production / Acceptance 物理隔离；
- 父 Runtime 退出时 MCP 子进程退出；
- `mcp-state.json` 记录运行身份；
- Token 保存在 owner DataRoot 的 `storage/mcp_http_token`；
- Runtime 合同保持 Schema 2，新增向后兼容 `mcp` 字段。

### 3.2 Codex 一键设置

- 读取 `CODEX_HOME/config.toml` 或 `~/.codex/config.toml`；
- 生成写入预览并隐藏 Token；
- 只管理标记区块；
- 写入前验证 TOML；
- 发现同名外部配置时拒绝覆盖；
- 写入前备份；
- 支持连接测试；
- 支持移除管理区块并保留其他设置。

### 3.3 Claude Code 一键设置

- 只调用官方 `claude mcp` CLI；
- 使用 user scope；
- 使用 HTTP Transport 与 Bearer Header；
- 写入前备份 `~/.claude.json`；
- 发现同名外部配置时拒绝覆盖；
- 支持 `get` 测试和 `remove` 回滚；
- Windows 子进程隐藏运行。

### 3.4 WorkBuddy / CodeBuddy 引导设置

- 生成可复制的 HTTP MCP JSON；
- UI 只在主人确认后复制含 Token 的配置；
- 不修改未公开或不稳定的本地配置文件；
- 连接测试留给客户端官方 Try to Run / 自定义连接器流程。

### 3.5 Desktop

- 将首次设置流程拆成扫描、连接、导入、审核四步；
- 新增记忆网关运行状态；
- 新增 Codex、Claude Code、WorkBuddy 独立连接状态；
- 新增设置预览；
- 新增备份、确认、连接测试和回滚操作；
- 明确“连接不等于导入历史”；
- 明确 AI 不能直接写 Core Memory。

## 4. 不在本轮范围

```text
Claude Code history adapter
WorkBuddy / CodeBuddy history adapter
ChatGPT live local connector
remote/public MCP exposure
per-AI Agent Scope UI
per-AI private-memory permission matrix
automatic permanent-memory approval
Qdrant / Embedding phase
```

所有客户端暂时使用同一 `lingji-local` owner-approved 记忆视图。该限制必须在 UI、文档与验收中保持可见。

## 5. 安全审查

### 已落实

- Connector ID allowlist；
- 固定客户端命令；
- 固定配置目标；
- 无 `shell=True`；
- 无任意路径 API；
- 所有 8766 管理路由需要 `X-LingJi-Token`；
- 所有 8767 MCP 请求需要 Bearer Token；
- loopback-only；
- 写入前精确 confirmation；
- 写入前备份；
- Token 不在 UI 预览显示；
- Core Memory 自动写入关闭。

### 真机仍需验证

- Codex CLI 对新配置的实际识别；
- Claude Code CLI 实际写入与连接；
- WorkBuddy 自定义连接器实际接受 HTTP + Header 配置；
- Core 重启后的 MCP 恢复；
- 没有黑窗；
- MCP 工具真实调用；
- Token 未进入公开诊断、日志或截图。

## 6. 自动测试清单

### Python

```text
tests/test_ai_memory_connectors.py
tests/test_assistant_hub_api.py
tests/test_mcp_http_auth.py
tests/test_packaged_mcp_runtime.py
```

覆盖：

- Codex 配置保留；
- TOML 解析；
- 同名冲突拒绝；
- 备份和回滚；
- 精确确认；
- WorkBuddy copy-only 配置；
- Claude 官方 CLI 命令；
- 未知 Connector 拒绝；
- 8766 管理接口认证；
- 8767 Bearer 认证；
- 非 loopback 拒绝；
- Runtime 合同与 Token；
- MCP 状态文件。

### Desktop Smoke

```text
desktop/lingji-control/scripts/assistant-hub-smoke.mjs
desktop/lingji-control/scripts/assistant-memory-connectors-smoke.mjs
desktop/lingji-control/scripts/runtime-sidecar-smoke.mjs
```

覆盖：

- 四步用户流程；
- 预览 / 应用 / 测试 / 回滚入口；
- UI 不混淆连接和导入；
- API 路由存在；
- 固定客户端与安全 Token；
- 安装版 MCP 子进程与打包依赖；
- PyInstaller 收集 MCP 包；
- 发布合同禁止自动 Core Memory 写入。

## 7. CI 门槛

合并前必须在同一最终 Head 上通过：

```text
tests
P0 Windows Gate
Windows Desktop Release Baseline
```

Windows Release 必须生成唯一 Artifact，并验证：

- `lingji-core.exe` GUI subsystem；
- MCP Python 依赖已打包；
- 8766 authenticated health；
- managed stop；
- Runtime contract 的 `mcp` 字段；
- NSIS 安装包；
- SHA256SUMS；
- Artifact 与 Head 对应。

## 8. 主人真机验收

### 基础

1. 同版本覆盖安装最终 Artifact；
2. 灵机启动后 8766 正常；
3. 页面显示“灵机记忆网关已运行”；
4. 没有 PowerShell、CMD 或黑色窗口。

### Codex

1. 点击预览；
2. 确认只修改 LingJi 区块；
3. 点击连接；
4. 新开 Codex 会话；
5. 测试 `get_core_memory`、`search_memory`、`build_context_pack`；
6. 测试 `propose_memory`；
7. 确认候选进入人工审核；
8. 测试断开和回滚。

### Claude Code

执行与 Codex 相同的读取、候选提交与回滚测试。

### WorkBuddy / CodeBuddy

1. 复制配置；
2. 粘贴到官方自定义连接器页面；
3. 执行官方连接测试；
4. 在对话中调用 LingJi 工具；
5. 确认主人审核边界。

### 生命周期

1. 重启 Core；
2. MCP 恢复；
3. Codex / Claude 重新连接；
4. Windows 重启后再验证一次；
5. Production / Acceptance 分别验证 Token 和数据隔离。

## 9. 当前结论

```text
CODE COMPLETE: YES
AUTOMATED PASS: NOT YET
INSTALLED ARTIFACT: NOT YET
OWNER ACCEPTANCE: NOT YET
MERGE ALLOWED: NO
```
