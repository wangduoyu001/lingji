# 灵机本地音视频提取开发报告

## 1. 目标

为视频号录屏、抖音/小红书下载文件、会议录音、短剧素材和其他本地音视频建立统一媒体入口，复用现有 Extraction Queue、Raw Snapshot、隐私分流、Obsidian 路由和增量索引。

## 2. 模块

```text
src/extraction/adapters/media.py
scripts/process_media.py
```

适配器：

```text
media_local 1.0.0
```

支持格式：

```text
视频：mp4 mov mkv avi webm m4v flv ts mts m2ts
音频：mp3 wav m4a aac flac ogg opus wma
```

## 3. 已实现能力

### 3.1 文件识别与原始快照

- 按本地文件后缀判断视频或音频。
- 计算完整 SHA-256。
- 原文件进入 `storage/raw/<source_type>/<sha256>/`。
- 标准化笔记使用内容哈希稳定 ID。

### 3.2 FFprobe 元数据

FFprobe 可用时读取：

- 容器格式。
- 时长。
- 码率。
- 视频编码。
- 分辨率。
- 帧率。
- 音频编码。
- 采样率。
- 声道数。

FFprobe 不可用时，仍保存文件路径、大小和 SHA-256，并添加警告，不让整个任务失败。

### 3.3 可选派生文件

FFmpeg 可用并由主人明确启用时：

- 提取单声道 16kHz WAV 音轨。
- 按指定时间间隔提取关键帧。
- 限制最大关键帧数量，避免长视频无限占用空间。

派生文件保存到：

```text
storage/derived/media/<media_sha256>/
├── audio.wav
└── keyframes/
```

### 3.4 语义资料接入

适配器可接收：

- 已有转写文本。
- OCR 文本。
- 视觉描述文本。

这些内容进入同一媒体笔记。若全部缺失，则标记：

```yaml
semantic_status: metadata_only
status: needs_review
review_status: needs_review
```

### 3.5 隐私

转写、OCR 和视觉描述会经过本地敏感检测。高风险内容进入：

```text
08-Private/Imports/video/
08-Private/Imports/audio/
```

## 4. Obsidian 入口

`LingJi Control` 插件新增命令：

```text
新建本地音视频提取请求
```

请求类型：

```yaml
memory_type: extraction_request
request_type: media_extract
status: draft
input_path: D:/media/example.mp4
extract_audio: true
extract_keyframes: true
keyframe_interval_seconds: 30
max_keyframes: 120
```

主人确认后将 `status` 改为 `queued`，后台服务再执行。

## 5. CLI

只提取元数据：

```powershell
python scripts/process_media.py "D:\media\example.mp4"
```

生成音轨和关键帧：

```powershell
python scripts/process_media.py "D:\media\example.mp4" `
  --extract-audio `
  --extract-keyframes `
  --keyframe-interval 20 `
  --max-keyframes 100
```

接入已有转写：

```powershell
python scripts/process_media.py "D:\media\example.mp4" `
  --transcript "D:\media\example.txt" `
  --project LingJi
```

异步队列：

```powershell
python scripts/process_media.py "D:\media\example.mp4" --queue
```

## 6. 与视频号的关系

视频号来源由两部分组成：

```text
WebCaptureAdapter
  负责链接、账号、标题、简介、发布时间、封面等来源信息

MediaExtractionAdapter
  负责录屏或本地视频文件的媒体元数据、音轨、关键帧和语义资料承接
```

后续应使用 `related` 或统一 `external_id` 将网页来源笔记和本地媒体笔记关联。

## 7. 尚未实现

当前没有把以下能力伪装成已完成：

- Whisper 或其他 ASR 自动转写 Provider。
- 说话人分离。
- 自动字幕时间码对齐。
- 关键帧 OCR Provider。
- 视觉模型描述。
- 镜头、人物、动作和场景识别。
- 网页来源与本地媒体自动配对。
- GPU 任务调度。

这些能力应作为 Provider 插件接入，不应硬编码进通用媒体适配器。

## 8. 测试

`tests/test_media_extraction.py` 覆盖：

- FFprobe 元数据写入。
- 转写接入。
- 无语义资料时进入待审核。
- 敏感转写进入私密目录。

CI 同时覆盖 Ubuntu、Windows、MCP 和 Obsidian 插件语法检查。
