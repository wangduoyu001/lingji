# 灵机本地模型中心报告

> 模块：P3 本地模型中心，第一增量  
> 分支：`feature/local-model-registry-inventory`  
> Draft PR：`#8`  
> 堆叠基线：`feature/hardware-capability-service`  
> 状态：`REVIEW_REQUIRED`  
> 验证 Head：`00d57747136868044cc70414420ec8f29b990f2e`  
> GitHub Actions：`29699695259`

## 当前范围

完成：

- Research Notes；
- 模型用途与 Provider Registry；
- 只读模型 Inventory；
- Ollama 安装、运行和官方能力读取；
- 配置缺失模型提示；
- faster-whisper 和 PaddleOCR Provider 状态；
- FastAPI；
- “AI 与模型”桌面页面；
- 自动测试和 UI Smoke。

明确不做：

- 下载、暂停、删除；
- 大型模型加载；
- 正式基准；
- 兼容性通过结论；
- 默认模型正式切换；
- Qdrant 或 Embedding 索引修改；
- 数据库 Schema 变更。

## Research Notes

### 官方资料

1. Ollama List Models：`GET /api/tags`  
   https://docs.ollama.com/api/tags
2. Ollama List Running Models：`GET /api/ps`  
   https://docs.ollama.com/api/ps
3. Ollama Show Model Details：`POST /api/show`  
   https://docs.ollama.com/api-reference/show-model-details
4. faster-whisper  
   https://github.com/SYSTRAN/faster-whisper
5. PaddleOCR Quick Start  
   https://www.paddleocr.ai/v2.10.0/en/quick_start.html

### 类似项目

- Open WebUI：借鉴统一清单、运行状态和 Provider 分区；
- AnythingLLM：借鉴本地优先和多 Provider 页面；
- LM Studio CLI：借鉴清单、加载和目录管理分离。

### 采用

- 安装清单只信任 Ollama `/api/tags`；
- 运行状态和显存证据只信任 `/api/ps`；
- 模型能力优先使用 `/api/show` 的 `capabilities`；
- `installed`、`running`、`capabilities` 和 `compatibility` 分开；
- 配置中缺失的主模型和备用模型仍显示；
- faster-whisper 包存在不等于指定模型已缓存；
- PaddleOCR 包存在不等于模型文件完整；
- 所有兼容性初始为 `unverified`；
- 当前阶段只读。

### 拒绝

- 根据名称猜测模型能力；
- 根据 GPU 名称宣布兼容；
- 扫描整个磁盘找模型；
- 为了 UI 放置不可用的下载或删除按钮；
- 自动加载模型验证；
- 静默隐藏缺失配置。

## 测试优先

测试文件：

```text
tests/test_model_inventory.py
```

测试先于实现提交：

```text
d413d714ba6d75de5a1952049ba9820b2698343a
```

旧代码缺少 `src.model_center` 和模型 API，无法通过这些测试。

最终专项测试 5 项：

1. Ollama 安装、运行、显存、官方能力和兼容性分离；
2. 配置中缺失的模型明确显示；
3. faster-whisper/PaddleOCR 不触发下载；
4. Ollama 离线正常降级；
5. FastAPI Registry、Inventory 和只读刷新。

## 后端实现

新增：

```text
src/model_center/__init__.py
src/model_center/contracts.py
src/model_center/registry.py
src/model_center/transport.py
src/model_center/inventory.py
```

### 模型用途

```text
chat_reasoning
embedding
asr
ocr
vision
reranker
```

### Ollama 模型字段

- 模型名、Digest、大小、格式、Family；
- 参数规模、量化；
- 官方 Provider 能力；
- 映射后的灵机用途；
- Embedding 维度和上下文长度；
- 安装状态；
- 运行状态；
- 运行显存证据；
- License 摘要；
- 兼容性 `unverified`；
- 最近错误；
- 最近测速和当前任务占位为 `null`。

没有顶层 `compatible=true` 一类未经验证的字段。

### 配置引用

清单显示：

```text
chat_primary
chat_fallback
embedding_primary
embedding_fallback
```

配置模型未安装时状态为 `missing`，不会从页面消失。

### Python Provider

faster-whisper：

- Python 包状态；
- 当前配置模型；
- 本地路径是否存在；
- 名称模型显示 `provider_managed_cache_unknown`。

PaddleOCR：

- Python 包状态；
- 模型根目录；
- 具体模型缓存保持 `model_cache_not_verified`。

## LocalControlService 与 API

复用现有 LocalControlService，新增：

```text
model_registry
models
refresh_models
```

FastAPI：

```text
GET  /api/models/registry
GET  /api/models
POST /api/models/refresh
```

刷新只重新读取清单，不执行安装、删除或加载。

## 桌面 UI

新增一级页面：

```text
AI 与模型
```

显示：

- 已安装模型；
- 正在运行模型；
- 未完成兼容测试；
- 缺失配置模型；
- 六类模型用途；
- 大小、参数、量化和 Embedding 维度；
- 预计 RAM/显存当前显示“待实测”；
- 当前设备证据；
- 兼容性状态；
- 最近测速、当前任务和错误；
- 当前配置引用；
- ASR/OCR Provider。

当前唯一操作是“刷新模型清单”。页面明确说明下载、删除、测速和正式切换尚未启用。

## 自动验证

```text
Run 29699695259
Head 00d57747136868044cc70414420ec8f29b990f2e
Windows: 123 tests / OK
```

结果：

- Ubuntu Python 3.11：success；
- Ubuntu Python 3.12：success；
- Windows Python 3.12：success；
- Desktop UI Smoke、TypeScript、Vite、Tauri：success；
- MCP、浏览器扩展、Obsidian 插件：success。

## 已知限制

1. 当前只支持 Ollama 模型的详细清单；
2. faster-whisper 和 PaddleOCR 只报告包、配置和路径状态；
3. 没有静态 RAM/显存估算；
4. 没有实际加载和短基准；
5. 没有模型下载、暂停、恢复、删除和空间检查；
6. 没有正式 Model Assignment 写入；
7. 没有模型目录迁移；
8. P3 仍堆叠在 PR #7；
9. 主人真实 Ollama 清单尚未验收。

## 下一增量边界

等待真机验收前仍可安全开发：

- 纯数据契约的 Model Assignment；
- 静态资源估算，但必须标记低置信度；
- 下载和删除的影响预览契约与失败测试；
- 基准输入、结果数据模型和空实现；
- 所有新增默认值的 UI 定义。

暂不允许真正下载、删除、加载大型模型或修改正式向量索引。

## 风险与回滚

- 所有 Ollama 调用都是本机只读接口；
- 不扫描未授权目录；
- 不写模型文件；
- 不修改数据库 Schema；
- 不保存模型响应正文以外的敏感内容；
- HTTP Session 在服务关闭时释放。

回滚 PR #8 即可移除本模块，不影响 Vault、SQLite、Ollama 模型和向量索引。

## 当前结论

```text
P3 第一增量 = REVIEW_REQUIRED
```

剩余门槛：主人真实 Ollama 清单验收、P0-B/P1/P2 收口、正式集成分支复验，以及后续兼容性与模型操作安全增量。
