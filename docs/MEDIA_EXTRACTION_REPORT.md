# 灵机本地音视频提取开发报告

> 文档角色：历史实施/验证快照，不是当前进度或当前架构权威。
> 当前状态看 `docs/PROJECT_STATUS.md`；当前代码入口看 `docs/MODULES/CODE_MAP.md`。

## 1. 目标

为视频号录屏、抖音/小红书下载文件、会议录音、短剧素材和其他本地音视频建立统一媒体入口，复用 Extraction Queue、Raw Snapshot、隐私分流、Obsidian 路由和增量索引。

媒体处理的主要管理入口是未来独立本地控制中心。Obsidian 插件和命令行仅作为可选快捷入口。

## 2. 模块

```text
src/extraction/adapters/media.py
src/control/runtime_settings.py
src/control/service.py
src/control/api.py
scripts/process_media.py
run_control_api.py
```

适配器：

```text
media_local 1.1.0
```

支持格式：

```text
视频：mp4 mov mkv avi webm m4v flv ts mts m2ts
音频：mp3 wav m4a aac flac ogg opus wma
```

## 3. 已实现能力

### 3.1 文件识别与原始快照

- 按本地文件后缀判断视频或音频。
- 处理前执行可配置文件体积限制。
- 通过限制后计算完整 SHA-256。
- 原文件进入 `storage/raw/<source_type>/<sha256>/`。
- 标准化笔记使用内容哈希稳定 ID。

### 3.2 FFprobe 元数据

FFprobe 可用时读取：

- 容器格式与时长。
- 码率、视频编码、分辨率和帧率。
- 音频编码、采样率和声道数。

探测后执行可配置最大时长限制。FFprobe 不可用时仍保存文件路径、大小和 SHA-256，并添加降级警告。

### 3.3 FFmpeg 派生处理

FFmpeg 可用并由主人明确启用时：

- 提取单声道 16kHz WAV 音轨。
- 按指定时间间隔提取关键帧。
- 限制关键帧数量和最大边长。
- 使用 `-threads` 与 `-filter_threads` 限制单任务线程。
- 使用进程内信号量限制 FFmpeg 并发任务数。
- 使用可配置超时阻止失控任务长期占用资源。

派生文件保存到：

```text
storage/derived/media/<media_sha256>/
├── audio.wav
└── keyframes/
```

### 3.4 默认值与用户设置

默认值：

| 参数 | 默认值 |
|---|---:|
| 关键帧间隔 | 30 秒 |
| 关键帧最大数量 | 500 |
| 关键帧最大边长 | 1280 px |
| FFmpeg 最大并发 | 1 |
| FFmpeg 单任务线程 | 2 |
| 单文件最大体积 | 20 GB |
| 单文件最大时长 | 360 分钟 |
| 媒体任务默认优先级 | 100 |
| FFprobe 超时 | 60 秒 |
| FFmpeg 超时 | 1800 秒 |

优先级：

```text
代码安全默认值
    ↓
storage/runtime_settings.json 用户设置
    ↓
单任务临时覆盖
```

所有数值都应由独立本地 UI 灵活修改。默认值仅用于首次运行，不能散落硬编码在 UI 或 Adapter 中。

### 3.5 本地控制 API

```text
GET   /api/settings
PATCH /api/settings
POST  /api/settings/reset
GET   /api/health
```

启动：

```powershell
python -m pip install -r requirements-ui.txt
python run_control_api.py
```

API 默认只绑定 `127.0.0.1:8766`，使用本机随机令牌。Tauri + React 可视化设置页尚未实现。

### 3.6 语义资料接入

适配器可接收：

- 已有转写文本。
- OCR 文本。
- 视觉描述文本。

若全部缺失，则标记：

```yaml
semantic_status: metadata_only
status: needs_review
review_status: needs_review
```

### 3.7 隐私

转写、OCR 和视觉描述经过本地敏感检测。高风险内容进入：

```text
08-Private/Imports/video/
08-Private/Imports/audio/
```

## 4. CLI

不传限制参数时继承本地 UI 保存的设置：

```powershell
python scripts/process_media.py "D:\media\example.mp4" --extract-keyframes --queue
```

单任务临时覆盖：

```powershell
python scripts/process_media.py "D:\media\example.mp4" `
  --extract-audio `
  --extract-keyframes `
  --keyframe-interval 20 `
  --max-keyframes 1000 `
  --keyframe-max-dimension 1920 `
  --ffmpeg-concurrency 2 `
  --ffmpeg-threads 4 `
  --max-input-gb 50 `
  --max-duration-minutes 720 `
  --priority 25 `
  --queue
```

## 5. 与视频号来源的关系

```text
WebCaptureAdapter
  负责链接、账号、标题、简介、发布时间和封面

MediaExtractionAdapter
  负责录屏或本地视频的媒体元数据、音轨、关键帧和语义资料承接
```

后续应使用 `related` 或统一 `external_id` 将网页来源笔记和本地媒体笔记自动关联。

## 6. 尚未实现

- Whisper 或其他 ASR 自动转写 Provider。
- 说话人分离与字幕时间码对齐。
- 关键帧 OCR 与视觉模型描述。
- 镜头、人物、动作和场景识别。
- 网页来源与本地媒体自动配对。
- Windows Job Object 级 CPU、内存和进程优先级硬限制。
- Tauri + React 可视化媒体设置页。

这些能力应作为可替换 Provider 或本地控制台模块接入，不硬编码进通用媒体适配器。

## 7. 测试

测试覆盖：

- FFprobe 元数据与转写写入。
- 无语义资料时进入待审核。
- 敏感转写进入私密目录。
- FFmpeg 线程、帧数和最大边长参数。
- 输入体积与媒体时长限制。
- UI 默认值、用户覆盖、任务级覆盖和任务优先级。
- 本地控制 API 令牌与设置修改。

CI 覆盖 Ubuntu Python 3.11/3.12、Windows Python 3.12、MCP 与 Obsidian 插件语法检查。
