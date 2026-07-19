# 灵机后续开发、实施与验收总计划

> 计划版本：`v2.2`  
> 更新日期：`2026-07-19`  
> 仓库：`wangduoyu001/lingji`  
> 当前基线：`feature/extraction-hardening-web-skills-ui`  
> 当前工作分支：`test/real-environment-acceptance`  
> 当前 Draft PR：`#4`  
> 计划维护者：ChatGPT，负责需求、架构边界、代码审查、CI 与验收  
> 长期权威源：Obsidian Markdown  
> SQLite 定位：索引、任务状态、来源映射、Freshness、审计和可重建派生缓存

---

# 0. 本文件的权威级别

本文件是灵机后续开发的唯一总计划、状态表和验收入口。

1. 每个模块开始前必须先研究官方文档和类似项目。
2. 代码必须先补失败测试，再做最小实现。
3. 每次代码更新后，本文件必须更新真实状态。
4. 未经 Diff、测试、CI、Demo、UI 和风险审查，不得标记 `ACCEPTED`。
5. 模块报告放在 `docs/<MODULE>_REPORT.md`，本文件保存权威状态和下一动作。
6. Obsidian Markdown 始终是长期权威内容；SQLite 必须可删除、可重建。
7. 主人需要手动操作的功能必须在独立桌面 UI 中有入口、状态、设置和结果。
8. 不因“顺便优化”重写无关代码，不建立平行网关、平行队列或平行数据库。
9. 不允许使用模拟 SHA、虚构 CI、固定成功输出或无效测试。

## 状态定义

| 状态 | 含义 |
|---|---|
| `TODO` | 尚未开始 |
| `RESEARCHING` | 正在研究官方文档和类似项目 |
| `IN_PROGRESS` | 已开始实现 |
| `REVIEW_REQUIRED` | 代码已提交，仍有验收门槛未完成 |
| `CHANGES_REQUIRED` | 审查未通过，需要最小修复 |
| `ACCEPTED` | 代码、测试、CI、Demo、UI 和真实验收全部通过 |
| `BLOCKED` | 被依赖或外部条件阻塞 |
| `DEFERRED` | 暂缓，只保留接口和规划 |

---

# 1. 当前真实状态

## 1.1 已具备基础

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
14. Windows SQLite 生命周期已修复。
15. 真实环境严格只读验收代码、CLI、API、报告和 UI 已完成代码验证。

## 1.2 当前发布阻断

1. P0-B 尚未在主人电脑对真实 `E:\obsidian\本地知识库` 执行。
2. 真实 ChatGPT 导出包和真实媒体尚未完成脱敏验收。
3. Tauri 仍不是完整可安装、可托盘管理、可自动启动后端的正式 `LingJi.exe`。
4. PR #2 体积过大，禁止继续直接堆叠新功能。
5. PR #4 在真实环境验收前保持 Draft。
6. `integration/lingji-v1` 需要 P0-B 验收后建立。

## 1.3 完成度状态表

| 板块 | 状态 | 说明 |
|---|---|---|
| P0 Windows 生命周期 | `ACCEPTED` | Windows 文件锁和调度器退出已通过 CI |
| P0-B 真实环境只读验收 | `REVIEW_REQUIRED` | 代码全绿，等待主人电脑真实运行 |
| 单 Vault 记忆底座 | 已有基础 | 仍需可信引用和 Freshness |
| ChatGPT/Codex 导入写回 | 已有基础 | 大型流式导入和附件关系未完成 |
| 网页主动采集 | 首版 | HTML、截图、离线队列和站点增强未完成 |
| 媒体处理 | 首版 | Provider 已有，自动编排和高级理解未完成 |
| 桌面控制中心 | 原型 | 页面模块化、打包和服务生命周期未完成 |
| 本地文件检索 | `TODO` | PDF、Office、图片和代码检索未完成 |
| 项目关系图 | `TODO` | 类型化关系和项目详情页未完成 |
| 手机入口 | `TODO` | 分享、配对、权限和断点上传未完成 |
| 活动感知 | `TODO` | 只允许低侵入信号，禁止键盘记录 |
| 主动推荐 | `TODO` | 需要项目状态和可信来源作为前置 |
| 微信聊天 | `DEFERRED` | 只预留 Provider 接口 |

---

# 2. 最近验收记录

## 2.1 P0 Windows DB Lifecycle Fix

状态：`ACCEPTED`

- 分支：`fix/windows-db-lifecycle`
- PR：`#3`
- 合并提交：`156ee3e1cc5abd4e054028606079a16a12fa29b0`
- 最终验证：Linux 3.11/3.12、Windows、MCP、浏览器扩展、Obsidian 插件、桌面构建全部成功
- Windows：`108 tests / OK`
- 报告：`docs/WINDOWS_DB_LIFECYCLE_REPORT.md`

