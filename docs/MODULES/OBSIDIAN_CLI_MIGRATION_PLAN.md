# OBSIDIAN_CLI_MIGRATION_PLAN.md — Obsidian CLI 迁移计划

> Updated（更新时间）: 2026-07-21  
> Branch（分支）: `work/p0-engineering-hygiene`  
> Verified Commit（已验证提交）: `NOT_FULL_REPOSITORY_VALIDATED`  
> Status（状态）: `PLANNED_COMPATIBILITY_PATH_FIXED`  
> Evidence（证据来源）: `second_brain/obsidian_cli.py`、`docs/ARCHITECTURE.md`、`docs/MEMORY_SYSTEM.md`

## 1. 目标

将 Obsidian CLI（命令行接口）从 `second_brain/` 的兼容实现逐步迁移到 `src/` 正式主线，同时保持一份命令实现、一套 Workspace（工作区）路径合同和一个 Local Control API（本地控制接口）入口。

P0 只修复兼容层的机器专属路径，并登记最终迁移合同，不迁移完整命令面。

## 2. 当前状态

当前兼容实现：

```text
second_brain/obsidian_cli.py
```

P0 已收口：

- `OBSIDIAN_CLI_PATH` 保持最高优先级。
- `PATH` 依次探测 `Obsidian.com` 与 `obsidian`。
- Windows 标准候选从 `LOCALAPPDATA`、`ProgramFiles`、`ProgramFiles(x86)` 构造。
- macOS 与 Linux 使用平台标准候选。
- 不再写死 C:、D: 或用户目录。
- CLI 发现来源区分为 `environment`、`path`、`platform_location`、`not_found`。
- Vault 路径合同支持 Workspace、Runtime Settings、`OBSIDIAN_VAULT_PATH` 与旧 `SECOND_BRAIN_OBSIDIAN_DIR`。
- 非 Windows 平台不再直接依赖 `subprocess.CREATE_NO_WINDOW`。

兼容实现仍然是 `DEPRECATED_COMPATIBILITY_ONLY`，不得继续增加正式产品能力。

## 3. 最终目录

```text
src/obsidian/
  __init__.py
  config.py
  discovery.py
  models.py
  client.py
  service.py
```

职责：

| 文件 | 最终职责 |
|---|---|
| `config.py` | CLI、Vault、超时、Dry Run（试运行）与能力配置模型 |
| `discovery.py` | 可执行文件和平台候选发现，返回路径及发现来源 |
| `models.py` | 命令结果、Vault 信息、能力状态与稳定错误模型 |
| `client.py` | 类型化参数、超时、编码、错误转换和安全子进程执行 |
| `service.py` | Workspace/Runtime Settings 接线、能力聚合、权限与审计 |
| `__init__.py` | 仅导出稳定公共接口 |

不得把完整 `ObsidianCli` 类复制一份后再逐渐分叉。迁移必须按能力移动，并保持单一写入实现。

## 4. 最终数据流

```text
Workspace Vault
-> ObsidianService
-> ObsidianCliClient
-> Local Control API :8766
-> Tauri 状态与设置
```

边界：

1. Workspace 决定当前 Vault 和隔离环境。
2. Runtime Settings 保存用户可编辑配置，不取代 Workspace 权威。
3. Client 只执行已经注册的类型化命令，不接受任意 Shell 字符串。
4. Service 负责能力判断、状态、权限、审计与降级。
5. Tauri 只调用 `127.0.0.1:8766`，不得直接启动 CLI 或读取兼容配置。
6. `second_brain/` 在迁移期间只保留兼容转发或只读验收。

## 5. 配置优先级

### 5.1 CLI 可执行文件

```text
显式 Runtime Settings 或 Workspace 配置
-> OBSIDIAN_CLI_PATH
-> PATH: Obsidian.com / obsidian
-> 平台标准位置
-> not_found
```

P0 兼容层仍将 `OBSIDIAN_CLI_PATH` 放在自动发现之前。迁入 `src` 时，用户在 UI 中保存的显式配置应成为最高优先级，并记录配置来源。

### 5.2 Vault

