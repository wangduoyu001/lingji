#!/usr/bin/env python3
"""Generate reviewable LingJi connection examples without editing user settings."""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

READ_TOOLS = [
    "search_memory",
    "fetch_memory",
    "get_core_memory",
    "build_context_pack",
    "recent_changes",
    "memory_health",
]
ALL_SAFE_TOOLS = [*READ_TOOLS, "propose_memory"]


def _json(data) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2) + "\n"


def generate_configs(
    output_dir: Path,
    project_root: Path,
    python_executable: str,
) -> dict[str, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    run_script = project_root / "run_mcp_server.py"
    python_path = str(Path(python_executable))
    cwd = str(project_root)

    generic = {
        "mcpServers": {
            "lingji-memory": {
                "command": python_path,
                "args": [str(run_script), "--transport", "stdio", "--agent", "lingji-local"],
                "cwd": cwd,
            }
        }
    }

    codex = "\n".join(
        [
            "# Review and append to ~/.codex/config.toml or a trusted project .codex/config.toml",
            "[mcp_servers.lingji_memory]",
            f'command = {json.dumps(python_path)}',
            "args = [",
            f"  {json.dumps(str(run_script))},",
            '  "--transport", "stdio",',
            '  "--agent", "codex"',
            "]",
            f'cwd = {json.dumps(cwd)}',
            "enabled = true",
            'enabled_tools = ["search_memory", "fetch_memory", "get_core_memory", "build_context_pack", "propose_memory", "recent_changes", "memory_health"]',
            "startup_timeout_ms = 30000",
            "tool_timeout_sec = 60",
            "",
        ]
    )

    claude_command = (
        "claude mcp add --scope user lingji-memory -- "
        + _shell_quote(python_path)
        + " "
        + _shell_quote(str(run_script))
        + " --transport stdio --agent claude\n"
    )
    claude_json = {
        "type": "stdio",
        "command": python_path,
        "args": [str(run_script), "--transport", "stdio", "--agent", "claude"],
        "cwd": cwd,
    }

    gemini = {
        "mcp": {"allowed": ["lingji-memory"]},
        "mcpServers": {
            "lingji-memory": {
                "command": python_path,
                "args": [str(run_script), "--transport", "stdio", "--agent", "gemini"],
                "cwd": cwd,
                "timeout": 60000,
                "trust": False,
                "includeTools": ALL_SAFE_TOOLS,
            }
        },
    }
    gemini_command = (
        "gemini mcp add --scope user --transport stdio lingji-memory "
        + _shell_quote(python_path)
        + " "
        + _shell_quote(str(run_script))
        + " --transport stdio --agent gemini\n"
    )

    openai_remote = {
        "type": "mcp",
        "server_label": "lingji_memory",
        "server_description": "Owner-controlled LingJi permanent memory and retrieval gateway",
        "server_url": "https://YOUR-AUTHENTICATED-LINGJI-HOST/mcp",
        "allowed_tools": {"read_only": True, "tool_names": READ_TOOLS},
        "require_approval": "always",
    }

    direct_clients = {
        "kimi": {
            "agent_id": "kimi",
            "recommended_mode": "mcp_stdio_or_context_envelope",
            "command": [python_path, str(run_script), "--transport", "stdio", "--agent", "kimi"],
        },
        "deepseek": {
            "agent_id": "deepseek",
            "recommended_mode": "context_envelope",
            "adapter": "AIContextAdapter.generic_prompt",
        },
        "ollama": {
            "agent_id": "ollama",
            "recommended_mode": "mcp_stdio_or_context_envelope",
            "command": [python_path, str(run_script), "--transport", "stdio", "--agent", "ollama"],
            "can_read_restricted": True,
        },
    }

    readme = f"""# LingJi AI connection files

These files are examples only. The generator does not modify any AI client settings.

## Local stdio server

```powershell
{python_path} "{run_script}" --transport stdio --agent codex
```

## Files

- `generic-mcp.json`: standard `mcpServers` example.
- `codex-config.toml`: append after reviewing; project-local config requires a trusted project.
- `claude-command.txt`: Claude Code registration command.
- `claude-server.json`: payload for `claude mcp add-json`.
- `gemini-settings.json`: merge into user or project `settings.json`.
- `gemini-command.txt`: Gemini CLI registration command.
- `openai-remote-mcp-tool.json`: template only. It requires an authenticated HTTPS MCP endpoint and must not point directly at the current unauthenticated localhost server.
- `direct-clients.json`: Kimi, DeepSeek and Ollama adapter modes.

## Safety

Remote clients receive only `public/private` memory by default. `restricted` memory is reserved for owner-authorized local agents such as Ollama. AI clients may propose memory candidates but cannot promote them into Core Memory.
"""

    files = {
        "generic-mcp.json": _json(generic),
        "codex-config.toml": codex,
        "claude-command.txt": claude_command,
        "claude-server.json": _json(claude_json),
        "gemini-settings.json": _json(gemini),
        "gemini-command.txt": gemini_command,
        "openai-remote-mcp-tool.json": _json(openai_remote),
        "direct-clients.json": _json(direct_clients),
        "README.md": readme,
    }
    written = {}
    for name, content in files.items():
        path = output_dir / name
        path.write_text(content, encoding="utf-8")
        written[name] = str(path)
    return written


def _shell_quote(value: str) -> str:
    if os.name == "nt":
        return '"' + value.replace('"', '\\"') + '"'
    return "'" + value.replace("'", "'\"'\"'") + "'"


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate LingJi AI connection examples")
    parser.add_argument(
        "--output",
        default=str(BASE_DIR / "generated" / "ai-connections"),
        help="Directory for generated examples",
    )
    parser.add_argument("--project-root", default=str(BASE_DIR))
    parser.add_argument("--python", default=sys.executable)
    args = parser.parse_args()
    files = generate_configs(
        Path(args.output).expanduser(),
        Path(args.project_root).expanduser().resolve(),
        args.python,
    )
    print(_json({"created": files}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
