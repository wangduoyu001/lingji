# 灵机后续开发、实施与验收总计划

> 计划版本：`v2.1`  
> 更新日期：`2026-07-19`  
> 仓库：`wangduoyu001/lingji`  
> 当前基线：`feature/extraction-hardening-web-skills-ui`  
> 当前修复 PR：`#3 fix/windows-db-lifecycle`  
> 计划维护者：ChatGPT，负责需求、架构边界、代码审查、CI 与验收  
> 长期权威源：Obsidian Markdown  
> SQLite 定位：索引、任务状态、来源映射、Freshness、审计和可重建派生缓存

---

## 0. 本文件的使用规则

本文件是灵机后续开发的唯一总计划、状态表和验收入口。

1. 每次代码更新后，必须在本文件追加或更新一次真实状态。
2. 任何功能只有经过 Diff、测试、CI、Demo、UI 和风险审查后才能标记为 `ACCEPTED`。
3. 未验收代码只能标记为 `REVIEW_REQUIRED` 或 `CHANGES_REQUIRED`。
4. 功能报告放在 `docs/<MODULE>_REPORT.md`，本文件只保存权威状态、范围和验收结果。
5. Obsidian Markdown 始终是长期权威内容；SQLite 数据必须可删除、可重建。
6. 所有主人需要手动使用的能力必须在独立桌面 UI 中有入口、状态、设置和结果展示。
7. 不为展示“先进”而引入复杂前端、重复网关、重复队列或大型基础设施。

### 状态定义

| 状态 | 含义 |
|---|---|
| `TODO` | 尚未开始 |
| `RESEARCHING` | 正在研究官方文档和类似项目 |
| `IN_PROGRESS` | 已开始实现 |
| `REVIEW_REQUIRED` | 已提交，等待审查 |
| `CHANGES_REQUIRED` | 审查未通过，需要最小修复 |
| `ACCEPTED` | 代码、测试、CI、Demo、UI 和文档全部通过 |
| `BLOCKED` | 被依赖或外部条件阻塞 |
| `DEFERRED` | 暂缓，只保留接口和规划 |

---

# 1. 当前真实状态

## 1.1 已具备的基础

1. 单 Vault 长期记忆架构。
2. ChatGPT 导出、Codex 工作报告、网页和社交页面、本地媒体适配器。
3. 提取队列、幂等、租约、心跳、重试、进度和失败恢复。
4. Raw 原始快照、历史版本、人工元数据保护和敏感内容路由。
5. FFprobe/FFmpeg 元数据、音轨和关键帧派生。
6. 可选本地 Provider：faster-whisper、PaddleOCR、PySceneDetect。
7. Skill 注册表和 Obsidian 辅助入口。
8. FastAPI 独立本地控制 API。
9. React + Tauri 桌面控制中心首版。
10. Chrome/Edge 主动投喂扩展首版。
11. 存储盘点、可恢复清理计划和冷存储计划。
12. 校验备份、SQLite 在线快照和隔离恢复目录。
13. Vault 索引和 Memory DB 增量同步。
14. 真实环境只读验收脚本。
15. Linux Python 3.11/3.12、Windows Python 3.12、MCP、浏览器扩展、Obsidian 插件和桌面前端 CI。

## 1.2 当前发布阻断

1. 真实 `E:\obsidian\本地知识库` 尚未执行只读验收。
2. 真实 ChatGPT 导出包和真实媒体尚未执行脱敏验收。
3. Tauri 仍不是完整可安装、可托盘管理、可自动启动后端的正式 `LingJi.exe`。
4. PR #2 体积过大，禁止继续直接堆叠新功能。
5. PR #3 必须先合入基线，随后创建 `integration/lingji-v1`。

Windows SQLite 文件锁不再是当前阻断；P0 已通过 CI 验收。

## 1.3 功能完成度判断

