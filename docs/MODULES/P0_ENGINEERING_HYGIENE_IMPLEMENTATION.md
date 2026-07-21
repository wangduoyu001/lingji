# P0_ENGINEERING_HYGIENE_IMPLEMENTATION.md — 工程卫生实施记录

> Updated（更新时间）: 2026-07-21  
> Branch（分支）: `work/p0-engineering-hygiene`  
> Base Commit（基础提交）: `e113c55d1e4738b20d60abe3bf79460a6f493a5f`  
> Verified Code Commit（已验证代码提交）: `70e1a23b56f19287b3823a24c951f6c51c88aeff`  
> Status（状态）: `IMPLEMENTED_PARTIALLY_VALIDATED_BLOCKED_FULL_REPOSITORY`  
> Evidence（证据来源）: GitHub 分支代码、隔离 Linux/Python 3.13 环境、`docs/TEST_REPORTS/P0_ENGINEERING_HYGIENE_TEST_REPORT.md`

## 1. 任务目标

P0 Engineering Hygiene（工程卫生）在 P2-05 开发前收口：

- 机器专属路径默认值。
- Obsidian CLI 可执行文件与 Vault 路径发现。
- Python 依赖所有权和可复现约束。
- 启动入口行为合同。
- 可选外部 Provider（提供器）测试边界。
- 全新环境、完整测试和前端构建证据。

本轮没有开发 P2-05 功能。

## 2. 已读取的规则与架构

已核对：

- `AGENTS.md`
- `docs/AI_CONTEXT.md`
- `docs/DEVELOPMENT_RULES.md`
- `docs/AI_COLLABORATION_RULES.md`
- `docs/DOCUMENTATION_MAINTENANCE.md`
- `docs/PROJECT_STATUS.md`
- `docs/ARCHITECTURE.md`
- `docs/MEMORY_SYSTEM.md`
- `docs/VECTOR_DATABASE.md`
- `docs/MODULES/P0_ENGINEERING_HYGIENE_PLAN.md`
- `docs/MODULES/P2_05_MANUAL_CAPTURE_CENTER_PLAN.md`
- `docs/MODULES/UNIFIED_MEMORY_ARCHITECTURE_PLAN.md`

代码权威仍是：

```text
src/
= 长期正式主线

second_brain/
= 兼容、迁移和验收

desktop/lingji-control/
= 唯一正式桌面 UI
```

## 3. 修改文件

### 3.1 路径与兼容实现

- `src/config.py`
- `second_brain/obsidian_cli.py`

### 3.2 依赖与验证

- `requirements-test.txt`
- `constraints/python-3.13-linux.txt`
- `scripts/validate_clean_install.py`

### 3.3 测试

- `tests/test_workspace_contract.py`
- `tests/test_obsidian_cli.py`
- `tests/test_obsidian_cli_behavior.py`
- `tests/test_startup_contracts.py`

### 3.4 文档

- `docs/MODULES/P0_ENGINEERING_HYGIENE_IMPLEMENTATION.md`
- `docs/MODULES/OBSIDIAN_CLI_MIGRATION_PLAN.md`
- `docs/TEST_REPORTS/P0_ENGINEERING_HYGIENE_TEST_REPORT.md`

未更新：

- `docs/CHANGELOG.md`，因为本分支尚未合并正式分支。
- `docs/PROJECT_STATUS.md` 与 `docs/MODULES/CODE_MAP.md`，因为完整仓库测试和 Windows/Tauri 验收尚未通过。

## 4. 备份路径合同

### 4.1 修复前

`src/config.py` 使用机器专属默认值：

```text
D:/codex/backups/pemis
```

### 4.2 修复后

```text
backup_dir 为空
-> Settings.backup_path 使用 storage_path / backups

backup_dir 非空
-> 使用环境变量或显式配置路径
```

`backup_path` 返回经过 `expanduser()` 和 `resolve(strict=False)` 规范化的 `Path`。

正式 Workspace 合同继续复用 `WorkspaceResolver`：

```text
Production storage/backups
Acceptance storage/backups
```

