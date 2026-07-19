# 灵机后续开发、实施与验收总计划

> 计划版本：`v2.3`  
> 更新日期：`2026-07-20`  
> 仓库：`wangduoyu001/lingji`  
> 当前稳定基线：`feature/extraction-hardening-web-skills-ui`  
> 当前依赖链：`PR #4 → PR #6`  
> 架构增补：`PR #5`  
> 计划维护者：ChatGPT  
> 长期权威源：Obsidian Markdown  
> 派生数据：SQLite、Qdrant、缓存、任务状态和运行报告必须可删除、可重建

---

# 0. 本文件的权威级别

本文件是灵机后续开发的唯一总计划、状态表和验收入口。

1. 每个模块编码前必须研究官方资料和至少三个仍维护的类似项目。
2. 先写失败测试，再做最小实现。
3. 每次代码更新后必须同步本文件的真实状态。
4. 未通过 Diff、专项测试、全量 CI、Demo、UI、安全和回滚审查，不得标记 `ACCEPTED`。
5. 每个模块必须有 `docs/<MODULE>_REPORT.md`。
6. 主人需要手动操作的能力必须在桌面 UI 中有入口、设置、状态、结果、错误和帮助。
7. Obsidian Markdown 始终是长期权威内容。
8. 禁止模拟 SHA、虚构 CI、固定成功输出、装饰性进度和无效测试。
9. 禁止借“顺便优化”重写无关代码或建立平行系统。
10. 微信聊天保持 `DEFERRED`，只保留 Provider 能力声明和接口位置。

## 0.1 状态定义

| 状态 | 含义 |
|---|---|
| `TODO` | 尚未开始 |
| `RESEARCHING` | 正在研究和定义契约 |
| `IN_PROGRESS` | 已开始编码 |
| `REVIEW_REQUIRED` | 代码已提交，仍有验收门槛 |
| `CHANGES_REQUIRED` | 审查失败，需要最小修复 |
| `ACCEPTED` | 代码、测试、CI、Demo、UI、文档和真实验收全部通过 |
| `BLOCKED` | 被依赖或真实环境阻塞 |
| `DEFERRED` | 暂缓，只保留规划和接口 |

---

# 1. 当前真实状态

## 1.1 已具备基础

1. 单一 Obsidian Vault。
2. SQLite FTS5、中文子串搜索和元数据排序。
3. MemoryDatabase、HybridRetriever、MemoryGateway、Context Pack 和 MCP。
4. ChatGPT 导入、Codex 工作报告写回。
5. 网页、社交页面和本地媒体采集框架。
6. faster-whisper、PaddleOCR、PySceneDetect 可选本地 Provider。
7. SQLiteExtractionQueue、重试、租约、进度和失败恢复。
8. FastAPI LocalControlService 和 RuntimeSettingsStore。
9. React + Tauri 桌面控制中心原型。
10. 备份、隔离恢复、存储生命周期和审计。
11. Linux、Windows、MCP、浏览器扩展、Obsidian 插件和桌面 UI CI。
12. Windows SQLite 生命周期已经修复。
13. 真实环境严格只读验收代码、CLI、API、报告和 UI 已完成自动验证。

## 1.2 真实缺口

1. 主人电脑真实 Vault、ChatGPT 导出和媒体尚未完成最终验收。
2. HybridRetriever 启动时仍是 `semantic_provider=None`。
3. Qdrant 未接入。
4. Source 与 Canonical 双层向量索引未建立。
5. Embedder 仍是逐条伪批处理，没有持久任务和 UI 进度。
6. 硬件、GPU、模型和云端 Provider 中心未实现。
7. CPU、RAM、GPU、显存、CUDA、驱动和动态负载检测未实现。
8. 活动流仍主要依靠轮询，没有持久游标 WebSocket。
9. PDF、DOCX、XLSX、PPTX、图片和代码全文检索未完成。
10. Tauri 尚未成为正式可安装、托盘管理、自动启动后端的 `LingJi.exe`。

## 1.3 当前状态表

