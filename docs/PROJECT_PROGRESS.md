# LingJi 项目总进度与需求台账

> 状态：长期维护 / 每轮开发必读  
> 最近更新：2026-08-14  
> 产品核心：**第二永久记忆大脑**  
> 当前产品分支：`feature/owner-autopilot-ui-codexpp`  
> 当前产品 PR：`#88`  
> 最近一次 M5 真机被测产品 Commit：`90398fd87f3419c598632479d2a00626b4554122`  
> 最近一次 M5 结论：`FAIL / DO NOT MERGE`  

## 0. 本文档职责

本文档是 LingJi 的**长期产品进度、用户需求和开发执行队列总账**。

它不替代其他权威：

- `docs/ARCHITECTURE.md`：架构、边界、数据权威。
- `docs/PROJECT_STATUS.md`：仓库当前技术状态、风险和阻塞。
- `docs/MODULES/CODE_MAP.md`：代码入口、所有权和测试导航。
- `docs/ACCEPTANCE/`：验收任务、结果和增量门禁。
- 本文档：**用户到底要什么、分成哪些长期项目、每个项目做到哪里、下一步先做什么。**

### 强制维护规则

1. 用户提出新的 LingJi 产品需求时，**先更新本文档，再开始代码开发**。
2. 每个需求必须挂到一个或多个 `Pxx` 项目，并分配唯一 `R-YYYYMMDD-NN` 需求编号。
3. 开发开始时把需求状态改为 `IN_PROGRESS`；代码完成但未真机验证只能标记 `CODE_DONE_WAITING_ACCEPTANCE`。
4. 完成后必须回填：实现 Commit、PR、测试、真机结果、报告路径和已知限制。
5. 被替代的需求保留历史，标记 `SUPERSEDED`，禁止直接删除，避免项目再次“失忆”。
6. 用户的新反馈优先级高于旧计划；发生方向调整时必须在“决策记录”中说明原因。
7. 本文档只记录产品级事实和进度，不复制大段架构实现，详细内容通过链接指向对应权威文档。

---

# 1. 产品永久定义

LingJi 的核心不是聊天软件，也不是通用 AI 软件控制台。

```text
LingJi
=
用户的第二永久记忆大脑
+
所有获授权 AI 共用的一套长期记忆
+
自动收纳、整理、更新、检索和维护系统
+
让上述过程看得见、可控、可验证的桌面 UI
```

长期交互关系：

```text
Codex / ChatGPT / Claude / Kimi / 本地模型 / 未来 AI
                         ↓
                    MCP / API
                         ↓
                   MemoryGateway
                         ↓
              LingJi 永久记忆系统
```

### 固定边界

- 不开发 LingJi 聊天框；Codex、ChatGPT、Claude 等承担聊天和推理入口。
- UI 和自动化只服务于“第二永久记忆大脑”的可见性、自动维护和可验证取回。
- `src/` 是唯一长期正式平台主线。
- `desktop/lingji-control/` 是唯一正式 Desktop UI。
- `second_brain/` 只用于迁移、兼容、只读和验收，不再新增正式产品能力。
- Obsidian Vault + Git 是永久记忆与正式知识正文唯一权威。
- SQLite、Qdrant、Structured Read Model 都必须可重建，不得成为第二事实源。

---

# 2. 当前 11 条长期项目主线

> 这里的“11 个项目”是长期工作主线，不等同于 11 个独立软件。后续如果新增正式主线，编号顺延，不为了凑数量强行合并。

