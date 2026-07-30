# PR60 AI 助手中心主动引导修复报告

## 1. 结论

```text
状态：代码完成，自动测试与 Windows Artifact 构建通过，待主人真机复验
产品 Commit：d69874afd8def42a40c4a5cc5e678a71921d44b5
旧 Artifact：lingji-windows-0.1.0-1c514877（已废弃，不得继续验收）
新 Artifact：lingji-windows-0.1.0-d69874af
Artifact ID：8762312712
Artifact ZIP SHA256：6bf1f591502617c400ce482f6beb0d5e430a172cd036137bb4a39cae2cbf4cb4
```

本次修复针对主人在 Day 0 发现的两个阻塞缺陷：

```text
D0-UX-001：扫描、连接、导入、审核和向量状态彼此割裂，无法一眼判断下一步与阻塞原因
D0-CODEX-002：Codex 配置存在时可显示“等待测试”，但系统同时找不到 codex 命令，状态自相矛盾
```

## 2. 产品行为变化

### 2.1 单一当前动作

AI 助手中心新增统一的“当前状态 / 唯一推荐下一步”区域，按以下优先级决策：

```text
MCP 网关不可用
→ 客户端连接阻塞
→ 客户端待配置或待真实验证
→ 发现可处理历史资料
→ Embedding / Qdrant 待处理
→ 可以开始导入和审核
```

页面不再要求主人自行在扫描、连接、导入和审核卡片之间猜测先后顺序。

### 2.2 四项准备度

同一屏幕明确分开显示：

```text
灵机记忆网关
真实 AI 客户端
历史导入
Embedding / Qdrant
```

每项显示当前状态、事实来源、阻塞原因和下一步。

### 2.3 主动发现历史资料但不越权读取

扫描到 Codex 本地目录后，页面主动弹出提示，说明：

- 发现的脱敏目录；
- 候选文件元数据数量；
- 当前真正支持的是结构化 Codex Report JSON；
- 原始 Session、JSONL 和 Markdown 正文尚未自动读取；
- 主人可选择“暂不处理”或“查看可导入内容”。

扫描继续保持元数据只读。未经主人确认，不读取真实正文，不创建导入任务，不扫描任意目录。

### 2.4 连接状态改为真实状态机

每个连接器分别显示：

```text
配置文件
客户端命令
真实连接测试
阻塞原因
下一步
```

Codex 状态现在区分：

```text
configuration_required
verification_required
ready
blocked
client_not_found
conflict
```

只有配置、客户端命令和真实 CLI/MCP 验证全部通过时才显示绿色“连接可用”。

配置文件已写入但找不到 `codex` 命令时：

```text
status_state = blocked
ok = false
live_test = false
```

并明确提示“配置存在不等于连接可用”。

### 2.5 测试结果持久化

连接测试现在记录：

```text
last_test_ok
last_test_state
last_test_detail
last_test_at
```

刷新页面后不会丢失真实失败原因，也不会重新退化成模糊的“已配置”。

### 2.6 Embedding 与 Qdrant 状态说明

AI 助手中心直接读取 `/api/vector/status`，显示：

- 配置模型与实际激活模型；
- Embedding 是否可用、是否验证；
- 不可用模型；
- 最近错误；
- Qdrant 状态与模式；
- Collection 是否存在；
- 是否需要安全重建；
- 全文检索是否仍可用。

本次修复没有静默下载模型、自动重建 Production Collection 或假装语义检索已经激活。真正激活仍需根据主人机器返回的明确错误单独处理。

## 3. 代码变更

```text
src/assistant_hub/governed.py
desktop/lingji-control/src/components/AssistantConnectorPanel.tsx
desktop/lingji-control/src/components/AssistantSetupDirector.css
tests/test_ai_memory_connectors.py
desktop/lingji-control/scripts/assistant-memory-connectors-smoke.mjs
docs/ACCEPTANCE/CHANGE_ACCEPTANCE_LOG.md
docs/TEST_REPORTS/PR60_ASSISTANT_HUB_GUIDED_FLOW_PLAN.md
```