| 板块 | 状态 | 说明 |
|---|---|---|
| 单 Vault 记忆底座 | 已有基础 | 仍需可信引用和 Freshness |
| ChatGPT/Codex 导入写回 | 已有基础 | 大型流式导入和附件关系未完成 |
| 网页主动采集 | 首版 | HTML、截图、离线队列和站点增强未完成 |
| 媒体处理 | 首版 | Provider 已有，自动编排和高级理解未完成 |
| 桌面控制中心 | 原型 | 页面、打包、服务生命周期未完成 |
| 本地文件检索 | TODO | PDF、Office、图片和代码检索未完成 |
| 项目关系图 | TODO | 类型化关系和项目详情页未完成 |
| 手机入口 | TODO | 分享、配对、权限和断点上传未完成 |
| 活动感知 | TODO | 只允许低侵入信号，禁止键盘记录 |
| 主动推荐 | TODO | 需要项目状态和可信来源作为前置 |
| 微信聊天 | DEFERRED | 只预留 Provider 接口 |

---

# 2. 最近验收记录

## 2.1 P0 Windows DB Lifecycle Fix

状态：`ACCEPTED`

- 分支：`fix/windows-db-lifecycle`
- Draft PR：`#3`
- 验收 Head：`78f044fda3149f01cf27fa1bc003873ca8ece69c`
- GitHub Actions Run：`29690940470`
- Windows Python 3.12：`108 tests / OK`
- Ubuntu Python 3.11：成功
- Ubuntu Python 3.12：成功
- MCP smoke：成功
- Browser capture smoke：成功
- Obsidian plugin smoke：成功
- Desktop UI build：成功
- 详细报告：`docs/WINDOWS_DB_LIFECYCLE_REPORT.md`

### 根因

1. 两个测试使用 `with sqlite3.connect(...)`，只提交或回滚事务，没有关闭连接；Windows 删除临时数据库时产生 `WinError 32`。
2. `CronScheduler.stop()` 不等待轮询线程和执行器退出，后台任务仍可能访问 `state.db`。
3. FastAPI 测试未通过 `TestClient` 上下文运行完整生命周期。

### 已验收修改

- 直接 SQLite 测试连接使用 `contextlib.closing()`。
- 调度器使用停止事件、线程 join、`executor.shutdown(wait=True)`。
- TestClient 在临时目录删除前退出生命周期上下文。
- 新增真实数据库、调度器和 TestClient 文件删除测试。
- Demo 调用真实 LingJi 类，失败时返回非零退出码。
- 未修改 Schema，未引入新依赖，未重构检索。

### 下一动作

1. 将 PR #3 合入 `feature/extraction-hardening-web-skills-ui`。
2. 在最新基线再次确认 PR #2 CI 全绿。
3. 执行真实环境只读验收。
4. 创建 `integration/lingji-v1`。
5. 开始 P1-0 UI 模块化基础。

---

# 3. 强制开发原则

## 3.1 开发前研究

每个模块编码前至少完成：

1. 一个官方标准或官方文档。
2. 三个仍在维护的类似开源项目或公开产品。
3. 检查许可证、维护状态、Windows、离线能力、数据格式、资源占用和安全边界。
4. 写明采用什么、拒绝什么、为什么。
5. 不得只抄 README 宣传词。

模块报告必须先包含：

```text
## Research Notes
- 官方文档：
- 类似项目：
- 可借鉴设计：
- 明确拒绝的设计：
- 许可证与兼容性：
- 对 LingJi 的最小实现结论：
```

## 3.2 测试优先

```text
研究
→ 明确接口与非目标
→ 写失败测试
→ 证明测试在实现前失败
→ 最小实现
→ 专项测试
→ 全量测试
→ Demo
→ UI 验收
→ 模块报告
→ Draft PR
```

禁止：

- `assertTrue(True)` 一类无效测试。
- 固定打印成功的 Demo。
- 只测 Mock，不验证真实文件和真实写入结果。
- 跳过 Windows。
- 伪造 CI、截图或运行结果。

## 3.3 最小修改

