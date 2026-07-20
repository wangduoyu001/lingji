# LingJi（灵机）仓库开发规则

## 项目与分支

- 仓库：`https://github.com/wangduoyu001/lingji.git`
- 当前升级分支：`feature/second-brain-memory`
- 本地工作目录：`D:\codex\lingji-second-brain`
- 旧版目录：`C:\Users\Administrator\Documents\New project-ai`
- 本分支不得修改旧版目录，也不得向旧版目录写入运行数据。

## 开发前必须执行

1. 检查 `git status`、当前分支、最新提交和远程同步状态。
2. 阅读：
   - `docs/AI_CONTEXT.md`
   - `docs/PROJECT_STATUS.md`
   - `docs/ARCHITECTURE.md`
   - `docs/DEVELOPMENT_RULES.md`
3. 阅读本次任务涉及的源代码、测试和模块文档。
4. 新功能或新依赖必须先查官方文档和可靠开源实现，并把结论写入 `docs/TECH_RESEARCH/`。
5. 未完整了解现有实现前，禁止直接改代码。

## 核心原则

1. 使用最少代码完成明确需求，优先复用已有模块。
2. 不为了“看起来更整齐”进行大规模重构。
3. SQLite 是结构化事实来源；Qdrant 是可重建的向量检索层。
4. Obsidian 是用户正式知识入口，不得自动蒸馏为个人记忆。
5. AI 对话和 Codex 任务可以进入自动记忆流程。
6. 监听范围只能使用明确配置的白名单目录，禁止全盘扫描。
7. 所有下载、模型、缓存、数据库、日志和临时文件优先放在 D 盘。
8. 未经用户确认的建议不得写成长期事实或正式决策。
9. 禁止自动发布内容。

## 代码标准

- Python 文件统一使用 UTF-8；读取旧文件时兼容 UTF-8 BOM。
- 函数职责清晰，避免重复逻辑和无意义抽象。
- 新依赖必须有必要性说明，不得为一个小功能引入大型框架。
- 配置、路径和端口不得散落硬编码，优先使用现有配置层。
- 修改接口、数据结构或启动链路前必须检查兼容性。
- 不得把 Second Brain 服务擅自加入旧版 `start_lingji.bat`、`start_lingji.py` 或 `run_service.py`。

## 数据与安全边界

- 禁止提交 `.env`、API Key、Token、Cookie、真实聊天原文、真实数据库和个人隐私数据。
- 禁止提交 `node_modules`、构建缓存、模型文件、Qdrant 数据、日志和临时文件。
- 测试优先使用隔离目录、假数据或 acceptance workspace。
- 不得修改真实 Obsidian Vault，除非任务明确要求且具备可回滚方案。
- 所有写操作必须说明目标路径和影响范围。

## 测试与验收

每个功能或较大修改完成后必须：

1. 增加或更新对应测试。
2. 运行相关单元测试、集成测试、API 测试或 UI 测试。
3. 运行必要的回归测试，已有测试数量不得无故减少。
4. 记录测试命令、结果、失败项和已知限制。
5. 在 `docs/TEST_REPORTS/` 或对应开发报告中留下 Markdown 记录。
6. 本地真实环境未验证时，只能标记为“代码完成，待真机验收”，不得宣布完全通过。

## 文档同步

完成开发后，按实际影响更新：

- `docs/PROJECT_STATUS.md`
- `docs/ROADMAP.md`
- `docs/CHANGELOG.md`
- `docs/DEVELOPMENT_LOG/`
- `docs/DECISIONS/`
- `docs/TEST_REPORTS/`

文档必须基于真实代码、提交和测试结果，禁止编造。

## Git 要求

- 开发前确保工作区状态可解释，不覆盖他人未提交修改。
- 一个提交只处理一个清晰任务。
- 提交信息使用：`feat:`、`fix:`、`docs:`、`test:`、`refactor:`、`chore:`。
- 只提交本任务相关文件。
- 推送后报告：分支、commit SHA、测试结果、修改文件和未解决问题。
- 合并前必须完成本地测试与验收。

## PowerShell 与 Windows 注意事项

- Windows PowerShell 5.1 不支持 Bash heredoc，也不要依赖 `&&`。
- 路径含空格时必须正确引用。
- 停止服务时优先按 PID 或明确端口定位，禁止粗暴结束全部 Python 进程。
