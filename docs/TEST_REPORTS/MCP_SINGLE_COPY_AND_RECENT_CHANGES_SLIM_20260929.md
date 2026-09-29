# MCP_SINGLE_COPY_AND_RECENT_CHANGES_SLIM — 2026-09-29

## 环境

- macOS arm64（darwin 25.5.0），Python 3.12（/Library/Frameworks/Python.framework/Versions/3.12），mcp 1.29.1
- 分支 `codex/owner-source-intake-mac-repair`（worktree）

## 变更范围

- `src/mcp/tool_payload.py`（新增）：`tool_result()` 单份 CallToolResult 包装。
- `src/mcp_server.py`：22 个 MCP 工具单份化 + 去 dict 返回注解；新增 `slim_recent_changes`；`slim_search_results` citation 收紧为四字段契约。
- `src/mcp/project_context_tools.py`：lingji_build_context 单份化。
- 测试：`tests/test_mcp_tool_payload.py`（新增 2 例）；`tests/test_codex_mcp_tools.py`（+3 例）；test_automatic_memory_mcp / test_project_context_tools / integration packaged_flow helper 解包适配。

## 命令与结果

```text
python3 -m pytest tests/test_mcp_tool_payload.py tests/test_codex_mcp_tools.py tests/test_project_context_tools.py tests/test_automatic_memory_mcp.py tests/test_mcp_project_timeline.py -q
→ 16 passed

python3 -m pytest tests/test_lingji_tools.py tests/test_mcp_control_bridge.py tests/test_mcp_extraction_submission.py tests/test_mcp_server.py tests/test_memory_retrieval.py tests/test_gateway_ai_profiles.py tests/test_task7_timeline_retrieval.py tests/test_semantic_runtime_wiring.py -q
→ 78 passed

python3 -m pytest tests/test_automatic_memory_context_pack.py tests/test_task6s_source_authority_versions.py tests/test_promotion_recovery_matrix.py tests/test_mcp_tool_payload.py -q
→ 39 passed, 1 failed（既有项，见下）

python3 -m pytest tests/integration/test_automatic_memory_packaged_flow.py -q
→ 1 failed（既有项）, 1 passed（qdrant_outage 适配后通过）
```

## 既有失败甄别（与本变更无关）

以下两项经 `git stash` 在未改动树上复现一致，均为 CHANGE_ACCEPTANCE_LOG 在案的 macOS 本地既有独立根因：

- `test_automatic_memory_packaged_flow.py::test_automatic_memory_packaged_flow_runs_twice_from_clean_acceptance_roots`（reconciliation 扫描事件等待超时）
- `test_automatic_memory_context_pack.py::test_hybrid_diagnostics_are_per_call_and_semantic_failure_is_safe`（语义 reason_code）

## 关键实测证据（设计依据）

同解释器同版本（mcp 1.29.1）端到端 stdio 探针：`-> dict[str, Any]` 注解工具的线上载荷含 content 文本 + structuredContent 双份；裸 `dict` 注解与显式 CallToolResult 均单份；str 返回会被包成 `{"result": ...}` structuredContent（不能作为修复路径）。修复后由 `tests/test_mcp_tool_payload.py` 以真实 FastMCP 低层 handler 固化回归。

## 限制

- 运行中生产后端（lingji-core.exe）为旧打包，本变更需下次打包装机后在真机生效；生效后按 CHANGE_ACCEPTANCE_LOG 对应条目做装机验收。