| 模块 | 状态 | 分支 / PR | 说明 |
|---|---|---|---|
| P0 Windows DB Lifecycle | `ACCEPTED` | PR #3，合并提交 `156ee3e1cc5abd4e054028606079a16a12fa29b0` | Windows 文件锁和调度器退出已修复 |
| P0-B 真实环境只读验收 | `REVIEW_REQUIRED` | `test/real-environment-acceptance` / PR #4 | 自动 CI 全绿，等待主人真实资料运行 |
| v1.1 架构增补 | `REVIEW_REQUIRED` | `docs/architecture-v1.1-hardware-model-vector-control` / PR #5 | 只改文档，不覆盖 v1.0 |
| v1.1 默认值 UI 政策 | `REVIEW_REQUIRED` | PR #5 | 已建立强制规范，等待架构 PR 合并 |
| P1-0 桌面 UI 模块化 | `REVIEW_REQUIRED` | `refactor/desktop-ui-modular-foundation` / PR #6 | 代码和 CI 全绿，等待人工 UI 与 P0-B 依赖收口 |
| P2 硬件与算力模式 | `TODO` | 待建立 | 依赖 P1 稳定 UI 契约 |
| P3 本地模型中心 | `TODO` | 待建立 | 可在 P2 契约稳定后有限并行 |
| P4 向量记忆与混合检索 | `TODO` | 待建立 | 依赖 P2/P3 |
| P5 语义记忆与活动中心 | `TODO` | 待建立 | 依赖 P1/P4，活动后端可在 P4 后期并行 |
| P6 云端 Provider 与密钥安全 | `TODO` | 待建立 | 本地优先，所有 Provider 默认关闭 |
| P7 本地文件检索 | `TODO` | 待建立 | PDF、Office、图片和代码 |
| 微信聊天 | `DEFERRED` | Provider ID `wechat_chat` | 暂不开发数据读取，只预留能力接口 |

---

# 2. 最近验收记录

## 2.1 P0 Windows DB Lifecycle

状态：`ACCEPTED`

- PR：#3
- 合并提交：`156ee3e1cc5abd4e054028606079a16a12fa29b0`
- Windows 文件删除、调度器退出和 TestClient 生命周期通过。
- 没有 Schema 变更和新依赖。
- 报告：`docs/WINDOWS_DB_LIFECYCLE_REPORT.md`

## 2.2 P0-B 真实环境只读验收

状态：`REVIEW_REQUIRED`

- 分支：`test/real-environment-acceptance`
- Draft PR：#4
- 自动验证：Linux 3.11/3.12、Windows、MCP、扩展、插件和桌面 UI 全绿。
- 只读检查覆盖 Vault 全部普通文件、SQLite/WAL/SHM、设置、ChatGPT 导出和媒体。
- SQLite 在系统临时副本上执行 quick_check，避免原库产生 SHM。
- 唯一持久写入是 `storage/reports/acceptance` 和一条审计事件。
- 报告：`docs/REAL_ENVIRONMENT_ACCEPTANCE_REPORT.md`

主人真机通过条件：

```text
error_count = 0
inputs_unchanged = true
Vault 路径正确
SQLite 检查无错误
ChatGPT 导出被识别
样例媒体 FFprobe 成功
报告不包含敏感正文
```

## 2.3 P1-0 桌面 UI 模块化

状态：`REVIEW_REQUIRED`

- 分支：`refactor/desktop-ui-modular-foundation`
- Draft PR：#6
- 堆叠 Base：`test/real-environment-acceptance`
- 验证 Head：`43152429f57561afee196ad23866e3e5445db619`
- 代码验证 Run：`29696562955`
- 文档收尾 Run：`29696666899`
- Windows：`113 tests / OK`
- Desktop UI Smoke、TypeScript、Vite、Tauri：success
- Linux 3.11/3.12、MCP、浏览器扩展、Obsidian 插件：success
- 报告：`docs/DESKTOP_UI_MODULARIZATION_REPORT.md`

已完成：

