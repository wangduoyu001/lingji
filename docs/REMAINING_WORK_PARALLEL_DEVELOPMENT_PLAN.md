# 灵机后续开发、Grok 执行与 ChatGPT 验收总规范

> 计划版本：`v2.0`  
> 更新日期：`2026-07-19`  
> 仓库：`wangduoyu001/lingji`  
> 当前基线分支：`feature/extraction-hardening-web-skills-ui`  
> 当前 Draft PR：`#2`  
> 计划维护者：ChatGPT，负责规划、架构边界、审查与验收  
> 主要实现者：Grok，负责按本文件编写最少量、可维护、可测试的代码  
> 长期权威源：Obsidian Markdown  
> 状态与派生数据：SQLite 仅保存索引、任务状态、来源映射、freshness、审计和可重建缓存

---

## 0. 本文件的权威级别

本文件是灵机后续开发的唯一总计划和验收依据。

1. Grok 开发前必须完整阅读本文件和 `AGENTS.md`。
2. Grok 不得自行把本文件中的功能标记为完成。
3. 每次 Grok 推送代码后，由主人把 commit SHA 或 PR 发给 ChatGPT。
4. ChatGPT 检查 Diff、测试、CI、Demo、UI 和风险后，更新本文件中的进度与验收结论。
5. Grok 只更新对应模块的 `docs/<MODULE>_REPORT.md`，不得替代 ChatGPT 修改本总计划的验收状态。
6. 仓库代码与本文件不一致时，以 ChatGPT 最新验收结论为准；未验收代码只能标记为“待验收”。

### 状态定义

| 状态 | 含义 |
|---|---|
| `TODO` | 尚未开始 |
| `RESEARCHING` | 正在搜索、比较类似项目和官方文档 |
| `IN_PROGRESS` | 已开始实现，但尚未提交完整验收材料 |
| `REVIEW_REQUIRED` | Grok 已提交，等待 ChatGPT 审查 |
| `CHANGES_REQUIRED` | 审查未通过，需要最小修复 |
| `ACCEPTED` | 代码、测试、Demo、UI、文档全部验收通过 |
| `BLOCKED` | 被明确依赖或外部条件阻塞 |
| `DEFERRED` | 明确暂缓，只保留接口或规划 |

---

## 1. 当前真实状态

### 1.1 已具备可用基础

1. 单 Vault 长期记忆架构和统一提取管线。
2. ChatGPT 导出、Codex 工作报告、网页/社交页面、本地媒体适配器。
3. 提取队列、幂等、租约、心跳、重试、进度和失败恢复。
4. 原始快照、历史版本、人工元数据保护、敏感内容路由。
5. FFprobe/FFmpeg 元数据、音轨和关键帧派生。
6. 可选本地 Provider：faster-whisper、PaddleOCR、PySceneDetect。
7. Skill 注册表和 Obsidian 辅助入口。
8. FastAPI 独立本地控制 API。
9. React + Tauri 独立桌面控制中心首版。
10. Chrome/Edge 主动投喂扩展首版。
11. 存储盘点、可恢复清理计划、冷存储计划。
12. 校验备份、SQLite 在线快照、隔离恢复目录。
13. Vault 索引和 Memory DB 增量同步。
14. 真实环境只读验收脚本。
15. Linux Python 3.11/3.12、MCP、浏览器扩展、Obsidian 插件和桌面前端构建已具备 CI。

### 1.2 当前阻断项

1. Windows 单元测试仍存在 SQLite 文件占用问题，当前不能发布。
2. PR #2 体积过大，除 P0 阻断修复外不得继续加入新功能。
3. 真实 `E:\obsidian\本地知识库`、真实 ChatGPT 导出和真实媒体尚未完成只读验收。
4. Tauri 目前只有前端构建和壳，不是可安装、可托盘管理、可自动启动后端的正式 `LingJi.exe`。

### 1.3 已确定但尚未完整实现

1. Source Citation 来源引用和无来源结论降级。
2. Freshness 新鲜度、过期和冲突检测。
3. Section-level Markdown Write 区块级安全写入。
4. Obsidian 中 `@lingji`、`@codex` Agent 任务闭环。
5. MCP 项目上下文、任务、决策候选和 Codex 交接工具。
6. Context Packet v2。
7. PDF、Word、Excel、PowerPoint、图片和代码文件检索。
8. 类型化项目关系图。
9. 完整桌面 UI 页面和 Windows 安装生命周期。
10. 媒体语义自动编排、说话人分离和视觉理解。
11. 手机分享入口和设备配对。
12. 大型 ChatGPT/Codex 导入和附件关系。
13. 存储预警、完整恢复切换、加密和权限。
14. 活动感知、项目信号和主动推荐。

### 1.4 微信聊天记录

状态：`DEFERRED`

当前阶段不实现微信聊天解析、私聊、群聊、语音、附件或联系人导入，只预留通用来源 Provider 接口。

必须预留：

