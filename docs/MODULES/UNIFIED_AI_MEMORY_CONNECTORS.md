# 统一 AI 记忆连接器

状态：开发分支 `feature/unified-ai-memory-connectors`

## 1. 目标

让本机 AI 工具通过同一套 LingJi Memory Gateway 使用主人批准的记忆，而不是为每个客户端复制一份记忆数据库。

正式用户流程：

```text
扫描客户端
→ 预览连接改动
→ 备份现有配置
→ 设置 LingJi MCP
→ 立即测试连接
→ AI 读取批准记忆 / 提交候选记忆
→ 主人人工审核
```

连接与历史导入必须保持分离：

```text
连接 = 今后任务调用 LingJi Memory Gateway
导入 = 把已有聊天或报告送入采集队列
```

## 2. 当前客户端支持

| 客户端 | 设置方式 | 自动写配置 | 连接测试 | 历史导入 |
|---|---|---:|---:|---:|
| Codex | 管理 `~/.codex/config.toml` 中的单一 LingJi 区块 | 是 | 配置文件 + `codex mcp list` | Codex Report 已有 |
| Claude Code | 调用官方 `claude mcp` CLI 的 user scope | 是 | `claude mcp get lingji-memory` | 待正式 Adapter |
| WorkBuddy / CodeBuddy | 生成自定义 MCP JSON，由用户粘贴到官方页面 | 否 | 在客户端内 Try to Run | 待正式 Adapter |
| ChatGPT | 本地 Plus 客户端不属于本轮本机连接器范围 | 否 | 否 | 官方 Export ZIP/JSON 已有 |

不得把以下状态混为一谈：

```text
detected
configured
runtime_ready
client_verified
history_import_available
live_sync_available
```

## 3. 唯一正式链路

```text
Codex / Claude Code / WorkBuddy
→ authenticated http://127.0.0.1:8767/mcp
→ existing src.mcp_server tools
→ MemoryGateway
→ owner-approved Core Memory + searchable knowledge
```

写入链路：

```text
AI propose_memory
→ reviewable candidate
→ Human Memory Review
→ owner approval
→ formal permanent memory
```

强制边界：

```text
automatic_core_memory_write = false
owner_approved_memory_only = true
candidate_write_available = true
```

## 4. 安装版 Runtime

`lingji-core.exe` 继续作为唯一打包 Runtime 二进制。

控制进程：

```text
lingji-core.exe --service control
→ 127.0.0.1:8766 Local Control API
→ managed child: lingji-core.exe --service mcp
```

MCP 子进程：

```text
127.0.0.1:8767
transport = streamable-http
endpoint = /mcp
authentication = Authorization: Bearer <owner-local token>
```

生命周期规则：

- MCP 子进程由 Control Runtime 启动；
- 父 Runtime 停止或重启时，MCP 同步退出；
- MCP 记录 `mcp-state.json`；
- Token 保存于当前 Workspace 的 `storage/mcp_http_token`；
- 只绑定 loopback；
- 不开放公网；
- 不在安装目录保存主人数据；
- Production 与 Acceptance 使用各自独立 Token 和数据根。

## 5. Codex 配置治理

LingJi 只管理以下标记之间的区块：

```toml
# BEGIN LINGJI MANAGED MCP: lingji-memory
[mcp_servers.lingji-memory]
url = "http://127.0.0.1:8767/mcp"
http_headers = { Authorization = "Bearer <owner-local token>" }
enabled = true
startup_timeout_sec = 15.0
tool_timeout_sec = 120.0
# END LINGJI MANAGED MCP: lingji-memory
```

规则：

- 保留文件中的模型、审批、沙箱和其他 MCP 配置；
- 写入前解析完整 TOML；
- 发现非 LingJi 管理的同名 Server 时拒绝覆盖；
- 写入前创建备份；
- 回滚只移除 LingJi 标记区块。

## 6. Claude Code 配置治理

LingJi 不直接猜测 Claude 内部配置结构，使用官方 CLI：