1. `App.tsx` 收缩为 Shell、导航和页面组合。
2. 页面进入 `pages/`。
3. 共用组件进入 `components/`。
4. API 连接、初始化和总览轮询进入 `useLingJiConnection`。
5. 连接与 Token 状态只保留一份。
6. 环境验收进入正式左侧导航。
7. 设置页增加搜索、只看已修改、单项恢复、分组恢复和取消修改。
8. SettingDefinition 预留推荐值、推荐原因、修改时机、风险和影响字段。
9. Smoke 强制检查模块文件、设置帮助入口和 `App.tsx < 100` 行。

未完成：

1. 主人桌面人工检查导航、排版和设置交互。
2. P0-B 真实环境验收。
3. PR #4 合入并建立 `integration/lingji-v1`。
4. PR #6 重新基于正式集成分支验证后合并。

---

# 3. 默认值与 UI 强制政策

权威规范：`docs/LINGJI_V1_1_DEFAULTS_UI_POLICY.md`

凡是主人有合理理由学习、选择或调整的默认值，都必须有桌面 UI 设置入口。

每项可配置设置至少显示：

```text
名称
用途
当前有效值
系统默认值
推荐值
是否被主人覆盖
允许范围或选项
单位
为什么推荐
什么情况下修改
修改影响
是否需要重启
是否创建后台任务
性能、存储、隐私和费用影响
风险等级
恢复默认
帮助说明
```

## 3.1 单一权威流程

```text
后端 Setting Registry
→ GET /api/settings
→ React 动态渲染
→ RuntimeSettingsStore 保存主人覆盖
→ Service 解析有效值
```

禁止前端、文档和后端各保存一套互相冲突的默认值。

## 3.2 设置状态

UI 必须显示：

- 使用系统默认；
- 使用推荐值；
- 主人已修改；
- 等待保存；
- 需要重启；
- 存在风险；
- 当前不可用及原因。

## 3.3 高风险设置

以下操作必须先影响预览，再人工确认：

- 全量向量重建；
- Embedding 正式索引切换；
- 模型删除；
- 旧向量索引删除；
- 隐私索引范围扩大；
- 云端 Provider 启用；
- 自定义 Provider 网络策略；
- 审计清理；
- 模型或 Qdrant 目录迁移；
- 高频硬件遥测；
- API Key 发送到局域网或公网。

影响预览必须显示旧值、新值、依赖、任务量、空间、服务影响和回滚方式。

## 3.4 UI 映射

| 设置类别 | UI 入口 |
|---|---|
| 硬件采样与算力模式 | 系统与算力 |
| 本地模型与默认分配 | AI 与模型 |
| Embedding、覆盖率、保留期和 RRF | 语义记忆 |
| 活动保留期与采样 | 活动中心 |
| 云端 Provider、费用和轮换 | AI 与模型 / 密钥与安全 |
| 隐私向量范围 | 隐私与安全 |
| 模型、Qdrant、Raw 和备份目录 | 存储与备份 |
| 文件类型、白名单目录和大小限制 | 本地文件 |

开发治理 ADR 不作为普通运行设置。

---

# 4. 已批准的 v1.1 ADR 默认建议

| ADR | 建议默认值 | UI 路径 |
|---|---|---|
| Qdrant Local 规模 | 20 万 Point / 4 GB 黄色预警；50 万 / 8 GB 迁移评估 | 语义记忆 > 高级设置 |
| Embedding | `qwen3-embedding:0.6b`，1024 维；BGE-M3 做 A/B 对照 | AI 与模型 > Embedding |
| Source 隐私 | public/private 可本机索引；highly_sensitive 默认排除 | 隐私与安全 |
| 旧索引保留 | 30 天、至少 2 个版本、至少一次回滚演练 | 语义记忆 > 索引版本 |
| 云端 Provider | 全部默认关闭 | AI 与模型 > 云端 Provider |
| 自定义 API 网络 | localhost 显式允许；LAN 精确白名单；公网 HTTPS 同源 | AI 与模型 > 网络安全 |
| 活动保留 | 遥测 24h、事件 30d、摘要 180d、安全审计 365d | 活动中心 > 保留与清理 |
| 硬件遥测 | 前台 2s、后台 5s、空闲 30s、最小化 60s、nvidia-smi ≥10s | 系统与算力 |
| 数据目录 | 模型和 Qdrant 放 `E:\LingJiData`，禁止实时云盘同步 | 存储与备份 |
| 并行开发 | P1 先完成；P2/P3 有限并行；再 P4；最后 P5 UI | 本计划，不是运行设置 |

