# LingJi Personal Memory OS Architecture v1.1 增补方案

> 中文名称：灵机个人记忆操作系统 v1.1 增补方案  
> 文档类型：对《灵机第二大脑总体功能架构与落地解决方案 v1.0》的增量补充  
> 仓库：`wangduoyu001/lingji`  
> 当前有效开发基线：`feature/extraction-hardening-web-skills-ui`  
> 本文档分支：`docs/architecture-v1.1-hardware-model-vector-control`  
> 状态：`ARCHITECTURE_PROPOSAL`  
> 更新日期：`2026-07-20`  
> 长期权威源：Obsidian Markdown  
> 派生状态：SQLite、Qdrant 和缓存必须可删除、可重建

---

# 0. 文档边界

## 0.1 本文不做什么

本文禁止覆盖、替换或重新解释 v1.0。

v1.0 继续负责定义：

- 灵机的总体定位；
- Capture Hub、Processing Bus、Memory Gateway、Console 等总体结构；
- Obsidian、SQLite、Git、对象存储、采集、处理、记忆、项目、MCP、备份恢复等长期架构；
- Obsidian Markdown 作为长期权威源；
- SQLite 保存索引、任务状态、来源映射、审计和可重建状态；
- AI 不能绕过主人确认直接篡改正式记忆和正式决定。

v1.1 只增加以下四类设计：

1. 硬件能力检测与算力模式；
2. 本地模型和云端模型管理；
3. 双层向量记忆与真正的混合检索；
4. 可视化运行控制、实时活动流和相关 UI。

本文没有把规划功能描述为已经实现，也不授权一次性大规模重写。

## 0.2 v1.1 的核心目标

让主人可以在桌面 UI 中明确看到并控制：

- 电脑有什么算力；
- 哪些模型能运行、实际运行在哪个设备；
- 当前使用哪个模型、为什么选择它；
- 哪些资料已经生成语义索引；
- 原始证据和正式记忆如何分别召回；
- 当前任务正在解析、分块、生成向量还是等待确认；
- Qdrant、Ollama、FFmpeg、GPU 或云端 Provider 故障时系统如何降级；
- API Key 是否安全、何时轮换、谁使用过；
- 每个检索结果为什么被找到。

## 0.3 设计原则

1. **CPU 始终可用**：GPU 是加速器，不是基础记忆检索的依赖。
2. **Obsidian 始终权威**：Qdrant 和 SQLite 都是派生层。
3. **真实状态优先**：禁止模拟进度、固定数字和装饰性“运行中”。
4. **渐进增强**：FTS5 必须在 Qdrant、Embedding 或 GPU 故障时继续工作。
5. **版本化索引**：Embedding 模型变化不得直接覆盖正式向量索引。
6. **最小修改**：复用现有 Service、Gateway、Queue、Retriever、API 和桌面控制中心。
7. **安全默认关闭**：密钥存储不可用时禁用云端 Provider，不允许回退到明文配置。
8. **可解释检索**：每条结果必须暴露召回通道、过滤和排序原因。
9. **可回滚**：模型切换、索引切换、下载、删除和 Provider 变更均有预览、确认和恢复路径。
10. **先验收真实环境**：P0 真机验收完成前，不得宣称 v1.1 已进入正式运行。

---

# 1. 与 v1.0 的继承关系

## 1.1 保持不变的权威关系

```text
Obsidian Markdown
    长期权威内容、正式项目、正式决定、主人确认的规则

SQLite
    全文索引、任务状态、运行配置、来源映射、模型元数据、审计和活动事件

Qdrant
    可重建语义向量、Payload 和向量索引版本

Raw / Source Files
    原始证据、网页快照、聊天导出、文档、媒体和转写

Memory Gateway
    所有 AI 访问记忆的统一权限和检索入口

FastAPI Control API
    UI、Tauri、浏览器扩展和本地工具的统一控制接口
```

## 1.2 v1.1 在 v1.0 中的位置

```text
v1.0 Capture Hub
    ↓
现有 Processing Bus / SQLiteExtractionQueue
    ↓
新增 Hardware Capability Service
新增 Model Runtime Service
新增 Vector Memory Service
新增 Cloud Model Provider Service
新增 Activity Event Stream
    ↓
扩展现有 HybridRetriever / MemoryGateway
    ↓
扩展现有 FastAPI Control API
    ↓
扩展现有 React + Tauri 控制中心
```

v1.1 不是第二套后端、第二套队列、第二套记忆网关或第二个控制台。

## 1.3 v1.1 对 v1.0 的兼容承诺

- 不启用向量服务时，现有 FTS5 检索保持可用。
- 不安装 GPU 驱动时，基础检索、MCP、Obsidian、文件扫描和已生成向量查询保持可用。
- 不配置云端 API 时，本地模式保持可用。
- 删除 `storage/qdrant/` 后，可以从权威 Markdown、原始资料和 SQLite 映射重新生成。
- 删除模型运行缓存后，不损坏正式记忆。
- 升级 Embedding 模型时，旧索引在主人确认切换前继续服务。

---

# 2. 当前仓库已有能力

以下能力在当前有效基线中已经存在，不得重复建设。

## 2.1 记忆与检索基础

- 单一 Obsidian Vault；
- SQLite FTS5 全文索引；
- 中文子串补充搜索和元数据排序；
- `MemoryDatabase`；
- `HybridRetriever` 的词法检索、RRF 融合框架和可选 `SemanticProvider` 协议；
- `MemoryGateway` 和权限配置；
- Context Pack；
- MCP 服务；
- 增量 Vault 和 Memory DB 同步；
- 引用路径、Heading 和 Markdown 行号基础字段。

当前 `HybridRetriever` 已经定义可选语义 Provider，并能把 `lexical`、`semantic` 写入 `retrieval_channels`；但启动构造时仍明确传入 `semantic_provider=None`。

## 2.2 数据入口和处理基础

- ChatGPT 导出导入；
- Codex 工作报告写回；
- 网页和社交页面采集框架；
- 本地媒体采集和派生框架；
- faster-whisper、PaddleOCR、PySceneDetect 可选 Provider；
- SQLiteExtractionQueue 的任务状态、重试、租约和进度；
- Raw、Derived、备份、恢复和审计。

## 2.3 控制和 UI 基础

- FastAPI 本地控制接口；
- LocalControlService；
- RuntimeSettingsStore；
- React + Tauri 桌面控制中心原型；
- 总览、任务、投喂、媒体、存储、备份、设置和日志页面；
- Linux、Windows、MCP、浏览器扩展、Obsidian 插件和桌面 UI CI。

## 2.4 当前 Embedder 基础

当前 `Embedder` 已有：

- Ollama 主模型和备用模型；
- 内存缓存；
- 失败后模型回退；
- 状态和切换记录；
- `embed_batch()` 方法名。

但 `embed_batch()` 实际只是逐条调用 `embed()`；当前还使用旧式单文本请求，不具备真正数组批处理、持久任务、覆盖率、重试队列、Collection 切换和 UI 进度。

---

# 3. 当前仓库缺失能力

## 3.1 语义检索缺失

- `HybridRetriever` 启动时 `semantic_provider=None`；
- Qdrant 未接入 Memory Gateway；
- 没有 `VectorMemoryService`；
- 没有原始资料层和正式记忆层独立向量索引；
- 没有向量覆盖率、失败任务和索引版本；
- 没有 Embedding 模型迁移流程；
- 没有真实语义检索 UI；
- 没有语义召回和词法召回对比验收。

## 3.2 硬件和模型缺失