| ID | 项目 | 长期目标 | 当前状态 | 当前最重要缺口 | 下一动作 |
|---|---|---|---|---|---|
| P01 | 永久记忆核心与生命周期 | 从候选到审核、版本、冲突、Core、归档形成唯一稳定长期记忆 | `IMPLEMENTED_PARTIAL_PRODUCTIZATION` | 生命周期在 UI 中不可连续理解；真实长期数据试运行仍需闭环 | 把生命周期状态接入 Memory Dashboard v2，并补真实数据质量试运行 |
| P02 | 自动采集与自动收纳 | 自动发现授权来源，进入 raw → extraction → candidate，不要求用户手工搬运资料 | `IMPLEMENTED_NEEDS_AUTOMATION_VISIBILITY` | 后端有 Capture/Extraction/Queue，但用户看不到“发现了什么、正在处理什么、失败后怎么处理” | 建立来源/收纳流水线和真实进度展示 |
| P03 | 记忆审核、版本、关系与冲突 | AI 提候选，用户掌握永久记忆写入；冲突不静默覆盖，历史可追溯 | `PARTIAL` | 审核/冲突/版本能力分散，主人待决事项没有统一入口 | 建立“待你决定”统一队列，仅保留真正需要主人确认的事项 |
| P04 | 统一检索与 Context Pack | FTS/BM25/中文回退 + Qdrant + 权限过滤 + RRF，共用一条检索链 | `IMPLEMENTED_FOCUSED_TESTED` | 技术链已存在，但用户看不见每次取回为什么命中，也没有真实质量结论 | 接 Retrieval Trace、质量评测和 UI 可解释结果 |
| P05 | 取回质量评估 | 用真实问题集证明 Recall、Precision、Citation、False Positive，而不是用覆盖率代替准确率 | `NOT_COMPLETE` | 当前只有 coverage；`precision_state=not_measured`，没有正式验证样本 | 建立 Retrieval Evaluation Dataset 与自动评测报告 |
| P06 | 多 AI 共享记忆与 MCP/权限 | Codex、ChatGPT、Claude 等在授权范围读取同一套长期记忆 | `IMPLEMENTED_NEEDS_END_TO_END_PROOF` | MCP 和权限已有基础，但不同 AI 的真实端到端共享记忆证据仍不完整 | 先锁 Codex 真实 MCP 调用，再扩展其他 AI 客户端 |
| P07 | Obsidian / Vault / Git 永久权威 | 正式知识可编辑、可版本化、可恢复，派生索引可重建 | `IMPLEMENTED_CORE` | UI 对“原文、版本、索引状态、重建关系”展示不足，备份/恢复仍需更直观 | 把 Vault/Git 状态与自动索引、备份、恢复进入统一可视流程 |
| P08 | Memory Inspector 与来源视图 | 看清记忆、Source/Conversation/Message、引用、版本、向量和检索原因 | `IMPLEMENTED_NEEDS_PRODUCT_UX` | API/Desktop 基础存在，但功能仍像开发者检查器，普通用户难理解 | 做可解释 Memory Inspector，并接首页钻取 |
| P09 | Vector Center / Embedding / 模型状态 | Qdrant 与 Embedding 状态真实、可恢复、可重建、不可伪报 | `IMPLEMENTED_NEEDS_TRUTHFUL_UX` | unavailable/degraded 的原因和影响不清晰；运行状态不够主动解释 | 将技术状态翻译成“原因/影响/系统动作/是否需要主人处理” |
| P10 | Desktop UI、自动维护与 Mac/Windows 双平台 | 同一 LingJi 核心在 Win/Mac 稳定运行，首页展示第二大脑持续工作的真实过程 | `ACTIVE_PR88_M5_FAIL` | M5-UX-003：仍是统计卡片，不是完整记忆进度看板；M5-PROCESS-001：替换安装流程有偏差 | 先完成 Memory Dashboard v2 + 自动维护透明化，再生成新 exact Artifact 复验 M5 |
| P11 | 机会系统与项目级应用层 | 在永久记忆之上做机会发现、项目上下文和主动信息价值提炼 | `DEFERRED_UNTIL_MEMORY_FOUNDATION_STABLE` | 基础永久记忆、检索质量和 UI 自动化尚未完全稳定 | 暂不扩张，等 P01-P10 达到稳定门槛后恢复 |

---

# 3. 当前用户需求池

状态枚举：

```text
BACKLOG
READY
IN_PROGRESS
CODE_DONE_WAITING_ACCEPTANCE
ACCEPTED
FAILED
BLOCKED
SUPERSEDED
```

