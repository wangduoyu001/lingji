# 灵机 Hardware Capability Service 与算力模式报告

> 模块：P2 Hardware Capability Service  
> 分支：`feature/hardware-capability-service`  
> Draft PR：`#7`  
> 堆叠基线：`refactor/desktop-ui-modular-foundation`  
> 状态：`REVIEW_REQUIRED`  
> 最终验证 Head：`c2590a9d5af9decf1a69aadc310867eaaca80bd0`  
> 最终 GitHub Actions：`29699277515`

## 范围

完成只读硬件检测、资源快照、全局算力模式、FastAPI 和“系统与算力”UI。

不包含具体模型加载、模型下载或删除、Qdrant 检索、数据库迁移和云端 Provider。

## Research Notes

官方资料：

- psutil：https://psutil.readthedocs.io/
- NVIDIA NVML：https://docs.nvidia.com/deploy/nvml-api/
- NVIDIA SMI：https://developer.nvidia.com/system-management-interface
- Ollama Tags：https://docs.ollama.com/api/tags
- Python 标准库 `platform`、`shutil.disk_usage`、`subprocess`、`urllib.request`。

参考项目：Open WebUI、Glances、NVIDIA DCGM Exporter、Ollama。

采用：

- 标准库始终可运行；
- psutil 作为 UI 安装依赖，同时保留缺失降级；
- NVIDIA 第一版使用结构化 `nvidia-smi`；
- Windows 磁盘介质使用只读系统查询；
- Ollama 使用 `/api/tags`；
- GPU 只作为候选设备。

拒绝：

- 根据显卡名称宣布模型兼容；
- GPU、Ollama、FFmpeg 或 psutil 缺失时关闭控制中心；
- UI 直接执行系统命令；
- 高频遥测永久写入 SQLite；
- 第二套设置或控制服务。

## 测试优先

测试文件：`tests/test_hardware_capability.py`。

测试先于实现提交：

```text
8ceb12b29c2c741b8af7a472366817f072aaa020
```

最终专项测试 5 项：

1. GPU、显存、驱动和 CUDA 解析；
2. 无 GPU、无 psutil、Ollama 离线降级；
3. 算力默认值和帮助字段；
4. 设置修改真正更新静态、遥测和 GPU 探测缓存；
5. FastAPI 算力模式切换。

## 实现

新增：

```text
src/hardware/__init__.py
src/hardware/service.py
src/hardware/detectors.py
src/hardware/system_detectors.py
src/hardware/tool_detectors.py
src/hardware/runner.py
```

检测内容：系统、CPU、核心/线程、内存、磁盘、NVIDIA GPU、显存、负载、温度、驱动、CUDA、Ollama、FFmpeg、FFprobe 和 Qdrant Client/目录。

响应始终包含：

```text
compatibility_requires_load_test = true
```

P2 只返回候选设备。具体模型仍需静态评估、依赖检测、加载测试和短基准。

## 算力模式

```text
auto
gpu_preferred
cpu_only
```

无 GPU 时自动回退 CPU。所有模式下基础检索、Memory Gateway 和 MCP 保持可用。

## 设置与真实生效

设置组：`hardware_compute / 系统与算力`。

| 设置 | 默认值 |
|---|---:|
| 全局算力模式 | `auto` |
| 首选 GPU ID | 空 |
| 静态检测缓存 | 30 秒 |
| 前台遥测缓存 | 2 秒 |
| 后台采样策略 | 5 秒 |
| 空闲采样策略 | 30 秒 |
| 最小化采样策略 | 60 秒 |
| GPU 命令最短间隔 | 10 秒 |

静态缓存、前台遥测缓存和 GPU 探测最短间隔已经由 RuntimeSettingsStore 驱动。后台、空闲和最小化调度将在 P5 活动中心消费，UI 说明中不得把它们描述为已经自动调度。

能力页和遥测页共享 GPU 缓存，普通读取不会绕过主人设置连续启动 GPU 查询命令。手动“重新检测硬件”才会强制刷新。

## API 与 UI

```text
GET  /api/hardware/capabilities
GET  /api/hardware/telemetry
POST /api/hardware/refresh
GET  /api/compute/policy
PATCH /api/compute/policy
```

桌面新增“系统与算力”页面，显示真实检测源、候选设备、回退原因和模型兼容性警告。所有可调默认值在设置页可学习、修改和恢复。

## 最终自动验证

```text
Run 29699277515
Head c2590a9d5af9decf1a69aadc310867eaaca80bd0
Windows: 118 tests / OK
```

Linux 3.11/3.12、Windows、Desktop UI、TypeScript、Vite、Tauri、MCP、浏览器扩展和 Obsidian 插件全部成功。

## 真机门槛

状态保持 `REVIEW_REQUIRED`，因为 CI 没有主人的 RTX 4060。

主人电脑需要确认：

- GPU 名称、显存、负载、温度和驱动；
- CUDA Driver 与 Runtime；
- Windows 磁盘介质；
- Ollama 模型数量；
- CPU_ONLY 与 GPU 优先切换；
- 设置修改和恢复；
- 禁用 NVIDIA 工具后基础检索与 MCP 仍可用。

## 已知限制与回滚

- 第一版 NVIDIA 动态检测使用 `nvidia-smi`；NVML 低开销采样尚未实现；
- AMD 和 Intel 独显专用探测器未实现；
- Qdrant 只检查客户端和目录；
- WebSocket 和自适应活动调度属于 P5；
- PR #7 仍堆叠在 P1 上。

本模块无数据库迁移。回滚 PR #7 不影响 Vault、Raw、Memory DB、State DB 和备份。