- 没有统一硬件能力快照；
- 没有 CPU、RAM、GPU、显存、CUDA、驱动和实时负载完整检测；
- 没有模型兼容性实测；
- 没有全局算力模式；
- 没有本地模型安装、下载、基准、删除和依赖影响管理；
- 没有模型用途分类和默认分配；
- 没有云端 Provider 的真实调用服务；
- 没有系统级安全密钥存储和轮换。

## 3.3 可视化运行缺失

- UI 主要依靠手动刷新和定时轮询；
- 没有统一 WebSocket 活动流；
- 没有活动事件持久游标；
- 没有解析、分块、Embedding、向量同步、蒸馏和审核的真实流水线展示；
- 没有 CPU/GPU、模型、速度和实际完成量的统一任务状态。

## 3.4 真实环境与本地文件缺失

- 主人真实 Vault、ChatGPT 导出和媒体样例尚未完成最终真机验收；
- PDF、Word、Excel、PowerPoint、图片和代码全文检索尚未完成；
- 非 Markdown 文档的页码、幻灯片、工作表、单元格和代码行定位尚未完成。

---

# 4. v1.1 总体新增架构

```text
┌────────────────────────────────────────────────────────────┐
│                    React + Tauri Control Center             │
│ 系统与算力 │ AI与模型 │ 语义记忆 │ 活动中心 │ Provider安全 │
└───────────────────────────┬────────────────────────────────┘
                            │ REST + WebSocket
┌───────────────────────────▼────────────────────────────────┐
│                    FastAPI Control API                      │
│ hardware / compute / models / vectors / providers / events │
└───────────────────────────┬────────────────────────────────┘
                            │
┌───────────────────────────▼────────────────────────────────┐
│                    LocalControlService                      │
│  统一编排，不承载重复业务逻辑                               │
└───────┬──────────────┬───────────────┬─────────────────────┘
        │              │               │
┌───────▼──────┐ ┌─────▼────────┐ ┌────▼──────────────────┐
│ Hardware     │ │ Model Runtime │ │ Cloud Provider        │
│ Capability   │ │ & Benchmark   │ │ & Secret Resolver     │
└───────┬──────┘ └─────┬────────┘ └────┬──────────────────┘
        │              │               │
        └──────────────┼───────────────┘
                       │
┌──────────────────────▼────────────────────────────────────┐
│ Existing SQLiteExtractionQueue + Activity Event Journal    │
│ 模型下载、基准、Embedding、索引同步仍复用同一任务系统       │
└──────────────────────┬────────────────────────────────────┘
                       │
┌──────────────────────▼────────────────────────────────────┐
│ Vector Memory Service                                     │
│ Source Collection │ Canonical Collection │ Index Registry │
└──────────────────────┬────────────────────────────────────┘
                       │ SemanticProvider
┌──────────────────────▼────────────────────────────────────┐
│ Existing HybridRetriever                                  │
│ FTS Canonical + Vector Canonical + FTS Source + Vector Src │
│ Filters + RRF + Optional Reranker + Explanation            │
└──────────────────────┬────────────────────────────────────┘
                       │
┌──────────────────────▼────────────────────────────────────┐
│ Existing MemoryGateway / MCP / Context Pack                │
└───────────────────────────────────────────────────────────┘
```

---

# 5. Hardware Capability Service

## 5.1 模块定位

建立统一硬件能力检测服务，分成两类数据：

1. **Capability Snapshot 静态能力快照**：设备型号、核心数、总内存、总显存、驱动、CUDA、磁盘和工具版本。
2. **Resource Telemetry 动态资源状态**：CPU、RAM、GPU、显存、磁盘剩余和当前任务占用。

不能把静态规格和动态负载混成一个模糊的“可用/不可用”。

## 5.2 推荐后端模块

```text
src/hardware/
├── __init__.py
├── service.py                 # HardwareCapabilityService
├── models.py                  # 数据契约
├── cpu_memory.py              # psutil/platform
├── gpu.py                     # NVML，可选；nvidia-smi 回退
├── disk.py                    # 容量、文件系统、介质类型
├── toolchain.py               # Ollama/FFmpeg/Qdrant/CUDA
├── telemetry.py               # 有界频率动态采样
└── compatibility.py           # 模型兼容性编排
```

## 5.3 数据来源

- 操作系统和 Python：`platform`、`sys`；
- CPU、线程、RAM、磁盘和负载：`psutil`；
- NVIDIA GPU：优先 NVML，失败时调用 `nvidia-smi --query-* --format=csv,noheader,nounits`；
- CUDA：驱动报告、运行时库和实际 Provider Probe 分开记录；
- 磁盘介质类型：Windows CIM/PowerShell 或平台接口；无法可靠确定时返回 `unknown`，不得猜测；
- Ollama：`/api/tags` 和短请求；
- FFmpeg：`ffmpeg -version`、`ffprobe -version`；
- Qdrant Local：客户端可打开、Collection 可读取；
- Qdrant Server：健康和版本接口。

## 5.4 硬件数据模型

```text
HardwareSnapshot
- snapshot_id
- collected_at
- os_name
- os_version
- architecture
- python_version
- cpu_model
- physical_cores
- logical_threads
- memory_total_bytes
- memory_available_bytes
- gpu_devices[]
- disks[]
- toolchains[]
- warnings[]
- collection_sources[]
```

```text
GpuDevice
- gpu_id
- vendor
- name
- total_vram_bytes
- free_vram_bytes
- used_vram_bytes
- utilization_percent
- temperature_c
- driver_version
- cuda_driver_version
- runtime_available
- detection_source
- detection_error
```

```text
DiskDevice
- mount
- filesystem
- media_type: ssd | hdd | removable | network | unknown
- total_bytes
- free_bytes
- read_only
- detection_source
```

## 5.5 模型兼容性判断

禁止只按显卡名称或参数规模输出“能运行”。

每次兼容性判断必须经过：

```text
阶段 1：静态规格评估
    模型格式、量化、预计 RAM、预计显存、上下文、Provider要求

阶段 2：依赖检测
    Provider、驱动、CUDA/DirectML/CPU Runtime、模型文件完整性

阶段 3：小规模加载测试
    加载模型或最小权重，验证实际设备、内存和错误

阶段 4：短基准测试
    使用固定小样本，记录速度、峰值 RAM/显存、稳定性和降级情况

阶段 5：输出结论
    compatible / compatible_with_limits / cpu_only / unavailable / unverified
```

结论必须包含：

- `assessment_level`；
- `effective_device`；
- `tested_at`；
- `benchmark_id`；
- `limitations`；
- `failure_reason`；
- `estimated` 与 `measured` 字段分离。

## 5.6 采样频率和性能边界

- 静态快照：启动、手动刷新、驱动或模型变化后；
- 动态采样：默认 2 秒，UI 隐藏时降到 10 秒；
- 不在每个 API 请求中重新调用 `nvidia-smi`；
- NVML/psutil 采样失败时保留上次成功值并标记 stale；
- 活动流发送差异事件，不每次发送完整硬件快照。

---

# 6. 全局算力模式

## 6.1 用户可选模式

```text
AUTO             自动选择
GPU_PREFERRED    GPU 优先
CPU_ONLY         仅使用 CPU
```

UI 中文显示：

1. 自动选择；
2. GPU 优先；
3. 仅使用 CPU。

## 6.2 解析规则

算力模式只表达主人偏好，最终设备选择由 `ComputePolicyResolver` 输出。

```text
用户全局模式
+ 任务类型
+ Provider 支持
+ 实际硬件状态
+ 模型兼容性测试
+ 当前资源阈值
+ 每任务临时覆盖
= effective_device
```

每项任务必须记录：

- `requested_compute_mode`；
- `effective_device`；
- `fallback_reason`；
- `gpu_id`；
- `provider`；
- `resource_snapshot_id`。