注意：Embedding 默认模型只有通过真实中文 Query Set、CPU/GPU 基准和新旧索引对比后，才能成为正式索引。

---

# 5. 强制开发流程

```text
研究
→ 接口与非目标
→ 失败测试
→ 证明实现前失败
→ 最小实现
→ 专项测试
→ 全量测试
→ Windows 和 CPU_ONLY
→ 真实 Demo
→ UI 与 Smoke
→ 模块报告
→ Draft PR
→ ChatGPT 验收
→ 更新本计划
```

禁止：

- `assertTrue(True)`；
- 固定打印成功的 Demo；
- 只测 Mock；
- 跳过 Windows；
- 跳过无 GPU 降级；
- 伪造截图、SHA、Run 或结果；
- 未研究就直接编码；
- 新增默认值却没有 UI；
- 前端硬编码另一套默认值。

---

# 6. Git 与并行开发

## 6.1 当前依赖链

```text
feature/extraction-hardening-web-skills-ui
└── PR #4 test/real-environment-acceptance
    └── PR #6 refactor/desktop-ui-modular-foundation
```

架构 PR #5 独立基于稳定基线。

## 6.2 P0-B 收口后

```text
合并 PR #4
→ 合并 PR #5
→ 创建 integration/lingji-v1
→ 将 PR #6 重新基于 integration/lingji-v1
→ 重新运行全量 CI
→ 人工 UI 验收
→ 合并 P1
```

## 6.3 后续分支

- 一个模块一个分支、一个 Worktree、一个 Draft PR。
- Base 为 `integration/lingji-v1`。
- 合并使用 Squash。
- 不直接推送集成分支。
- 同时编码分支最多 3 个。
- 同时修改共享热点的分支最多 1 个。

共享热点：

```text
src/control/api.py
src/control/service.py
src/control/runtime_settings.py
src/config.py
src/storage/state_db.py
src/gateway/bootstrap.py
src/gateway/memory_gateway.py
src/retrieval/hybrid.py
src/retrieval/memory_db.py
desktop 全局导航、Shell 和共享类型
数据库 Schema 与迁移
.github/workflows/
```

---

# 7. v1.1 核心实施计划

## P0：真实环境与稳定集成

状态：`REVIEW_REQUIRED`

内容：

1. 真实 Vault、ChatGPT 导出和媒体验收；
2. 合并 PR #4；
3. 合并 PR #5；
4. 整合本机未推送代码；
5. 创建 `integration/lingji-v1`；
6. 基线 CI 全绿。

验收：真实报告满足第 2.2 节条件，且没有遗留本机代码。

## P1：桌面 UI 模块化

状态：`REVIEW_REQUIRED`

代码已完成，见第 2.3 节。最终验收还需要：

- 主人桌面截图和操作；
- PR #4 收口；
- 重新基于集成分支；
- 最终 CI 全绿。

## P2：Hardware Capability Service 与算力模式

状态：`TODO`

输出：

- 操作系统、CPU、核心/线程、RAM；
- GPU、显存、驱动、CUDA 和实际 Runtime；
- 磁盘容量、类型和空间；
- Ollama、FFmpeg、Qdrant 状态；
- 静态 Capability Snapshot 和动态 Telemetry；
- 自动选择、GPU 优先、CPU_ONLY；
- `SystemAndComputePage` 和相关设置。

验收：

- RTX 4060 真机值与系统工具基本一致；
- 无 GPU 环境不致命；
- CPU_ONLY 下 FTS5、已有向量查询、Gateway 和 MCP 通过；
- GPU 失败可解释降级；
- 所有采样默认值有 UI 和帮助；
- `docs/HARDWARE_COMPUTE_MODE_REPORT.md`。