- Provider ID：`wechat_chat`
- Provider 状态：`reserved`
- 能力声明：文本、图片、音频、附件、联系人、群聊元数据
- UI 来源中心显示“微信聊天：暂缓开发 / 接口已预留”
- API 返回能力与状态，但不得提供虚假的可执行导入按钮
- 不破解微信数据库，不绕过权限，不读取用户未明确导出的聊天数据

最小预留不得新建一套连接器框架，应复用现有提取 Adapter/Registry，只增加通用能力描述和 `reserved` 状态。

---

## 2. 协作职责

### 2.1 Grok 的职责

1. 严格按本文件指定范围实现。
2. 开发前搜索并学习类似项目和官方文档。
3. 先补失败测试，再写实现。
4. 使用最少量代码完成要求。
5. 不改写与本任务无关的文件。
6. 不进行顺手重构、统一格式化、目录大搬迁或框架替换。
7. 每个功能提供最小可运行 Demo。
8. 每个功能在桌面 UI 中提供可见入口、状态、设置或操作。
9. 提交完整的修改文件清单、测试命令、测试结果、风险和回滚方式。
10. 只提交 Draft PR，不自行合并。

### 2.2 ChatGPT 的职责

1. 维护本文件。
2. 明确每阶段范围、接口、非目标和验收标准。
3. 审查 Grok 的 Diff 是否最小、是否重复实现已有功能。
4. 审查测试是否先于实现、是否只用 Mock 冒充真实验收。
5. 审查 UI 是否真正可操作，而不是后端功能藏在命令行里。
6. 检查跨平台、隐私、数据安全、回滚和长期维护风险。
7. 在验收后更新本文件状态。
8. 不通过时只要求最小修复，不鼓励重写。

### 2.3 主人的职责

1. 把 Grok 的 commit SHA、分支或 PR 发给 ChatGPT。
2. 在需要真实本机环境时运行明确命令并提供输出。
3. 对危险操作、真实数据迁移和正式决策做最终确认。

---

## 3. 强制研究门槛

任何功能开始编码前，状态必须先进入 `RESEARCHING`。

### 3.1 最低研究要求

每个模块至少研究：

1. 一个官方标准或官方开发文档。
2. 三个仍在维护的相似开源项目或公开产品设计。
3. 对每个候选记录：许可证、最近维护时间、Windows 支持、离线能力、数据格式、资源占用、安全边界。
4. 明确写出“采用什么、不采用什么、为什么”。
5. 不允许只复制 README 宣传语，不看代码结构、Issue、测试和许可证。

### 3.2 研究结果存放位置

每个模块报告必须先包含：

```text
## Research Notes
- 官方文档：
- 类似项目：
- 可借鉴设计：
- 明确拒绝的设计：
- 许可证与兼容性：
- 对 LingJi 的最小实现结论：
```

没有研究记录，不允许开始实现。

### 3.3 已确定的参考思想

- DocuSmart AI：答案引用到准确文档和区块，资料变化和过期可见。
- OpenMarkdown：原始 Markdown 不被无意义重排、修剪或格式化。
- Unabyss：统一上下文通过 MCP 服务多个 AI，用户控制来源和权限。
- Obsidian Web Clipper / Defuddle：网页正文提取和 Markdown 保真。
- Obsidian Tasks：稳定任务标识、状态和依赖，不靠重复扫描猜测任务身份。

参考链接：

- https://www.docusmart.eu/
- https://openmarkdown.dev/
- https://unabyss.com/
- https://docs.obsidian.md/
- https://github.com/obsidianmd/obsidian-clipper
- https://github.com/kepano/defuddle

---

## 4. 最小代码原则

### 4.1 禁止事项

1. 禁止重写能复用的现有模块。
2. 禁止为了统一风格改写与功能无关的文件。
3. 禁止全仓格式化。
4. 禁止复制已有 Service、Gateway、Queue、Registry、Retriever 或数据库能力。
5. 禁止创建“新版”和“旧版”并存的平行系统。
6. 禁止引入 Redis、Prometheus、Electron、Docker 主部署等当前不需要的基础设施。
7. 禁止把付费 API 设为基础必需项。
8. 禁止未经主人确认自动删除 Vault、Raw 或 Backup。
9. 禁止 UI 直接写 SQLite 或任意覆盖 Vault 文件。
10. 禁止把低置信度推断写成确定事实。

### 4.2 最小修改顺序

```text
复用现有接口
→ 增加最小字段或方法
→ 增加测试
→ 增加薄 UI
→ 增加 Demo
→ 记录报告
```

只有现有结构无法满足并且报告说明原因时，才允许新增模块。

### 4.3 依赖控制

新增依赖必须在模块报告中说明：

- 解决什么问题
- 为什么标准库或现有依赖不能解决
- 安装体积
- Windows 支持
- 许可证
- 是否可选
- 卸载后核心功能是否仍可运行

---

## 5. UI 完整性硬规则

“不要引入复杂前端”不等于“功能只藏在 API 或脚本中”。灵机桌面 UI 是主人日常管理入口。

### 5.1 每个功能必须在 UI 中至少具备

