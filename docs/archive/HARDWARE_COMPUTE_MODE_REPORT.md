# 灵机 Hardware Capability Service 与算力模式报告

> 文档角色：历史实施/验证快照，不是当前进度或当前架构权威。
> 当前状态看 `docs/PROJECT_STATUS.md`；当前代码入口看 `docs/MODULES/CODE_MAP.md`。

> 模块：P2 Hardware Capability Service
> 分支：`feature/hardware-capability-service`
> Draft PR：`#7`
> 堆叠基线：`refactor/desktop-ui-modular-foundation`
> 状态：`REVIEW_REQUIRED`
> 验证 Head：`b85c1ff4ebd46d60e17152ac0616d746b3d3c219`
> GitHub Actions：`29698784423`

## 范围

本模块完成只读硬件能力检测、实时资源快照、全局算力模式、FastAPI 接口和桌面 UI。

明确不包含：

- 具体模型加载和基准；
- 模型下载或删除；
- Qdrant 向量检索；
- 数据库 Schema 变更；
- 云端 API Key。

## Research Notes

官方资料：

1. psutil：https://psutil.readthedocs.io/
2. NVIDIA NVML：https://docs.nvidia.com/deploy/nvml-api/
3. NVIDIA SMI：https://developer.nvidia.com/system-management-interface
4. Ollama `/api/tags`：https://docs.ollama.com/api/tags
5. Python `platform`、`shutil.disk_usage`、`subprocess`、`urllib.request`。

参考项目：

- Open WebUI：后端统一暴露本地模型和系统状态；
- Glances：以 psutil 为基础并诚实处理平台缺失能力；
- NVIDIA DCGM Exporter：GPU 指标带设备 ID 和采集源；
- Ollama：通过本地 API 读取真实模型列表。

采用：

- 标准库始终可运行；
- psutil 由 `requirements-ui.txt` 安装，但缺失时允许降级；
- NVIDIA 第一版使用结构化 `nvidia-smi` 查询；
- Windows 磁盘介质使用只读 `Get-PhysicalDisk`；
- Ollama 使用 `/api/tags`；
- FFmpeg/FFprobe 使用版本命令；
- Qdrant 只检查客户端和目录；
- GPU 只作为候选加速器。

拒绝：

- 根据显卡名称判断模型一定能运行；
- GPU 或 Ollama 缺失导致控制中心失败；
- UI 直接执行系统命令；
- 高频遥测永久写入 SQLite；
- 建立第二套设置或控制服务。

## 测试优先

测试文件：

```text
tests/test_hardware_capability.py
```

测试先于实现提交：

```text
8ceb12b29c2c741b8af7a472366817f072aaa020
```

覆盖：

1. NVIDIA GPU、显存、驱动和 CUDA Runtime 解析；
2. 无 GPU、无 psutil、Ollama 离线降级；
3. GPU 优先无 GPU 时回退 CPU；
4. 基础检索始终可用；
5. 默认值进入 RuntimeSettingsStore；
6. 设置定义包含推荐原因和修改提示；
7. FastAPI 返回硬件、遥测和算力策略；
8. API 可切换 CPU_ONLY；
9. 响应不包含未经测试的模型兼容结论。

## 后端实现

新增：

```text
src/hardware/__init__.py
src/hardware/service.py
src/hardware/detectors.py
src/hardware/system_detectors.py
src/hardware/tool_detectors.py
src/hardware/runner.py
```

检测内容：

- 操作系统、架构和 Python；
- CPU 型号、核心数和线程数；
- 总内存、可用内存和使用率；
- NVIDIA GPU、总显存、空闲显存、负载、温度和驱动；
- CUDA Driver 和 Runtime；
- 磁盘容量、空闲空间、文件系统和只读状态；
- Windows 物理磁盘介质和健康；
- Ollama、FFmpeg、FFprobe、Qdrant Client 和目录。

响应固定包含：

```text
compatibility_requires_load_test = true
```

P2 只返回 `candidate_device`。具体模型必须在 P3 经过依赖检测、加载测试和短基准。

## 全局算力模式

