# 灵机剩余工作、并行开发与 Git 验收规范

> 日期：2026-07-19  
> 当前开发分支：`feature/extraction-hardening-web-skills-ui`  
> 当前 Draft PR：`#2`  
> 目标：把“剩余工作”拆成边界明确、可独立开发、可独立测试、可独立回滚的板块。

---

## 1. 当前真实状态

### 1.1 已完成或已具备可用基础

1. 单 Vault 长期记忆架构与统一提取管线。
2. ChatGPT 导出、Codex 工作报告、网页/社交页面、本地媒体适配器。
3. 提取任务队列、幂等、租约、心跳、重试、进度、失败恢复。
4. 原始快照、历史版本、人工元数据保护、敏感内容路由。
5. 本地 FFprobe/FFmpeg 元数据、音轨与关键帧派生。
6. 可选本地 Provider：faster-whisper、PaddleOCR、PySceneDetect。
7. Skill 注册表与 Obsidian 辅助入口。
8. 独立本地控制 API。
9. React + Tauri 独立桌面控制中心首版。
10. Chrome/Edge 主动投喂扩展首版。
11. 存储盘点、可恢复清理计划、冷存储计划。
12. 校验备份、SQLite 在线快照、隔离恢复目录。
13. Vault 文件索引与 Memory DB 增量同步。
14. 真实环境只读验收脚本。
15. Linux Python 3.11/3.12、Windows Python 3.12、MCP、浏览器扩展、Obsidian 插件、桌面 UI 构建 CI。

### 1.2 部分完成，不能标记为最终完成

1. 桌面控制中心只有总览、任务、投喂、媒体、存储、备份、设置、日志页面。
2. Tauri 目前是壳与前端构建，尚未完成 Windows 安装包、服务自动启动、托盘和升级流程。
3. 浏览器扩展能投喂页面文字和选中文字，但尚未实现完整 DOM 快照、截图、附件、项目选择和站点专用增强。
4. 本地 ASR/OCR/镜头 Provider 已实现，但尚未完全接入媒体提取 Worker 的自动编排。
5. 备份可以校验和隔离恢复，但尚未提供“验收后切换当前数据”的受控恢复向导。
6. 存储清理已有预览、确认、恢复，但自动调度和磁盘预警通知尚未接入 Scheduler。
7. 真实验收脚本已存在，但尚未在主人的真实 `E:\obsidian\本地知识库`、真实 ChatGPT 导出和真实媒体上执行。

### 1.3 尚未完成

1. 手机分享入口、设备配对和安全远程投喂。
2. 登录态视频号、抖音、小红书的完整正文/媒体采集验收。
3. 说话人分离、人物/场景/动作视觉理解、视频摘要。
4. 网页来源与本地媒体自动配对。
5. 大型单个 ChatGPT JSON 真正流式解析。
6. ChatGPT/Codex 附件、图片、文件的完整导入关系。
7. 来源、记忆、项目、关系图、Skill、模型、权限等完整桌面 UI。
8. 原始私密快照加密、密钥管理、恢复密钥和权限隔离。
9. 完整恢复切换、回滚演练和灾难恢复验收。
10. Windows 安装器、开机启动、托盘、崩溃恢复和版本升级。
11. 大规模真实 Vault 性能基准和长期运行测试。

---

## 2. 并行开发总原则

### 2.1 可以并行的前提

每个板块必须满足：

1. 有独立分支。
2. 有独立 Worktree。
3. 有明确负责目录。
4. 不修改其他板块的负责目录。
5. 公共接口先写契约，再写实现。
6. 每个功能必须有测试和 Markdown 报告。
7. 不允许直接向集成分支推送功能提交。
8. 不允许把付费 API 作为基础功能硬依赖。
9. 不允许绕过平台权限、偷取 Cookie 或关闭安全校验。
10. 不允许自动删除 Raw、Vault、Backup。

### 2.2 不能直接并行修改的共享热点

以下文件或目录由“集成负责人”统一修改：

