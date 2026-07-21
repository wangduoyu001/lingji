# P0_ENGINEERING_HYGIENE_TEST_REPORT.md — 工程卫生测试报告

> Updated（更新时间）: 2026-07-21  
> Branch（分支）: `work/p0-engineering-hygiene`  
> Base Commit（基础提交）: `e113c55d1e4738b20d60abe3bf79460a6f493a5f`  
> Verified Code Commit（已验证代码提交）: `70e1a23b56f19287b3823a24c951f6c51c88aeff`  
> Status（状态）: `BLOCKED_FULL_REPOSITORY_AND_WINDOWS_VALIDATION`  
> Evidence（证据来源）: 隔离全新 Python 环境、隔离修改文件测试集、GitHub 分支文件

## 1. 结论

已验证：

- 核心依赖可在全新 Python 3.13 Linux 环境安装。
- UI 依赖可在另一全新 Python 3.13 Linux 环境安装。
- `pip check` 无损坏依赖。
- FastAPI TestClient 依赖可导入。
- 修改后的 Config、Workspace 与 Obsidian CLI 隔离测试为零失败。
- 未连接生产 Qdrant，未启动 Ollama，未修改生产数据。

未验证：

- 完整仓库 compileall。
- 完整仓库聚焦测试。
- 完整仓库 pytest。
- Windows Python 3.12 路径和依赖。
- npm 安装、Smoke Test（冒烟测试）与构建。
- 全部旧启动逐字比较测试是否已经被清除。

因此本报告不能支持 `READY_TO_REBASE_P2_05_BRANCHES`。

## 2. 环境

```text
Operating System: Linux x86_64
Kernel: 4.4.0
Python: 3.13.5
Base pip: 25.1.1
Clean environment pip: 26.1.2
Node: v22.16.0
npm: 10.9.2
```

该环境不是用户 Windows 本机，不能替代 Windows/Tauri 验收。

## 3. 依赖文件

```text
requirements.txt
requirements-ui.txt
requirements-media.txt
requirements-mcp.txt
requirements-test.txt
constraints/python-3.13-linux.txt
```

所有权：

| 文件 | 范围 |
|---|---|
| `requirements.txt` | 生产核心 |
| `requirements-ui.txt` | Local Control API，包含核心 |
| `requirements-media.txt` | 可选媒体，包含核心 |
| `requirements-mcp.txt` | 可选 MCP，包含核心 |
| `requirements-test.txt` | pytest 等测试依赖 |
| `constraints/python-3.13-linux.txt` | Python 3.13 Linux 可复现版本约束 |

约束由 `pip-tools==7.6.0` 从直接依赖生成，不是从开发环境随手复制的 `pip freeze`。

提交前已删除运行环境注入的私有包源 URL 和认证信息。约束文件不含本机路径、editable 安装、Token 或私有源凭据。

## 4. 全新核心环境

### 4.1 命令

```text
python -m venv /tmp/lingji-p0-core-env
/tmp/lingji-p0-core-env/bin/python -m pip install --upgrade pip
/tmp/lingji-p0-core-env/bin/python -m pip install \
  -r requirements.txt \
  -r requirements-test.txt
/tmp/lingji-p0-core-env/bin/python -m pip check
```

### 4.2 导入

```text
pydantic_settings
qdrant_client
requests
yaml
pytest
```

### 4.3 结果

```text
install: PASS
imports: PASS
pip check: PASS
exit code: 0
```

## 5. 全新 UI 环境

### 5.1 命令

```text
python -m venv /tmp/lingji-p0-ui-env
/tmp/lingji-p0-ui-env/bin/python -m pip install --upgrade pip
/tmp/lingji-p0-ui-env/bin/python -m pip install \
  -c constraints/python-3.13-linux.txt \
  -r requirements-ui.txt \
  -r requirements-test.txt
/tmp/lingji-p0-ui-env/bin/python -m pip check
```

### 5.2 导入

