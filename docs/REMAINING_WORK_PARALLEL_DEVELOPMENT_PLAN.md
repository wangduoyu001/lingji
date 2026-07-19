# 灵机后续开发、实施与验收总计划

> 版本：`v2.5`  
> 日期：`2026-07-20`  
> 仓库：`wangduoyu001/lingji`  
> 稳定基线：`feature/extraction-hardening-web-skills-ui`  
> 当前堆叠：`PR #4 → PR #6 → PR #7 → PR #8`  
> 架构增补：`PR #5`  
> 长期权威源：Obsidian Markdown

---

# 1. 全局规则

1. 先研究官方资料和至少三个仍维护的类似项目。
2. 先写失败测试，再做最小实现。
3. 每个模块必须有独立分支、Draft PR、测试、Demo、UI、报告、风险和回滚。
4. Linux、Windows、无 GPU 或 CPU_ONLY、桌面构建必须通过。
5. 主人需要操作的功能必须在桌面 UI 中有入口、状态、错误和帮助。
6. 所有主人可调整默认值必须显示当前值、默认值、推荐值、原因、影响和恢复默认。
7. 未经真实环境和人工验收，不得标记 `ACCEPTED`。
8. 禁止模拟 SHA、CI、进度、状态和固定成功输出。
9. 禁止建立第二套控制台、任务队列、Memory Gateway 或设置系统。
10. Obsidian 是长期权威源；SQLite、Qdrant 和缓存属于可重建派生层。

状态：`TODO`、`RESEARCHING`、`IN_PROGRESS`、`REVIEW_REQUIRED`、`CHANGES_REQUIRED`、`ACCEPTED`、`BLOCKED`、`DEFERRED`。

---

# 2. 当前状态

| 模块 | 状态 | 分支 / PR | 当前结论 |
|---|---|---|---|
| P0 Windows DB Lifecycle | `ACCEPTED` | PR #3 | 已合并，Windows 文件锁修复 |
| P0-B 真实环境只读验收 | `REVIEW_REQUIRED` | PR #4 | 自动 CI 全绿，等待主人真实资料 |
| v1.1 架构与默认值 UI 政策 | `REVIEW_REQUIRED` | PR #5 | 只改文档，不覆盖 v1.0 |
| P1 桌面 UI 模块化 | `REVIEW_REQUIRED` | PR #6 | 代码 CI 全绿，等待主人 UI 和正式集成 |
| P2 硬件与算力模式 | `REVIEW_REQUIRED` | PR #7 | 最终 CI 全绿，等待 RTX 4060 真机和正式集成 |
| P3 本地模型中心第一增量 | `REVIEW_REQUIRED` | PR #8 | 只读 Registry/Inventory 与 UI 全绿，等待真机清单 |
| P3 模型兼容与安全操作 | `TODO` | 后续独立 PR | 加载测试、短基准、下载和删除保护尚未开始 |
| P4 向量记忆与混合检索 | `TODO` | 待建立 | 依赖 P2/P3 稳定契约 |
| P5 语义记忆与活动中心 | `TODO` | 待建立 | 依赖 P1/P4 |
| P6 云端 Provider 与密钥安全 | `TODO` | 待建立 | 本地优先，默认关闭 |
| P7 本地文件检索 | `TODO` | 待建立 | PDF、Office、图片和代码 |
| 微信聊天 | `DEFERRED` | `wechat_chat` | 只保留 Provider 接口 |

当前真实缺口：

- 主人 Vault、ChatGPT 导出和媒体尚未真机验收；
- P1 尚未主人桌面验收；
- P2 尚未核对 RTX 4060、CUDA、磁盘和 Ollama 真值；
- P3 尚未核对主人真实 Ollama 清单，未实现加载和基准；
- HybridRetriever 仍以 `semantic_provider=None` 启动；
- Qdrant、双层向量索引、真正批量 Embedding 未实现；
- WebSocket 活动流、云端 Provider、本地 Office/PDF/代码检索未实现。

---

# 3. 最近验收记录

## P0-B