```text
auto
gpu_preferred
cpu_only
```

规则：

- CPU_ONLY 固定使用 CPU；
- 自动或 GPU 优先在检测到 GPU 时返回 GPU 候选；
- 无 GPU 自动回退 CPU；
- 所有模式下基础检索、Memory Gateway 和 MCP 保持可用。

## 设置 UI

新增设置组：

```text
hardware_compute / 系统与算力
```

默认值：

| Key | 默认值 |
|---|---:|
| `compute_mode` | `auto` |
| `compute_preferred_gpu_id` | 空 |
| `hardware_static_refresh_seconds` | 30 秒 |
| `hardware_foreground_interval_seconds` | 2 秒 |
| `hardware_background_interval_seconds` | 5 秒 |
| `hardware_idle_interval_seconds` | 30 秒 |
| `hardware_minimized_interval_seconds` | 60 秒 |
| `hardware_nvidia_smi_min_interval_seconds` | 10 秒 |

每项显示当前值、默认值、推荐值、推荐原因、修改时机、范围、影响、风险和恢复默认。

## FastAPI

```text
GET  /api/hardware/capabilities
GET  /api/hardware/telemetry
POST /api/hardware/refresh
GET  /api/compute/policy
PATCH /api/compute/policy
```

继续复用 LocalControlService、RuntimeSettingsStore 和本地控制令牌。

## 桌面 UI

新增一级页面：

```text
系统与算力
```

显示：

- 系统、CPU、内存、GPU、CUDA；
- 实时 CPU/内存/GPU 状态；
- 磁盘和介质；
- Ollama、FFmpeg、FFprobe 和 Qdrant；
- 当前算力模式、候选设备和回退原因；
- 明确的模型兼容性提示。

支持重新检测和三种算力模式切换。所有其他默认值在设置页学习和修改。

## 自动验证

GitHub Actions：

```text
Run 29698784423
Head b85c1ff4ebd46d60e17152ac0616d746b3d3c219
```

| 检查 | 结果 |
|---|---|
| Ubuntu Python 3.11 | success |
| Ubuntu Python 3.12 | success |
| Windows Python 3.12 | `117 tests / OK` |
| Desktop UI Smoke | success |
| TypeScript / Vite / Tauri | success |
| MCP / Browser / Obsidian | success |

新增硬件专项测试 4 项。

## 真机验收

当前不能标记 `ACCEPTED`，因为 GitHub Runner 没有主人的 RTX 4060。

主人电脑需要确认：

1. RTX 4060 名称、显存、负载、温度和驱动基本正确；
2. CUDA Driver 与 Runtime 状态真实；
3. 磁盘类型与 Windows 基本一致；
4. Ollama 模型数量正确；
5. CPU_ONLY 切换成功；
6. GPU 优先仍提示具体模型需要加载测试；
7. 设置页可以修改并恢复全部采样默认值；
8. 禁用 NVIDIA 工具后基础检索和 MCP 仍正常。

## 已知限制

- 第一版 GPU 采样使用 `nvidia-smi`，NVML 低开销采样尚未实现；
- AMD 和 Intel 独显专用探测器尚未实现；
- 只有驱动没有 CUDA Toolkit 时，Runtime 会显示未检测到；
- Windows 可能把磁盘介质报告为 `unknown`；
- Qdrant 只检查客户端和目录；
- 实时 WebSocket 活动流属于 P5；
- PR #7 仍堆叠在 P1 上。

## 风险与回滚

- 系统命令使用参数数组，不使用 shell 拼接；
- PowerShell 内容固定且只读；
- 错误信息限制长度；
- 不记录 API Key；
- 不修改 Vault 或数据库 Schema。

回滚 PR #7 即可移除本模块。Runtime Settings 中新增覆盖字段会被旧代码忽略，不影响 Vault、Raw、Memory DB、State DB 和备份。

## 当前结论

```text
P2 = REVIEW_REQUIRED
```

剩余门槛：P0-B 真机资料验收、P1 UI 验收、RTX 4060 真机数值验收，以及建立 `integration/lingji-v1` 后重新基线验证。