根因：

1. `with sqlite3.connect(...)` 只控制事务，不关闭连接。
2. `CronScheduler.stop()` 未等待轮询线程和执行器结束。
3. FastAPI TestClient 未完整退出生命周期。

结果：

- 显式关闭测试连接。
- 调度器 stop event、thread join、executor wait。
- TestClient 在临时目录清理前关闭。
- 真实数据库文件删除测试和 Demo。
- 未改 Schema，未引入依赖。

## 2.2 P0-B 真实环境只读验收

状态：`REVIEW_REQUIRED`

- 分支：`test/real-environment-acceptance`
- Draft PR：`#4`
- 代码验收 Head：`011142a2ac070c2ab6091f72783bda0c465ac674`
- 代码验证 Run：`29692373806`
- Windows：`113 tests / OK`
- Ubuntu Python 3.11：成功
- Ubuntu Python 3.12：成功
- Windows Python 3.12：成功
- MCP smoke：成功
- Browser capture smoke：成功
- Obsidian plugin smoke：成功
- Desktop UI smoke、TypeScript、Vite build：成功
- 报告：`docs/REAL_ENVIRONMENT_ACCEPTANCE_REPORT.md`

已实现：

1. Vault、SQLite、设置、ChatGPT 导出和媒体输入验收前后指纹。
2. Vault 指纹覆盖 Markdown、图片、附件和其他普通文件。
3. SQLite 数据库、`-wal`、`-shm` 都进入输入指纹。
4. 数据库和 WAL 复制到系统临时目录，在副本上执行 `quick_check`。
5. ChatGPT ZIP 结构、加密成员和 CRC 检查。
6. FFprobe 媒体结构检查。
7. Ollama 服务和模型列表。
8. JSON/Markdown 报告历史。
9. CLI、控制 API 和桌面“环境验收”入口。
10. 唯一持久写入为验收报告和验收审计事件。

未完成：

1. 主人电脑真实 Vault 验收。
2. 真实 ChatGPT 导出包验收。
3. 真实样例媒体验收。
4. 真实报告内容审查。

P0-B 只有在真实报告满足以下条件后才能标记 `ACCEPTED`：

```text
error_count = 0
inputs_unchanged = true
Vault 路径正确
SQLite 检查无错误
ChatGPT 导出被识别
样例媒体 FFprobe 成功
报告未包含敏感正文
```

---

# 3. 强制开发原则

## 3.1 开发前研究

每个模块至少研究：

1. 一个官方标准或官方文档。
2. 三个仍在维护的类似开源项目或公开产品。
3. 许可证、维护状态、Windows 支持、离线能力、数据格式、资源和安全边界。
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
→ 证明实现前失败
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
- 伪造 CI、截图、SHA 或运行结果。

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
2. 危险操作先预览，再确认，再执行，并可恢复。
3. UI 不直接写 SQLite。
4. AI 不允许整文件覆盖主人维护的 Markdown。
5. AI 不允许直接批准正式决策。
6. SQLite 只保存索引、状态、映射、审计或可重建派生数据。
7. 不保存浏览器 Cookie、密码、验证码或全局键盘输入。
8. 真实环境验收不得创建、修改或迁移被检查输入。

---

# 4. UI 完整性要求

“薄 UI”不等于“只有命令行”。凡是主人需要手动操作的功能，都必须在独立桌面 UI 中显示。

每个功能至少具备：

1. 可发现的导航入口或页面模式。
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
- 成功与失败状态截图或可复现证据。
- `npm run build` 结果。
- 至少一个组件测试或 smoke test。

---

# 5. Git 与并行开发规则

## 5.1 当前阶段

1. PR #4 保持 Draft，直到真实环境验收完成。
2. P0-B 不得混入 P1 新功能。
3. P0-B 验收通过后，PR #4 才允许合入基线。
4. 随后创建 `integration/lingji-v1`。

## 5.2 集成分支

```powershell
git fetch origin
git switch feature/extraction-hardening-web-skills-ui
git pull --ff-only origin feature/extraction-hardening-web-skills-ui
git switch -c integration/lingji-v1
git push -u origin integration/lingji-v1
```

## 5.3 Worktree

```powershell
git fetch origin
git worktree add ..\lingji-<module> `
  -b feature/<module> `
  origin/integration/lingji-v1
```

同步：

```powershell
git fetch origin
git rebase origin/integration/lingji-v1
```

## 5.4 PR