- `src/control/api.py`
- `src/control/service.py`
- `src/config.py`
- `src/storage/state_db.py`
- `src/retrieval/memory_db.py`
- `.github/workflows/`
- `AGENTS.md`
- `desktop/lingji-control/src/App.tsx`，直到 UI 完成模块化拆分
- 数据库迁移版本号与 Schema

其他开发板块如需修改共享热点，必须：

1. 先提交接口需求文档或最小补丁。
2. 由集成负责人合入公共接口。
3. 功能分支再基于更新后的集成分支继续。

---

## 3. 推荐 Git 基线

### 3.1 当前阶段

当前 PR #2 继续保持 Draft，直到：

1. 全部 CI 通过。
2. 真实环境只读验收至少执行一次。
3. 桌面 UI 可在 Windows 启动。
4. 备份创建、校验、隔离恢复在 Windows 通过。

### 3.2 建立集成分支

在当前功能分支 CI 全绿后执行：

```powershell
# 更新当前功能基线
git fetch origin
git switch feature/extraction-hardening-web-skills-ui
git pull --ff-only origin feature/extraction-hardening-web-skills-ui

# 创建下一阶段集成分支
git switch -c integration/lingji-v1
git push -u origin integration/lingji-v1
```

后续所有独立板块都从 `integration/lingji-v1` 创建，不再从 `master` 或旧分支创建。

### 3.3 每个板块使用独立 Worktree

示例：

```powershell
git fetch origin

git worktree add ..\lingji-desktop-packaging `
  -b feature/desktop-packaging `
  origin/integration/lingji-v1

cd ..\lingji-desktop-packaging
```

完成后清理：

```powershell
cd ..\lingji
git worktree remove ..\lingji-desktop-packaging
git branch -d feature/desktop-packaging
```

### 3.4 提交规则

提交信息格式：

```text
feat(scope): 功能说明
fix(scope): 修复说明
perf(scope): 性能优化说明
test(scope): 测试说明
docs(scope): 文档说明
build(scope): 构建或依赖说明
```

每个板块至少包含：

1. 功能提交。
2. 测试提交。
3. `docs/<MODULE>_REPORT.md` 报告提交。

### 3.5 PR 规则

- PR Base：`integration/lingji-v1`
- 一个板块一个 PR。
- PR 初始状态为 Draft。
- PR 必须列出：目标、非目标、修改目录、接口变化、测试、风险、回滚方式、真实验收结果。
- CI 全绿后转 Ready for review。
- 合并方式：`Squash and merge`。
- 合并后功能分支删除。
- 集成负责人每天只做一次或少量批次合并，避免基础分支不断抖动。

### 3.6 同步规则

功能分支开发期间：

```powershell
git fetch origin
git rebase origin/integration/lingji-v1
```

禁止在功能分支反复执行无意义的 Merge Commit。发生冲突时由修改冲突文件的板块负责人解决，不能用 `ours/theirs` 粗暴覆盖。

---

## 4. 独立开发板块

## 板块 A：基线稳定与真实验收

### 分支

`feature/real-environment-acceptance`

### 独立目录

- `scripts/acceptance_check.py`
- `scripts/migration/`
- `tests/test_acceptance_*.py`
- `docs/REAL_ENVIRONMENT_ACCEPTANCE_REPORT.md`

### 要求

1. 在真实 `E:\obsidian\本地知识库` 上执行只读扫描。
2. 检查 Markdown 数量、总容量、最大文件、非法 Frontmatter、重复 ID、路径异常。
3. 检查真实 ChatGPT 导出 ZIP/JSON。
4. 检查真实媒体 FFprobe。
5. 检查数据库完整性、Ollama、FFmpeg、磁盘空间。
6. 生成 JSON 和 Markdown 报告。
7. 任何迁移必须先生成快照和迁移计划。
8. 默认只读，必须显式确认才允许写入。

### 验收标准

- 不修改真实 Vault 任何文件。
- 运行前后 Vault 文件 SHA-256 汇总一致。
- 报告包含所有错误、警告、路径和建议动作。
- 10,000 个 Markdown 文件扫描不会崩溃。
- Windows PowerShell 可执行。
- `python -m unittest discover -s tests -v` 通过。