两者通过现有 Workspace 物理隔离校验，未创建第二套路由器或路径解析系统。

### 4.3 测试覆盖

- 默认路径。
- 环境变量覆盖。
- 相对路径。
- 绝对路径。
- Production/Acceptance 隔离。
- 默认配置不包含 `D:/codex`。
- Windows 普通测试路径动态选择非系统盘。
- `C:\` 系统盘拒绝测试保留。

## 5. Obsidian CLI 路径发现

兼容实现仍位于：

```text
second_brain/obsidian_cli.py
```

本轮只修复迁移阻塞问题，没有复制完整类到 `src/obsidian/`。

### 5.1 CLI 优先级

```text
OBSIDIAN_CLI_PATH
-> shutil.which("Obsidian.com")
-> shutil.which("obsidian")
-> 平台标准候选
-> not_found
```

Windows 候选只从以下环境变量构造：

- `LOCALAPPDATA`
- `ProgramFiles`
- `ProgramFiles(x86)`

macOS 与 Linux 使用平台标准候选，不写死开发者盘符或用户目录。

### 5.2 发现来源

```text
environment
path
platform_location
not_found
```

发现来源进入配置和健康状态，避免 UI 将猜测显示成已配置事实。

### 5.3 Vault 优先级

```text
Workspace Vault
-> Runtime Settings Vault
-> OBSIDIAN_VAULT_PATH
-> SECOND_BRAIN_OBSIDIAN_DIR（兼容）
-> not_found
```

### 5.4 跨平台子进程

仅在 Windows 添加 `creationflags`，并通过 `getattr(subprocess, "CREATE_NO_WINDOW", 0)` 兼容缺失属性的平台。

Dry Run（试运行）在调用子进程前返回。

## 6. 依赖所有权

本轮采用一套 Requirements + Constraints（依赖声明与约束）模型：

| 文件 | 所有权 |
|---|---|
| `requirements.txt` | 生产核心直接依赖 |
| `requirements-ui.txt` | Local Control API 额外依赖，并包含核心 |
| `requirements-media.txt` | 可选媒体依赖，并包含核心 |
| `requirements-mcp.txt` | 可选 MCP SDK 依赖，并包含核心 |
| `requirements-test.txt` | 测试与开发依赖 |
| `constraints/python-3.13-linux.txt` | 从 UI、测试、MCP 直接依赖生成的 Python 3.13 Linux 版本集合 |

没有把以下大型可选依赖塞进核心：

- PaddleOCR
- faster-whisper
- scenedetect

### 6.1 约束生成方式

使用 `pip-tools==7.6.0` 的 `pip-compile`，输入为：

```text
requirements-ui.txt
requirements-test.txt
requirements-mcp.txt
```

生成后删除运行环境注入的私有 Index URL（包索引地址）和认证信息，再执行凭据模式检查。

该约束文件目前只证明：

```text
CPython 3.13
Linux x86_64
```

它不是 Windows/Python 3.12 验收替代品。

### 6.2 依赖升级流程

1. 只修改对应直接依赖文件。
2. 使用规定 Python/平台重新运行 `pip-compile`。
3. 检查约束文件不含私有源、Token、本机路径或 editable（可编辑安装）路径。
4. 创建全新核心与 UI 环境。
5. 执行 `pip check`、导入、聚焦测试和完整测试。
6. 记录测试数量变化和版本变更原因。

## 7. 离线合同验证脚本

新增：

```text
scripts/validate_clean_install.py
```

检查：

- 依赖文件是否存在。
- 核心、UI、媒体、MCP、测试依赖所有权。
- 约束是否精确固定。
- 依赖文件是否包含本机路径、editable、本地文件 URL 或凭据。
- `package.json` 与 `package-lock.json` 根依赖是否一致。
- P0 关键运行文件是否包含机器专属路径。
- 可选 `--import-check` 导入检查。

该脚本不替代 `venv + pip install`、pytest 或 npm 构建。

## 8. 启动合同测试

新增 `tests/test_startup_contracts.py`，使用 AST（抽象语法树）和 Settings 行为断言，不比较整个文件文本。

覆盖：

- 五个 Python 启动入口存在 main guard。
- 模块导入阶段不直接调用服务 `start/serve/run_forever`。
- Local Control API 使用 `settings.control_api_host` 与 `settings.control_api_port`。
- MCP 入口通过 `resolve_mcp_runtime_config(settings)` 获取运行配置。
- 8765、8766、8767 分别属于 Compatibility、Control API、MCP。
- 启动文件不硬编码服务端口。
- 启动文件不包含机器专属绝对路径。

受当前执行环境限制，未完成对全仓所有旧逐字比较测试的完整目录级清点，因此该项仍是放行阻塞点。

## 9. Qdrant 与 Windows 测试边界

### 9.1 Windows

- 普通 Workspace 测试不再固定使用 `D:\LingJiTest`，而是动态选择非系统盘合成路径。
- `C:\` 系统盘拒绝测试继续保留。
- 未降低系统盘保护。

### 9.2 Qdrant

本轮没有修改生产 Qdrant、Collection 或 Schema。

完整仓库 Qdrant 测试尚未在完整仓库环境执行，因此不能确认所有外部服务依赖测试已经转换为 in-memory、embedded、Fake Provider 或明确 skip。

## 10. 已执行验证

### 10.1 全新核心环境依赖安装

```text
python -m venv /tmp/lingji-p0-core-env
pip install -r requirements.txt -r requirements-test.txt
pip check
核心包导入
```

结果：通过。

### 10.2 全新 UI 环境依赖安装

```text
python -m venv /tmp/lingji-p0-ui-env
pip install -c constraints/python-3.13-linux.txt \
  -r requirements-ui.txt -r requirements-test.txt