1. 优先复用现有 Service、Gateway、Queue、Registry、Retriever 和数据库层。
2. 不改无关文件，不全仓格式化。
3. 不创建“旧版/新版”平行系统。
4. 不引入 Redis、Prometheus、Electron 或 Docker 主部署。
5. 付费 API 只能是可选 Provider。
6. 不因顺手优化重构稳定模块。
7. 新依赖必须说明用途、体积、许可证、Windows 支持和卸载影响。

推荐顺序：

```text
复用现有接口
→ 增加最小字段或方法
→ 增加测试
→ 增加薄 UI
→ 增加 Demo
→ 记录报告
```

## 3.4 数据安全

1. Vault、Raw 和 Backup 默认永不自动删除。
2. 危险操作必须先生成预览，再确认，再执行，并可恢复。
3. UI 不直接写 SQLite。
4. AI 不允许整文件覆盖主人维护的 Markdown。
5. AI 不允许直接批准正式决策。
6. SQLite 表必须属于索引、状态、映射、审计或可重建派生数据。
7. 不保存浏览器 Cookie、密码、验证码或全局键盘输入。

---

# 4. UI 完整性要求

“薄 UI”不等于“只有命令行”。凡是主人需要手动操作的功能，都必须在独立桌面 UI 中显示。

每个功能至少具备：

1. 可发现的导航入口或现有页面区块。
2. Loading、Empty、Error、Success、Disabled/Unavailable 状态。
3. 当前状态和最近更新时间。
4. 默认设置与用户覆盖值。
5. 输入校验和明确错误。
6. 适用的执行、暂停、恢复、取消、刷新或重试按钮。
7. 结果列表与详情。
8. 来源、时间、置信度、Freshness 和冲突状态。
9. 失败原因与日志入口。
10. 危险操作预览、确认和恢复提示。
11. 数据写入位置说明。

前端边界：

- 业务逻辑全部在 Python Service/API。
- React 只负责展示、输入、调用和反馈。
- UI 不复制后端校验规则。
- UI 不直接读写数据库和 Markdown。
- 不增加无意义动画、3D 或大型前端框架。
- 关系图只加载当前项目局部节点。

UI PR 必须提供：

- 页面路径。
- 操作步骤。
- 成功与失败状态截图。
- `npm run build` 结果。
- 至少一个组件测试或 smoke test。

---

# 5. Git 与并行开发规则

## 5.1 集成分支

P0 合入并完成真实环境只读验收后创建：

```powershell
git fetch origin
git switch feature/extraction-hardening-web-skills-ui
git pull --ff-only origin feature/extraction-hardening-web-skills-ui
git switch -c integration/lingji-v1
git push -u origin integration/lingji-v1
```

后续所有新功能从 `integration/lingji-v1` 创建。

## 5.2 Worktree

```powershell
git fetch origin
git worktree add ..\lingji-<module> `
  -b feature/<module> `
  origin/integration/lingji-v1
```

同步基线：

```powershell
git fetch origin
git rebase origin/integration/lingji-v1
```

## 5.3 PR

- 一个模块一个 Draft PR。
- Base 为 `integration/lingji-v1`。
- 不直接推送集成分支。
- 合并方式为 Squash and merge。
- PR 写明研究、目标、非目标、修改文件、接口、测试、Demo、UI、风险和回滚。
- CI 全绿不代表自动通过，仍需验收。

## 5.4 共享热点

以下文件原则上由集成负责人统一修改：

- `src/control/api.py`
- `src/control/service.py`
- `src/config.py`
- `src/storage/state_db.py`
- `src/retrieval/memory_db.py`
- `.github/workflows/`
- `AGENTS.md`
- 数据库 Schema 和迁移版本
- 桌面全局路由、导航和共享类型

## 5.5 推荐并行度

基础稳定前：

```text
1 个主线编码任务
+ 2 个独立编码任务
+ 1～2 个研究任务
```

稳定后最多同时推进五个模块。禁止多个分支同时改同一 Schema、控制 API 或全局导航。

---

# 6. 全局验收标准

任何模块标记为 `ACCEPTED` 必须满足：

