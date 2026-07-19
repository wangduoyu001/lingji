# 灵机运行时媒体设置与启动健康检查开发报告

## 1. 目标

本阶段把媒体处理限制从适配器内部常量提升为“默认值 + 用户持久化覆盖 + 单任务覆盖”三层配置，并为未来独立本地控制中心提供统一设置服务和本机 HTTP API。

同时修复 Embedding 备用模型故障路径，并增加启动前健康检查，避免 Vault、磁盘、SQLite、Ollama 或 FFmpeg 异常直到任务运行时才暴露。

## 2. 免费与开源方案

本阶段仅使用免费开源组件：

- Pydantic Settings：配置类型与范围验证。
- FastAPI + Uvicorn：独立本地 UI 的控制 API。
- FFmpeg / FFprobe：媒体探测与派生处理。
- SQLite：运行时设置审计、任务状态和健康状态。

没有引入收费 API，也没有为了单机个人负载增加 Redis、Prometheus 或其他常驻服务。

## 3. 三层配置规则

优先级从低到高：

```text
src/config.py 安全默认值
    ↓
storage/runtime_settings.json 用户持久化覆盖
    ↓
单次任务 options 临时覆盖
```

所有用户覆盖由 `RuntimeSettingsStore` 白名单验证并原子写入。恢复默认值时移除对应覆盖项，避免把旧默认值永久复制进用户配置。

## 4. 可由独立本地 UI 管理的媒体参数

| 参数 | 默认值 | 说明 |
|---|---:|---|
| 关键帧间隔 | 30 秒 | 每隔多少秒提取一帧 |
| 关键帧最大数量 | 500 | 单个任务最大输出数量 |
| 关键帧最大边长 | 1280 px | 保持原比例缩放 |
| FFmpeg 最大并发 | 1 | 同时执行的派生任务数量 |
| FFmpeg 单任务线程 | 2 | `-threads` 与 `-filter_threads` |
| 单文件最大体积 | 20 GB | 0 表示用户明确关闭限制 |
| 单文件最大时长 | 360 分钟 | 0 表示用户明确关闭限制 |
| 媒体默认优先级 | 100 | 数值越小越优先 |
| FFprobe 超时 | 60 秒 | 元数据探测超时 |
| FFmpeg 超时 | 1800 秒 | 单个派生步骤超时 |

这些数值不是不可修改的产品限制，只是首次运行的安全默认值。

## 5. 实现模块

```text
src/control/runtime_settings.py
src/control/service.py
src/control/api.py
src/health.py
src/config.py
src/extraction/pipeline.py
src/extraction/adapters/media.py
src/extraction/bootstrap.py
src/extraction/requests.py
src/embedding/embedder.py
run_service.py
run_control_api.py
requirements-ui.txt
```

### 5.1 RuntimeSettingsStore

提供：

- 设置名称、中文说明、类型、最小值、最大值、默认值和是否需要重启。
- 当前有效值、用户覆盖值与默认值。
- 原子保存、恢复默认值和修改审计。
- 按来源类型生成媒体 Adapter 默认 options。
- 按来源类型生成任务默认优先级。

### 5.2 LocalControlService 与 API

框架无关的 `LocalControlService` 供 Tauri、CLI 和测试共同调用。

当前本机 API：

```text
GET   /api/health
GET   /api/settings
PATCH /api/settings
POST  /api/settings/reset
```

API 默认绑定 `127.0.0.1:8766`，使用本机随机令牌验证。启动入口：

```powershell
python -m pip install -r requirements-ui.txt
python run_control_api.py
```

当前只完成后端设置 API，Tauri + React 可视化设置页仍需后续开发。

### 5.3 ExtractionPipeline

新增动态默认值 Provider：

- 每次入队和立即执行时读取最新用户设置。
- 默认值参与幂等键，设置变化后不会错误复用旧配置任务。
- 单次任务 options 始终高于全局默认值。
- 未明确传入任务优先级时使用 UI 中保存的媒体默认优先级。

### 5.4 MediaExtractionAdapter 1.1.0

新增：

- 输入文件大小限制。
- FFprobe 后媒体时长限制。
- FFmpeg 并发信号量。
- `-threads` 与 `-filter_threads`。
- 可配置关键帧数量、间隔和最大边长。
- 媒体笔记记录实际采用的关键参数。

原始媒体不会因超限而删除。任务会在派生处理前失败并返回明确错误。

### 5.5 启动健康检查

检查：

- Vault、Storage 与日志目录是否存在且可写。
- 备份目录状态。
- 磁盘剩余空间。
- State DB 与 Memory DB 的 `PRAGMA quick_check`。
- FFmpeg 与 FFprobe 是否可用。
- Ollama 是否可连接。

可选组件不可用时默认进入 `degraded`，不拖垮全文检索等基础能力；关键目录或 SQLite 损坏时可阻止严格启动。

### 5.6 Embedding 回退修复

修复不存在的 `_fallback_model` 字段引用。主模型请求失败时会正确尝试备用模型，并记录当前模型与切换状态。

## 6. 安全边界

- 设置文件只允许白名单字段。
- 每个字段都有类型与范围验证。
- 设置写入使用临时文件加原子替换。
- UI 不直接修改 Adapter 源代码或 SQLite 表。
- 输入限制设为 0 才表示用户明确关闭限制。
- 关键帧和音轨派生失败不得删除原始文件。
- 控制 API 不允许绑定公网地址。

## 7. 测试

新增或更新：

```text
tests/test_runtime_settings.py
tests/test_startup_health.py
tests/test_embedder_fallback.py
tests/test_control_api.py
tests/test_media_extraction.py
```

覆盖：

- 默认值展示。
- 用户覆盖持久化与恢复。
- 无效范围拒绝。
- Pipeline 动态默认值与任务级覆盖。
- FFmpeg 线程、分辨率和帧数参数。
- 文件大小与媒体时长限制。
- Ollama/FFmpeg 缺失时降级。
- 非法 Vault 阻止严格启动。
- Embedding 备用模型回退。
- 本地 API 令牌、读取、更新和恢复默认值。

## 8. 后续工作

- 实现 Tauri + React 可视化设置页面。
- 增加 Windows Job Object 级 CPU、内存和进程优先级控制。
- 增加持久化 Embedding 缓存、模型调用统计与外部 API 费用统计。
- 将大型 Vault 启动流程改为完整增量同步并执行压力测试。
- 在独立 UI 中加入 Scheduler 失败、重试与下次执行时间视图。