| 需求 ID | 日期 | 用户需求 | 关联项目 | 优先级 | 状态 | 验收关键点 |
|---|---|---|---|---|---|---|
| R-20260814-01 | 2026-08-14 | 灵机必须保持“第二永久记忆大脑”定位，不得偏成聊天软件或通用 AI 控制台 | P01,P06,P10 | P0 | `ACCEPTED_AS_PRODUCT_RULE` | 所有新 UI/自动化必须能说明它如何服务长期记忆 |
| R-20260814-02 | 2026-08-14 | 不需要聊天框，Codex 等现有 AI 就是聊天入口 | P06,P10 | P0 | `ACCEPTED_AS_PRODUCT_RULE` | Desktop 不新增聊天主页或重复 Agent 对话层 |
| R-20260814-03 | 2026-08-14 | 很多已经开发的功能看不见，必须完整盘点并在 UI 中显性化 | P01-P10 | P0 | `READY` | 建立功能可见性矩阵；正式能力必须能定位到 UI/高级入口/自动运行状态 |
| R-20260814-04 | 2026-08-14 | 首页要展示自动收纳、更新、取回、异常处理、待主人决定事项的连续进度，不只是统计卡片 | P02,P03,P04,P10 | P0 | `READY` | 10 秒内看懂“刚做了什么/正在做什么/下一步/异常/是否需要我决定” |
| R-20260814-05 | 2026-08-14 | 自动化要更主动：能自己发现来源/环境、自动处理能处理的事情，只把必要决策交给主人 | P02,P03,P09,P10 | P1 | `READY` | 自动 retry/恢复/索引/同步可见；隐私、永久写入、删除、不可逆操作才请求确认 |
| R-20260814-06 | 2026-08-14 | 取回质量必须用真实样本和量化指标验证，不能把覆盖率冒充准确率 | P04,P05 | P0 | `READY` | Recall@K、Precision@K、MRR、Citation Accuracy、False Positive Rate；无样本时明确 not measured |
| R-20260814-07 | 2026-08-14 | Memory Inspector / Vector / 模型状态要让普通用户看懂，不要只显示技术错误 | P08,P09 | P1 | `BACKLOG` | 每个异常显示原因、影响、系统正在做什么、是否需要主人行动 |
| R-20260814-08 | 2026-08-14 | Mac 与 Windows 是同一个 LingJi 产品的双平台发行，不得修好 Mac 又破坏 Windows | P10 | P0 | `IN_PROGRESS` | 同一 exact product SHA 上 Win/Mac 门禁与 Artifact 全部通过 |
| R-20260814-09 | 2026-08-14 | 修正 M5 首次 whole-bundle replace 的流程偏差 | P10 | P1 | `READY` | backup root 先验证，再整体替换、签名校验；失败可安全恢复 |
| R-20260814-10 | 2026-08-14 | 创建长期项目进度文档，每次记录所有项目、用户后续需求、开发状态并逐步执行 | P01-P11 | P0 | `ACCEPTED` | 本文档存在；后续 Agent 必读；每个新需求先登记再开发 |

---

# 4. 当前执行队列

## Stage 0 — 项目“防失忆”治理

状态：`IN_PROGRESS`

目标：解决代码、验收和状态文档互相漂移，建立统一需求总账。

- [x] 创建 `docs/PROJECT_PROGRESS.md`。
- [x] 在 `AGENTS.md` 把本文档加入每轮开发的必读与必更新规则。
- [ ] 盘点并修正 `PROJECT_STATUS.md`、旧 `UNIFIED_MEMORY_EXECUTION_STATUS.md`、当前 PR88/M5 的状态漂移。
- [ ] 确认旧 PR60 `LOCAL_EXECUTION_TASK` 不再被当前产品开发误判为 ACTIVE 权威。
- [ ] 形成一次 Markdown 治理记录并通过 acceptance-doc-sync。

完成门槛：任何 Agent 进入仓库都能在 2 分钟内确定核心定位、当前 11 条主线、当前需求、当前唯一执行阶段和最近失败原因。

## Stage 1 — 功能可见性审计

状态：`READY`

目标：回答“已经做了哪些能力，但用户为什么看不见”。

交付：`docs/MODULES/FUNCTION_VISIBILITY_MATRIX.md`

至少覆盖：

- Capture / Extraction / Raw
- Memory Candidate / Review / Core / Archive
- Source / Conversation / Message
- FTS / Qdrant / Hybrid Retrieval / Context Pack
- MCP / AI clients / permissions
- Obsidian / Git / indexing
- Tasks / Queue / Scheduler / Watcher / Retry
- Backup / Storage / Recovery
- Models / Embedding / GPU
- Opportunity
- Desktop pages / settings / diagnostics