1. 可发现的导航入口或现有页面区块。
2. 当前状态。
3. 默认设置和用户覆盖值。
4. 输入校验和错误信息。
5. 执行、暂停、恢复、取消或刷新等适用操作。
6. 结果列表或结果详情。
7. 来源、时间、置信度、freshness 等适用字段。
8. 日志或失败原因。
9. 危险操作预览、确认和恢复提示。
10. 对应帮助文字，说明数据写到哪里。

### 5.2 薄 UI 原则

1. 业务逻辑全部在 Python Service/API。
2. React 只负责展示、输入、调用和反馈。
3. UI 不复制后端校验规则。
4. UI 不直接读写数据库。
5. UI 不直接整文件覆盖 Markdown。
6. 不做无意义动画、3D、复杂主题和大型可视化框架。
7. 图谱页面只加载当前项目或局部节点，不一次渲染全部知识库。

### 5.3 页面状态

每个页面必须具备：

```text
Loading
Empty
Error
Success
Disabled/Unavailable
```

### 5.4 UI 验收证据

每个功能 PR 必须提供：

- 页面路径或导航名称
- UI 截图
- 操作步骤
- 成功状态截图
- 失败状态截图
- `npm run build` 结果
- 至少一个 UI smoke test 或组件测试

没有 UI 证据的后端功能不能标记为 `ACCEPTED`，除非该功能是内部基础设施且在相关状态页中可观测。

---

## 6. Git 与 Worktree 规则

### 6.1 P0 阶段

PR #2 只允许修复 Windows、CI、生命周期和真实验收阻断，不再加入新功能。

P0 修复分支：

```text
fix/windows-db-lifecycle
```

基线：

```text
feature/extraction-hardening-web-skills-ui
```

PR Base：

```text
feature/extraction-hardening-web-skills-ui
```

P0 合并并验收后，PR #2 才能继续进入基线收口。

### 6.2 下一阶段集成分支

P0 全绿后创建：

```powershell
git fetch origin
git switch feature/extraction-hardening-web-skills-ui
git pull --ff-only origin feature/extraction-hardening-web-skills-ui
git switch -c integration/lingji-v1
git push -u origin integration/lingji-v1
```

后续所有新功能从 `integration/lingji-v1` 创建。

### 6.3 每个模块独立 Worktree

```powershell
git fetch origin
git worktree add ..\lingji-<module> `
  -b feature/<module> `
  origin/integration/lingji-v1
cd ..\lingji-<module>
```

### 6.4 同步规则

```powershell
git fetch origin
git rebase origin/integration/lingji-v1
```

禁止无意义 Merge Commit，禁止 `ours/theirs` 粗暴覆盖冲突。

### 6.5 提交格式

```text
feat(scope): 功能
fix(scope): 修复
perf(scope): 性能优化
test(scope): 测试
docs(scope): 模块报告
build(scope): 构建或依赖
```

提交应按逻辑拆分，但不得为凑数量制造几十个微小提交。

### 6.6 PR 规则

- 一个模块一个 Draft PR。
- Base 为 `integration/lingji-v1`。
- 不直接推送集成分支。
- 合并方式为 `Squash and merge`。
- PR 必须包含研究结论、目标、非目标、修改文件、接口变化、测试、Demo、UI、风险和回滚。
- CI 全绿不等于自动通过，仍需 ChatGPT 验收。

### 6.7 共享热点

以下由集成负责人统一修改，功能分支需要改动时先提交接口需求：

- `src/control/api.py`
- `src/control/service.py`
- `src/config.py`
- `src/storage/state_db.py`
- `src/retrieval/memory_db.py`
- `.github/workflows/`
- `AGENTS.md`
- 数据库 Schema 与迁移版本
- 桌面全局路由、导航和共享类型

---

## 7. 测试优先规则

### 7.1 开发顺序

```text
研究
→ 写接口契约
→ 写失败测试
→ 运行并证明测试失败
→ 最小实现
→ 运行专项测试
→ 运行全量测试
→ Demo
→ UI 验收
→ 模块报告
→ Draft PR
```

### 7.2 基础测试命令

```powershell
python -m compileall -q main.py run_service.py run_control_api.py run_mcp_server.py run_extraction_worker.py src tests scripts
python -m unittest discover -s tests -v
```

前端：

```powershell
cd desktop/lingji-control
npm install --no-audit --no-fund
npm run build
```

### 7.3 禁止的测试替代

1. 只测 Mock，不测真实文件。
2. 只测函数返回，不验证 Vault、数据库和 UI 结果。
3. 手工点一次后宣称稳定。
4. 跳过 Windows。
5. 使用不存在的成功截图或伪造测试输出。

---

## 8. 全局完成标准

任何模块标记为 `ACCEPTED`，必须同时满足：

