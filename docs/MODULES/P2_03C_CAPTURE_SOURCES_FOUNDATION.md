# P2-03C Capture Sources Foundation（信息入口基础框架）

> Updated（更新时间）: 2026-07-21  
> Branch（分支）: `work/p2-03c-capture-sources`  
> Base Commit（基础提交）: `432ae059454cc7db8ab0ba4aaa63d24f5c9173e9`  
> Status（状态）: `IMPLEMENTED_NOT_TESTED`

## 1. 架构

```text
Capture Input（采集输入）
-> CaptureEnvelope（统一采集信封）
-> CapturePolicy（采集策略）
-> CaptureDeduplicator（采集去重器）
-> ExtractionPipeline.enqueue() / execute()
-> Adapter（适配器）
-> ExtractedDocument（提取文档）
-> StructuredSource（结构化来源）
-> Vault
-> Structured Read Model（结构化读取模型）
```

Capture 模块只负责入口合同、策略、去重和调度决策。Extraction 模块继续负责解析、Vault 写入和结构化读取模型接线。没有创建第二套队列或第二套 SourceReadModel。

## 2. 文件所有权

新增：

- `src/capture/__init__.py`
- `src/capture/models.py`
- `src/capture/policy.py`
- `src/capture/service.py`
- `src/capture/deduplication.py`
- `src/capture/watchers.py`

修改：

- `src/extraction/registry.py`

测试：

- `tests/test_capture_models.py`
- `tests/test_capture_policy.py`
- `tests/test_capture_service.py`
- `tests/test_capture_adapters.py`

未修改 Tauri、SourceReadModel、Gateway、Control API、数据库 Schema 或 Qdrant。

## 3. 入口合同

`CaptureEnvelope` 是 frozen dataclass（不可变数据类），主要字段包括：

```text
capture_id
source_type
capture_method
title
url
text
html
input_path
author
account_name
published_at
media_url
cover_url
transcript
ocr_text
project_ids
tags
privacy
priority
received_at
metadata
```

正式 `capture_method`：

```text
mobile_share
browser_extension
clipboard
folder_watch
manual_upload
local_control_share
scheduled_import
```

URL 不是强制字段，因此同一合同可表达纯文本、文件、网页、媒体和聊天材料。

## 4. 手机分享合同

手机分享通过 `CaptureEnvelope(capture_method="mobile_share")` 表达：

- 平台：`source_type` 或 metadata 中的非敏感平台信息。
- URL：`url`。
- 标题：`title`。
- 选中文本或描述：`text`。
- 作者：`author`。
- 账号：`account_name`。
- 封面：`cover_url`。
- 媒体地址：`media_url`。
- 项目：`project_ids`。
- 标签：`tags`。
- 隐私：`privacy`。
- 稍后处理：由 CapturePolicy 的 queue-only（只排队）决策表达。

本轮不实现 iOS 或 Android 原生应用。

## 5. 浏览器入口合同

浏览器扩展通过 `capture_method="browser_extension"` 提交：

- 当前页面 URL。
- 页面标题。
- 选中文字。
- 渲染 HTML。
- 作者和发布时间。
- 来源域名可由 Web Adapter 根据 URL 解析。

CaptureService 不读取 Cookie，不接收 Token，不包含平台专用解析。

## 6. 低功耗策略

正式模式：

```text
LOW_POWER
NORMAL
DEEP_CAPTURE
PAUSED
```

默认 LOW_POWER：

- 不实时执行。
- 默认只排队。
- 不允许 OCR。
- 不允许视频转写。
- 允许后续向量化。
- 仅空闲时运行。
- CPU 预算 20%。
- GPU 默认禁用。
- 文件监听必须使用系统事件合同。
- 全局键盘监听默认禁用。
- 全屏截图监听默认禁用。
- 软件安装监听默认关闭。

视频、OCR 和转写即使在 NORMAL 模式下也由 CaptureService 选择排队，不在入口提交路径执行重处理。

## 7. 去重规则

去重优先级：

1. 文件内容 SHA-256。
2. 规范化 URL + 内容哈希。
3. source_type + capture_method + 标题 + 文本 + transcript + OCR + external identity。

URL 规范化会：

- 小写协议和主机。
- 删除 fragment。
- 删除常见 UTM、spm、share token 等追踪参数。
- 稳定排序剩余 query 参数。

结果包含：

```text
is_duplicate
deduplication_key
matched_capture_id
reason
```

同一文件内容不重复排队；文件变化后哈希变化，可以再次处理。

## 8. 监听器规则

`CaptureWatcher` 定义：

```text
start(callback)
stop()
status()
capabilities()
```

提供安全 NoOp 合同：

- ClipboardWatcher
- FolderWatcher
- BrowserShareWatcher
- MobileShareWatcher

FolderWatcher 禁止文件系统根目录，且要求 filesystem-event-only（仅系统文件事件）策略。

本轮没有无限循环、全盘轮询、键盘 Hook、自动截图、密码框读取或浏览器 Cookie 读取。

## 9. Adapter 结构化映射

为避免 Codex、Web、Media 三个 Adapter 重复解析或复制接线代码，`AdapterRegistry` 在注册时使用 `_StructuredOutputAdapter` 装饰旧 Adapter。

执行过程：

```text
legacy adapter.extract()
-> 原 ExtractedDocument 和 Markdown 保持不变
-> 直接根据同一批 documents 生成 StructuredSource
```

映射：

### Codex

- Source：仓库、账号或 `codex:default`。
- Conversation：task_id 或工作报告外部 ID。
- Message：工作报告、错误、决策和后续任务文档。

### Web

- Source：平台、账号或网站来源。
- Conversation：单篇网页或一次分享。
- Message：已生成的网页正文 Markdown。

### Media

- Source：音频或视频来源。
- Conversation：单个媒体资产。
- Message：媒体文档，包含已有转写、OCR 或视觉备注。

本地输入路径在 StructuredMessage 内容中替换为 `[local file]`，但原 Vault Markdown 输出不改变。

ChatGPT Adapter 已有正式 `structured_sources` 时，装饰器直接保留，不重新生成。

## 10. 隐私规则

- 默认 privacy 为 `private`。
- metadata 顶层禁止 token、cookie、api_key、authorization、secret 等字段。
- CaptureService 不读取 Cookie 或系统密码输入。
- Structured Adapter metadata 不复制原始路径字段。
- 本地输入路径从结构化消息内容中脱敏。

## 11. 后续 UI 接线方式

未来 Capture Center（采集中心）只能调用 CaptureService 或其正式 Control API 门面：

- 提交 CaptureEnvelope。
- 查看 mode、paused 和 submitted 状态。
- 查看 capabilities。
- 调用 pause/resume。

UI 不应直接操作 watcher、SQLite 或 ExtractionQueue。

## 12. 未实现内容

- Capture Center UI。
- iOS/Android 原生分享扩展。
- 浏览器扩展前端。
- 系统级剪贴板注册。
- 系统级文件监听注册。
- 全局键盘监听。
- 全屏截图监听。
- 软件安装监听实现。
- OCR、ASR 或视频分析 Provider。
- 高频扫描或生产数据导入。

## 13. 下一步

等待1号、2号、3号开发报告统一审查。  
不自行开始 Capture Center UI。