- PR #4；
- 严格只读检查 Vault、SQLite、导出和媒体；
- 唯一持久写入为验收报告和审计事件；
- 通过条件：`error_count=0`、`inputs_unchanged=true`、真实导出和媒体识别成功。

## P1

- PR #6；
- Head `8b1c5380fc02d733f6c6b357c3c32546082839fc`；
- Run `29696837874` 全绿；
- Windows `113 tests / OK`；
- App Shell、pages、components、hooks、types、正式导航和设置基础已拆分；
- 报告：`docs/DESKTOP_UI_MODULARIZATION_REPORT.md`。

剩余：主人检查导航、排版和设置交互；P0-B 后重新基于正式集成分支。

## P2

- PR #7；
- 最终 Head `c2590a9d5af9decf1a69aadc310867eaaca80bd0`；
- 最终 Run `29699277515` 全绿；
- Windows `118 tests / OK`；
- 检测系统、CPU、内存、磁盘、NVIDIA GPU、显存、驱动、CUDA、Ollama、FFmpeg、FFprobe 和 Qdrant Client/目录；
- 无 GPU、无 psutil、Ollama 离线时降级；
- 算力模式、设置和“系统与算力”页面完成；
- 静态缓存、遥测缓存和 GPU 检测最短间隔随主人设置生效；
- 报告：`docs/HARDWARE_COMPUTE_MODE_REPORT.md`。

剩余：RTX 4060/CUDA/磁盘/Ollama 真机核对、主人操作算力模式、正式集成复验。

## P3 第一增量

- PR #8；
- 验证 Head `00d57747136868044cc70414420ec8f29b990f2e`；
- Run `29699695259` 全绿；
- Windows `123 tests / OK`；
- 新增模型专项测试 5 项；
- Linux、Windows、Desktop UI、TypeScript、Vite、Tauri、MCP、浏览器扩展和 Obsidian 插件全部成功；
- 报告：`docs/LOCAL_MODEL_CENTER_REPORT.md`。

已完成：

1. 六类模型用途和 Provider Registry；
2. Ollama 安装清单、运行状态、显存证据和官方能力；
3. 参数规模、量化、Embedding 维度和上下文；
4. 配置中缺失模型明确显示；
5. faster-whisper/PaddleOCR 包、配置和路径状态；
6. 所有兼容性保持 `unverified`；
7. FastAPI Registry、Inventory 和只读刷新；
8. “AI 与模型”一级页面；
9. 下载、删除、测速和正式切换未伪装成可用。

剩余：主人真实 Ollama 清单、静态资源估算、实际加载、短基准、Model Assignment、空间检查、下载/删除保护和正式集成复验。

---

# 4. 默认值 UI 政策

统一流程：

```text
后端 Setting Registry
→ FastAPI settings
→ React 动态展示
→ RuntimeSettingsStore 保存主人覆盖
→ Service 使用有效值
```

每项设置至少显示：名称、用途、当前值、默认值、推荐值、范围、单位、推荐原因、修改时机、性能/存储/隐私/费用影响、风险和恢复默认。

高风险修改必须先显示影响预览和回滚方式，再人工确认。

已批准建议：

| 类别 | 建议默认值 |
|---|---|
| Qdrant 规模 | 20 万 Point / 4 GB 预警；50 万 / 8 GB 迁移评估 |
| Embedding | `qwen3-embedding:0.6b`，1024 维；BGE-M3 对照 |
| Source 隐私 | public/private 本机索引；highly_sensitive 默认排除 |
| 旧索引 | 30 天、至少 2 个版本、至少一次回滚 |
| 云端 Provider | 全部默认关闭 |
| 活动保留 | 遥测 24h、事件 30d、摘要 180d、安全审计 365d |
| 硬件采样 | 前台 2s、后台 5s、空闲 30s、最小化 60s、GPU 命令 ≥10s |
| 数据目录 | `E:\LingJiData`，禁止实时同步活跃数据库 |

---

# 5. Git 与并行边界

```text
feature/extraction-hardening-web-skills-ui
└── PR #4 test/real-environment-acceptance
    └── PR #6 refactor/desktop-ui-modular-foundation
        └── PR #7 feature/hardware-capability-service
            └── PR #8 feature/local-model-registry-inventory
```