## 6.3 CPU_ONLY 保证

仅使用 CPU 时必须继续运行：

- SQLite FTS5；
- 已生成的 Qdrant 向量查询；
- 文件扫描和解析；
- Obsidian 读取；
- Memory Gateway；
- MCP；
- 正式记忆召回；
- 项目、来源、隐私和时间过滤；
- 任务、日志、备份和审计。

CPU_ONLY 可以降低或关闭：

- 大批量向量生成速度；
- ASR 速度；
- OCR 速度；
- 视觉理解速度；
- 本地大模型速度；
- 全量蒸馏和重建速度。

## 6.4 GPU 故障策略

```text
GPU 任务失败
→ 判断是否允许 CPU fallback
→ 记录 provider_unavailable / resource_warning
→ 可降级任务改为 CPU 并继续
→ 不可降级任务进入 retrying 或 failed
→ 基础检索继续使用 FTS5 和已有向量
```

不得因为 GPU 驱动、CUDA 或显存错误关闭 Memory Gateway。

---

# 7. AI 与模型中心

## 7.1 一级菜单

桌面 UI 新增一级菜单：

```text
AI 与模型
```

页面内部使用标签：

- 本地模型；
- 云端 Provider；
- 模型分配；
- 兼容性与基准；
- 下载任务；
- 密钥与安全。

## 7.2 模型用途分类

```text
chat_reasoning
embedding
asr
ocr
vision
reranker
```

显示中文：

- 对话与推理模型；
- Embedding 语义索引模型；
- ASR 语音识别模型；
- OCR 模型；
- 视觉理解模型；
- Reranker 重排模型。

## 7.3 推荐后端模块

```text
src/models/
├── __init__.py
├── registry.py                # ModelRegistry，定义用途和 Provider
├── inventory.py               # 已安装模型扫描
├── runtime.py                 # ModelRuntimeService
├── compatibility.py           # 兼容性评估
├── benchmark.py               # 固定短基准
├── downloads.py               # 复用 SQLiteExtractionQueue
├── assignments.py             # 默认模型和任务模型分配
├── impact.py                  # 删除/切换影响预览
└── providers/
    ├── ollama.py
    ├── faster_whisper.py
    ├── paddleocr.py
    ├── scene_detect.py
    └── optional_runtime.py
```

## 7.4 模型记录

```text
ModelDefinition
- model_id
- display_name
- provider_id
- capability
- family
- parameter_count
- quantization
- embedding_dimension
- source_registry
- license
- official_url
- expected_ram_bytes
- expected_vram_bytes
- install_method
- removable
```

```text
ModelInstallation
- installation_id
- model_id
- provider_id
- local_path
- installed
- size_bytes
- installed_at
- checksum_status
- version
- last_error
```

```text
ModelCompatibilityResult
- model_id
- snapshot_id
- assessment_level
- status
- requested_device
- effective_device
- estimated_ram_bytes
- measured_peak_ram_bytes
- estimated_vram_bytes
- measured_peak_vram_bytes
- benchmark_id
- limitations
- error_code
- tested_at
```

```text
ModelBenchmark
- benchmark_id
- model_id
- capability
- device
- input_profile
- duration_ms
- throughput
- peak_ram_bytes
- peak_vram_bytes
- output_valid
- error
- measured_at
```

## 7.5 UI 必须显示

每个本地模型显示：

- 模型名称；
- Provider；
- 用途；
- 是否安装；
- 模型大小；
- 参数规模；
- 量化等级；
- 预计 RAM；
- 预计显存；
- 实测 RAM；
- 实测显存；
- 适配结论；
- 当前运行设备；
- 最近测速；
- 最近错误；
- 当前任务；
- 关联正式索引。

## 7.6 操作

- 设置默认模型；
- 测试运行；
- 运行短基准；
- 下载；
- 暂停下载；
- 恢复下载；
- 查看模型目录；
- 删除模型；
- 查看相关任务；
- 查看依赖该模型的索引和配置。

## 7.7 下载与删除安全

下载前：

```text
检查目标盘空间
→ 预估临时空间和最终空间
→ 检查网络和来源
→ 创建可暂停任务
→ 下载到临时文件
→ 校验大小/哈希
→ 原子移动到正式目录
```

删除前必须显示：

- 模型大小；
- 当前是否运行；
- 是否为默认模型；
- 哪些任务依赖；
- 哪些向量索引依赖；
- 删除后是否可重新下载；
- 是否保留缓存和基准；
- 释放空间。

不得删除正在服务正式向量索引的 Embedding 模型，除非已经切换并完成归档。

## 7.8 Embedding 模型切换

Embedding 模型不是普通聊天模型，不允许直接覆盖切换。

推荐流程：

```text
选择新 Embedding 模型
→ 创建 embedding_profile
→ 创建版本化 Source Collection
→ 创建版本化 Canonical Collection
→ 持久任务批量生成
→ 计算覆盖率和失败率
→ 使用固定 Query Set 对比新旧检索
→ 输出质量、速度、占用报告
→ 主人确认
→ 更新 Active Index Registry
→ 新查询使用新索引
→ 旧索引进入 recoverable_archived
→ 保留策略到期后才允许删除
```

### Local Mode 的重要修正

Qdrant Server 可以使用 Collection Alias，但 Local Mode 的能力和 Server 并非完全等价。因此 v1.1 不把 Alias 作为唯一切换机制。

统一使用：

```text
VectorIndexRegistry（SQLite）
- logical_index: source | canonical
- active_collection
- previous_collection
- embedding_profile_id
- status
- switched_at
```

Server Mode 可额外同步 Qdrant Alias；Local Mode 只依赖 Registry 指针。

Collection 名称推荐：

```text
lingji_source_chunks__<embedding_profile>__v<generation>
lingji_canonical_memories__<embedding_profile>__v<generation>
```

---

# 8. Cloud Model Provider Service

## 8.1 范围

第一阶段：

- OpenAI；
- Kimi；
- DeepSeek；
- 自定义 OpenAI Compatible API。

第二阶段：

- Gemini；
- Anthropic；
- 通义百炼。

第一阶段不要求所有 Provider 支持完全相同的模型能力。统一层必须声明实际能力，不得伪装兼容。

## 8.2 推荐后端模块

```text
src/cloud_providers/
├── __init__.py
├── registry.py                # 固定 Provider Registry
├── service.py                 # CloudModelProviderService
├── capabilities.py            # 能力矩阵
├── secret_store.py            # keyring 封装
├── key_resolver.py            # 请求瞬时读取 active key
├── rotation.py                # 轮换状态机
├── client.py                  # 统一 HTTP Client
├── middleware.py              # 敏感头剥离和请求审计
├── audit.py                   # 调用审计
├── redaction.py               # SensitiveDataFilter
├── leak_detection.py          # 日志泄露扫描
├── registry_urls.py           # 官方页面白名单
└── providers/
    ├── openai.py
    ├── kimi.py
    ├── deepseek.py
    └── openai_compatible.py
```

## 8.3 Provider UI 字段

- 启用开关；
- API Key 状态；
- 脱敏 Key 指纹；
- Base URL；
- 测试连接；
- 拉取模型列表；
- 默认模型；
- 支持能力；
- 最近调用；
- Token 输入/输出；
- 估算成本；
- 错误；
- 上次轮换；
- 建议轮换；
- 打开官方控制台；
- 打开 API 文档；
- 打开账单或充值页面。

## 8.4 Provider Registry

一键打开页面必须来自代码内固定 Registry：

```text
ProviderRegistryEntry
- provider_id
- display_name
- default_base_urls[]
- console_url
- api_docs_url
- billing_url
- model_list_strategy
- capabilities
- allowed_auth_scheme
```

