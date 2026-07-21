# OBSIDIAN_CLI_MIGRATION_PLAN.md — Obsidian CLI 迁移计划

> Updated（更新时间）: 2026-07-21  
> Branch（分支）: `work/p2-06-obsidian-cli-migration`  
> Validated Commit（已验证提交）: `4b0ad577eb396030ee6baa5c3bb217e990385475`  
> Status（状态）: `IMPLEMENTED_COORDINATOR_VALIDATED`  
> Implementation Report（实施报告）: `docs/MODULES/P2_06_OBSIDIAN_CLI_MIGRATION_IMPLEMENTATION.md`  
> Test Report（测试报告）: `docs/TEST_REPORTS/P2_06_OBSIDIAN_CLI_MIGRATION_TEST_REPORT.md`

## 1. 目标

将 Obsidian CLI（命令行接口）从 `second_brain/` 兼容实现迁入 `src/` 正式主线，同时保持：

```text
一份 CLI 命令实现
+ 一套 Workspace / Runtime Settings 路径合同
+ 一个 8766 Local Control API 入口
+ 一个 Tauri 状态与设置入口
```

迁移不得创建第二套 Vault 写入、数据库、任务队列或 Schema。

## 2. 当前完成状态

已完成：

- `src/obsidian/` 正式 CLI 包。
- 可执行文件与 Vault 跨平台发现。
- Workspace 与 Runtime Settings 接线。
- 类型化只读与安全写入命令面迁移。
- 超时、编码、稳定错误和路径边界。
- 写入后读取验证与 Dry Run。
- 8766 状态、草稿校验和刷新 API。
- Tauri Obsidian 状态与设置页。
- `second_brain/obsidian_cli.py` 降为兼容转发。
- Windows Python、Desktop 与 Cargo 协调门禁通过。

正式迁移不覆盖既有 `src/obsidian/management.py` 和 `system_ui.py`，而是与它们组成同一正式包。

## 3. 正式目录

```text
src/obsidian/
  __init__.py
  models.py
  discovery.py
  config.py
  client.py
  service.py
  management.py
  system_ui.py
```

职责：

| 文件 | 职责 |
|---|---|
| `models.py` | 稳定状态、错误码和公共数据模型 |
| `discovery.py` | Runtime、环境变量、PATH、平台标准位置发现 |
| `config.py` | CLI、Vault、超时、Dry Run 与 Workspace 配置模型 |
| `client.py` | 类型化参数、安全子进程、编码、超时、写入验证 |
| `service.py` | Runtime Settings、状态、脱敏、校验和审计 |
| `management.py` | 已有安全笔记属性、标签和关系管理 |
| `system_ui.py` | 已有 Obsidian 系统界面生成 |
| `__init__.py` | 稳定公共接口导出 |

## 4. 单一实现合同

```text
second_brain/obsidian_cli.py
= DEPRECATED COMPATIBILITY FACADE
```

兼容模块：

- 只从 `src.obsidian` 转发公共接口；
- 保留旧调用方和测试需要的导入名；
- 不保留 `_run`、发现、读写或校验实现；
- 不接受新的正式产品能力。

因此同一输入不会被两套 CLI 实现重复处理。

## 5. 数据流

```text
Workspace Vault
-> Runtime Settings owner override
-> ObsidianService
-> ObsidianCliClient
-> authenticated Local Control API :8766
-> Tauri Obsidian page
```

边界：

1. Workspace Vault 保持路径权威。
2. Runtime Settings 提供主人可编辑覆盖，不绕过 Production/Acceptance 隔离。
3. Client 只执行注册过的类型化命令，不接受 Shell 字符串。
4. Service 负责状态、错误、脱敏、校验和审计。
5. Tauri 只调用 8766，不直接启动 CLI、读取 SQLite 或导入兼容模块。

## 6. 配置优先级

### 6.1 CLI 可执行文件

