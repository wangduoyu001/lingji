# LingJi（灵机）

LingJi 是一个本地优先的个人第二大脑与桌面控制中心。正式代码主线位于 `src/`，正式桌面界面位于 `desktop/lingji-control/`；`second_brain/` 仅保留兼容、迁移和验收用途。

## 唯一可信入口

- 开发与 AI 执行入口：[`AGENTS.md`](AGENTS.md)
- 当前状态：[`docs/PROJECT_STATUS.md`](docs/PROJECT_STATUS.md)
- 稳定架构：[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)
- 代码与局部测试导航：[`docs/MODULES/CODE_MAP.md`](docs/MODULES/CODE_MAP.md)
- 长期开发规则：[`docs/DEVELOPMENT_RULES.md`](docs/DEVELOPMENT_RULES.md)
- 历史验收证据：[`docs/TEST_REPORTS/`](docs/TEST_REPORTS/)

不要把历史模块计划、阶段报告或兼容文档当作当前架构与运行说明。

## 正式运行边界

```text
Tauri Desktop
-> Rust RuntimeManager
-> packaged Python Sidecar
-> authenticated 127.0.0.1:8766 Local Control API
-> shared Python Service Layer
```

- Obsidian Vault + Git 是正式知识与永久记忆正文的权威来源。
- SQLite 与 Qdrant 是可重建的运行状态、检索与派生层。
- MCP 默认使用 stdio；可选 HTTP 使用 8767。
- 8765 仅为迁移期兼容 API，不是正式 Desktop 后端。

## 开发环境

```powershell
python -m pip install -r requirements-ui.txt -r requirements-test.txt -r requirements-mcp.txt
cd desktop/lingji-control
npm ci
```

Sidecar 或 Windows 安装包开发还需要：

```powershell
python -m pip install -r requirements-sidecar-build.txt
```

所有缓存、模型、数据库、日志和构建辅助文件应使用可配置位置，优先放在 `D:\codex\` 或主人明确选择的目录。禁止向旧项目目录 `C:\Users\Administrator\Documents\New project-ai` 写入运行数据。

## 统一验收入口

```powershell
.\scripts\validate.ps1 -Mode focused -Area <area>
.\scripts\validate.ps1 -Mode full
.\scripts\validate.ps1 -Mode release
```

- `focused`：模块开发期间的局部验收。
- `full`：合并前最终树的完整本机门禁。
- `release`：在完整门禁后构建并整理 Windows Sidecar/Tauri/NSIS 发布产物。

正式发布仍以 GitHub Windows release workflow 和主人机器安装验收为最终证据。

## 安全原则

- 默认仅绑定 `127.0.0.1`。
- 不提交密钥、真实聊天、数据库、日志、模型、缓存或构建产物。
- 不自动批准、拒绝、删除或覆盖正式记忆。
- 不自动删除或重建生产 Qdrant Collection。
- 不自动下载大型模型，不粗暴结束全部 Python 进程。