自定义 OpenAI Compatible API 可以填写 Base URL，但：

- “打开官网”按钮不接受用户任意 URL；
- 默认禁止将 Authorization 发送到重定向后的不同主机；
- 重定向必须禁用或严格同源；
- TLS 校验默认开启；
- 私有网段和 localhost 必须显式标记为本地兼容服务；
- 云端 Provider 默认拒绝私有网段，防止 SSRF 和误发密钥。

## 8.5 密钥存储

所有 API Key 使用系统安全存储：

- Windows Credential Manager / Credential Locker；
- macOS Keychain；
- Linux Secret Service；
- Python `keyring` 作为统一适配层。

如果安全 Backend 不可用：

```text
Provider 状态 = secret_store_unavailable
禁止保存 Key
禁止启用 Provider
UI 提示安装或解锁系统密钥服务
绝不回退到明文文件
```

数据库只保存：

```text
provider_id
secret_reference
key_fingerprint
last_rotated_at
rotation_due_at
status
created_at
updated_at
```

### 指纹修正

不保存普通 SHA-256(Key)。推荐：

```text
key_fingerprint = HMAC-SHA256(installation_pepper, api_key)
```

`installation_pepper` 也存放在系统 keyring。该指纹只用于变更检测和脱敏识别。

## 8.6 运行时密钥使用

```text
Cloud 请求开始
→ KeyResolver 根据 provider_id 解析 active secret_reference
→ 从 keyring 读取 Key
→ 构造仅本次请求使用的 Authorization Header
→ HTTP Middleware 发出请求
→ 审计记录脱敏 key_reference
→ 清除请求对象和局部引用
```

必须诚实说明：Python 运行时无法可靠保证字符串立即从进程内存物理清零。v1.1 的保证是：

- 不持久化；
- 不缓存；
- 最短局部作用域；
- 不进入日志、异常、队列和 Crash Report；
- 可选高级模式使用短生命周期子进程承载高风险调用。

不得在架构文档中承诺无法验证的“使用后立即从内存彻底消失”。

## 8.7 密钥轮换

通用流程：

```text
主人在 Provider 控制台创建或取得新 Key
→ UI 写入新 secret_reference
→ 测试连接
→ 标记新 Key active
→ 新请求只使用新 Key
→ 旧 Key 标记 deprecated
→ 观察过渡期使用情况
→ 主人在 Provider 端撤销旧 Key
→ 本地删除旧 secret_reference
```

只有 Provider 官方 API 支持安全创建和撤销 Key 时，才允许 Provider 特定自动化。通用层不得假装能自动创建所有厂商的 Key。

轮换策略：

- 手动；
- 30/60/90 天提醒；
- 过期和撤销状态；
- 双 Key 过渡期；
- 新请求强制新 Key；
- 旧 Key 调用单独告警。

## 8.8 云端调用审计

```text
CloudCallAudit
- audit_id
- timestamp
- provider_id
- model_name
- request_type
- key_reference_masked
- caller_module
- project_id
- token_input
- token_output
- estimated_cost
- currency
- latency_ms
- status
- error_code
- error_message_redacted
- retry_count
- request_id_from_provider
```

禁止保存：

- API Key；
- Authorization Header；
- 完整敏感 Prompt；
- 未脱敏响应正文；
- 文件原文。

审计 UI 支持按 Provider、时间、项目、模型、状态过滤和脱敏导出。

## 8.9 SensitiveDataFilter

统一强制：

- 日志 Filter；
- HTTP Client Middleware；
- Exception Sanitizer；
- Debug Guard；
- Export Redactor；
- WebSocket Event Redactor。

敏感字段：

```text
authorization
api_key
access_token
secret
credential
cookie
set-cookie
x-api-key
proxy-authorization
```

UI 只显示脱敏值，例如：

```text
abc…xyz
```

## 8.10 CI 和运行时泄露检测

CI：

- 扫描新增代码和测试输出中的 Key 模式；
- 扫描 `Bearer `、常见 Provider Key 前缀和敏感 Header；
- 测试 fixture 必须使用明显无效的 `REDACTED_TEST_KEY`；
- 文档示例使用 `<API_KEY>`，不使用近似真实 Key；
- 允许列表必须最小且有注释。

运行时：

- 定期扫描 LingJi 自己的日志和审计导出；
- 大量失败、Token 激增、deprecated Key 使用和异常访问触发告警；
- Provider 支持时记录地区或 IP 异常；
- 可选自动禁用 Provider；
- UI 提供轮换入口。

### 内存快照检测修正

进程内存扫描属于高风险高级诊断：

- 可能需要管理员权限；
- 可能产生包含敏感内容的新快照；
- 跨平台不稳定；
- 不能作为 P6 基础验收要求。

v1.1 将其标记为 `DEFERRED_ADVANCED_SECURITY`，默认关闭。

---

# 9. Vector Memory Service

## 9.1 第一阶段部署

第一阶段：

```text
qdrant-client Local Mode
path = storage/qdrant/
```

特点：

- 不要求 Docker；
- 本地磁盘持久化；
- 与未来 Server Mode 使用统一 Service 接口；
- 适合当前单用户、本机、初始规模。

## 9.2 Local Mode 升级阈值

以下任一条件出现时，进入独立 Qdrant 服务评估，不自动迁移：

- 向量点数量超过主人配置阈值，默认建议从 500,000 开始预警；
- `storage/qdrant/` 超过默认建议 8 GB；
- 需要多个进程并发写入；
- P95 向量查询持续超过目标阈值；
- Local Mode 功能不支持所需 Alias、Snapshot 或过滤行为；
- 数据恢复和在线迁移要求提高。

上述数字是 v1.1 的初始运维阈值，不是 Qdrant 官方极限，必须在真实机器基准后调整。

## 9.3 推荐后端模块

```text
src/vector_memory/
├── __init__.py
├── service.py                 # VectorMemoryService
├── client.py                  # Local/Server adapter
├── collections.py             # Collection 创建和版本
├── registry.py                # Active Index Registry
├── payloads.py                # Payload 契约和校验
├── embedding_profiles.py      # 模型、维度和版本
├── jobs.py                    # 复用现有任务队列
├── synchronizer.py            # 增量同步
├── coverage.py                # 覆盖率和缺失检查
├── migration.py               # 新旧索引对比与切换
├── snapshots.py               # Server 模式快照；Local 目录备份策略
├── semantic_provider.py       # 实现现有 SemanticProvider
└── diagnostics.py             # 状态和一致性检查
```

## 9.4 双层 Collection

逻辑层：

1. `source` 原始资料层；
2. `canonical` 正式记忆层。

实际 Collection 使用版本化名称，不使用固定名称直接覆盖：

```text
lingji_source_chunks__<profile>__v<generation>
lingji_canonical_memories__<profile>__v<generation>
```

UI 显示逻辑名称：

- 原始资料层；
- 正式记忆层。

## 9.5 两层语义

### 原始资料层

保存：

- 原始文档片段；
- ChatGPT/Codex 对话片段；
- 网页正文；
- 视频和音频转写；
- OCR 片段；
- PDF 页；
- PPT 幻灯片；
- Excel 工作表/单元格；
- 代码片段。

回答：

```text
为什么这样判断？原文在哪里？
```

### 正式记忆层

保存：

- 主人确认的知识；
- 正式决定；
- 长期规则；
- 项目状态；
- 经验；
- 约束；
- 已批准的偏好和记忆。

回答：

```text
现在应该相信什么？当前采用什么？
```

原始资料不需要先蒸馏才能进入 Source Collection。蒸馏和主人确认后，才进入 Canonical Collection。