1. 研究记录完整。
2. 范围内需求全部完成。
3. 非目标明确。
4. 先有失败测试，再有实现。
5. 单元测试和集成测试通过。
6. Linux Python 3.11/3.12 和 Windows Python 3.12 CI 通过。
7. 前端相关模块 `npm run build` 通过。
8. 至少一个真实样例 Demo。
9. UI 有入口、状态、操作和反馈。
10. 不破坏 Vault、Raw、Backup。
11. 有性能、资源和容量边界。
12. 有隐私与安全检查。
13. 有回滚或恢复方式。
14. 免费、本地、开源优先。
15. 有 `docs/<MODULE>_REPORT.md`。
16. 修改文件列表完整。
17. 失败风险和已知限制完整。
18. 集成分支全量测试通过。
19. 主人无需修改源代码即可从 UI 或明确命令使用。
20. ChatGPT 已更新本文件并标记 `ACCEPTED`。

---

# 9. 后续开发路线

## P0：Windows 生命周期与基线收口

状态：`TODO`

### 分支

`fix/windows-db-lifecycle`

### 目标

1. 修复 Windows 上 `lingji_memory.db` 被占用导致测试清理失败。
2. 为 MemoryDatabase、Gateway、Control Service 和测试对象提供显式生命周期关闭。
3. 确认后台线程、TestClient、数据库连接和临时对象全部释放。
4. 当前 PR #2 全部 CI 通过。
5. 执行真实环境只读验收。

### 最小修改范围

- `src/retrieval/memory_db.py`
- `src/gateway/memory_gateway.py`
- `src/control/service.py`
- 相关测试 teardown
- `docs/WINDOWS_DB_LIFECYCLE_REPORT.md`

不得顺手重构检索逻辑、Schema 或 UI。

### 先写测试

1. 连续创建和关闭 Gateway 20 次后数据库可删除。
2. FastAPI TestClient 关闭后数据库可删除。
3. 异常路径仍关闭连接。
4. Windows 临时目录清理成功。
5. 重复启动和关闭无残留线程。

### UI 要求

系统状态页显示：

- 数据库状态
- 打开连接数或可用的生命周期状态
- 后台服务状态
- 关闭失败原因

不需要新增复杂页面，只扩展现有系统状态。

### Demo

`scripts/demo_windows_lifecycle.py`

### 验收标准

- Windows 105 项及后续新增测试全部通过。
- 临时目录可删除。
- 连续启动/关闭 20 次无文件锁和残留线程。
- Linux 测试不回归。
- PR #2 CI 全绿。

### 风险

- 隐藏的后台线程或 SQLite WAL 连接。
- 测试对象持有循环引用。
- 关闭方法破坏长运行服务。

---

## P1-0：桌面 UI 最小模块化基础

状态：`TODO`

### 分支

`feature/ui-module-foundation`

### 目标

把当前单文件 UI 拆成最小页面、组件、Hooks 和类型结构，为后续每个功能提供独立页面文件。

### 强制限制

1. 不重新设计视觉风格。
2. 不改变现有 API 行为。
3. 不重写现有页面内容。
4. 只做移动和最小公共组件抽取。
5. 拆分前后截图和行为一致。

### 目录

```text
desktop/lingji-control/src/
├── app/
├── components/
├── pages/
├── hooks/
├── types/
└── api/
```

### 先写测试

- 每个已有导航页面可渲染。
- 刷新后路由保持。
- API 错误显示 Error 状态。
- `npm run build` 通过。

### 验收标准

- `App.tsx` 只保留应用壳和路由。
- 原有八个页面功能不减少。
- 不引入大型状态管理或 UI 框架。
- 关键页面有 smoke test。

---

## P1-A：可信引用、Freshness 与冲突

状态：`TODO`

### 分支

`feature/trust-citations-freshness`

### 目标

所有检索和上下文结果可核查，旧资料、废弃资料和冲突资料可见。

### 输出契约

每条结果必须返回：

```json
{
  "source_file": "04-Projects/LingJi/Plan.md",
  "heading": "开发计划",
  "line_range": {"start": 20, "end": 42},
  "updated_at": "2026-07-19T12:00:00",
  "source_confidence": 0.9,
  "retrieval_confidence": 0.82,
  "verification_status": "verified",
  "freshness_status": "fresh",
  "consistency_status": "normal"
}
```

### Freshness 默认规则

| 类型 | 默认天数 |
|---|---:|
| 模型价格/API 文档 | 7 |
| 平台规则 | 7 |
| 项目计划 | 14 |
| 长期原则 | 90 |

默认值必须可在 UI 中修改，可按类型、项目和单文件覆盖。

### 状态

- `fresh`
- `stale`
- `deprecated`
- `conflict`

内部应区分 freshness 和 consistency，外部可提供汇总状态。

### 无来源规则

- 没有可靠来源时返回 `verification_status=unverified`。
- 可以给建议或推测，但不得生成确定性结论。
- 冲突来源必须同时返回，不能静默选择一方。

### 最小修改范围

- `src/retrieval/citations.py`
- `src/retrieval/freshness.py`
- 现有 Memory DB、Retriever、Gateway 的最小字段扩展
- `scripts/demo_citation_search.py`
- `scripts/demo_freshness.py`
- `tests/test_source_citations.py`
- `tests/test_freshness.py`
- `docs/TRUST_CITATIONS_FRESHNESS_REPORT.md`

### UI 要求

记忆中心增加：