### 依赖

无，可最先进行。

---

## 板块 B：桌面程序打包与本机服务生命周期

### 分支

`feature/desktop-packaging`

### 独立目录

- `desktop/lingji-control/src-tauri/`
- `desktop/lingji-control/package.json`
- `scripts/install_desktop_control.ps1`
- `scripts/uninstall_desktop_control.ps1`
- `docs/DESKTOP_PACKAGING_REPORT.md`

### 要求

1. 生成 Windows 安装包。
2. 启动桌面程序时检测或启动本机 FastAPI 服务。
3. 服务只能默认绑定 `127.0.0.1`。
4. 自动读取本机控制令牌，不在 UI 明文显示。
5. 提供托盘、退出、重启服务、打开日志目录。
6. 崩溃后可再次启动，不遗留僵尸进程。
7. 卸载不删除 Vault、Raw、Backup。
8. 升级不覆盖用户运行时设置。

### 验收标准

- Windows 10/11 安装、启动、退出、卸载通过。
- 未安装 Python 的目标机要么使用打包后端，要么安装器明确阻止并给出可执行修复。
- 连续启动/退出 20 次无残留服务进程。
- API 端口被占用时显示明确错误并允许改端口。
- 安装和卸载前后 Vault 文件哈希不变。
- Tauri 构建 CI 通过。

### 依赖

当前桌面前端构建全绿后开始。

---

## 板块 C：桌面 UI 模块化与完整页面

### 分支

`feature/control-center-domains`

### 独立目录

- `desktop/lingji-control/src/components/`
- `desktop/lingji-control/src/pages/`
- `desktop/lingji-control/src/hooks/`
- `desktop/lingji-control/src/types/`
- `docs/CONTROL_CENTER_DOMAINS_REPORT.md`

### 前置要求

先把单文件 `App.tsx` 拆分成路由、页面和公共组件，拆分完成前禁止多个 UI 开发者同时修改 `App.tsx`。

### 页面要求

1. 来源中心。
2. 记忆中心。
3. 项目中心。
4. 关系图。
5. Skill 中心。
6. 模型与 Provider 中心。
7. 权限与隐私中心。
8. 任务详情与重试。
9. 备份对比和恢复向导。
10. 文件/目录选择器。

### 验收标准

- 每个页面有 Loading、Empty、Error、Success 状态。
- 页面刷新不丢失当前路由。
- 任务、设置、备份等危险操作有确认和结果反馈。
- 1,000 条列表数据不卡死，使用分页或虚拟列表。
- 不在前端保存敏感内容或明文令牌。
- `npm run build` 通过。
- 关键页面至少有组件测试或 Playwright UI smoke test。

### 依赖

需要集成负责人先提供稳定 API 契约。

---

## 板块 D：浏览器采集增强

### 分支

`feature/browser-capture-v2`

### 独立目录

- `browser-extension/lingji-capture/`
- `tests/browser-extension/`
- `docs/BROWSER_CAPTURE_V2_REPORT.md`

### 要求

1. 当前页面、选中文字、主要正文、完整 HTML 快照。
2. 可选截图和页面元数据。
3. 项目、标签、隐私级别选择。
4. 公众号、视频号、抖音、小红书等站点增强提取。
5. 不读取或上传 Cookie。
6. 不绕过登录或反爬机制。
7. 内容过大时分块或保存本地快照后提交路径。
8. 离线时进入本地待提交队列，恢复连接后由用户确认重试。

### 验收标准

- 普通网页、公众号文章、登录后可见动态页分别有真实样例。
- HTML、文字、标题、URL、时间、作者在 Vault 可追溯。
- 重复提交同一页面不会无限生成重复记忆。
- 超大页面不会导致扩展崩溃。
- 扩展权限最小化并通过 manifest smoke test。
- 不出现 Cookie、Authorization Header 或浏览器密码数据。

### 依赖