```text
当前 Workspace Vault
-> Runtime Settings 显式 Vault
-> OBSIDIAN_VAULT_PATH
-> SECOND_BRAIN_OBSIDIAN_DIR（兼容）
-> configuration_required
```

Production 与 Acceptance 不得共享可写 Vault。

## 6. 迁移阶段

### Stage 1：配置、发现、状态

目标：

- 建立 `config.py`、`discovery.py`、`models.py`。
- 输出 CLI 路径、发现来源、Vault 路径、版本、可用性和稳定错误。
- 接入 Workspace 与 Runtime Settings。
- 不执行写命令。

验收：

- 环境变量、PATH 和平台位置优先级测试。
- Production/Acceptance 路径隔离。
- 未安装 CLI 时稳定返回 `configuration_required` 或 `unavailable`。

### Stage 2：只读命令

目标：

- 迁移版本、Vault 信息、文件列表、搜索、读取和只读健康检查。
- 建立类型化命令参数和统一错误映射。

验收：

- 超时、UTF-8/BOM、中文路径和空结果。
- 不存在笔记与 CLI 不可用的稳定错误。
- 只读命令不得修改 Vault。

### Stage 3：安全写入命令

目标：

- 迁移 create、append、Daily Note 等允许的写入能力。
- 增加 Dry Run、路径边界、原子或可验证写入、审计和回滚信息。

验收：

- 只在 Acceptance fixture Vault 执行写测试。
- 写后重新读取验证。
- 禁止任意命令拼接和路径遍历。
- 批量写入遵守预览、确认与 Git checkpoint 合同。

### Stage 4：8766 API 与 Tauri

目标：

- `ObsidianService` 接入 Local Control API `8766`。
- Tauri 设置页展示路径来源、CLI 版本、Vault、状态和错误。
- 用户可选择或修改显式路径，并在保存前校验。

验收：

- Tauri 不访问 `8765`、SQLite 或 CLI 子进程。
- API 不泄露 Token、完整私人正文或未脱敏绝对路径。
- UI 不推测 CLI/Vault 正常状态。

### Stage 5：停止 second_brain CLI 写入

目标：

- 兼容入口转发到 `src` 服务或进入只读模式。
- 停止 `second_brain` 的正式写入。
- 保留迁移验收和回滚窗口。

验收：

- 同一输入不会由两套 CLI 实现重复写入。
- 关闭兼容写入后正式桌面功能仍正常。
- 迁移差异、数据导出和回滚方案有报告。

## 7. 错误与状态合同

建议稳定状态：

```text
healthy
unavailable
configuration_required
disabled
degraded
```

建议稳定错误码：

```text
OBSIDIAN_CLI_NOT_FOUND
OBSIDIAN_CLI_TIMEOUT
OBSIDIAN_CLI_FAILED
OBSIDIAN_VAULT_NOT_CONFIGURED
OBSIDIAN_VAULT_NOT_FOUND
OBSIDIAN_PATH_OUTSIDE_WORKSPACE
OBSIDIAN_WRITE_VERIFICATION_FAILED
```

完整命令、正文和本机敏感路径只进入受控本地日志，不进入普通 API 响应。

## 8. 测试策略

- Discovery（发现）使用 `shutil.which`、环境变量和临时平台目录模拟。
- Client 使用 Fake Process（假进程）验证参数、编码、超时和错误。
- Service 使用临时 Workspace 和 Acceptance Vault。
- 真正 Obsidian CLI 测试必须显式标记为可选集成测试，未安装时说明原因后跳过。
- 写入测试不得使用 Production Vault。
- Windows 专有标志必须通过 `getattr` 或平台判断，保证 Linux/macOS 可导入。

## 9. 本轮不做

P0 不实现：

- `src/obsidian/` 完整命令代码。
- 8766 Obsidian 新 API。
- Tauri 设置页或状态页。
- 新 Obsidian 功能。
- 批量知识修改。
- 兼容运行时退役。

## 10. 回滚

P0 兼容层路径修复可通过回退对应提交恢复旧实现，但旧机器专属默认值不得重新进入正式主线。

未来每一阶段必须保持：

```text
新 src 能力可关闭
+
兼容实现可只读回退
+
Production Vault 不被测试修改
```