1. 搜索结果引用卡片。
2. 点击打开来源文件和行号。
3. Fresh/Stale/Deprecated/Conflict 筛选。
4. 待更新资料清单。
5. Freshness 规则设置。
6. 手动确认“仍有效”、标记废弃、查看冲突来源。

总览增加：

- 过期资料数量
- 冲突资料数量
- 最近检查时间

### 先写测试

1. Markdown 行号和 Heading 引用准确。
2. 文档修改后旧行号通过 chunk hash 重新定位。
3. 没有来源返回 unverified。
4. 四类默认规则正确。
5. 用户覆盖优先于默认值。
6. 冲突来源不被覆盖。
7. 删除 SQLite 后可从 Markdown 重建。

### 验收标准

- 所有检索结果字段完整。
- UI 可以查看来源和待更新清单。
- Freshness 默认值可修改和恢复默认。
- Context Packet 使用同一引用契约。
- 不重复实现现有 citation 逻辑。

### 风险

- 行号随文件变化漂移。
- 来源可信度和检索相似度混淆。
- 旧资料被错误当成错误资料。

---

## P1-B：区块级 Markdown 写入与 Agent Task

状态：`TODO`

### 分支

`feature/section-write-agent-tasks`

### 目标

AI 只能安全修改指定区块，并把 Obsidian 任务映射到 task_queue。

### 区块写入规则

1. 已存在且由主人维护的 Markdown 禁止整文件覆盖。
2. 写入必须指定 `file_path + block_id`，没有 block_id 时才允许 heading。
3. 写入必须携带 `expected_hash`。
4. 写入前生成 unified diff。
5. 目标已变化时拒绝写入并返回冲突。
6. 写入后记录 changelog 和事件日志。
7. 使用临时文件和原子替换。
8. 新建文件、自动报告、索引和用户明确批准的整文件替换除外。

### 推荐区块格式

```markdown
<!-- lingji:block project-status -->
## 项目状态
内容
<!-- /lingji:block -->
```

### Agent Task 格式

```markdown
- [ ] @lingji 整理最近决策
- [ ] @codex 修复媒体任务重试
```

完成后：

```markdown
- [x] @codex 修复媒体任务重试
  - task_id: LJ-TASK-...
  - completed_at: 2026-07-19T21:30:00+08:00
  - result_file: "[[05-Operations/Work-Reports/...]]"
  - status: completed
```

### 幂等规则

使用 `file_path + block_hash + task_text` 生成稳定任务身份。系统自己回写不得再次产生新任务。

### 最小修改范围

- `src/markdown/section_writer.py`
- `src/markdown/block_parser.py`
- `src/tasks/markdown_scanner.py`
- `src/tasks/task_service.py`
- 现有 queue/state_db 的最小扩展
- `scripts/demo_section_write.py`
- `scripts/demo_agent_tasks.py`
- `tests/test_section_writer.py`
- `tests/test_markdown_task_scanner.py`
- `tests/test_task_completion_writeback.py`
- `docs/SECTION_WRITE_AGENT_TASKS_REPORT.md`

### UI 要求

任务中心增加：

1. Markdown 任务来源、文件、行号和 Agent。
2. 待执行、执行中、完成、失败、冲突筛选。
3. Diff 预览。
4. 批准、拒绝、重试、取消。
5. 任务结果文件跳转。
6. 写回冲突提示。

记忆编辑操作增加区块 Diff 确认弹窗。

### 先写测试

1. 相同 Heading 冲突时要求 block_id。
2. expected_hash 不一致拒绝写入。
3. 写入前 diff 正确。
4. 写入后 changelog 存在。
5. 重复扫描不重复建任务。
6. 系统回写不产生循环。
7. 主人修改任务后拒绝自动勾选。
8. 非目标区块字节保持不变。

### 验收标准

- 不整文件覆盖主人维护文档。
- UI 可以预览 Diff 和冲突。
- 任务完成写回可追溯。
- 新建报告文件仍可正常工作。

### 风险

- 重复 Heading。
- 换行符和编码改变整文件。
- Watchdog 与任务回写产生循环。

---

## P1-C：MCP 项目工作流和 Context Packet v2

状态：`TODO`

### 分支

`feature/mcp-project-workflow`

### 目标

扩展现有 MCP，不创建第二套 MCP Server。

### 必须提供的工具

- `lingji.search_memory(query, project_id?)`
- `lingji.read_project_context(project_id)`
- `lingji.read_active_tasks(project_id?)`
- `lingji.write_decision(project_id, decision, source?)`
- `lingji.check_freshness(project_id?)`
- `lingji.create_codex_handoff(project_id, task_id?)`

`write_decision` 只创建 `needs_review` 的 Decision Candidate，不直接批准正式决策。

### Context Packet v2

```json
{
  "schema_version": 2,
  "user_goal": "",
  "project_status": "",
  "recent_decisions": [],
  "active_tasks": [],
  "relevant_files": [],
  "constraints": [],
  "next_action": "",
  "citations": [],
  "freshness_summary": {},
  "unverified_claims": [],
  "memory_revision": 0
}
```