现有 `/api/share` 契约；需要变化时先提交契约文档给集成负责人。

---

## 板块 E：手机分享与设备配对

### 分支

`feature/mobile-capture`

### 独立目录

- `mobile/`
- `src/mobile_gateway/`
- `tests/test_mobile_gateway.py`
- `docs/MOBILE_CAPTURE_REPORT.md`

### 要求

1. Android 分享目标或 PWA 分享入口。
2. 支持分享链接、文字、图片、视频和文件。
3. 手机与电脑通过一次性配对码或 QR 配对。
4. 每台设备使用独立、可撤销、最小权限令牌。
5. 默认不把本机完整控制 API 暴露到公网。
6. 支持局域网或受控私有网络；公网模式必须单独设计与审核。
7. 离线缓存加密，提交成功后可清理。
8. UI 可选择项目、隐私、标签。

### 验收标准

- Android 分享链接、图片、视频各成功一次。
- 未配对设备无法访问。
- 撤销设备后旧令牌立即失效。
- 重放旧请求无法重复写入。
- 上传中断可恢复或明确失败，不产生半文件。
- 手机端不保存主控制令牌。

### 依赖

需要先完成设备令牌数据模型，由集成负责人维护 Schema。

---

## 板块 F：媒体语义自动编排

### 分支

`feature/media-semantic-pipeline`

### 独立目录

- `src/media/`
- `src/extraction/adapters/media.py`
- `scripts/process_media.py`
- `tests/test_media_*.py`
- `docs/MEDIA_SEMANTIC_PIPELINE_REPORT.md`

### 要求

1. 媒体 Worker 自动按设置执行音轨、关键帧、ASR、OCR、镜头检测。
2. Provider 懒加载，缺失时任务降级而不是崩溃。
3. 结果写入统一 Derived 目录并回填 Vault 来源文档。
4. 可暂停、恢复、取消和查看进度。
5. 模型下载目录、设备、精度、并发可配置。
6. 同一媒体哈希与相同参数不重复计算。
7. 后续可插入说话人分离和视觉模型，不改主流程。

### 验收标准

- 真实中文视频完成转写、OCR、镜头切分。
- 结果包含时间码和 Provider/模型版本。
- 关闭 Provider 后只做元数据处理。
- 中途失败后重试不会破坏已有派生文件。
- RTX 4060 与 CPU 模式分别验收。
- 不安装可选依赖时核心测试仍通过。

### 依赖

现有 Provider 与提取队列，可独立进行。

---

## 板块 G：说话人分离与视觉理解

### 分支

`feature/media-understanding`

### 独立目录

- `src/media/diarization/`
- `src/media/vision/`
- `tests/test_media_understanding.py`
- `docs/MEDIA_UNDERSTANDING_REPORT.md`

### 要求

1. 说话人分离作为可选 Provider。
2. 人物、场景、动作、镜头类型、字幕区域作为可选视觉 Provider。
3. 输出标准化 JSON，不让某个模型格式污染主流程。
4. 支持本地免费模型优先。
5. 模型不可用时不影响 ASR/OCR。
6. 生成可检索的场景级与人物级摘要。

### 验收标准

- 多人对话样例输出至少两个说话人区间。
- 视频镜头样例输出场景与动作结构。
- 所有输出有时间码、模型名、版本、置信度。
- 不把低置信度结果写成事实，必须标记待审核。
- Provider 可完全卸载。

### 依赖

板块 F 的标准语义结果契约。

---

## 板块 H：ChatGPT/Codex 大规模导入

### 分支

`feature/import-streaming-attachments`

### 独立目录

- `src/extraction/adapters/chatgpt.py`
- `src/extraction/adapters/codex.py`
- `src/importers/`
- `tests/test_import_*.py`
- `docs/IMPORT_STREAMING_ATTACHMENTS_REPORT.md`

### 要求

1. 大型单 JSON 流式读取或事件式解析。
2. 导入进度、断点、取消和重试。
3. 图片、附件、文件引用和会话关系。
4. 同一导出包重复导入保持幂等。
5. 导出包损坏、压缩炸弹、路径穿越继续阻止。
6. 不把整个大型文件一次读入内存。