## 9.6 向量 Payload

每个点至少保存：

```text
point_id
chunk_id
source_id
memory_id
layer
project_id
source_type
source_path
page_number
slide_number
sheet_name
cell_range
start_line
end_line
video_start_ms
video_end_ms
privacy
status
review_status
valid_from
valid_to
content_hash
embedding_profile_id
embedding_model
embedding_dimension
embedding_version
created_at
updated_at
```

## 9.7 确定性 Point ID

推荐：

```text
point_id = UUIDv5(
  layer + stable_chunk_id + embedding_profile_id + content_hash
)
```

作用：

- 幂等 Upsert；
- 内容变化生成新 Point；
- 模型变化不覆盖旧向量；
- 重试不重复；
- 可定位向量来源。

## 9.8 Embedding Profile

```text
EmbeddingProfile
- profile_id
- provider
- model
- dimension
- distance
- normalization
- chunking_version
- preprocessing_version
- batch_size
- max_input_chars
- compute_mode
- created_at
- status
```

Collection 必须绑定一个不可变 Embedding Profile。

## 9.9 真正批量 Embedding

Ollama 新 Embedding API 支持文本或文本数组输入。v1.1 应：

```text
从任务队列取得待生成 Chunk
→ 按字符数和条数组成批次
→ 调用数组 Embedding
→ 验证返回数量和维度
→ 批量 Upsert Qdrant
→ 更新 SQLite 任务和覆盖率
→ 发布 embedding_progress
```

不能继续使用：

```python
return [self.embed(t) for t in texts]
```

作为“批处理”的最终实现。

## 9.10 向量任务状态

复用 `SQLiteExtractionQueue`，增加任务类型或阶段：

```text
vector_sync
embedding_generate
vector_upsert
vector_verify
index_compare
index_switch
index_archive
```

不得新建第二套任务队列。

每个任务保存：

- 总 Chunk；
- 已处理；
- 成功；
- 失败；
- 跳过；
- 批次；
- 当前模型；
- 当前设备；
- 平均速度；
- 重试；
- 最后错误；
- 任务参数哈希。

## 9.11 降级

```text
Qdrant 不可用
→ semantic_provider 状态 unavailable
→ HybridRetriever 只运行 FTS5 + substring + metadata
→ MemoryGateway 继续返回结果
→ UI 显示语义检索降级
→ 生成 provider_unavailable 活动事件
```

Embedding 模型不可用只影响新向量生成，不影响已有向量查询和 FTS5。

---

# 10. 真正的混合检索

## 10.1 检索通道

```text
C1: SQLite FTS5 搜正式记忆
C2: Qdrant 搜正式记忆
C3: SQLite FTS5 搜原始资料
C4: Qdrant 搜原始资料
C5: 中文子串和精确字段补充
```

## 10.2 流程

```text
解析 query 和 filters
→ 权限、项目、隐私、有效期预过滤
→ 并行运行 C1-C5
→ 统一 Candidate Schema
→ RRF 融合
→ 元数据可解释加权
→ 可选 Reranker
→ Canonical 与 Source 交叉验证
→ 输出引用、通道、解释和验证状态
```

## 10.3 RRF

继续复用现有 `HybridRetriever` 的 RRF 框架，不另建检索器。

建议默认权重：

```text
canonical lexical   1.20
canonical semantic  1.20
source lexical      1.00
source semantic     1.00
substring           0.80
```

权重必须可配置、可测试，不能把语义结果无条件放在词法结果之前。

## 10.4 Candidate Schema

```text
RetrievalCandidate
- candidate_id
- layer
- memory_id
- source_id
- chunk_id
- text
- citation
- retrieval_channels[]
- channel_ranks{}
- lexical_score
- semantic_score
- rrf_score
- metadata_boosts[]
- final_score
- verification_status
- freshness_status
- consistency_status
- explanation[]
```

## 10.5 retrieval_channels

必须显示：

```text
lexical
semantic
substring
canonical
source
```

可以同时包含多个值。

## 10.6 为什么找到

输出 `explanation`，可包含：

- 关键词命中；
- 语义相近；
- 项目匹配；
- 当前有效；
- 主人确认；
- 时间较新；
- 来源可信；
- 人工收藏；
- 标题命中；
- 标签命中；
- Canonical 和 Source 同时支持。

不得输出无法追溯的“AI 认为相关”。

## 10.7 Canonical 与 Source 交叉验证

```text
Canonical 命中
→ 读取其 source_id / sources
→ 检查 Source 层是否存在支持片段
→ 标记 verified / partially_verified / unverified / conflict
```

如果没有可靠来源：

- 允许返回建议或记忆候选；
- 不允许生成确定性结论；
- 必须标记 `unverified`。

## 10.8 Reranker

Reranker 是可选增强：

- 不安装时不影响检索；
- CPU_ONLY 可关闭或使用轻量 CPU 模型；
- 只处理 RRF 后的有限候选；
- 记录模型、耗时和是否参与排序；
- 失败时回退到 RRF 结果。

---

# 11. 语义记忆 UI

## 11.1 一级菜单

```text
语义记忆
```

不使用“Qdrant”作为主人一级菜单名称。Qdrant 只是实现细节。

## 11.2 页面区域

### 概览

- 关键词检索状态；
- 语义检索状态；
- 原始资料索引数量；
- 正式记忆索引数量；
- 待生成向量；
- 失败向量任务；
- Source 覆盖率；
- Canonical 覆盖率；
- 当前 Embedding 模型；
- 向量维度；
- 活跃索引版本；
- 上一个可恢复版本；
- 最后同步；
- Qdrant 占用；
- CPU/GPU 状态。

### 分层解释

```text
原始资料层
用于寻找原文、原始文件、聊天、页码、单元格和视频时间码。

正式记忆层
用于寻找主人已经确认的结论、规则、约束和决定。
```

### 操作

- 增量同步；
- 暂停；
- 恢复；
- 重试失败；
- 检查缺失索引；
- 测试语义检索；
- 只处理当前项目；
- 生成重建预览；
- 查看索引目录；
- 查看索引版本；
- 对比新旧索引。

“重建全部索引”放在高级操作，显示：

- 预计 Chunk 数；
- 预计读取量；
- 预计新空间；
- 当前模型；
- 当前设备；
- 旧索引保留策略；
- 确认文字。

## 11.3 推荐前端文件

P1 模块化完成后：

```text
desktop/lingji-control/src/pages/SemanticMemoryPage.tsx
desktop/lingji-control/src/components/vector/VectorStatusCards.tsx
desktop/lingji-control/src/components/vector/LayerCoverage.tsx
desktop/lingji-control/src/components/vector/VectorJobsTable.tsx
desktop/lingji-control/src/components/vector/IndexVersionPanel.tsx
desktop/lingji-control/src/components/vector/SearchExplainPanel.tsx
desktop/lingji-control/src/components/vector/RebuildPreviewDialog.tsx
desktop/lingji-control/src/hooks/useVectorStatus.ts
desktop/lingji-control/src/api/vector.ts
```

---

# 12. 运行活动中心

## 12.1 一级菜单

```text
活动中心
```

## 12.2 真实流水线

```text
已接收
→ 正在解析
→ 正在分块
→ 正在生成语义索引
→ 正在蒸馏
→ 等待主人确认
→ 已进入正式记忆
```

不是所有任务都经过全部阶段。UI 必须显示当前任务实际阶段，不补齐虚假步骤。

## 12.3 活动事件

至少支持：

```text
job_started
job_progress
job_completed
job_failed
model_loading
model_ready
embedding_progress
vector_sync_completed
provider_unavailable
resource_warning
memory_candidate_created
review_required
```