每项必须记录：后端入口、API、是否自动运行、当前 UI、用户是否能理解、异常路径、下一步产品化动作。

## Stage 2 — Memory Dashboard v2

状态：`READY`

目标：直接关闭当前 `M5-UX-003`。

首页必须从统计卡片升级为真实记忆生命周期：

```text
来源发现
→ 自动收纳
→ 解析
→ 候选
→ 主人确认
→ 永久记忆
→ 全文/向量索引
→ 可验证取回
→ 自动更新
```

每个阶段必须显示真实变化量、当前工作、最近完成、失败/重试、更新时间和下一步。

禁止伪造 percentage / precision / success。

## Stage 3 — 自动维护与主人决策

状态：`BACKLOG_AFTER_STAGE2`

目标：让系统自己处理正常维护，只把真正需要人的事情留下。

自动处理优先：retry、增量索引、向量同步、健康恢复、可安全重连、备份检查。

主人决策只保留：永久记忆确认、冲突覆盖、隐私授权、删除、权限扩大、其他不可逆动作。

## Stage 4 — Retrieval Quality Evaluation

状态：`BACKLOG_AFTER_STAGE2`

目标：建立真实问题样本，计算：

- Recall@K
- Precision@K
- MRR
- Citation Accuracy
- False Positive Rate

没有验证集时，UI 必须继续显示 `not_measured`，不得把 coverage 改名成准确率。

## Stage 5 — Inspector / Source / Vector 产品化

状态：`BACKLOG`

目标：把已有检查器和技术页从“开发者诊断”升级成普通用户能理解的第二大脑视图。

## Stage 6 — 多 AI 共享记忆端到端验证

状态：`BACKLOG`

先验证 Codex → MCP → MemoryGateway → citation 的真实闭环，再扩其他 AI。

## Stage 7 — Win/Mac 新 Artifact + M5 复验

状态：`BLOCKED_BY_STAGE2_AND_STAGE3`

当前旧被测产品 `90398fd` 的 M5 结论必须永久保留为 FAIL；不得覆盖或把旧 Artifact 改报 PASS。

新代码必须重新跑 exact-SHA：

```text
tests
→ P0 Windows Gate
→ Windows Desktop Release
→ macOS Desktop Gate
→ acceptance-doc-sync
→ local-execution-handoff
→ 独立 Artifact/hash 核对
→ 新 M5 真机验收
```

## Stage 8 — 真实数据质量试运行与兼容层退役

状态：`DEFERRED`

只有前述长期记忆、检索质量、双平台和自动维护通过后，才进行真实数据质量试运行和 `second_brain` 最终退役。

## Stage 9 — 机会系统与上层应用恢复开发

状态：`DEFERRED`

机会发现、项目级 Context、主动信息价值提炼继续保留，但不抢占当前永久记忆主线。

---

# 5. 当前 M5 / PR #88 事实

最近一次 M5 被测产品：

```text
PR: #88
Product commit: 90398fd87f3419c598632479d2a00626b4554122
Artifact ID: 9215481793
DMG: 灵机_0.1.0_aarch64.dmg
M5 verdict: FAIL / DO NOT MERGE
```

已经通过：

- macOS / Windows CI exact-SHA 门禁。
- macOS arm64 App / Sidecar。
- 签名检查。
- `8766` 仅绑定 `127.0.0.1`。
- Acceptance task-scoped 数据隔离。
- 首页已增加基础收纳/更新/取回数据，并明确无验证集时不宣称准确率。

当前产品级失败：

### `M5-UX-003`

首页仍停留在统计层，没有把自动收纳、更新、取回、异常恢复、待决事项组织为连续可追踪的长期记忆工作流。

### `M5-PROCESS-001`

首次 whole-bundle replace 存在流程偏差；后续必须在移动旧 App 前先验证 backup root，再完成整体替换和签名校验。

旧 `90398fd / 9215481793` 只作为失败基线证据，不再作为后续 PASS 候选。

---

# 6. 需求新增模板

以后每次用户提出新需求，在“当前用户需求池”追加：