### 验收标准

- 5GB 级导出包不因内存耗尽崩溃。
- 峰值内存有基准记录。
- 中途取消后可从断点继续。
- 重复导入不重复生成会话。
- 附件哈希、来源会话、原始路径可追溯。

### 依赖

现有提取队列，可独立进行。

---

## 板块 I：来源与本地媒体自动配对

### 分支

`feature/source-media-linking`

### 独立目录

- `src/linking/`
- `tests/test_source_media_linking.py`
- `docs/SOURCE_MEDIA_LINKING_REPORT.md`

### 要求

1. 基于 URL、标题、时间、作者、文件名、时长、内容哈希生成候选配对。
2. 自动配对仅在高置信度时执行。
3. 中低置信度进入人工确认列表。
4. 关系写入 Vault Frontmatter 和关系索引。
5. 人工否决后不得再次自动配对。

### 验收标准

- 至少 50 组正负样例。
- 自动配对精确率优先，目标大于 95%。
- 错误配对可一键撤销。
- 重建索引后关系仍存在。
- 不依赖付费云服务。

### 依赖

板块 D 与 F 的标准化来源、媒体元数据。

---

## 板块 J：存储调度、预警与完整恢复

### 分支

`feature/storage-operations`

### 独立目录

- `src/storage/`
- `src/scheduler/`
- `scripts/storage_*.py`
- `tests/test_storage_operations.py`
- `docs/STORAGE_OPERATIONS_REPORT.md`

### 要求

1. 定时盘点和磁盘空间预警。
2. 自动模式也必须先生成计划并留下审计。
3. Raw、Vault、Backup 永不进入自动清理。
4. 冷存储复制后校验哈希，再删除源派生文件。
5. 备份恢复先隔离，验收后才能切换。
6. 切换前自动备份当前状态。
7. 恢复失败可回滚。

### 验收标准

- 模拟低磁盘空间产生预警。
- 模拟 Derived 清理后可完整恢复。
- 模拟冷存储中断不删除源文件。
- 模拟备份损坏拒绝恢复。
- 完成一次恢复演练并记录 RTO/RPO。
- 所有危险操作有确认文字和事件日志。

### 依赖

现有 StorageLifecycleManager 与 BackupManager，可独立进行；Schema 修改需集成负责人。

---

## 板块 K：私密数据加密与权限

### 分支

`feature/private-storage-security`

### 独立目录

- `src/security/`
- `src/permissions/`
- `tests/test_private_storage_security.py`
- `docs/PRIVATE_STORAGE_SECURITY_REPORT.md`

### 要求

1. 不自行发明加密算法。
2. 使用成熟库和操作系统安全存储保存密钥。
3. 私密 Raw、附件、备份可选择加密。
4. 每台设备、每个 Agent 最小权限。
5. 支持密钥轮换、恢复密钥和吊销。
6. 日志不得泄露密钥、Token、私密正文。
7. 加密状态与解密失败必须可见。

### 验收标准

- 加密文件不能被普通文本工具读取。
- 正确密钥可完整恢复并校验哈希。
- 错误密钥不会损坏原文件。
- 密钥不进入 Git、日志、Vault Frontmatter。
- 权限测试覆盖允许与拒绝路径。
- 完成威胁模型和恢复演练。

### 依赖

先完成数据分类与权限契约；与板块 J 协调备份格式。

---

## 板块 L：项目、关系图与主动推荐

### 分支

`feature/projects-relations-recommendations`

### 独立目录

- `src/projects/`
- `src/relations/`
- `src/recommendations/`
- `tests/test_projects_relations.py`
- `docs/PROJECTS_RELATIONS_RECOMMENDATIONS_REPORT.md`

### 要求

