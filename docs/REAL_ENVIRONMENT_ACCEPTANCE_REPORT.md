# 灵机真实环境只读验收报告

> 文档角色：历史实施/验证快照，不是当前进度或当前架构权威。
> 当前状态看 `docs/PROJECT_STATUS.md`；当前代码入口看 `docs/MODULES/CODE_MAP.md`。

## 状态

- 模块：P0-B 真实环境只读验收
- 分支：`test/real-environment-acceptance`
- Draft PR：`#4`
- 验收 Head：`011142a2ac070c2ab6091f72783bda0c465ac674`
- GitHub Actions Run：`29692373806`
- 当前状态：`REVIEW_REQUIRED`
- 代码状态：Linux、Windows、MCP、桌面 UI、扩展和插件 CI 全绿
- 剩余条件：在主人电脑对真实 Vault、ChatGPT 导出和样例媒体运行一次
- 非目标：迁移、修复、索引重建、内容导入、媒体转写、自动删除

## Research Notes

### 官方文档

1. Python sqlite3 URI 和只读模式：
   - https://docs.python.org/3.12/library/sqlite3.html#how-to-work-with-sqlite-uris
   - SQLite 副本使用 `file:...?...mode=ro` 执行完整性检查。
2. Python zipfile 完整性检查：
   - https://docs.python.org/3.12/library/zipfile.html#zipfile.ZipFile.testzip
   - `testzip()` 读取成员并检查 CRC，返回首个损坏成员。
3. FFprobe 官方文档：
   - https://ffmpeg.org/ffprobe.html
   - 使用 `-show_format -show_streams -print_format json` 获取媒体参数。
4. Ollama 官方 API：
   - https://docs.ollama.com/api/tags
   - 使用 `GET /api/tags` 验证服务和本地模型列表。
5. Python hashlib：
   - https://docs.python.org/3.12/library/hashlib.html
   - SHA-256 用于验收前后输入指纹，不用于修改内容。

### 类似项目与设计

1. Homebrew `brew doctor`
   - https://docs.brew.sh/Manpage#doctor-dr
   - 借鉴“诊断并报告问题，不自动替用户改变环境”的边界。
2. Flutter `flutter doctor`
   - https://docs.flutter.dev/reference/flutter-cli#flutter-doctor
   - 借鉴分项环境检查、状态和可操作诊断输出。
3. GitHub CLI `gh auth status`
   - https://cli.github.com/manual/gh_auth_status
   - 借鉴清晰列出连接目标、状态和失败原因，而不是只返回布尔值。

### 采用

- 输入目录和文件只读扫描。
- 验收前后计算文件数、大小、mtime 和可选 SHA-256 指纹。
- Vault 指纹覆盖 Markdown、附件和其他普通文件。
- SQLite 原数据库、`-wal`、`-shm` 都进入验收前后指纹。
- 数据库和 WAL 复制到系统临时目录，在副本上执行 `quick_check`。
- ChatGPT ZIP 支持结构识别、加密成员检测和可选 CRC 全量检查。
- FFprobe 只读检查真实媒体格式、时长和流数量。
- Ollama 返回实际模型名。
- 报告只写入 `storage/reports/acceptance`。
- JSON 和 Markdown 双报告，并保留历史列表。
- 桌面 UI 提供路径、开关、运行状态、错误、结果和历史。

### 拒绝

- 不在原 SQLite 上建立只读连接，因为 WAL 模式下仍可能创建 `-shm`。
- 不调用索引重建、导入、媒体分析或迁移流程。
- 不使用启动健康检查的目录创建和写入探针。
- 不自动修复缺失目录、损坏数据库或过期索引。
- 不上传 Vault、导出包或媒体。
- 不绕过权限读取未授权目录。
- 不为了诊断引入新依赖或复杂前端框架。

## 实现

### 新增

- `src/acceptance.py`
  - `AcceptanceChecker`
  - 输入指纹、只读检查和结果汇总
- `src/acceptance_reports.py`
  - 原子写入 JSON/Markdown 报告
  - 历史报告列表
- `src/sqlite_snapshot.py`
  - 数据库和 WAL 临时快照完整性检查
  - 所有 SQLite 协调文件只出现在系统临时目录
- `tests/test_acceptance_read_only.py`
  - 输入不变、附件指纹、SQLite/WAL/SHM、ZIP CRC 和报告目录测试
- `desktop/lingji-control/src/AcceptancePage.tsx`
  - UI 表单、状态、结果和历史
- `desktop/lingji-control/src/Root.tsx`
  - 当前控制中心与环境验收模式切换