建议补充：

```text
model_download_progress
model_benchmark_completed
index_switch_started
index_switch_completed
index_switch_failed
cloud_call_completed
secret_rotation_due
security_warning
```

## 12.4 后端设计

WebSocket 不能只依赖进程内存列表。使用：

```text
StateDatabase event journal
+ ActivityEventBroker
+ WebSocket tail
```

流程：

```text
业务模块 append_event()
→ SQLite 事件表获得单调 event_id
→ EventBroker 通知在线连接
→ WebSocket 推送
→ UI 断线后携带 after_event_id 重连
→ 后端补发丢失事件
```

这样进程重启或短暂断线不会丢失关键状态。

## 12.5 推荐后端模块

```text
src/activity/
├── __init__.py
├── models.py
├── broker.py
├── service.py
├── websocket.py
├── redaction.py
└── metrics.py
```

复用现有 `state_db.append_event()` 和事件表。只有现有表无法满足单调游标、保留策略和过滤时，才做最小迁移。

## 12.6 WebSocket API

```text
WS /api/activity/stream
```

连接参数：

```text
after_event_id
project_id
job_id
event_types
```

鉴权：

- 使用本地控制令牌；
- 不把令牌写入 URL 日志；
- 优先使用 WebSocket 子协议或安全握手方式；
- 失败使用合适关闭码；
- 限制本机来源。

## 12.7 轮询降级

WebSocket 不可用时：

```text
GET /api/activity/events?after_event_id=...
```

UI 显示“实时连接已降级为轮询”，不能静默假装实时。

## 12.8 任务字段

每项任务显示：

- 当前步骤；
- 当前文件；
- 来源；
- 项目；
- 已完成数；
- 总数；
- 百分比；
- 当前速度；
- CPU 或 GPU；
- 使用模型；
- 已运行时间；
- 预计剩余工作量；
- 最近错误。

### 进度规则

- `total` 未知时显示不确定进度，不显示假百分比；
- 只有真实 completed/total 才显示百分比；
- ETA 样本不足时返回 `null`；
- 速度使用滑动窗口，标记单位；
- “预计剩余工作量”可以是 Chunk、文件、字节或批次，不强制伪造剩余时间。

## 12.9 推荐前端文件

```text
desktop/lingji-control/src/pages/ActivityCenterPage.tsx
desktop/lingji-control/src/components/activity/ActivityPipeline.tsx
desktop/lingji-control/src/components/activity/ActiveJobsTable.tsx
desktop/lingji-control/src/components/activity/ResourceUsageStrip.tsx
desktop/lingji-control/src/components/activity/EventTimeline.tsx
desktop/lingji-control/src/components/activity/ErrorDrawer.tsx
desktop/lingji-control/src/hooks/useActivityStream.ts
desktop/lingji-control/src/api/activity.ts
```

---

# 13. 推荐前端页面和组件

P1 拆分后建议一级导航：

```text
总览
项目中心
记忆检索
语义记忆
任务
活动中心
主动投喂
本地文件
媒体分析
AI 与模型
存储与备份
隐私与安全
环境验收
设置
日志
```

v1.1 当前只要求新增或改造：

- 系统与算力区块；
- AI 与模型；
- 语义记忆；
- 活动中心；
- 云端 Provider 和密钥安全；
- 总览中的硬件、向量和活动摘要。

## 13.1 公共组件

```text
StatusBadge
CapabilityCard
ResourceMeter
TaskProgress
ErrorDetails
ConfirmationDialog
ImpactPreview
ProviderBadge
ModelCapabilityBadge
CitationBadge
FreshnessBadge
EmptyState
LoadingState
UnavailableState
```

## 13.2 前端边界

- UI 不直接调用 NVML、Ollama、Qdrant 或 keyring；
- UI 不直接操作 SQLite；
- UI 不直接删除模型文件；
- UI 不计算模型兼容性结论；
- UI 不复制后端安全过滤；
- UI 只展示 Service 返回的真实值；
- 不引入大型状态管理框架，除非 P1 研究证明必要；
- WebSocket 状态和 REST 状态使用统一类型。

---

# 14. 数据模型

SQLite 保存以下派生和运行数据。

## 14.1 compute_policy

```text
scope_type              global | project | task
scope_id
requested_mode           auto | gpu_preferred | cpu_only
gpu_id
allow_fallback
updated_at
updated_by
```

## 14.2 hardware_snapshots

```text
snapshot_id
collected_at
payload_json
source_versions_json
warnings_json
```

只保留有限历史，默认 30 条；动态遥测不永久保存全部采样。

## 14.3 model_definitions

```text
model_id
provider_id
capability
display_name
family
parameter_count
quantization
embedding_dimension
license
official_url
expected_ram_bytes
expected_vram_bytes
metadata_json
```

## 14.4 model_installations

```text
installation_id
model_id
local_path
installed
size_bytes
version
checksum_status
installed_at
last_verified_at
last_error
```

## 14.5 model_assignments

```text
scope_type
scope_id
capability
model_id
provider_id
priority
active
updated_at
```

## 14.6 model_benchmarks

```text
benchmark_id
model_id
capability
device
input_profile_json
result_json
created_at
```

## 14.7 embedding_profiles

```text
profile_id
provider
model
dimension
distance
normalization
chunking_version
preprocessing_version
batch_size
compute_mode
status
created_at
```

## 14.8 vector_index_registry

```text
logical_index            source | canonical
active_collection
previous_collection
embedding_profile_id
generation
status
coverage_percent
point_count
failed_count
switched_at
archived_at
```

## 14.9 vector_chunk_state

```text
layer
chunk_id
content_hash
embedding_profile_id
point_id
status
attempts
last_error
updated_at
```

该表用于幂等、覆盖率和缺失检测，向量本身只在 Qdrant。

## 14.10 cloud_providers

```text
provider_id
enabled
base_url
secret_reference
key_fingerprint
status
last_rotated_at
rotation_due_at
default_model
capabilities_json
last_tested_at
last_error
```

## 14.11 cloud_call_audit

使用第 8.8 节字段。对高频调用可按月分表或归档，但第一阶段不提前复杂化。

## 14.12 activity_events

优先复用现有事件表；需要补充时增加：

```text
event_id
timestamp
event_type
entity_type
entity_id
project_id
job_id
severity
payload_json
```

---

# 15. FastAPI API 设计

## 15.1 Hardware

```text
GET  /api/hardware/capabilities
GET  /api/hardware/telemetry
POST /api/hardware/refresh
POST /api/hardware/compatibility/test
```

## 15.2 Compute

```text
GET   /api/compute/policy
PATCH /api/compute/policy
GET   /api/compute/effective
```

## 15.3 Local Models

```text
GET  /api/models
GET  /api/models/{model_id}
POST /api/models/{model_id}/test
POST /api/models/{model_id}/benchmark
POST /api/models/{model_id}/download
POST /api/models/{model_id}/download/pause
POST /api/models/{model_id}/download/resume
POST /api/models/{model_id}/delete-preview
POST /api/models/{model_id}/delete
GET  /api/models/{model_id}/tasks
GET  /api/model-assignments
PATCH /api/model-assignments
```

## 15.4 Cloud Providers

```text
GET    /api/providers/cloud
GET    /api/providers/cloud/{provider_id}
PATCH  /api/providers/cloud/{provider_id}
POST   /api/providers/cloud/{provider_id}/secret
DELETE /api/providers/cloud/{provider_id}/secret
POST   /api/providers/cloud/{provider_id}/test
POST   /api/providers/cloud/{provider_id}/models/refresh
POST   /api/providers/cloud/{provider_id}/rotate
GET    /api/providers/cloud/audit
GET    /api/providers/cloud/security
```