```text
fastapi
fastapi.testclient.TestClient
uvicorn
httpx
psutil
pytest
qdrant_client
pydantic_settings
```

### 5.3 结果

```text
install: PASS
imports: PASS
pip check: PASS
exit code: 0
```

观察到 Starlette 关于 TestClient/httpx 后续接口的 Deprecation Warning（弃用警告）。本轮没有无理由升级或重构框架；该警告不影响当前导入结果，应在正式 Python/Windows 锁定时复核。

## 6. 可选媒体依赖

```text
PaddleOCR: NOT INSTALLED
faster-whisper: NOT INSTALLED
scenedetect: NOT INSTALLED
GPU PaddlePaddle: NOT INSTALLED
```

本轮只确认媒体依赖仍位于 `requirements-media.txt`，没有进入核心依赖。

## 7. 隔离 compileall

### 7.1 范围

隔离目录包含真实修改后的：

```text
src/config.py
src/runtime/workspace.py
second_brain/obsidian_cli.py
tests/test_obsidian_cli.py
tests/test_obsidian_cli_behavior.py
tests/test_workspace_contract.py
```

### 7.2 命令

```text
/tmp/lingji-p0-core-env/bin/python -m compileall -q src second_brain tests
```

### 7.3 结果

```text
scope: isolated modified-file set
passed: PASS
failed: 0
duration: 0.05s
exit code: 0
```

这不是完整仓库 compileall。

## 8. 隔离聚焦 pytest

### 8.1 命令

```text
/tmp/lingji-p0-core-env/bin/python -m pytest \
  tests/test_obsidian_cli.py \
  tests/test_obsidian_cli_behavior.py \
  tests/test_workspace_contract.py \
  -q --tb=short
```

### 8.2 结果

```text
collected: 45
passed: 40
failed: 0
skipped: 5
xfailed: 0
pytest duration: 0.29s
wall duration: 0.72s
exit code: 0
```

### 8.3 Skip 说明

五项跳过属于真实 Obsidian CLI 集成测试，原因是隔离环境未配置：

```text
Obsidian CLI
或
OBSIDIAN_VAULT_PATH / SECOND_BRAIN_OBSIDIAN_DIR
```

单元测试已使用临时文件和 Fake Process（假进程）覆盖路径发现、超时、Dry Run、读取失败、空搜索和写后验证。

没有通过 skip 隐藏代码失败。

### 8.4 Warning

```text
Pydantic class-based Config deprecation warning: 1
```

该警告来自现有 Settings 配置风格，不属于本轮路径合同修复范围。

## 9. 启动合同测试

新增：

```text
tests/test_startup_contracts.py
```

计划覆盖：

- main guard。
- import 阶段不启动服务。
- Settings 端口所有权。
- 8765/8766/8767 隔离。
- Control API host/port 接线。
- MCP Runtime Settings 接线。
- 无机器专属路径。
- 不再比较完整文件字符串。

当前没有完整仓库工作树，因此该文件只完成代码提交，未进入真实完整 P0 聚焦测试。

状态：

```text
IMPLEMENTED_NOT_FULL_REPOSITORY_TESTED
```

## 10. 前端锁文件静态核对

GitHub 分支上的 `package.json` 和 `package-lock.json` 根包记录一致：

- name 一致。
- version 一致。
- dependencies 一致。
- devDependencies 一致。

新增离线校验脚本会比较以上字段。

但以下命令未执行：

```text
npm ci
npm run test:smoke
npm run build
```

原因：当前执行环境没有完整 `desktop/lingji-control` 工作树。

## 11. 完整仓库 pytest

### 11.1 上次正式记录

```text
collected: 338
passed: 306
failed: 19
skipped: 13
xfailed: not recorded
 duration: 45.99s
```

历史失败分类：

- Qdrant 外部服务：7。
- Windows `C:\Temp` 系统盘限制：12。

### 11.2 本轮