- `desktop/lingji-control/scripts/acceptance-smoke.mjs`
  - UI 入口和 API 契约 smoke test

### 修改

- `src/health.py`
  - 增加 `read_only=True` 模式
  - 不创建目录、不写探针、SQLite 快照检查、Ollama 模型列表
- `scripts/acceptance_check.py`
  - 变成薄 CLI，复用统一 Checker 和报告服务
- `src/control/service.py`
  - 运行验收、保存报告、列出历史、写审计事件
- `src/control/api.py`
  - `POST /api/acceptance/run`
  - `GET /api/acceptance/reports`
- `tests/test_acceptance_check.py`
  - 适配统一只读 Checker
- `tests/test_control_api_extended.py`
  - 验证 API、输入不变和报告历史
- `desktop/lingji-control/src/main.tsx`
  - 挂载最小 Root
- `desktop/lingji-control/package.json`
  - 构建前运行 UI smoke

## 只读边界

被检查输入：

- Obsidian Vault 全部普通文件，包括 Markdown 和附件
- `lingji_state.db`、`-wal`、`-shm`
- `lingji_memory.db`、`-wal`、`-shm`
- `runtime_settings.json`
- ChatGPT ZIP/JSON/目录
- 样例媒体

允许写入：

- `storage/reports/acceptance/acceptance-*.json`
- `storage/reports/acceptance/acceptance-*.md`
- 一条验收审计事件
- 系统临时目录中的 SQLite 快照

审计事件在输入不变比较完成后写入，因此不会掩盖检查期间的输入变化。

## 测试命令

```powershell
python -m compileall -q main.py run_service.py run_control_api.py run_mcp_server.py run_extraction_worker.py src tests scripts
python -m unittest tests.test_acceptance_check tests.test_acceptance_read_only tests.test_control_api_extended -v
python -m unittest discover -s tests -v

cd desktop/lingji-control
npm install --no-audit --no-fund
npm run test:smoke
npm run build
```

## GitHub Actions 验证

Run `29692373806`：

- Ubuntu Python 3.11：success
- Ubuntu Python 3.12：success
- Windows Python 3.12：`113 tests / OK`
- MCP smoke：success
- Browser capture smoke：success
- Obsidian plugin smoke：success
- Desktop UI smoke、TypeScript 和 Vite build：success

## CLI Demo

```powershell
python scripts/acceptance_check.py `
  --vault "E:\obsidian\本地知识库" `
  --storage "E:\LingJiData\storage" `
  --backup "E:\LingJiData\backups" `
  --chatgpt-export "D:\Downloads\chatgpt-export.zip" `
  --media "D:\media\sample.mp4"
```

输出：

- JSON 报告路径
- Markdown 报告路径
- 总状态、错误、警告
- `inputs_unchanged`
- 环境版本、模型、数据库、ZIP 和媒体检查详情

未指定 ChatGPT 导出或媒体时只产生警告，不伪装为已验收。

## UI Demo

1. 启动 `python run_control_api.py`。
2. 打开 LingJi 桌面 UI。
3. 右下角选择“环境验收”。
4. 连接本机 API。
5. 填写 Vault、可选 ChatGPT 导出和样例媒体。
6. 保持“深度检查 ZIP CRC”和“验收前后计算输入哈希”开启。
7. 点击“开始只读验收”。
8. 查看状态、输入未变化、错误、警告和历史报告。

## 风险

1. 大型 Vault 全量 SHA-256 会消耗时间和磁盘读取带宽，但不会写入输入。
2. 大型 ChatGPT ZIP 深度 CRC 检查需要读取全部压缩成员。
3. 验收期间其他程序修改文件会导致 `inputs_unchanged=false`，这是正确失败。
4. 活跃 SQLite 在快照复制期间发生写入时，WAL 指纹变化会使验收失败，应在系统相对空闲时重试。
5. FFprobe 只验证媒体可读和结构，不执行转写、OCR 或画面理解。

## 已知限制

- GitHub Actions 无法访问主人电脑的 `E:\obsidian\本地知识库`。
- 代码 CI 已通过，但 P0-B 仍需主人电脑真实运行才能标记 `ACCEPTED`。
- 当前验收入口通过顶层 UI 模式切换提供；P1-0 UI 模块化后再并入正式侧栏路由。
- 报告路径当前以文本显示，Tauri 的“打开目录”按钮在桌面打包阶段实现。

## 回滚

本模块没有数据迁移。回滚 PR #4 即可；删除派生验收报告不会影响 Vault、Raw、Backup、索引或正式知识。