- 一个模块一个 Draft PR。
- Base 为 `integration/lingji-v1`。
- 不直接推送集成分支。
- 合并方式为 Squash and merge。
- PR 写明研究、目标、非目标、修改文件、接口、测试、Demo、UI、风险和回滚。
- CI 全绿不代表自动通过，仍需验收。

## 5.5 共享热点

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

## 5.6 推荐并行度

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

## P1-0：桌面 UI 最小模块化

状态：`TODO`

分支：`feature/ui-module-foundation`

目标：

- 将巨型 `App.tsx` 拆为 app、pages、components、hooks、types、api。
- 把临时顶层“环境验收”模式并入正式侧栏路由。
- 保持现有视觉和行为不变。
- 为后续页面并行开发建立稳定边界。

非目标：

- 不重新设计界面。
- 不改变 API。
- 不引入大型状态管理或 UI 框架。

验收：

1. 原有八个页面和环境验收页全部可渲染。
2. `App.tsx` 只保留应用壳和路由。
3. Loading、Empty、Error 状态不丢失。
4. 连接配置只保留一份，不重复管理 Token。
5. `npm run build` 和页面 smoke test 通过。

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
- `freshness_status` 与 `consistency_status` 分开保存。

UI：

- 搜索结果引用卡片。
- 打开来源和定位。
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

## P3-C：大型 ChatGPT/Codex 导入和附件

状态：`TODO`

分支：`feature/import-streaming-attachments`

要求：

- 大型 JSON 流式解析。
- 进度、取消、断点和重试。
- 图片、附件、文件和会话关系。
- 重复导入幂等。
- 阻止压缩炸弹、路径穿越和损坏包。

UI 显示文件、大小、进度、峰值内存、会话、附件、错误、恢复和项目归属。

验收目标：5GB 级导出包不因内存耗尽崩溃。

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

## 当前阶段

1. P0 已 `ACCEPTED`。
2. P0-B 代码已通过，等待主人真实环境运行。
3. P0-B 通过后合入 PR #4。
4. 创建 `integration/lingji-v1`。
5. 开始 P1-0 UI 模块化。

## 第二阶段：最多四条并行线

1. P1-A 可信引用与 Freshness。
2. P1-B 区块写入与 Agent Task。
3. P2-C 媒体语义自动编排。
4. P2-D Windows 桌面打包。

共享 Schema 和全局 API 由集成负责人先合入最小契约。

## 第三阶段

1. P1-C MCP 与 Context Packet v2。
2. P2-A 本地文件检索。
3. P2-B 项目和类型化关系。
4. P3-A 浏览器采集增强。

## 第四阶段

1. P3-B 手机分享。
2. P3-C 大型导入。
3. P3-D 存储、安全和完整恢复。
4. 媒体高级理解。

## 第五阶段

1. P4-A 活动感知。
2. P4-B 主动推荐。
3. 微信聊天继续保持 `DEFERRED`。

---

# 10. P0-B 主人电脑验收命令

在仓库目录执行：

```powershell
git fetch origin
git switch test/real-environment-acceptance
git pull --ff-only origin test/real-environment-acceptance

python scripts/acceptance_check.py `
  --vault "E:\obsidian\本地知识库" `
  --storage "<当前灵机storage目录>" `
  --backup "<当前灵机backup目录>" `
  --chatgpt-export "<真实ChatGPT导出ZIP或JSON>" `
  --media "<真实样例视频或音频>"
```

验收前：

1. 不运行导入、索引重建和清理任务。
2. 建议暂停正在写入灵机数据库的后台 Worker。
3. 不需要关闭 Obsidian，但验收期间不要编辑 Vault。
4. 保留默认 SHA-256 和 ZIP CRC 检查。

验收后需要提供：

- JSON 报告路径。
- Markdown 报告路径。
- `status`。
- `error_count`。
- `warning_count`。
- `inputs_unchanged`。
- 不需要发送 ChatGPT 正文、Vault 正文或媒体内容。

---

# 11. 每次交付格式

```text
模块：
分支：
Commit SHA：
Draft PR：
Actions Run：

研究：
修改文件：
未修改但复用的文件：
测试优先证据：
测试命令：
测试结果：
Demo：
UI：
风险：
已知限制：
回滚方式：
自检：
```

不得使用 `simulated`、`XXXX`、假 SHA、固定成功输出或占位测试文件名。

---

# 12. 当前下一动作

当前唯一阻断动作：运行第 10 节的真实环境只读验收。

在真实报告通过前：

- PR #4 保持 Draft。
- 不合并 P0-B。
- 不创建正式 `integration/lingji-v1`。
- P1 模块只允许研究和接口设计，不允许合入生产代码。