### UI 要求

项目中心增加：

1. Context Packet 预览。
2. 选择目标 Agent：Codex、Claude、ChatGPT、其他 MCP 客户端。
3. 复制、导出和刷新。
4. 显示引用、过期、冲突和未验证内容。
5. 创建 Codex Handoff。
6. 最近生成记录。

### 先写测试

1. 六个工具可创建并调用。
2. Agent 权限限制生效。
3. Decision 只进入待审核。
4. Packet 字段完整且有引用。
5. 过期资料和冲突进入警告区。
6. 超出上下文预算时按优先级截断。

### 验收标准

- 不新建平行 Gateway。
- UI 可预览和导出 Packet。
- Codex Handoff 可追溯到任务和来源。
- 所有确定性信息有来源。

---

## P2-A：电脑本地文件检索

状态：`TODO`

### 分支

`feature/local-document-search`

### 目标

索引白名单目录中的 PDF、Word、Excel、PowerPoint、图片和代码文件，并精确定位到页码、标题、单元格、幻灯片或代码行。

### 目录建议

```text
src/local_files/
├── catalog.py
├── watcher.py
├── search.py
├── dedup.py
├── versioning.py
└── parsers/
```

### 支持顺序

1. PDF 文本和页码。
2. DOCX 标题和段落。
3. XLSX 工作表和单元格范围。
4. PPTX 幻灯片和备注。
5. 图片 OCR。
6. 常见代码和纯文本。
7. 扫描 PDF OCR 作为可选 Provider。

### 数据原则

- 外部文件保持原位置，不强制复制进 Vault。
- Vault 保存文件卡片和关系。
- SQLite 保存目录目录、哈希、解析状态、Chunk 和定位信息。
- 文件内容变化时增量更新。
- 白名单之外不扫描。

### UI 要求

文件检索页面必须有：

1. 白名单目录管理。
2. 扫描、暂停、重建、移除索引。
3. 文件类型和状态筛选。
4. 搜索结果和位置跳转。
5. 解析失败列表。
6. 大文件、重复文件和版本状态。
7. 与项目关联或取消关联。
8. OCR Provider 设置。

### 先写测试

- 每种格式至少一个真实样例。
- 引用定位准确。
- 修改文件后只更新该文件。
- 删除源文件后标记 missing，不删除历史关系。
- 同哈希文件去重。
- 目录逃逸和软链接边界阻止。
- 10,000 文件目录扫描不崩溃。

### 验收标准

- 文件名和正文统一搜索。
- 所有结果有标准 Citation Locator。
- UI 可管理目录、扫描和错误。
- 不复制大文件到 Vault。

### 风险

- Office 文件解析库体积。
- 扫描 PDF OCR 资源占用。
- Windows 文件锁和路径长度。

---

## P2-B：项目中心、类型化关系和局部关系图

状态：`TODO`

### 分支

`feature/projects-typed-relations`

### 目标

建立可重建、可确认、可拒绝、可追溯的类型化关系。

### 关系字段

```text
relation_id
source_entity_id
relation_type
target_entity_id
confidence
relation_status
source_memory_id
created_by
confirmed_by
created_at
updated_at
```

SQLite 保存派生关系索引，Obsidian Frontmatter 和正式项目 Markdown 保持长期权威。

### 关系类型首版

- project_contains_file
- project_has_task
- project_has_decision
- source_supports_decision
- task_uses_tool
- conversation_produced_artifact
- memory_mentions_entity
- file_related_to_source

### UI 要求

项目中心必须有：

1. 项目列表和项目详情。
2. 目标、状态、任务、决策、文件、来源、工具和模型。
3. 一层关系图和按需展开。
4. 关系来源、置信度和确认状态。
5. 接受、拒绝和撤销关系。
6. 冲突关系提示。
7. 创建 Context Packet 和 Codex Handoff。

### 先写测试

- 关系可从 Vault 重建。
- 主人拒绝后不会再次自动建立。
- 删除派生数据库后关系可恢复。
- 关系类型不在双向写入时丢失。
- 5,000 节点可按项目局部加载。

### 验收标准

- 不再只保存模糊 `related`。
- UI 可查看和管理关系。
- AI 推断与主人确认明确区分。

---

## P2-C：媒体语义自动编排

状态：`TODO`

### 分支

`feature/media-semantic-pipeline`

### 目标

把现有 FFmpeg、ASR、OCR、镜头检测 Provider 接入统一 Worker。

### 要求

1. 按 UI 设置执行音轨、关键帧、ASR、OCR、镜头检测。
2. Provider 懒加载，缺失时降级。
3. 同一媒体哈希和相同参数不重复计算。
4. 支持暂停、恢复、取消和进度。
5. 关键帧数量、分辨率、FFmpeg 并发、threads、输入大小、最大时长、任务优先级都可在 UI 设置，有默认值。
6. 结果有时间码、模型、版本和置信度。
7. 后续可插入说话人分离和视觉模型，不改主流程。

### UI 要求

媒体中心显示：