完整 Key 不通过 GET 返回。

## 15.5 Vector Memory

```text
GET  /api/vector/status
GET  /api/vector/indexes
GET  /api/vector/coverage
GET  /api/vector/jobs
POST /api/vector/sync
POST /api/vector/pause
POST /api/vector/resume
POST /api/vector/retry-failed
POST /api/vector/check-missing
POST /api/vector/search-test
POST /api/vector/rebuild-preview
POST /api/vector/rebuild
POST /api/vector/indexes/compare
POST /api/vector/indexes/switch
POST /api/vector/indexes/archive
```

## 15.6 Retrieval Explain

```text
POST /api/memory/search
POST /api/memory/search/explain
```

返回：

- 结果；
- retrieval_channels；
- explanation；
- citation；
- verification；
- freshness；
- semantic availability；
- fallback reason。

## 15.7 Activity

```text
WS  /api/activity/stream
GET /api/activity/events
GET /api/activity/jobs
GET /api/activity/jobs/{job_id}
```

---

# 16. 分阶段实施计划

## P0：真实环境和稳定基线

状态：未完成最终主人真机验收。

### 内容

1. 在主人电脑运行真实 Vault、ChatGPT 导出和媒体只读验收；
2. 合并 PR #4；
3. 整合主人本机未推送代码；
4. 创建稳定 `integration/lingji-v1`；
5. 基线 CI 全绿；
6. 记录真实硬件初始快照，为 P2 提供样本。

### 验收

- `error_count=0`；
- `inputs_unchanged=true`；
- 真实 Vault 正确；
- 真实导出和媒体可识别；
- 基线 CI 全绿；
- 没有本地未提交的重要代码；
- 总计划更新。

## P1：桌面 UI 模块化

### 内容

- 拆分巨型 `App.tsx`；
- 建立 `pages/components/hooks/types/api`；
- 统一连接状态、错误、Loading、Empty 和 Unavailable；
- 把环境验收入口并入正式导航；
- 不新增 v1.1 业务逻辑。

### 验收

- 原有所有页面行为不减少；
- App 只保留壳和路由；
- 导航测试；
- API 错误状态测试；
- Windows 和前端 CI；
- 截图对比；
- `docs/DESKTOP_UI_MODULARIZATION_REPORT.md`。

## P2：Hardware Capability Service 与算力模式

### 内容

- Hardware Capability Service；
- psutil；
- NVML 可选支持和 nvidia-smi 回退；
- CPU/RAM/GPU/VRAM/CUDA/驱动/磁盘/工具状态；
- 全局算力模式；
- UI 系统与算力区块；
- 真实资源事件。

### 验收

- RTX 4060 真机数据与系统工具基本一致；
- 无 NVIDIA GPU 环境不报致命错误；
- CPU_ONLY 下基础检索和 MCP 全部通过；
- GPU_PREFERRED 失败能回退；
- 磁盘类型不确定时返回 unknown；
- 无模拟负载；
- `docs/HARDWARE_COMPUTE_MODE_REPORT.md`。

## P3：本地模型中心

### 内容

- Model Registry；
- Ollama 和现有媒体 Provider inventory；
- 兼容性五阶段判断；
- 固定短基准；
- 模型分配；
- 下载、暂停、恢复、目录和删除预览；
- AI 与模型 UI 本地部分。

### 验收

- 至少一个聊天模型、Embedding、ASR、OCR 真实识别；
- 预计和实测分开；
- 仅名称判断测试必须失败；
- 下载空间不足拒绝；
- 删除默认模型或活跃索引依赖模型拒绝；
- CPU_ONLY 基准；
- Windows 测试；
- `docs/LOCAL_MODEL_CENTER_REPORT.md`。

## P4：Vector Memory Service 和真正混合检索

### 内容

- qdrant-client Local Mode；
- `storage/qdrant/`；
- Source/Canonical 双层版本化 Collection；
- Embedding Profile；
- Ollama 数组批处理；
- 持久任务和覆盖率；
- `QdrantSemanticProvider` 接入现有 HybridRetriever；
- C1-C5 混合通道；
- RRF、解释和交叉验证；
- FTS5 降级。

### 验收

- `semantic_provider` 不再固定为 None；
- Qdrant 不可用时 FTS5 仍返回结果；
- CPU_ONLY 可以查询已有向量；
- 真实批次请求，不是循环伪批处理；
- 两层覆盖率独立；
- 新旧 Embedding 索引并存和切换；
- 固定 Query Set 比较报告；
- 删除 Qdrant 后可重建；
- `docs/VECTOR_MEMORY_HYBRID_RETRIEVAL_REPORT.md`。

## P5：语义记忆 UI 和活动中心 WebSocket

### 内容

- 语义记忆页面；
- 覆盖率、版本、失败任务、增量同步和重建预览；
- 活动中心；
- SQLite Event Journal + WebSocket；
- 断线游标补发；
- REST 轮询降级；
- 真实 CPU/GPU、模型和速度；
- 检索解释 UI。

### 验收

- WebSocket 事件顺序正确；
- 断线重连不丢关键事件；
- 多客户端关闭无资源泄漏；
- WebSocket 不可用时明确降级；
- 未知总数不显示假百分比；
- ETA 不足返回 null；
- 所有按钮调用真实后端；
- Windows 和 UI smoke；
- `docs/SEMANTIC_MEMORY_ACTIVITY_CENTER_REPORT.md`。

## P6：Cloud Provider 与密钥安全

### 内容

- OpenAI、Kimi、DeepSeek、自定义 OpenAI Compatible；
- keyring；
- Provider Registry；
- Key Resolver；
- 轮换；
- 审计；
- SensitiveDataFilter；
- CI Secret Scanner；
- 安全 UI。

### 验收

- Key 不进入 Git、Obsidian、runtime settings、LocalStorage、日志和普通 SQLite；
- keyring 不可用时 Provider 禁用；
- 日志和异常自动脱敏；
- 固定 URL 白名单；
- 自定义 Base URL 重定向和私网策略测试；
- 真实测试连接；
- 成本和 Token 审计；
- 轮换演练；
- `docs/CLOUD_PROVIDER_SECURITY_REPORT.md`。

## P7：本地文件检索

### 内容

- PDF；
- DOCX；
- XLSX；
- PPTX；
- 图片 OCR；
- 代码和纯文本；
- Source Collection；
- 精确 Locator；
- 文件检索 UI。

### 验收

- 每种格式真实样例；
- 页码、幻灯片、工作表、单元格和代码行准确；
- 增量更新；
- 白名单目录；
- 删除源文件标记 missing；
- 10,000 文件压力测试；
- CPU_ONLY；
- `docs/LOCAL_DOCUMENT_SEARCH_REPORT.md`。

---

# 17. 每阶段统一验收标准

每个 P1-P7 模块必须有：

1. Research Notes；
2. 一个官方标准或官方文档；
3. 三个仍维护的相似项目；
4. 明确采用和拒绝；
5. 失败测试；
6. 最小实现；
7. 单元测试；
8. 集成测试；
9. Windows 测试；
10. 无 GPU 或 CPU_ONLY 测试；
11. 降级测试；
12. UI 入口；
13. UI smoke；
14. 真实 Demo；
15. Markdown 模块报告；
16. 风险和回滚；
17. 独立 Draft PR；
18. `docs/REMAINING_WORK_PARALLEL_DEVELOPMENT_PLAN.md` 状态更新；
19. ChatGPT Diff、CI、UI 和数据安全验收；
20. 主人不修改源码即可使用。

---

# 18. 禁止修改或重复建设的区域