1. 研究记录完整。
2. 目标和非目标明确。
3. 有实现前失败测试。
4. 单元测试和集成测试通过。
5. Ubuntu Python 3.11/3.12 通过。
6. Windows Python 3.12 通过。
7. 前端模块 `npm run build` 通过。
8. 至少一个真实样例 Demo。
9. UI 有入口、状态、操作和错误反馈。
10. 不破坏 Vault、Raw 和 Backup。
11. 有性能、资源和容量边界。
12. 有隐私和安全检查。
13. 有回滚或恢复方式。
14. 免费、本地、开源优先。
15. 有 `docs/<MODULE>_REPORT.md`。
16. 修改文件和复用文件清单完整。
17. 已知限制完整。
18. 集成分支全量 CI 通过。
19. 主人无需修改源代码即可使用。
20. 本文件已记录验收结论。

基础命令：

```powershell
python -m compileall -q main.py run_service.py run_control_api.py run_mcp_server.py run_extraction_worker.py src tests scripts
python -m unittest discover -s tests -v

cd desktop/lingji-control
npm install --no-audit --no-fund
npm run build
```

---

# 7. 后续模块计划

## P0-B：真实环境只读验收

状态：`TODO`

分支：`test/real-environment-acceptance`

目标：

- 对真实 Vault、ChatGPT 导出、Ollama、FFmpeg 和样例媒体执行只读检查。
- 不移动、不删除、不覆盖真实数据。
- 输出 JSON 和 Markdown 报告。

UI：

- 系统诊断页显示验收项、状态、警告、失败原因和报告路径。
- 提供“开始只读验收”和“打开报告目录”。

验收：

1. `E:\obsidian\本地知识库` 快照或只读副本通过。
2. 真实 ChatGPT 导出识别成功。
3. 真实媒体信息和资源边界可测。
4. 不产生 Vault 内容变化。
5. 报告包含环境版本、路径、容量和风险。

非目标：

- 不自动迁移。
- 不自动修复真实数据。
- 不上传任何内容。

---

## P1-0：桌面 UI 最小模块化

状态：`TODO`

分支：`feature/ui-module-foundation`

目标：

- 将巨型 `App.tsx` 拆为 app、pages、components、hooks、types、api。
- 保持现有视觉和行为不变。
- 为后续页面并行开发建立稳定边界。

UI 验收：

1. 原有八个页面全部可渲染。
2. `App.tsx` 只保留应用壳和路由。
3. Loading、Empty、Error 状态不丢失。
4. 不引入大型状态管理或 UI 框架。
5. `npm run build` 和页面 smoke test 通过。

---

## P1-A：可信引用、Freshness 与冲突

状态：`TODO`

分支：`feature/trust-citations-freshness`

输出契约：

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

默认有效期：

| 类型 | 天数 |
|---|---:|
| 模型价格/API 文档 | 7 |
| 平台规则 | 7 |
| 项目计划 | 14 |
| 长期原则 | 90 |

规则：

- 默认值可在 UI 修改，可按类型、项目、文件覆盖。
- 没有可靠来源时标记 `unverified`。
- 无来源内容只能作为建议或推测，不能写成确定事实。
- 冲突来源必须并列返回。
- 行号变化时通过 heading 和 chunk hash 重新定位。
- `freshness_status` 与 `consistency_status` 内部分开保存。

UI：

- 记忆搜索结果引用卡片。
- 打开来源文件和定位。
- Fresh/Stale/Deprecated/Conflict 筛选。
- 待更新资料清单。
- Freshness 规则设置。
- 手动确认仍有效、标记废弃和查看冲突。
- 总览显示过期、冲突数量和最近检查时间。

验收：

1. 每条检索结果字段完整。
2. 无来源稳定降级。
3. 默认和覆盖规则正确。
4. 冲突不被静默覆盖。
5. Context Packet 使用同一契约。
6. 删除 SQLite 后可从 Markdown 重建。
7. 不重复实现已有 citation 逻辑。

---

## P1-B：区块级 Markdown 写入与 Agent Task

状态：`TODO`

分支：`feature/section-write-agent-tasks`

区块写入：