- 队列和进度
- 资源设置
- Provider 状态
- 转写、OCR、镜头结果
- 时间线
- 失败重试
- 派生文件位置

### 验收标准

- 真实中文视频完成自动处理。
- RTX 4060 和 CPU 模式分别验收。
- 不安装可选依赖时核心服务仍运行。
- UI 全部参数可修改、恢复默认并校验。

---

## P2-D：Windows 桌面打包和服务生命周期

状态：`TODO`

### 分支

`feature/desktop-packaging`

### 目标

生成可安装的 Windows LingJi 控制中心。

### 要求

1. Tauri Windows 安装包。
2. 启动时检测或启动本机 FastAPI 服务。
3. 默认只绑定 `127.0.0.1`。
4. 本机令牌不明文展示。
5. 托盘、退出、重启服务、打开日志目录。
6. 崩溃恢复和端口占用提示。
7. 卸载不删除 Vault、Raw、Backup。
8. 升级不覆盖运行时设置。

### UI 要求

设置/系统页面显示：

- 后端路径和版本
- 服务状态
- 端口
- 开机启动
- 日志目录
- 更新状态
- 重启和诊断

### 验收标准

- Windows 10/11 安装、启动、退出、卸载通过。
- 连续启动和退出 20 次无残留进程。
- 未安装 Python 时有明确可执行方案。
- Vault 哈希不变。

---

## P3-A：浏览器采集增强

状态：`TODO`

### 分支

`feature/browser-capture-v2`

### 要求

1. 页面、选中文字、主要正文、完整 HTML 快照。
2. 可选截图和元数据。
3. 项目、标签、隐私选择。
4. 公众号、视频号、抖音、小红书站点增强。
5. 不读取或上传 Cookie。
6. 不绕过登录和反爬。
7. 超大页面分块或保存本地快照。
8. 离线队列由用户确认重试。

### UI 要求

来源中心显示：

- 浏览器扩展连接状态
- 最近投喂
- 等待补充正文的来源
- 重复来源
- 失败原因
- 项目和隐私归属

### 验收标准

- 普通网页、公众号和登录后可见动态页有真实样例。
- 来源可追溯。
- 不泄露 Cookie、Authorization 或密码数据。

---

## P3-B：手机分享和设备配对

状态：`TODO`

### 分支

`feature/mobile-capture`

### 要求

1. Android 分享目标或 PWA。
2. 支持链接、文字、图片、视频和文件。
3. 一次性配对码或 QR。
4. 每台设备独立可撤销令牌。
5. 不暴露完整控制 API 到公网。
6. 上传中断可恢复。

### UI 要求

设备与权限页面显示：

- 已配对设备
- 最后活动
- 权限范围
- 撤销
- 配对码
- 上传任务

### 验收标准

- 链接、图片、视频各成功一次。
- 未配对设备拒绝。
- 撤销后旧令牌失效。

---

## P3-C：大型 ChatGPT/Codex 导入和附件

状态：`TODO`

### 分支

`feature/import-streaming-attachments`

### 要求

1. 大型 JSON 流式解析。
2. 进度、取消、断点和重试。
3. 图片、附件、文件和会话关系。
4. 重复导入幂等。
5. 压缩炸弹、路径穿越和损坏包继续阻止。

### UI 要求

导入中心显示：

- 文件选择
- 预计大小
- 进度和峰值内存
- 会话数量
- 附件数量
- 错误和恢复
- 项目归属

### 验收标准

- 5GB 级导出包不因内存耗尽崩溃。
- 重复导入不重复生成。
- 附件和来源会话可追溯。

---

## P3-D：存储调度、完整恢复、加密与权限

状态：`TODO`

### 分支

`feature/storage-security-operations`

### 要求

1. 定时盘点和低磁盘预警。
2. 自动模式仍先生成计划和审计。
3. Raw、Vault、Backup 永不自动清理。
4. 冷存储复制后校验哈希再移除源派生文件。
5. 隔离恢复验收后才能切换。
6. 切换前自动备份当前状态。
7. 恢复失败可回滚。
8. 私密 Raw 和备份可选加密。
9. 密钥使用系统安全存储，不进入 Git、日志和 Frontmatter。

### UI 要求

存储与隐私页面必须有：

- 容量和增长趋势
- 保留时间、阈值、冷存储路径
- 清理预览
- 恢复演练
- 加密状态
- 密钥轮换和恢复提示
- 权限审计

### 验收标准

- 模拟低空间产生预警。
- 清理可恢复。
- 冷存储中断不删源文件。
- 损坏备份拒绝恢复。
- 完成一次 RTO/RPO 演练。

---

## P4-A：工作活动感知

状态：`TODO`

### 分支

`feature/activity-signals`

### 允许采集

- 软件名称和版本
- 软件使用时长
- 项目文件变化
- Git 活动
- 软件安装、卸载和更新
- 任务执行状态

### 禁止采集

- 全局键盘输入
- 密码和验证码
- 持续录屏
- 未授权私人聊天正文
- 浏览器密码和 Cookie

### UI 要求

活动页面显示：