同时将最新 `master` 验收治理通过 PR #66 合并回产品分支，PR #60 当前已恢复 `mergeable=true`，但仍保持 Draft，禁止在主人复验前合并。

## 4. 新增回归测试

### Python

```text
test_codex_config_without_command_is_blocked_not_connected
test_codex_is_ready_only_after_real_cli_verification
```

验证：

- 找不到 Codex 命令时不能算连接成功；
- 配置存在只能进入待验证或阻塞；
- 只有真实 CLI 验证后进入 ready；
- A-01 显式空环境隔离仍通过；
- 配置冲突、备份和回滚合同不变。

### Desktop Smoke

强制检查：

- 单一准备度与下一步；
- 主动导入提示；
- 扫描只读和导入确认说明；
- Embedding / Qdrant 状态；
- 配置、客户端命令、真实测试分离；
- 禁止旧文案“已设置，等待测试”重新出现。

## 5. 精确 Head CI

```text
acceptance-doc-sync #43：SUCCESS
local-execution-handoff #35：SUCCESS
tests #1138：SUCCESS
P0 Windows Gate #258：SUCCESS
Windows Desktop Release Baseline #142：SUCCESS
```

覆盖：

- Python 3.11 / 3.12 / Windows 完整测试；
- Desktop Smoke 和 React 生产构建；
- Tauri Rust 检查；
- MCP Smoke；
- Obsidian Plugin Smoke；
- Browser Capture Smoke；
- Windows PowerShell clean-install 合同；
- Sidecar 构建、认证健康检查、受管停止；
- Tauri NSIS 安装器和 Artifact 合同。

## 6. 新 Artifact

```text
Artifact：lingji-windows-0.1.0-d69874af
Artifact ID：8762312712
Artifact ZIP SHA256：6bf1f591502617c400ce482f6beb0d5e430a172cd036137bb4a39cae2cbf4cb4
安装器：LingJi_0.1.0_windows_x64_setup.exe
安装器 SHA256：d62867b7b7c90bee8273b3cf5720f53099c266897ce95d0e42224deae31bf262
便携 EXE SHA256：a852079b43b2f4020cb66942f44f1a5035633b65d3ff4122c2613c5ea7440a69
Sidecar EXE SHA256：20fe548e1be5cff5d1a34852f4fc0e223abb218eef1e51418724a6723e180599
Manifest SHA256：d78a91153b62bcf641bcbbdbc41819283fe0dbc5deff2cdab64cdffcea3e6c87
```

构建合同继续满足：

```text
desktop_pe_subsystem = windows_gui
sidecar_pe_subsystem = windows_gui
mcp_runtime_bundled = true
mcp_cli_bundled = false
automatic_core_memory_write = false
automatic_model_download = false
automatic_qdrant_rebuild = false
owner_data_bundled = false
uninstall_deletes_owner_data = false
system_drive_runtime_data_allowed = false
```

## 7. 真机复验重点

下一轮先重测：

1. 扫描完成后，主人能否在 5 秒内指出唯一下一步；
2. 是否能区分“发现目录、配置写入、命令可用、真实测试通过”；
3. Codex 命令缺失时是否只显示一个明确阻塞结论；
4. 是否主动提示发现的历史目录、可导入类型和未读取边界；
5. Embedding/Qdrant 是否显示具体模型、错误和状态，而不是“以后处理”；
6. 主人确认后再进入 Day 0 后续、Stage 1 和质量题。

## 8. 未完成与边界

```text
主人真机复验：未执行
真实 Codex 新会话调用：未执行
Embedding 实际激活：未实现自动修复
Qdrant 自动重建：明确禁止
Codex 原始 Session / JSONL 自动导入：尚未实现适配器
真实数据 Stage 1 / Stage 2：未执行
```

因此当前只能判定：

```text
代码和 Artifact：READY FOR OWNER RE-ACCEPTANCE
产品 PR：DRAFT
合并：NOT ALLOWED
```