```text
Runtime Settings 显式路径
-> OBSIDIAN_CLI_PATH
-> PATH: Obsidian.com / obsidian
-> 平台标准位置
-> not_found
```

### 6.2 Vault

```text
当前 Workspace Vault
-> Runtime Settings 显式回退路径
-> OBSIDIAN_VAULT_PATH
-> SECOND_BRAIN_OBSIDIAN_DIR（兼容）
-> configuration_required
```

### 6.3 Vault 名称

```text
Runtime Settings 显式名称
-> OBSIDIAN_VAULT_NAME
-> Vault 目录名
-> 兼容默认值
```

## 7. Runtime Settings

```text
obsidian_cli_enabled
obsidian_cli_path
obsidian_vault_path
obsidian_vault_name
obsidian_cli_timeout_seconds
obsidian_cli_dry_run
```

用户可以在通用设置页或 Obsidian 专页查看和修改这些值。

## 8. 正式命令面

只读：

```text
version
help
vault info
vault list
search
read
files
file count
tags
tasks
daily read
daily path
```

安全写入：

```text
create
append
daily append
```

写入合同：

- 只接受 Vault 相对路径；
- 拒绝绝对路径、盘符路径、NUL 和 `..`；
- 不使用 Shell；
- 支持 Dry Run；
- create/append 写后重新读取验证；
- 测试不使用 Production Vault。

## 9. 8766 API

```text
GET  /api/obsidian/status
POST /api/obsidian/validate
POST /api/obsidian/refresh
```

状态接口只返回：

- 稳定状态与错误码；
- 版本、发现来源、Vault 名称；
- 掩码路径显示；
- 超时、Dry Run 和能力状态。

状态接口不返回原始 `cli_path`、`vault_path`、正文或 Token。

`/api/obsidian/validate` 验证草稿配置，不持久化；保存仍统一走现有 `/api/settings`。

## 10. Tauri

Obsidian 页面支持：

- 状态、版本、发现来源和错误查看；
- CLI 文件和 Vault 目录选择；
- 启用、Vault 名称、超时和 Dry Run；
- 验证但不保存；
- 保存后刷新状态。

Tauri 使用官方 Dialog Plugin，不直接执行 CLI。

## 11. 状态与错误合同

状态：

```text
healthy
unavailable
configuration_required
disabled
degraded
```

错误码：

```text
OBSIDIAN_CLI_NOT_FOUND
OBSIDIAN_CLI_TIMEOUT
OBSIDIAN_CLI_FAILED
OBSIDIAN_VAULT_NOT_CONFIGURED
OBSIDIAN_VAULT_NOT_FOUND
OBSIDIAN_PATH_OUTSIDE_WORKSPACE
OBSIDIAN_WRITE_VERIFICATION_FAILED
```

完整命令、stderr 和本机绝对路径只进入受控本地诊断，不进入普通状态 DTO。

## 12. 测试策略与结果

协调门禁已验证：

```text
Python dependency install: PASS
pip check: PASS
clean-install validator: PASS
compileall: PASS
focused Obsidian tests: PASS
full repository pytest: PASS
npm ci: PASS
Obsidian Smoke: PASS
all Desktop Smoke: PASS
TypeScript/Vite Build: PASS
cargo check: PASS
git diff --check: PASS
```

正式 PR Linux 与 Windows CI 在文档提交后重新执行，最终精确计数写入测试报告。

## 13. 本轮明确不做

- Production Vault 写入验收；
- 批量知识修改；
- 系统、剪贴板或文件夹监听；
- 手机分享客户端；
- 浏览器扩展；
- 数据库 Schema 修改；
- 新数据库或第二套任务队列。

## 14. 回滚

回滚以正式分支 Git 提交为单位。兼容导入面仍然存在，因此调用方可以在迁移回滚窗口继续使用旧模块名，但所有执行都指向 `src.obsidian`。不得恢复机器专属路径或第二套命令实现。
