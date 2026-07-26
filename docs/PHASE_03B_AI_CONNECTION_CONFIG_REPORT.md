# 灵机第三阶段补充：各 AI 连接配置生成器报告

## 状态

- 分支：`feature/single-vault-memory-foundation`
- PR：Draft PR #1
- 本轮新增测试后总计：41/41 通过
- Python 3.11：通过
- Python 3.12：通过
- MCP Server smoke test：通过

本报告补充 `PHASE_03_PERMANENT_MEMORY_GATEWAY_REPORT.md`。此前报告记录的 37 项测试是永久记忆和召回功能完成时的阶段结果；加入各 AI 连接配置测试后，最新结果为 41 项。

## 新增功能

新增：

```text
scripts/generate_ai_connection_configs.py
```

该脚本生成可审查的连接示例，但不会直接修改任何用户配置文件。

默认输出：

```text
generated/ai-connections/
├── generic-mcp.json
├── codex-config.toml
├── claude-command.txt
├── claude-server.json
├── gemini-settings.json
├── gemini-command.txt
├── openai-remote-mcp-tool.json
├── direct-clients.json
└── README.md
```

## 使用方法

```powershell
python scripts/generate_ai_connection_configs.py
```

指定输出路径：

```powershell
python scripts/generate_ai_connection_configs.py `
  --output "D:\codex\lingji-ai-connections" `
  --project-root "C:\Users\Administrator\Documents\New project-ai" `
  --python "C:\Path\To\python.exe"
```

## Codex

生成 `codex-config.toml`：

```toml
[mcp_servers.lingji_memory]
command = "python"
args = ["run_mcp_server.py", "--transport", "stdio", "--agent", "codex"]
enabled = true
```

脚本只生成片段，不直接修改 `~/.codex/config.toml`。项目级配置需要工作区被 Codex 信任。

## Claude Code

生成：

```text
claude mcp add --scope user lingji-memory -- python run_mcp_server.py --transport stdio --agent claude
```

同时生成 `claude-server.json`，可用于 Claude Code 的 JSON 注册方式。

## Gemini CLI

生成 `gemini-settings.json`：

```json
{
  "mcp": {
    "allowed": ["lingji-memory"]
  },
  "mcpServers": {
    "lingji-memory": {
      "command": "python",
      "args": ["run_mcp_server.py", "--transport", "stdio", "--agent", "gemini"],
      "trust": false
    }
  }
}
```

保持 `trust: false`，工具调用继续由用户确认。

## ChatGPT / OpenAI API

生成 `openai-remote-mcp-tool.json` 仅作为远程 MCP 工具模板。

它不会指向：

```text
127.0.0.1
localhost
```

原因是 OpenAI Remote MCP 需要可访问的远程 HTTPS 地址。当前灵机 HTTP MCP 尚未实现认证、TLS、OAuth 和限流，不能直接暴露公网。

模板默认：

- HTTPS 占位地址
- 只读工具
- 不开放 `propose_memory`
- 工具调用需要审批

## Kimi、DeepSeek、Ollama

生成 `direct-clients.json`：

- Kimi：MCP stdio 或 Context Envelope
- DeepSeek：`AIContextAdapter.generic_prompt`
- Ollama：MCP stdio 或 Context Envelope
- 只有本地 Ollama 配置允许按授权读取 `restricted`

这些模型与其他 AI 使用同一个 `MemoryGateway`，不会维护独立永久记忆副本。

## 安全原则

1. 生成器不修改外部配置。
2. 不把无认证 localhost 伪装成远程服务。
3. 远程 AI 默认只读 `public/private`。
4. `restricted` 默认只允许主人授权的本地 Agent。
5. 所有 AI 只能提议候选记忆，不能直接写入 Core Memory。
6. Codex、Claude 和 Gemini 使用不同 `agent_id`，便于权限和审计。
7. Context Pack 携带 memory revision 和来源引用。

## 新增测试

新增 `tests/test_ai_connection_configs.py`，覆盖：

1. 生成 9 个配置文件。
2. 不修改项目外部 Codex 设置。
3. Codex、Claude、Gemini 使用各自 Agent Profile。
4. Gemini 默认不信任并自动批准服务器。
5. OpenAI Remote MCP 模板不暴露 localhost。
6. OpenAI 远程模板只开放只读工具。
7. Ollama 和 DeepSeek 隐私范围不同。
8. DeepSeek 使用统一 Context Adapter。

## 最新测试结果

```text
Ran 41 tests in 0.880s
OK
```

GitHub Actions：

```text
unit-tests (3.11): success
unit-tests (3.12): success
mcp-smoke-test: success
```

## 尚未完成

- 尚未将生成配置自动安装到各客户端，因为自动修改用户全局配置风险过高。
- 尚未对 Codex Desktop、Claude Code、Gemini CLI 做主人电脑上的真实连接验证。
- ChatGPT Remote MCP 尚缺认证反向代理和安全公网入口。
- Kimi、DeepSeek 的具体 CLI 版本差异仍需在主人当前安装版本上验证。
- 本机未推送 `second_brain/lingji_tools.py` 仍需合并。

## 结论

灵机现在不仅有统一 Memory Gateway，也能生成面向各 AI 的具体连接文件。连接配置仍保持“生成、审核、再安装”的流程，而不是让脚本偷偷改一圈用户目录，再把配置事故称作自动化成果。