pip check
FastAPI/TestClient/Control 依赖导入
```

结果：通过。

### 10.3 隔离修改集聚焦测试

在由真实修改文件组成的隔离目录中，使用全新核心环境执行：

```text
compileall: PASS
collected: 45
passed: 40
failed: 0
skipped: 5
xfailed: 0
duration: 0.29s pytest / 0.72s wall
exit code: 0
```

五项跳过均为真实 Obsidian CLI/Vault 未配置的可选集成测试。

## 11. 未执行与阻塞项

由于当前执行容器没有完整仓库工作树，且 GitHub 连接只支持逐文件读取/写入，以下项目未执行：

- 完整仓库 `python -m compileall -q src second_brain tests scripts`。
- 完整 P0 文件集合聚焦 pytest。
- 全仓 `python -m pytest -v --tb=short`。
- 全仓测试数量差异核对。
- Windows Python 3.12 全新环境安装。
- `npm ci`。
- `npm run test:smoke`。
- `npm run build`。
- 全部旧启动源码逐字比较测试的删除或改写核对。
- 外部 Qdrant 测试 skip/fake/in-memory 处理的完整验证。

因此不得更新 `PROJECT_STATUS` 为已放行，也不得开始 P2-05。

## 12. 数据与边界确认

```text
读取 Production 正文: NO
修改 Production Vault: NO
修改 Production SQLite: NO
访问 Production Qdrant: NO
启动 Qdrant: NO
启动 Ollama: NO
修改数据库 Schema: NO
开发 P2-05: NO
合并正式分支: NO
rebase: NO
force push: NO
```

## 13. 回滚方式

代码按逻辑提交拆分，可使用普通 `git revert <commit>` 回滚对应变更。

禁止使用：

```text
reset --hard
force push
```

回滚路径修复时不得恢复机器专属默认值进入正式主线。

## 14. 下一步

只允许在完整 Windows 仓库工作树执行 P0 最终验收：

1. 同步当前远端分支。
2. 创建 Python 3.12 核心/UI 全新环境并生成对应 Windows 约束。
3. 运行合同脚本和完整 compileall。
4. 定位并改写全部旧启动逐字测试。
5. 修复 Qdrant 可选测试边界。
6. 运行聚焦与全仓 pytest。
7. 运行 `npm ci`、`test:smoke`、`build`。
8. 所有门禁通过后再更新 `PROJECT_STATUS` 与 `CODE_MAP`。

当前不得 rebase P2-05 分支。