- 已存在且由主人维护的 Markdown 禁止整文件覆盖。
- 写入指定 `file_path + block_id`，没有 block_id 时才使用 heading。
- 写入携带 `expected_hash`。
- 写入前生成 unified diff。
- 哈希变化时拒绝写入并提示冲突。
- 临时文件写入后原子替换。
- 写入后记录 changelog 和事件。
- 新建文件、自动报告、索引和主人明确批准的整文件替换除外。

推荐格式：

```markdown
<!-- lingji:block project-status -->
## 项目状态
内容
<!-- /lingji:block -->
```

Agent Task：

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

幂等身份：`file_path + block_hash + task_text`。

UI：

- 任务来源、文件、行号、Agent。
- 待执行、执行中、完成、失败和冲突筛选。
- Diff 预览、批准、拒绝、重试和取消。
- 结果文件跳转。
- 写回冲突提示。

验收：

1. 重复 heading 要求 block_id。
2. expected_hash 不一致拒绝写入。
3. 非目标区块字节保持不变。
4. 重复扫描不重复建任务。
5. 系统回写不形成循环。
6. 主人修改任务后不自动勾选。

---

## P1-C：MCP 项目工作流与 Context Packet v2

状态：`TODO`

分支：`feature/mcp-project-workflow`

只扩展现有 MCP，不创建第二套服务器。

工具：

- `lingji.search_memory(query, project_id?)`
- `lingji.read_project_context(project_id)`
- `lingji.read_active_tasks(project_id?)`
- `lingji.write_decision(project_id, decision, source?)`
- `lingji.check_freshness(project_id?)`
- `lingji.create_codex_handoff(project_id, task_id?)`

`write_decision` 只创建 `needs_review` 的 Decision Candidate。

Context Packet v2：

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

UI：

- 项目上下文包预览。
- Codex、Claude、ChatGPT 和其他 MCP 客户端选择。
- 复制、导出、刷新和生成 Handoff。
- 显示引用、过期、冲突和未验证内容。
- 最近生成记录。

验收：

1. 六个工具可调用。
2. Agent 权限生效。
3. Decision 只进入待审核。
4. Packet 字段完整并有来源。
5. 过期和冲突进入警告区。
6. 超出预算时按优先级截断。

---

## P2-A：电脑本地文件检索

状态：`TODO`

分支：`feature/local-document-search`

支持顺序：

1. PDF 文本和页码。
2. DOCX 标题和段落。
3. XLSX 工作表和单元格范围。
4. PPTX 幻灯片和备注。
5. 图片 OCR。
6. 代码和纯文本。
7. 扫描 PDF OCR 作为可选 Provider。

数据原则：

- 外部文件保持原位置。
- Vault 保存文件卡片和正式关系。
- SQLite 保存目录、哈希、解析状态、Chunk 和定位信息。
- 白名单之外不扫描。
- 文件变化增量更新。
- 删除源文件标记 missing，不删除历史关系。

UI：

- 白名单目录管理。
- 扫描、暂停、重建和移除索引。
- 文件类型和状态筛选。
- 文件名和正文统一搜索。
- 页码、工作表、幻灯片和代码行跳转。
- 解析失败、大文件、重复和版本状态。
- 项目关联和 OCR Provider 设置。

验收：

1. 每种格式至少一个真实样例。
2. 引用定位准确。
3. 修改文件只更新自身。
4. 同哈希文件去重。
5. 防止目录逃逸和未授权软链接。
6. 10,000 文件目录扫描不崩溃。
7. 不复制大文件进 Vault。

---

## P2-B：项目中心、类型化关系和局部关系图

状态：`TODO`

分支：`feature/projects-typed-relations`

关系字段：

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

首版关系类型：

- project_contains_file
- project_has_task
- project_has_decision
- source_supports_decision
- task_uses_tool
- conversation_produced_artifact
- memory_mentions_entity
- file_related_to_source

UI：

- 项目列表和项目详情。
- 目标、状态、任务、决策、文件、来源、工具和模型。
- 一层关系图和按需展开。
- 关系来源、置信度和确认状态。
- 接受、拒绝和撤销关系。
- 冲突提示。
- Context Packet 和 Codex Handoff。