```markdown
| R-YYYYMMDD-NN | 日期 | 用户原始需求的准确摘要 | Pxx | P0/P1/P2 | BACKLOG | 可验证验收结果 |
```

同时在这里追加完整记录：

```markdown
### R-YYYYMMDD-NN · 需求标题

- 用户目标：
- 关联项目：
- 为什么需要：
- 不做什么：
- 产品验收：
- 自动测试：
- 真机/主人观察：
- 当前状态：
- 实现分支：
- 实现 Commit：
- PR：
- 测试报告：
- 最终结果：
- 后续遗留：
```

---

# 7. 每轮开发回填模板

```markdown
## YYYY-MM-DD · 开发批次 <名称>

- 关联需求：R-...
- 关联项目：P..
- 开始状态：
- 本轮目标：
- 修改文件：
- 自动测试：
- CI：
- 本机/真机：
- 主人观察：
- 文档：
- Commit：
- PR：
- 结束状态：
- 未完成：
- 下一批：
```

## 2026-08-14 · 开发批次 Project Progress Ledger

- 关联需求：`R-20260814-10`
- 关联项目：`P01-P11`
- 开始状态：没有统一的长期产品需求/项目进度总账，需求主要散落在聊天、状态文档和验收报告中。
- 本轮目标：建立唯一长期进度台账，并把它接进所有 Agent 的强制开发流程。
- 修改文件：`docs/PROJECT_PROGRESS.md`、`AGENTS.md`。
- 自动测试：纯文档治理变更，无 Runtime 行为测试。
- 远程验证：GitHub 已重新读取 `PROJECT_PROGRESS.md` 与 `AGENTS.md`，内容可见。
- 首次总账 Commit：`a075aa6e721517c3f4079517342d81dbe9b9aaba`
- AGENTS 接入 Commit：`bc9c712e07d9926507c10acf66259a2eee7600a6`
- 结束状态：`ACCEPTED`，长期维护规则正式生效。
- 未完成：Stage 0 仍需清理 `PROJECT_STATUS` / 旧执行状态 / PR60 ACTIVE 任务漂移。
- 下一批：继续 Stage 0“项目防失忆治理”。

---

# 8. 决策记录

## D-20260814-01 · UI 和自动化不改变产品核心

此前讨论曾把下一阶段描述为通用 `Control Center + Automation Layer`。该表述容易让 LingJi 偏离“第二永久记忆大脑”。

最终决定：

```text
永久记忆 = 产品核心
UI = 永久记忆的可视界面
自动化 = 永久记忆的维护方式
Codex/其他 AI = 交互与推理入口
机会系统 = 永久记忆上的应用层
```

因此不新增 LingJi 聊天框，也不为“智能化”另建第二套 Intelligence 数据库、事件数据库或独立事实源。

## D-20260814-02 · 先可见，再继续扩能力

当前最主要问题不是后端能力不足，而是已经实现的能力大量隐藏在 API、状态、脚本和高级诊断中。

下一阶段顺序固定为：

```text
项目防失忆治理
→ 功能可见性审计
→ Memory Dashboard v2
→ 自动维护与主人决策
→ Retrieval Quality
→ Inspector / Source / Vector 产品化
→ 多 AI 共享记忆闭环
→ Win/Mac 新 Artifact + M5
→ 真实数据试运行
→ 上层机会系统
```

除非用户明确改变优先级，否则后续开发按此队列执行。

---

# 9. 更新日志

## 2026-08-14 · v1.1

- `PROJECT_PROGRESS.md` 已创建并完成远程复读。
- `AGENTS.md` 已要求所有 Agent 每轮先读项目总账，新需求先登记、开发结束后回填。
- `R-20260814-10` 从 `IN_PROGRESS` 更新为 `ACCEPTED`。
- Stage 0 前两项完成，下一步进入仓库状态文档和旧任务权威漂移治理。

## 2026-08-14 · v1

- 创建长期项目进度与需求总账。
- 固定 LingJi “第二永久记忆大脑”产品定义。
- 建立当前 11 条长期项目主线。
- 登记 10 条当前明确用户需求。
- 固定当前 PR #88 / M5 FAIL 基线。
- 将下一阶段从“继续增加模块”调整为“功能可见性 → 记忆生命周期看板 → 自动维护 → 真实取回质量”。
