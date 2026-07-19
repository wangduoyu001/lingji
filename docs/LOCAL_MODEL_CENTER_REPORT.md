# 灵机本地模型中心报告

> 模块：P3 本地模型中心，第一增量  
> 分支：`feature/local-model-registry-inventory`  
> 堆叠基线：`feature/hardware-capability-service`  
> 状态：`IN_PROGRESS`  
> 当前范围：Research、数据契约、失败测试、只读 Registry、只读 Inventory 和 UI 骨架  
> 明确不做：模型下载、删除、加载基准、兼容性结论、向量索引切换

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

1. Open WebUI  
   https://github.com/open-webui/open-webui  
   借鉴：统一模型列表、运行状态和 Provider 管理；拒绝复制其服务端结构。
2. AnythingLLM  
   https://github.com/Mintplex-Labs/anything-llm  
   借鉴：本地优先和多 Provider 分区；拒绝以环境变量替代灵机统一设置。
3. LM Studio CLI  
   https://github.com/lmstudio-ai/lms  
   借鉴：模型清单、加载状态和目录管理分开；拒绝把内存估算当成兼容性结论。

### 采用

- Ollama 安装清单只信任 `/api/tags`；
- 运行状态只信任 `/api/ps`；
- 模型能力优先使用 `/api/show` 返回的 `capabilities`；
- `installed`、`running`、`capabilities`、`compatibility` 分开；
- faster-whisper 的名称可能触发远程缓存下载，未加载前不宣布已安装；
- PaddleOCR 包存在不等于具体模型缓存完整；
- 所有兼容性初始为 `unverified`；
- 当前阶段只读，不调用 pull、delete 或模型加载。

### 拒绝

- 根据模型名称猜测 vision、embedding 或 tools；
- 根据 GPU 名称宣布模型兼容；
- 扫描整个磁盘寻找模型；
- 为展示按钮而实现半套下载或删除；
- 把现有配置模型从列表中静默隐藏。

## 测试优先

测试文件：

```text
tests/test_model_inventory.py
```

测试提交：

```text
d413d714ba6d75de5a1952049ba9820b2698343a
```

实现前测试要求尚不存在的 `src.model_center.LocalModelInventoryService` 和模型 API，因此旧代码无法通过。

测试契约：

1. Ollama 安装、运行、显存和官方能力分开；
2. 所有兼容性保持 `unverified`；
3. 配置中缺失的模型仍显示；
4. faster-whisper 和 PaddleOCR 不触发下载；
5. Ollama 离线时正常降级；
6. API 暴露 Registry、Inventory 和只读刷新；
7. 当前明确 `mutating_operations_enabled=false`。

## 后续实现

计划新增：

```text
src/model_center/
├── __init__.py
├── contracts.py
├── registry.py
├── transport.py
└── inventory.py
```

计划 API：

```text
GET  /api/models/registry
GET  /api/models
POST /api/models/refresh
```

计划 UI：

```text
AI 与模型
```

当前阶段不提供下载、删除或兼容性通过按钮。

## 回滚

第一提交只有失败测试和报告，不修改数据。回滚分支不会影响 Vault、SQLite、模型文件、Ollama 或向量索引。