验收：

1. 关系可从 Vault 重建。
2. 主人拒绝后不再次自动建立。
3. 关系类型在双向写入时不丢失。
4. AI 推断和主人确认明确区分。
5. 5,000 节点按项目局部加载。

---

## P2-C：媒体语义自动编排

状态：`TODO`

分支：`feature/media-semantic-pipeline`

目标：

- 把 FFmpeg、ASR、OCR 和镜头检测 Provider 接入统一 Worker。
- Provider 懒加载，缺失时降级。
- 同媒体哈希和参数不重复计算。
- 支持暂停、恢复、取消和进度。
- 保存时间码、模型、版本和置信度。

UI 参数必须可调并有默认值：

- 最大关键帧：500。
- 关键帧最大尺寸：1280。
- FFmpeg 并发。
- FFmpeg threads。
- 最大输入大小。
- 最大时长。
- 任务优先级。
- ASR/OCR/镜头 Provider。

UI 显示队列、资源、Provider、转写、OCR、镜头、时间线、失败重试和派生目录。

验收：

1. 真实中文视频完成处理。
2. RTX 4060 和 CPU 模式分别验收。
3. 未安装可选依赖时核心服务仍可运行。
4. 所有参数可修改、恢复默认和校验。

---

## P2-D：Windows 桌面打包和服务生命周期

状态：`TODO`

分支：`feature/desktop-packaging`

目标：

- Tauri Windows 安装包。
- 启动、检测和停止本机 FastAPI 服务。
- 默认绑定 `127.0.0.1`。
- 托盘、退出、重启服务和打开日志。
- 崩溃恢复、端口占用、升级和卸载保护。
- 卸载不删除 Vault、Raw 和 Backup。

UI 显示后端路径、版本、服务状态、端口、开机启动、日志目录、更新状态和诊断。

验收：

1. Windows 10/11 安装、启动、退出和卸载通过。
2. 连续 20 次启动/退出无残留进程。
3. 未安装 Python 时有明确打包方案。
4. 升级不覆盖设置。
5. Vault 哈希不变。

---

## P3-A：浏览器采集增强

状态：`TODO`

分支：`feature/browser-capture-v2`

要求：

- 页面、选中文字、主要正文和完整 HTML 快照。
- 可选截图和元数据。
- 项目、标签和隐私选择。
- 公众号、视频号、抖音和小红书增强。
- 不读取 Cookie，不绕过登录和反爬。
- 大页面分块或保存本地快照。
- 离线队列由用户确认重试。

UI 显示扩展连接、最近投喂、待补正文、重复来源、失败原因和项目/隐私归属。

---

## P3-B：手机分享和设备配对

状态：`TODO`

分支：`feature/mobile-capture`

要求：

- Android 分享目标或 PWA。
- 链接、文字、图片、视频和文件。
- 一次性配对码或 QR。
- 每台设备独立可撤销令牌。
- 不把完整控制 API 暴露到公网。
- 上传中断可恢复。

UI 显示设备、最后活动、权限、撤销、配对码和上传任务。

---

## P3-C：大型 ChatGPT/Codex 导入和附件

状态：`TODO`

分支：`feature/import-streaming-attachments`

要求：

- 大型 JSON 流式解析。
- 进度、取消、断点和重试。
- 图片、附件、文件和会话关系。
- 重复导入幂等。
- 继续阻止压缩炸弹、路径穿越和损坏包。

UI 显示文件、大小、进度、峰值内存、会话、附件、错误、恢复和项目归属。

验收目标：5GB 级导出包不因内存耗尽崩溃。

---

## P3-D：存储调度、恢复、加密与权限

状态：`TODO`

分支：`feature/storage-security-operations`

要求：

- 定时盘点和低磁盘预警。
- 自动模式仍生成计划和审计。
- Raw、Vault、Backup 永不自动清理。
- 冷存储复制后校验哈希再移除源派生文件。
- 隔离恢复验收后才能切换。
- 切换前自动备份，失败可回滚。
- 私密 Raw 和备份可选加密。
- 密钥使用系统安全存储，不进入 Git、日志和 Frontmatter。