```text
command: python -m pytest -v --tb=short
status: NOT EXECUTED
collected: NOT AVAILABLE
passed: NOT AVAILABLE
failed: NOT AVAILABLE
skipped: NOT AVAILABLE
xfailed: NOT AVAILABLE
duration: NOT AVAILABLE
exit code: NOT AVAILABLE
```

原因：当前容器没有完整仓库工作树。

## 12. 测试数量变化解释

已知测试文件变化：

### 12.1 `tests/test_obsidian_cli.py`

```text
旧 collected: 20
新 collected: 28
变化: +8
```

变化原因：

- 新增环境变量最高优先级。
- 新增两个 PATH 可执行名称探测。
- 新增三个 Windows 标准环境变量候选。
- 新增 not_found 来源。
- 新增 Workspace/Runtime/Vault 优先级。
- 新增旧 Vault 环境变量兼容。
- 新增无固定盘符断言。
- 新增无 `CREATE_NO_WINDOW` 属性兼容。
- 新增超时转换。
- 真实环境写测试改为安全单元行为测试。

### 12.2 `tests/test_obsidian_cli_behavior.py`

```text
新增 collected: 3
```

覆盖：

- 读取不存在笔记。
- 搜索无结果。
- 临时环境写后验证。

### 12.3 `tests/test_workspace_contract.py`

```text
旧 collected: 8
新 collected: 14
变化: +6
```

新增备份默认、环境覆盖、相对/绝对路径、兼容环境变量和机器专属路径测试。

### 12.4 `tests/test_startup_contracts.py`

```text
新增 collected: 8
```

使用 AST 和 Settings 合同，不使用完整源码字符串快照。

### 12.5 名义总变化

```text
known nominal delta: +25
baseline 338 -> expected 363
```

该数字尚未通过完整仓库 collection 验证，状态为：

```text
UNRECONCILED_TEST_COUNT_DELTA
```

不能把预期数量当成真实收集数量。

## 13. Qdrant 测试处理状态

本轮代码没有访问、重建或切换生产 Qdrant。

```text
Production Qdrant access: NO
Qdrant service started: NO
Collection created/deleted: NO
```

由于未获得完整测试目录，以下合同尚未完整确认：

- 单元测试是否全部使用 in-memory、embedded 或 Fake Provider。
- 外部 Qdrant 集成测试是否在服务不可用时明确 skip。
- skip 原因是否稳定且不掩盖真实代码失败。

状态：`BLOCKED_FULL_REPOSITORY_VALIDATION`。

## 14. Windows 路径测试处理状态

已实现：

- 普通 Workspace 测试动态选择非系统盘合成路径。
- 专门 `C:\` 拒绝测试保留。
- 系统盘保护未降低。

未执行：

- Windows Python 3.12 真机测试。
- Windows 不同盘符、环境变量和 Obsidian 标准安装路径验证。

## 15. 未执行门禁

| 门禁 | 状态 |
|---|---|
| 完整仓库 compileall | NOT EXECUTED |
| 完整 P0 聚焦 pytest | NOT EXECUTED |
| 完整仓库 pytest | NOT EXECUTED |
| Windows Python 3.12 clean install | NOT EXECUTED |
| npm ci | NOT EXECUTED |
| npm run test:smoke | NOT EXECUTED |
| npm run build | NOT EXECUTED |
| 全部旧逐字启动测试清点 | NOT COMPLETED |
| Qdrant 可选测试合同全量核对 | NOT COMPLETED |

## 16. 安全声明

```text
读取 Production ChatGPT 正文: NO
修改 Production Vault: NO
修改 Production SQLite: NO
访问 Production Qdrant: NO
启动 Production Qdrant: NO
启动 Ollama: NO
修改数据库 Schema: NO
修改 P2-05: NO
合并正式分支: NO
rebase: NO
force push: NO
```

## 17. 最终测试状态

```text
P0_ENGINEERING_HYGIENE_BLOCKED
DO_NOT_START_P2_05
```

解除阻塞必须在完整 Windows 仓库执行全部未完成门禁，并准确记录真实统计。
