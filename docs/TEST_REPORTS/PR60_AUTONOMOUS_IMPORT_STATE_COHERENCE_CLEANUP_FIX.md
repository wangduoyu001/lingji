# PR #60 自动导入、状态一致性与清理闭环修复报告

## 1. 背景

`PR60-MEMORY-QUALITY-TRIAL-4161807C` 的 Day 0 结论为 `FAIL`，最终提交状态为 `BLOCKED_POST_CLEANUP`。

本轮只修复验收报告已经证明的缺陷，不扩展无关产品能力：

1. 导入仍以路径和二次提交为中心；
2. Codex 配置目录、命令启动和真实客户端验证状态不一致；
3. Control API 与 MCP 对 Qdrant 状态给出互相矛盾的结论；
4. 首次 Sidecar 恢复超过验收时限；
5. 安全清理 dry-run 把合法待删除清单误报为 `BLOCKED`。

旧 Artifact `8821878623` 及产品 Head `4161807c` 只能作为失败证据，不得复用进行下一轮验收。

## 2. 产品原则

```text
灵机自动发现和执行低风险、可逆工作。
UI 展示状态、进度、证据和授权边界。
主人只在读取真实正文、修改外部客户端、永久记忆和不可逆动作时决定。
```

菜单和手动操作继续保留为观察、授权、诊断和恢复入口，不得成为日常必经流水线。

## 3. 自动导入编排

新增：

```text
src/assistant_hub/imports.py
```

`AssistantImportPlanner` 只在受控位置扫描受支持导出包的文件名、大小和修改时间：

- 用户 Downloads；
- 用户 Desktop；
- LingJi `assistant_hub/import_inbox`；
- 最大深度 2；
- 不跟随符号链接；
- 不读取文件正文；
- 不向前端暴露本地绝对路径。

状态只有三类：

```text
candidate_ready
  已发现受支持导出包；主人一次授权后直接进入正式采集队列。

guided_action_required
  未发现导出包，但正式适配器存在；主人选择一次文件，选择完成后立即入队。

not_supported
  当前没有正式适配器；只解释边界，不展示无效导入按钮。
```

新增 API：

```text
GET  /api/assistant-hub/import-plan
POST /api/assistant-hub/import-candidates/{candidate_id}/authorize
POST /api/assistant-hub/import-selected-file
```

候选授权会重新执行受控扫描并通过候选 ID 解析路径，调用者不能提交隐藏的任意路径。选中文件入口只接受 ChatGPT ZIP/JSON 和 Codex Work Report JSON，并要求精确授权口令。

## 4. Desktop 导入体验

`AssistantHubPage` 删除路径输入状态和“选择后再提交”的两阶段流程。

现在：

- 发现候选时，一个按钮完成授权和入队；
- 没有候选时，一个按钮选择文件，选择完成即入队；
- 不支持时没有假按钮；
- 页面明确显示未读取正文；
- 入队后的解析、去重、进度和重试由灵机处理；
- Core Memory 仍必须主人审核。

## 5. Codex 三层状态合同

`AiMemoryConnectorService` 现在输出统一的 `readiness`：

```json
{
  "configuration": {"state": "configured|not_configured|conflict"},
  "client": {"state": "available|not_found|launch_blocked"},
  "real_connection": {"state": "verified|not_verified|failed|blocked"}
}
```

`status_state` 只由这三层事实推导：

- 可执行文件路径存在但启动 `Access is denied` 时为 `client_launch_blocked`；
- 配置存在但命令未验证时为 `verification_required`；
- `codex mcp list` 未列出 `lingji-memory` 时为 `verification_failed`；
- 只有命令真实运行并列出 LingJi MCP 后才为 `ready`。

测试结果会持久化：

```text
last_test_ok
last_test_state
last_test_code
last_test_detail
last_test_at
```

## 6. Qdrant 唯一状态来源

MCP Runtime 是 SQLite/Qdrant 实时资源的唯一拥有者。

新增跨平台操作系统锁：

```text
<data-root>/runtime/memory-owner.lock
```

锁由 OS 文件锁实现，进程异常退出时由操作系统释放。JSON 内容只提供诊断元数据，不作为锁本身。

MCP 启动顺序：

```text
确认 8767 未被占用
→ 获取 memory-owner.lock
→ 创建 MemoryGateway/Qdrant
→ 发布 memory_status.json
→ 每 5 秒刷新快照
→ 启动 MCP HTTP
```

Control API 不再创建第二个 Qdrant 客户端，只读 MCP 发布的快照。

向量状态新增明确事实：

```text
service_ready
collection_exists
vectors
semantic_search_available
lexical_search_available
reason_code
impact
recovery.state
recovery.action
producer
```

关键状态：

- 服务可用、无 collection 或零向量：`empty / collection_empty`，不再显示 healthy；
- 嵌入式目录锁：`unavailable / embedded_store_locked`；
- 快照过期：`status_snapshot_stale`，不宣称语义检索可用；
- 全文检索与语义检索分别显示。

## 7. 清理闭环

旧逻辑把 dry-run 的待删除 manifest 放进 `remaining`，随后因为 `remaining` 非空把合法 dry-run 标成 `BLOCKED`。

新状态：

```text
DRY_RUN_READY
  目标与任务身份匹配，清单已生成，下一步可安全追加 --execute。

PASS / cleanup_complete
  已执行且目标不存在。

PASS / nothing_to_remove
  目标原本不存在。

BLOCKED
  仅用于根目录错误、目标越界、任务身份不匹配、重解析点或真实删除失败。
```

## 8. 测试

新增或更新：

```text
tests/test_assistant_hub_imports.py
tests/test_assistant_hub_api.py
tests/test_ai_connector_readiness.py
tests/test_vector_truth_contract.py
tests/test_memory_owner_lock.py
tests/test_cleanup_acceptance_workspace.py
desktop/lingji-control/scripts/assistant-hub-smoke.mjs
```

覆盖：

- 元数据候选发现不泄露路径；
- 无候选时只有一步引导；
- 候选消失后拒绝旧授权；
- 任意无关 JSON/ZIP 不成为候选；
- 一步文件选择要求精确授权；
- Codex Access Denied 不得显示命令可用；
- Qdrant empty 与 lock 状态不得显示 healthy；
- OS 所有权锁互斥与释放；
- dry-run、execute 和不存在目标的清理状态；
- Desktop 不得重新引入路径输入与二次提交。

## 9. 尚未宣称完成的门禁

本报告提交时，以下结果必须由精确 Head CI 和新 Windows Artifact 证明：

```text
Python 3.11 / 3.12
Windows Python
Desktop smoke
React / TypeScript production build
Rust / Tauri check
P0 Windows Gate
Windows Desktop Release
真实 Windows 首次恢复时限
新 Day 0
```

在这些门禁完成前：

```text
PR #60 保持 Draft
旧 Artifact 不得复用
Stage 1 不得启动
真实资料读取保持 0
```