UI 显示容量趋势、保留时间、阈值、冷存储、清理预览、恢复演练、加密、密钥和权限审计。

---

## P4-A：工作活动感知

状态：`TODO`

分支：`feature/activity-signals`

允许采集：

- 软件名称和版本。
- 软件使用时长。
- 项目文件变化。
- Git 活动。
- 软件安装、卸载和更新。
- 任务状态。

禁止采集：

- 全局键盘输入。
- 密码和验证码。
- 持续录屏。
- 未授权私人聊天正文。
- 浏览器密码和 Cookie。

UI 显示今日/本周活动、项目归属、软件清单、Git/文件变化、隐私模式和保留设置。

---

## P4-B：主动推荐和视野扩展

状态：`TODO`

分支：`feature/horizon-recommendations`

能力：

- Interest Profile。
- Project Signals。
- Horizon Engine。
- Recommendation Feedback。

每条推荐必须说明：

- 来源。
- 推荐原因。
- 关联项目。
- 新增信息。
- Freshness 和 Confidence。
- 建议动作。

UI 支持接受、忽略、不再推荐、关联项目、来源和频率控制。不得自动发布或执行高风险动作。

---

# 8. 微信聊天预留接口

状态：`DEFERRED`

当前不实现聊天解析、私聊、群聊、语音、附件和联系人导入。

必须预留：

- Provider ID：`wechat_chat`
- Provider 状态：`reserved`
- 能力声明：文本、图片、音频、附件、联系人、群聊元数据
- 来源中心显示“微信聊天：暂缓开发 / 接口已预留”
- API 返回能力和状态，但不提供虚假导入按钮
- 复用现有 Adapter/Registry，不新建第二套连接器框架
- 不破解微信数据库，不绕过权限，不读取未明确导出的数据

---

# 9. 开发顺序与并行安排

## 阶段一：基线收口

1. P0 Windows 生命周期：`ACCEPTED`。
2. 合入 PR #3。
3. P0-B 真实环境只读验收。
4. 创建 `integration/lingji-v1`。
5. P1-0 UI 模块化。

## 阶段二：最多四条并行线

1. P1-A 可信引用与 Freshness。
2. P1-B 区块写入与 Agent Task。
3. P2-C 媒体语义自动编排。
4. P2-D Windows 桌面打包。

共享 Schema 和全局 API 由集成负责人先合入最小契约。

## 阶段三

1. P1-C MCP 与 Context Packet v2。
2. P2-A 本地文件检索。
3. P2-B 项目和类型化关系。
4. P3-A 浏览器采集增强。

## 阶段四

1. P3-B 手机分享。
2. P3-C 大型导入。
3. P3-D 存储、安全和完整恢复。
4. 媒体高级理解。

## 阶段五

1. P4-A 活动感知。
2. P4-B 主动推荐。
3. 微信聊天继续保持 `DEFERRED`。

---

# 10. 每次交付格式

```text
模块：
分支：
Commit SHA：
Draft PR：
Actions Run：

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
- 实现前失败测试：
- 实现前失败输出：
- 实现后成功输出：

测试命令：
- command

测试结果：
- Ubuntu 3.11：
- Ubuntu 3.12：
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
已知限制：
回滚方式：

自检：
- 是否只修改本模块：
- 是否有无关格式化：
- 是否重复实现已有能力：
- 是否增加不必要依赖：
- 是否满足 UI 要求：
```

不得使用 `simulated`、`XXXX`、假 SHA、固定成功输出或占位测试文件名。

---

# 11. 下一项允许执行的工作

当前下一项：`P0-B 真实环境只读验收`。

在 PR #3 合入前，可先准备验收命令、脱敏样例和 UI 诊断入口；不得把 P1 新功能继续塞进 PR #3。

P0-B 完成后，创建 `integration/lingji-v1`，再进入 P1-0 UI 模块化和第二阶段并行开发。
