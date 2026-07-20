# P2-03C Capture Sources Foundation（信息入口基础框架）

> Updated: 2026-07-21  
> Branch: `work/p2-03c-capture-sources`  
> Base Commit: `432ae059454cc7db8ab0ba4aaa63d24f5c9173e9`  
> Status: `COORDINATED_REVIEW_FIXES_IMPLEMENTED` / `IMPLEMENTED_NOT_TESTED`

## 1. 架构边界

```text
Capture Input
-> CaptureEnvelope
-> CapturePolicy
-> CaptureDeduplicator.probe()
-> ExtractionPipeline.enqueue() / execute()
-> CaptureDeduplicator.commit()（仅 Pipeline 成功后）
-> Adapter
-> ExtractedDocument
-> StructuredSource
-> Vault / StructuredReadModel
```

Capture 模块只负责入口合同、策略、去重和调度决策。没有新增队列、Schema、SourceReadModel、Control API 或 Tauri 代码。

## 2. 本轮返工修复

### Registry 显式结构化回退

`AdapterRegistry.register(adapter, structured_fallback=False)` 默认不包装 Adapter，旧 `register(adapter)` 调用继续兼容。

仅在 `src/extraction/bootstrap.py` 中为以下 Adapter 显式开启：

- `CodexWorkReportAdapter`
- `WebCaptureAdapter`
- `MediaExtractionAdapter`

`ChatGPTExportAdapter` 保留自身 `structured_sources`，未来未知 Adapter 不会自动得到通用 StructuredSource。

### Message 到 Memory 的精确关联

`StructuredReadModelSink` 对每条 Message：

1. 优先读取 `message.metadata.document_stable_id`。
2. 缺失时回退到 `conversation.metadata.document_stable_id`。
3. 单独确认对应 Memory 是否存在。
4. 只为当前 Message 写入对应 Memory Link。
5. 单条 Memory 缺失仅跳过该条 Link，不影响同 Conversation 其他 Message。

这保留了 ChatGPT 的 Conversation 级回退，同时修复 Codex 多文档批次全部指向第一篇 Memory 的问题。

### 去重两阶段提交

`CaptureDeduplicator` 现在提供：

```text
probe/check（只检查，不写 _seen）
remember/commit（成功后记录）
```

`CaptureService` 仅在 Pipeline enqueue/execute 成功后调用 commit。Pipeline 抛出异常时不会污染去重状态，下一次提交可正常重试。

## 3. CaptureEnvelope 正式字段

新增：

```text
platform
description
external_id
process_later
```

手机分享和浏览器入口不再依赖 metadata 暗中表达这些核心合同。`process_later=True` 无条件选择 enqueue。

## 4. metadata 安全合同

metadata 递归检查 dict/list/tuple，拒绝至少以下键：

```text
token
access_token
cookie
api_key
apikey
authorization
password
secret
credential
session
```

metadata 不得覆盖：

```text
title
url
capture_method
author
account_name
published_at
media_url
cover_url
transcript
ocr_text
```

Pipeline payload 使用 `payload["metadata"]` 保存扩展信息，平台、描述、外部 ID 通过 CaptureEnvelope 正式字段传递。

## 5. 兼容性

- 旧 Markdown 输出不改变。
- `_StructuredOutputAdapter` 仍从同一批 ExtractedDocument 生成结构化输出，不重新解析输入。
- 结构化消息中的本地绝对路径替换为 `[local file]`。
- `register(adapter)` 旧调用保持可用，默认不包装。
- ChatGPT 自有结构化输出不被替换。

## 6. 测试范围

已更新 Capture 测试覆盖：

- Registry 默认不包装未知 Adapter。
- Codex/Web/Media 显式回退。
- 已有结构化输出保持不变。
- Pipeline enqueue/execute 失败后可重试。
- 成功后第二次才判定 duplicate。
- process_later 强制排队。
- metadata 保留字段防覆盖。
- 嵌套 Token/Cookie/API Key 拒绝。
- 手机分享正式字段进入 payload。
- Markdown 与绝对路径兼容。

当前环境无法克隆 GitHub 仓库并执行 pytest，因此状态保持 `IMPLEMENTED_NOT_TESTED`。

## 7. 禁止事项确认

```text
Tauri: NOT MODIFIED
SourceReadModel: NOT MODIFIED
Control API: NOT MODIFIED
Schema: NOT MODIFIED
Capture Center UI: NOT STARTED
Merge: NOT PERFORMED
Rebase: NOT PERFORMED
Force push: NOT PERFORMED
```

## 8. 当前状态

```text
COORDINATED_REVIEW_FIXES_IMPLEMENTED
IMPLEMENTED_NOT_TESTED
NOT_MERGED
```

推送原分支后停止，不领取新任务。