```text
claude mcp add --transport http --scope user ...
claude mcp get lingji-memory
claude mcp remove --scope user lingji-memory
```

规则：

- 写入前备份 `~/.claude.json`（如果存在）；
- 发现非 LingJi 管理的同名 Server 时拒绝覆盖；
- 所有 CLI 子进程使用 Windows hidden/no-window 标志；
- 命令参数固定，API 不接受任意命令或任意路径。

## 7. WorkBuddy / CodeBuddy 边界

当前只生成可复制配置：

```json
{
  "mcpServers": {
    "lingji-memory": {
      "type": "http",
      "url": "http://127.0.0.1:8767/mcp",
      "headers": {
        "Authorization": "Bearer <owner-local token>"
      }
    }
  }
}
```

LingJi 不猜测或修改未公开的本地配置文件。

用户在 WorkBuddy / CodeBuddy 自定义连接器页面粘贴配置，并使用客户端提供的连接测试。

## 8. 安全合同

连接器管理 API 只通过认证的 `127.0.0.1:8766` 暴露：

```text
GET  /api/assistant-hub/connections
POST /api/assistant-hub/connections/{id}/preview
POST /api/assistant-hub/connections/{id}/apply
POST /api/assistant-hub/connections/{id}/test
POST /api/assistant-hub/connections/{id}/rollback
```

安全规则：

- 连接器 ID 固定为 allowlist；
- 不接受任意文件路径；
- 不接受任意命令；
- 不使用 `shell=True`；
- 写入需要精确 confirmation；
- UI 预览隐藏 Token；
- WorkBuddy 的完整 Token 配置只在主人确认后写入本机剪贴板；
- 所有配置和 Token 均不得进入日志或公开诊断信息。

## 9. 代码地图

后端：

```text
src/assistant_hub/connectors.py
src/mcp_http.py
src/control/capture_api.py
src/mcp_server.py
run_packaged_control_api.py
```

Desktop：

```text
desktop/lingji-control/src/pages/AssistantHubPage.tsx
desktop/lingji-control/src/components/AssistantConnectorPanel.tsx
desktop/lingji-control/src/pages/AssistantHubPage.css
```

构建：

```text
requirements-sidecar-build.txt
scripts/build_windows_sidecar.ps1
```

测试：

```text
tests/test_ai_memory_connectors.py
tests/test_assistant_hub_api.py
tests/test_mcp_http_auth.py
tests/test_packaged_mcp_runtime.py
desktop/lingji-control/scripts/assistant-memory-connectors-smoke.mjs
```

## 10. 当前限制

本轮不声称完成：

- Claude Code 历史对话 Adapter；
- WorkBuddy / CodeBuddy 历史对话 Adapter；
- ChatGPT 本地实时 MCP 接入；
- 每个 AI 的独立 Agent Scope 与细粒度权限 UI；
- 跨设备远程 MCP；
- 自动批准永久记忆；
- Qdrant / Embedding 后续阶段。

第一版所有本机客户端使用同一 owner-approved 记忆视图，默认 Agent ID 为 `lingji-local`。细粒度 Agent Scope 必须在下一阶段独立实现和验收，不能在 UI 上提前宣称已经隔离。

## 11. 验收标准

必须同时通过：

1. Codex 预览、备份、写入、测试和回滚；
2. Claude Code 官方 CLI 设置、测试和移除；
3. WorkBuddy 配置复制且不修改未知文件；
4. 未认证的 8766 管理请求被拒绝；
5. 未认证的 8767 MCP 请求被拒绝；
6. 安装版 MCP 仅绑定 `127.0.0.1:8767`；
7. Core 重启后 MCP 能重新启动；
8. 没有 PowerShell、CMD 或黑色控制台窗口；
9. AI 能调用 `get_core_memory`、`search_memory`、`build_context_pack` 和 `propose_memory`；
10. `propose_memory` 只生成候选，不直接修改 Core Memory；
11. Production / Acceptance 数据与 Token 隔离；
12. 自动测试、Windows 安装包和主人真机验收全部通过。