- 今日/本周活动
- 项目归属
- 软件清单
- Git 和文件变化
- 隐私模式
- 数据保留设置

### 验收标准

- 用户可暂停采集和删除派生活动记录。
- 隐私模式立即停止。
- 不采集禁止内容。

---

## P4-B：主动推荐和视野扩展

状态：`TODO`

### 分支

`feature/horizon-recommendations`

### 要求

1. Interest Profile 兴趣模型。
2. Project Signals 项目信号。
3. Horizon Engine 视野扩展。
4. Recommendation Feedback 推荐反馈。
5. 推荐必须说明来源、原因、项目关联、新增信息、可信度和建议动作。
6. 用户可关闭来源、主题和频率。
7. 不自动发布，不自动执行高风险动作。

### UI 要求

推荐中心显示：

- 推荐卡片
- 为什么推荐
- 证据来源
- freshness 和 confidence
- 接受、忽略、不再推荐
- 关联项目
- 推荐频率设置

### 验收标准

- 每条推荐有来源和解释。
- 用户否决后降低同类推荐。
- 冲突或过期资料明确标记。
- 不依赖付费服务作为基础能力。

---

## 10. 推荐开发顺序

### 第一阶段：必须串行完成

1. P0 Windows 生命周期和 CI 全绿。
2. 真实环境只读验收。
3. 创建 `integration/lingji-v1`。
4. P1-0 UI 最小模块化。

### 第二阶段：可以并行

1. P1-A 可信引用与 Freshness。
2. P1-B 区块写入与 Agent Task。
3. P2-D Windows 桌面打包。
4. P2-C 媒体语义自动编排。

P1-A 与 P1-B 需要共享数据库字段时，先由集成负责人合入最小 Schema。

### 第三阶段

1. P1-C MCP 项目工作流和 Context Packet v2。
2. P2-A 本地文件检索。
3. P2-B 项目和类型化关系。
4. P3-A 浏览器采集增强。

### 第四阶段

1. P3-B 手机分享。
2. P3-C 大型导入。
3. P3-D 存储、安全和完整恢复。
4. 媒体高级理解。

### 第五阶段

1. P4-A 活动感知。
2. P4-B 主动推荐和视野扩展。
3. 微信聊天保持 `DEFERRED`，只保留 Provider 接口。

---

## 11. Grok 每次交付格式

Grok 完成一个模块或一次可验收增量后，必须原样输出以下内容：

```text
模块：
分支：
Commit SHA：
Draft PR：

研究：
- 官方文档：
- 类似项目：
- 采用：
- 拒绝：

修改文件：
- path：修改原因

未修改但复用的文件：
- path：复用方式

测试优先证据：
- 先新增的失败测试：
- 实现前失败输出：
- 实现后通过输出：

测试命令：
- command

测试结果：
- Linux 3.11：
- Linux 3.12：
- Windows 3.12：
- UI build：

Demo：
- 命令：
- 输入：
- 输出：

UI：
- 页面：
- 操作步骤：
- 成功截图：
- 失败截图：

风险：
- 

已知限制：
- 

回滚方式：
- 

自检结论：
- 是否只修改本模块：
- 是否有无关格式化：
- 是否重复实现已有能力：
- 是否增加不必要依赖：
- 是否满足 UI 要求：
```

缺少任何一项，状态保持 `REVIEW_REQUIRED`，不能验收。

---

## 12. ChatGPT 验收流程

收到 Grok 的 commit 或 PR 后，ChatGPT 按以下顺序执行：

1. 核对基线分支和 Worktree 规则。
2. 查看完整 Diff 和修改文件。
3. 检查是否有无关改写、重复实现和依赖膨胀。
4. 核对研究记录是否真实、有用。
5. 检查测试是否覆盖失败路径和 Windows。
6. 检查 Demo 是否最小可运行。
7. 检查 UI 是否有入口、状态、操作、错误和设置。
8. 检查数据是否仍以 Obsidian Markdown 为长期权威。
9. 检查 SQLite 是否只保存派生和运行状态。
10. 检查隐私、安全、回滚和恢复。
11. 更新本文件状态为 `ACCEPTED`、`CHANGES_REQUIRED` 或 `BLOCKED`。
12. 提交独立的 `docs(plan): update acceptance status for <module>` 文档提交。

---

## 13. 当前下一项任务

当前唯一允许 Grok 立即开始的代码任务：

```text
P0：fix/windows-db-lifecycle
```

开始前必须：

1. 搜索 SQLite Python Windows 文件锁、FastAPI TestClient 生命周期、context manager 和线程关闭的官方资料及高质量案例。
2. 只修连接和对象释放。
3. 先补失败测试。
4. 不修改 Schema。
5. 不新增 UI 页面，只在现有系统状态增加最小数据库生命周期状态。
6. 提交 `docs/WINDOWS_DB_LIFECYCLE_REPORT.md`。
7. 提交 Draft PR，Base 为 `feature/extraction-hardening-web-skills-ui`。

P0 未被 ChatGPT 标记为 `ACCEPTED` 前，其他板块只允许研究和写接口契约，不允许合入实现代码。