## 18.1 必须复用

- FastAPI Control API；
- LocalControlService；
- RuntimeSettingsStore；
- MemoryGateway；
- HybridRetriever；
- SQLiteExtractionQueue；
- MemoryDatabase；
- StateDatabase 和现有事件审计；
- Tauri + React 控制中心；
- 现有 Provider 接口；
- 现有权限和隐私路由；
- 现有备份和存储生命周期。

## 18.2 禁止

- 另建平行控制台；
- 另建重复任务队列；
- 另建重复 Memory Gateway；
- 另建第二套 Runtime Settings；
- UI 直接操作 SQLite；
- UI 直接操作 Qdrant；
- UI 直接读取 keyring；
- API Key 写入普通配置、日志、Obsidian 或 LocalStorage；
- Docker 作为第一版强制依赖；
- GPU 作为系统强制依赖；
- 模拟数字冒充进度；
- 用模型名称代替实际兼容性测试；
- 直接覆盖现有 Embedding Collection；
- 新模型下载后自动切换正式索引；
- 自动删除旧索引；
- 未经确认重建全部向量；
- 在巨型 PR 中一次完成 P1-P7；
- 为统一风格全仓格式化；
- 借 v1.1 推翻 v1.0。

## 18.3 共享热点

以下文件只能由对应集成阶段最小修改，多个分支不得同时抢改：

```text
src/control/api.py
src/control/service.py
src/control/runtime_settings.py
src/gateway/bootstrap.py
src/gateway/memory_gateway.py
src/retrieval/hybrid.py
src/retrieval/memory_db.py
src/storage/state_db.py
src/config.py
.github/workflows/tests.yml
desktop/lingji-control/src/App.tsx
桌面全局路由和导航
数据库 Schema 和迁移
```

P1 完成后，前端共享热点应缩小到 App Shell、Router 和共享类型。

---

# 19. 需要主人确认的架构决策

以下决策在进入对应阶段前必须由主人明确确认。

## ADR-1：Qdrant Local Mode 的升级阈值

建议初始预警：

- 500,000 Points；
- 8 GB 存储；
- 多进程写入需求；
- P95 查询持续超标。

需要主人决定是否采用这些默认值。

## ADR-2：第一版默认 Embedding 模型

需要确认：

- 继续 `nomic-embed-text`；
- 改用其他中文/多语言模型；
- 是否使用当前规划中的 bge-m3；
- 默认维度、上下文和磁盘占用。

该决定必须通过真实中文 Query Set，而不是只看榜单。

## ADR-3：Source Collection 的隐私范围

需要确认：

- private 内容是否进入本机 Qdrant；
- 哪些 Agent 可搜索 private Source；
- 高隐私目录是否完全排除；
- 是否需要单独加密磁盘或独立 Collection。

## ADR-4：Embedding 模型归档保留期

建议：

- 切换后旧索引保留 14 或 30 天；
- 至少完成一次回滚演练后才允许删除。

## ADR-5：云端 Provider 默认关闭

建议所有云端 Provider 默认禁用，主人逐个启用。需要确认。

## ADR-6：自定义 OpenAI Compatible 私网策略

建议：

- 默认禁止私网；
- 主人显式选择“本地兼容服务”后才允许 localhost/private IP；
- 不允许跨主机重定向携带密钥。

## ADR-7：活动事件保留期

建议：

- 详细事件 30 天；
- 聚合统计 180 天；
- 安全审计按独立策略保留。

## ADR-8：硬件遥测频率

建议：

- 活动页面可见时 2 秒；
- 后台 10 秒；
- 无活动任务时暂停高频 GPU 采样。

## ADR-9：本地模型下载目录

需要确认默认目录，以及是否放在百度网盘同步目录之外。模型大文件不建议进入 Obsidian 或 Git。

## ADR-10：P1-P5 串并行策略

建议：

```text
P0 完成
→ P1 必须先完成
→ P2 与 P3 可以有限并行
→ P4 依赖 P2/P3 稳定契约
→ P5 依赖 P1/P4
```

禁止 P4 和 P5 在巨型 App.tsx 尚未拆分时直接开工。

---

# 20. Research Notes

## 20.1 官方资料

- Qdrant Python Client Local Mode：`QdrantClient(path="...")` 可在不运行 Server 的情况下持久化本地向量；Local Mode 与 Server Mode 使用相近客户端接口。  
  https://github.com/qdrant/qdrant-client
- Qdrant Collection 和 on-disk 配置：  
  https://qdrant.tech/documentation/manage-data/collections/
- Qdrant Snapshot：  
  https://qdrant.tech/documentation/operations/snapshots/
- Ollama Embedding API：`input` 支持文本或文本数组。  
  https://docs.ollama.com/api/embed
- Ollama Model List：  
  https://docs.ollama.com/api/tags
- FastAPI WebSocket：  
  https://fastapi.tiangolo.com/advanced/websockets/
- FastAPI WebSocket Test：  
  https://fastapi.tiangolo.com/advanced/testing-websockets/
- psutil CPU、RAM、磁盘和负载：  
  https://psutil.readthedocs.io/latest/
- NVIDIA NVML：  
  https://developer.nvidia.com/management-library-nvml
- NVML API Reference：  
  https://docs.nvidia.com/deploy/nvml-api/
- Python keyring：Windows Credential Locker、macOS Keychain、Linux Secret Service。  
  https://keyring.readthedocs.io/
- OpenAI API：  
  https://platform.openai.com/docs/
- Kimi API：  
  https://platform.kimi.com/docs/api/overview
- DeepSeek API：  
  https://api-docs.deepseek.com/

## 20.2 采用的设计

- Qdrant Local Mode 作为第一阶段，而不是 Docker 强制依赖；
- 版本化 Collection 和 SQLite Active Index Registry；
- Ollama 数组 Embedding；
- psutil + NVML + nvidia-smi 回退；
- FastAPI WebSocket + SQLite 事件游标；
- keyring 安全存储，Backend 不可用时禁用云端；
- RRF 继续复用现有 HybridRetriever；
- FTS5 永久作为降级基础；
- Source 和 Canonical 双层检索；
- 兼容性必须实测；
- UI 只展示真实状态。

## 20.3 明确拒绝

- 将 Qdrant 名称暴露为主人一级概念；
- 只靠显卡型号判断模型兼容；
- 用循环逐条调用冒充批处理；
- 在 LocalStorage、SQLite 明文或 runtime settings 保存 Key；
- 声称 Python 字符串能够可靠立即物理清零；
- 把内存扫描作为第一阶段强制安全措施；
- 进程内存 WebSocket 列表作为唯一事件源；
- Qdrant 故障导致 Memory Gateway 整体不可用；
- 未验证的新索引自动取代正式索引。

---

# 21. 最终实施结论

v1.1 不改变 v1.0 的总体架构，而是在现有灵机底座上补齐：

```text
真实硬件能力
→ 可验证模型兼容性
→ 可控 CPU/GPU 模式
→ 本地和云端模型中心
→ Source/Canonical 双层向量记忆
→ 真正混合检索
→ 语义记忆 UI
→ WebSocket 活动中心
→ 安全密钥和调用审计
```

实施顺序固定为：

```text
P0 真机验收和稳定基线
→ P1 UI 模块化
→ P2 硬件和算力模式
→ P3 本地模型中心
→ P4 向量记忆和混合检索
→ P5 语义记忆与活动中心
→ P6 云端 Provider 和安全
→ P7 本地文件检索
```

P1-P5 是下一轮核心开发主线，但在对应代码、测试、真实 Demo、UI、Windows CI 和模块报告通过前，全部保持 `TODO`，不得写成已完成。