## P3：本地模型中心

状态：`TODO`

输出：

- Chat/Embedding/ASR/OCR/Vision/Reranker 分类；
- Model Registry、Inventory、Assignment；
- 静态评估、依赖检测、小规模加载、短基准、实际结论；
- 下载、暂停、恢复、目录和删除影响预览；
- `AI 与模型` 页面。

验收：

- 至少一个聊天、Embedding、ASR 和 OCR 模型真实识别；
- 预计值与实测值分开；
- 仅按显卡名称判断的测试必须失败；
- 空间不足拒绝下载；
- 活跃索引依赖模型拒绝删除；
- 所有默认模型和阈值有 UI；
- `docs/LOCAL_MODEL_CENTER_REPORT.md`。

## P4：Vector Memory Service 与混合检索

状态：`TODO`

输出：

- Qdrant Client Local Mode，`storage/qdrant/`；
- Source 和 Canonical 两个逻辑层；
- 版本化不可变 Collection；
- SQLite VectorIndexRegistry；
- Embedding Profile；
- Ollama 数组批处理；
- 持久向量任务、覆盖率、失败重试；
- QdrantSemanticProvider 接入现有 HybridRetriever；
- FTS Canonical、Vector Canonical、FTS Source、Vector Source、Substring；
- RRF、可选 Reranker、交叉验证和解释；
- FTS5 自动降级。

验收：

- `semantic_provider` 不再固定为 None；
- Qdrant 故障时 FTS5 仍返回；
- CPU_ONLY 查询已有向量；
- 真正批量请求，不是循环伪批处理；
- Source/Canonical 覆盖率独立；
- 新旧索引并存、对比、人工切换和回滚；
- 所有阈值、模型、保留和权重有 UI；
- `docs/VECTOR_MEMORY_HYBRID_RETRIEVAL_REPORT.md`。

## P5：语义记忆 UI 与活动中心

状态：`TODO`

输出：

- `语义记忆` 一级菜单；
- 关键词/语义状态、双层数量、覆盖率、模型、维度、版本、存储和设备；
- 增量同步、暂停、恢复、重试、缺失检查、测试检索、重建预览；
- `活动中心` 一级菜单；
- SQLite Event Journal + WebSocket；
- after_event_id 断线补发；
- REST 轮询降级；
- 真实任务步骤、文件、模型、设备、速度和错误；
- 未知总数不显示假百分比。

验收：

- 事件顺序和游标补发正确；
- 多客户端关闭无泄漏；
- WebSocket 故障明确降级；
- 所有按钮调用真实后端；
- 所有默认频率和保留期有 UI；
- `docs/SEMANTIC_MEMORY_ACTIVITY_CENTER_REPORT.md`。

## P6：云端 Provider 与密钥安全

状态：`TODO`

第一阶段：OpenAI、Kimi、DeepSeek、自定义 OpenAI Compatible。

要求：

- keyring 和系统安全存储；
- Backend 不可用时禁用 Provider；
- Provider Registry 固定官网、文档和账单 URL；
- Key Resolver、轮换、审计、脱敏、泄露扫描；
- API Key 不进入 Git、Obsidian、runtime settings、LocalStorage、日志或普通 SQLite；
- 所有 Provider 默认关闭并有 UI。

报告：`docs/CLOUD_PROVIDER_SECURITY_REPORT.md`。

## P7：本地文件检索

状态：`TODO`

顺序：PDF、DOCX、XLSX、PPTX、图片 OCR、代码和纯文本。

要求：

- 页码、幻灯片、工作表、单元格和代码行定位；
- 白名单目录；
- 增量更新；
- Source Collection；
- 文件状态、错误、过滤和设置 UI；
- CPU_ONLY；
- `docs/LOCAL_DOCUMENT_SEARCH_REPORT.md`。

---

# 8. 记忆可信与项目工作流支线

这些能力继续保留，按共享热点和 v1.1 主线安排，禁止重复实现已有 citation、Gateway 或 MCP。

