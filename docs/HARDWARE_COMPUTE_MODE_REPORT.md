# 灵机 Hardware Capability Service 与算力模式报告

> 模块：P2 Hardware Capability Service  
> 分支：`feature/hardware-capability-service`  
> 堆叠基线：`refactor/desktop-ui-modular-foundation`  
> 状态：`IN_PROGRESS`  
> 非目标：不实现模型下载、不判断具体模型一定可运行、不接入 Qdrant、不修改数据库 Schema、不处理 API Key

## Research Notes

### 官方资料

1. psutil CPU、内存、磁盘和进程资源接口  
   https://psutil.readthedocs.io/
2. NVIDIA NVML 设备、显存、利用率、温度和驱动接口  
   https://docs.nvidia.com/deploy/nvml-api/
3. NVIDIA System Management Interface  
   https://developer.nvidia.com/system-management-interface
4. Ollama `/api/tags` 本地模型列表  
   https://docs.ollama.com/api/tags
5. Python `platform`、`shutil.disk_usage` 和 `subprocess` 标准库。

### 类似项目

1. Open WebUI  
   https://github.com/open-webui/open-webui  
   借鉴：本地模型和系统状态通过后端 API 暴露，前端不直接执行系统命令。
2. Glances  
   https://github.com/nicolargo/glances  
   借鉴：psutil 为基础，多平台能力不可用时返回缺失状态。
3. NVIDIA DCGM Exporter  
   https://github.com/NVIDIA/dcgm-exporter  
   借鉴：GPU 指标必须标明采集源和设备 ID，不按显卡名称推断模型兼容性。
4. Ollama  
   https://github.com/ollama/ollama  
   借鉴：使用本机 HTTP API读取模型和运行状态，不扫描模型文件猜测安装情况。

### 采用

- 标准库始终可运行。
- psutil 作为可选增强，不成为灵机启动强依赖。
- NVIDIA 第一版使用 `nvidia-smi` 结构化查询；后续可加入 NVML 低开销采样。
- Ollama 通过 `/api/tags` 检测。
- FFmpeg/FFprobe 通过版本命令检测。
- Qdrant 只报告客户端、路径和配置状态，不在 P2 启动向量服务。
- 所有结果记录检测源、错误和采集时间。
- 算力模式只输出候选设备，不声称具体模型兼容。

### 拒绝

- 根据 `RTX 4060` 名称直接输出“某模型可运行”。
- GPU、psutil、Ollama 或 FFmpeg 缺失时让控制中心启动失败。
- UI 直接调用 PowerShell、nvidia-smi 或 Ollama。
- 把动态遥测每两秒永久写入 SQLite。
- 在 P2 增加第二套设置系统或任务队列。

## 测试优先

实现前新增 `tests/test_hardware_capability.py`，规定：

1. 有 NVIDIA 环境能解析 GPU、显存、驱动和 CUDA Runtime。
2. 无 GPU、无 psutil、Ollama 离线时仍返回诚实降级结果。
3. `gpu_preferred` 无 GPU 时自动回退 CPU。
4. 基础检索始终标记可用。
5. 所有算力默认值进入 RuntimeSettingsStore，并带推荐原因和修改提示。
6. FastAPI 暴露 capabilities、telemetry 和 compute policy。
7. API 可以切换到 CPU_ONLY。
8. 响应禁止出现 `models_can_run` 一类未经加载测试的结论。

测试提交：`8ceb12b29c2c741b8af7a472366817f072aaa020`

当前测试预期失败，因为 `src.hardware`、API 和 Service 注入尚未实现。实现和 CI 结果将在后续提交补充。

## 回滚

当前阶段只有独立测试和报告，不修改现有数据。回滚分支不会影响 Vault、SQLite、运行设置或桌面控制中心。