PR #5 独立基于稳定基线。

P0-B 通过后：

```text
合并 PR #4 和 PR #5
→ 创建 integration/lingji-v1
→ 重新整理 PR #6、#7、#8
→ 全量 CI
→ 主人 P1/P2/P3 UI 与真机验收
```

同时编码分支最多 3 个；同时修改共享热点的分支最多 1 个。

共享热点：Control API、LocalControlService、RuntimeSettingsStore、MemoryGateway、HybridRetriever、StateDatabase、数据库迁移、桌面全局导航和 CI。

---

# 6. P0-P7 实施计划

## P0 真实环境与稳定集成

状态：`REVIEW_REQUIRED`。

完成真实资料只读验收、合并 PR #4/#5、整合本机代码、创建 `integration/lingji-v1`、全量 CI。

## P1 桌面 UI 模块化

状态：`REVIEW_REQUIRED`。

代码已完成。剩余主人 UI 验收和正式集成复验。

## P2 硬件与算力模式

状态：`REVIEW_REQUIRED`。

代码和最终自动 CI 已完成。剩余 RTX 4060/CUDA/磁盘/Ollama 真机核对、CPU_ONLY/GPU 优先操作验收和正式集成复验。

## P3 本地模型中心

第一增量状态：`REVIEW_REQUIRED`。

下一增量在等待真机期间允许：

- Model Assignment 数据契约；
- 静态 RAM/显存估算，必须标记低置信度；
- 加载测试和基准结果的数据模型与失败测试；
- 下载、删除、路径迁移的影响预览契约；
- 所有相关默认值的设置定义和 UI 说明。

暂不允许：

- 真正下载或删除模型；
- 自动加载大型模型；
- 输出正式兼容结论；
- 修改 Embedding 正式索引。

## P4 向量记忆与混合检索

状态：`TODO`。

Qdrant Local Mode、Source/Canonical 双层版本化 Collection、Embedding Profile、真正数组批处理、持久任务、覆盖率、失败重试、接入现有 HybridRetriever、RRF、解释和 FTS5 降级。

## P5 语义记忆与活动中心

状态：`TODO`。

语义记忆页面、双层覆盖率、增量同步、重建预览、SQLite Event Journal、WebSocket、断线补发、REST 降级和真实任务进度。

## P6 云端 Provider 与安全

状态：`TODO`。

第一阶段支持 OpenAI、Kimi、DeepSeek 和自定义兼容服务。使用系统安全存储、固定 Provider Registry、轮换、审计和脱敏。所有 Provider 默认关闭。

## P7 本地文件检索

状态：`TODO`。

依次完成 PDF、DOCX、XLSX、PPTX、图片 OCR、代码和纯文本，保留页码、幻灯片、工作表、单元格和代码行定位。

---

# 7. 全局验收标准

模块标记 `ACCEPTED` 必须满足：

- Research、边界、失败测试、最小实现完整；
- Linux、Windows、CPU_ONLY 或无 GPU 通过；
- 桌面 Build、Smoke 和人工 UI 通过；
- 所有默认值有 UI 和真实生效路径；
- 高风险操作有预览、确认和回滚；
- 有真实 Demo、模块报告、已知限制；
- 不破坏 Vault、Raw、Backup 和主人 Markdown；
- Draft PR、SHA 和 CI Run 可验证；
- 主人无需修改源码即可使用。

禁止 UI 直接操作 SQLite、Qdrant、系统密钥存储或系统命令；禁止 Docker/GPU 成为第一版强制依赖；禁止覆盖正式索引、自动切换未验证索引、删除最后可回滚版本和巨型 PR。

---

# 8. 当前下一动作

```text
等待 PR #8 文档收尾 CI
→ 可继续 P3 下一增量的数据契约和失败测试
→ 不执行真实下载、删除、大模型加载或正式兼容判定
→ 主人方便时完成 P0-B
→ 建立正式集成基线并重新验证 P1/P2/P3
```