## 8.1 可信引用、Freshness 与冲突

状态：`TODO`

- 精确来源、Heading、行号、页码和时间码；
- source_confidence、retrieval_confidence；
- verified/unverified/conflict；
- fresh/stale/deprecated；
- 类型、项目和文件覆盖规则全部有 UI；
- 冲突来源并列，不静默覆盖。

## 8.2 区块级 Markdown 写入与 Agent Task

状态：`TODO`

- block_id 或唯一 Heading；
- expected_hash；
- unified diff；
- 原子替换；
- 冲突拒绝；
- 任务幂等；
- UI Diff、批准、拒绝、重试和结果跳转。

## 8.3 MCP 项目工作流与 Context Packet v2

状态：`TODO`

- 扩展现有 MCP，不建第二套；
- 项目上下文、活跃任务、决定候选、Freshness 和 Handoff；
- Decision 只进入 `needs_review`；
- Context Packet 包含引用、过期、冲突和未验证内容。

## 8.4 后续入口

- 项目关系图；
- Windows 正式桌面打包；
- 浏览器采集增强；
- 手机分享与设备配对；
- 大型 ChatGPT/Codex 流式导入；
- 存储安全和换机恢复；
- 低侵入活动信号；
- 主动推荐和机会发现。

---

# 9. 全局验收标准

任何模块标记 `ACCEPTED` 必须满足：

1. Research Notes 完整。
2. 目标、非目标和边界明确。
3. 实现前失败测试真实有效。
4. 单元和集成测试通过。
5. Ubuntu Python 3.11/3.12 通过。
6. Windows Python 3.12 通过。
7. CPU_ONLY 或无 GPU 降级通过。
8. 前端 `npm run build` 通过。
9. UI 有导航、Loading、Empty、Error、Success 和 Disabled。
10. 所有可配置默认值有 UI、解释和恢复默认。
11. 高风险修改有影响预览、确认和回滚。
12. 有真实 Demo，不使用固定成功输出。
13. 不破坏 Vault、Raw、Backup 和主人维护的 Markdown。
14. 有性能、容量、隐私和安全边界。
15. 有模块 Markdown 报告。
16. 修改和复用文件清单完整。
17. 已知限制和回滚完整。
18. Draft PR 和 CI Run 真实可验证。
19. 主人无需修改源码即可使用。
20. 本计划记录验收结论。

---

# 10. 禁止修改或重复建设

必须复用：

- FastAPI Control API；
- LocalControlService；
- RuntimeSettingsStore；
- MemoryGateway；
- HybridRetriever；
- SQLiteExtractionQueue；
- MemoryDatabase；
- StateDatabase 和事件审计；
- Tauri + React 控制中心；
- 现有 Provider、备份和存储生命周期。

禁止：

- 第二套控制台、任务队列、Memory Gateway 或 Runtime Settings；
- UI 直接操作 SQLite、Qdrant 或 keyring；
- API Key 写入普通配置、日志、Obsidian 或 LocalStorage；
- Docker 作为第一版强制依赖；
- GPU 作为基础系统依赖；
- 模拟数字冒充状态；
- 直接覆盖正式 Embedding Collection；
- 未验证的新索引自动切换；
- 自动删除最后一个可回滚索引；
- 一次性巨型 PR 完成 P2-P7；
- 全仓无关格式化；
- 覆盖或重写 v1.0。

---

# 11. 当前下一动作

```text
主人电脑完成 P0-B 真实资料只读验收
→ 审查真实报告
→ 合并 PR #4
→ 合并架构与默认值政策 PR #5
→ 创建 integration/lingji-v1
→ 重新基于集成分支整理 PR #6
→ 主人桌面人工验收 P1
→ P1 ACCEPTED
→ 开始 P2 Hardware Capability Service
→ P2 契约稳定后有限并行 P3 Model Registry/Inventory
```

在 P0-B 和 P1 收口前，不启动 P4/P5 生产编码。研究和数据契约可以准备，但不能向共享热点堆入未验收实现。
