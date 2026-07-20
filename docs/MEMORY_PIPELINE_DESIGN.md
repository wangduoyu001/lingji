# 记忆管道 (Memory Pipeline) 设计文档

## 概述
记忆管道是灵机系统的核心数据处理流程，负责将原始信息转化为结构化的长期记忆。设计遵循 "Capture First" 原则，优先自动分类和打标签，而非直接分析商业机会。

## 架构

```
[原始输入] → [采集器] → [提取队列] → [提取工作器] → [记忆存储]
                                                      ↓
                                              [嵌入向量化] → [向量检索]
```

## 组件说明

### 1. 采集层 (Capture Layer)
- **主动投喂**: 通过 UI 手动提交网页链接、文字或本地文件
- **自动化采集**: `daily_capture` 定时任务（24小时周期）自动扫描新文件
- **ChatGPT 导入**: `ChatGPTImporter` 导入聊天记录
- **Web Capture**: 通过 `archived-web` 管道捕捉网页

### 2. 提取队列 (Extraction Queue)
- 基于 SQLite 的持久化队列 (`SQLiteExtractionQueue`)
- 支持优先级排序和延迟重试
- 状态跟踪: pending → running → completed/failed

### 3. 提取工作器 (Extraction Worker)
- 支持多种媒体类型: 文本、图片、音频、视频
- **ASR 转写**: faster-whisper (本地模型)
- **OCR 识别**: PaddleOCR（可插拔）
- **镜头检测**: PySceneDetect（视频关键帧）
- **语义分析**: MediaSemanticService

### 4. 记忆存储 (Memory Storage)
- **状态数据库**: SQLite，存储记忆元数据和生命周期状态
- **Qdrant 向量库**: 可选启用，默认关闭以节省资源
- **索引文件**: `pemis_index.json`（可重建的二级索引）

### 5. 嵌入向量化
- 使用 Ollama 本地嵌入模型 (`nomic-embed-text` 等)
- 支持主嵌入模型和回退模型
- 嵌入维度: 1024 (nomic-embed-text)

## 数据流

1. **Capture**: 新笔记写入 Obsidian Vault (不可变 Source of Truth)
2. **Index**: 扫描 Vault 更新 `pemis_index.json` (增量同步)
3. **Extract**: 从原始笔记提取结构化记忆
4. **Embed**: 生成向量嵌入存入向量库
5. **Retrieve**: 根据查询检索相关记忆

## 定时任务

| 任务 | 周期 | 功能 |
|---|---|---|
| `read_feedback` | 10分钟 | 读取 Control Center 反馈 |
| `daily_capture` | 24小时 | 自动扫描新文件 + 打标签 |
| `distill/distillation` | 24小时 | 知识蒸馏 |
| `integrity` | 24小时 | 数据完整性检查 |
| `full_check` | 24小时 | 更新看板 |

## 扩展指南

### 添加新的媒体处理器
1. 实现提取器接口 (`src/extraction/`)
2. 在 `build_extraction_pipeline` 中注册
3. 添加对应的测试

### 添加新的采集源
1. 实现采集适配器
2. 在 `src/control/api.py` 中添加投递端点
3. 更新前端投递页面