1. 项目、任务、来源、人物、工具、模型、文件、决策统一关系模型。
2. 关系来自显式元数据、内容引用和人工确认。
3. 主动推荐必须解释“为什么推荐”。
4. 用户可关闭来源、主题和推荐频率。
5. 不自动发布，不自动执行高风险操作。
6. Obsidian 与桌面 UI 都可查看关系。

### 验收标准

- 一个真实项目可展示来源、任务、文件、决策、工具和相关记忆。
- 删除派生索引后可从 Vault 重建关系。
- 推荐附证据来源和置信度。
- 用户否决后降低或停止同类推荐。
- 关系图 5,000 节点仍可按项目筛选和局部加载。

### 依赖

稳定的 Memory、Project 与 Source 数据契约；桌面页面由板块 C 展示。

---

## 5. 推荐并行顺序

### 第一批，可立即并行

1. A：真实环境验收。
2. B：桌面打包与服务生命周期。
3. D：浏览器采集增强。
4. F：媒体语义自动编排。
5. H：ChatGPT/Codex 大规模导入。
6. J：存储调度与恢复。

这些板块目录重叠较少，但公共 API 和 Schema 仍由集成负责人统一处理。

### 第二批，依赖第一批契约

1. C：完整桌面 UI。
2. E：手机分享与设备配对。
3. G：说话人分离与视觉理解。
4. I：来源与媒体配对。
5. K：加密与权限。
6. L：项目、关系图与主动推荐。

---

## 6. 全局 Definition of Done

任何板块要标记“完成”，必须同时满足：

1. 需求范围全部实现，非目标明确记录。
2. 单元测试、集成测试、跨平台测试通过。
3. Linux Python 3.11/3.12 和 Windows Python 3.12 CI 通过。
4. 前端相关板块 `npm run build` 通过。
5. 真实样例验收，不只使用 Mock。
6. 不破坏已有 Vault、Raw、Backup。
7. 有回滚或恢复方式。
8. 有性能、资源或容量边界。
9. 安全和隐私边界经过检查。
10. 免费、本地、开源方案优先；付费 Provider 只能可选。
11. 有 `docs/<MODULE>_REPORT.md`。
12. PR 描述、测试记录、风险、已知限制完整。
13. 集成分支全量测试通过。
14. 主人可通过 UI 或明确命令使用，不要求修改源代码。

---

## 7. Codex 任务交接模板

```text
你正在开发灵机仓库 wangduoyu001/lingji。

基线分支：integration/lingji-v1
功能分支：feature/<module-name>
Worktree：../lingji-<module-name>

先做：
1. 阅读 AGENTS.md。
2. 阅读 docs/REMAINING_WORK_PARALLEL_DEVELOPMENT_PLAN.md 中对应板块。
3. 搜索并比较当前维护中的开源项目和官方文档。
4. 检查许可证、Windows 支持、离线能力、资源占用和安全边界。
5. 先写开发计划和接口契约，再实现。

限制：
- 只修改本板块负责目录。
- 不直接修改共享热点；需要接口时先写契约并交给集成负责人。
- 免费、本地、开源优先。
- 不绕过平台权限，不偷取 Cookie。
- 不自动删除 Raw、Vault、Backup。
- 不直接向 integration/lingji-v1 推送。

交付：
1. 简洁、可维护代码。
2. 完整单元测试与集成测试。
3. 真实样例验收。
4. docs/<MODULE>_REPORT.md。
5. 提交记录清晰。
6. Draft PR，Base 为 integration/lingji-v1。
7. PR 中列出需求、非目标、测试、风险、回滚方式和已知限制。
```

---

## 8. 最终合并策略

1. 当前 PR #2 先完成基线稳定与真实验收，不立即合并到旧基础。
2. 建立 `integration/lingji-v1` 作为下一阶段唯一集成入口。
3. 第一批板块独立开发、独立 PR。
4. 集成负责人逐个合并并跑全量 CI。
5. 第二批板块基于稳定契约开发。
6. 完成 Windows 安装、真实 Vault 验收、备份恢复演练后，才创建面向 `master` 的发布 PR。
7. 发布 PR 不再混入新功能，只处理集成、文档、版本号和发布检查。
