# P2-03C Capture Sources Test Report（信息入口基础框架测试报告）

> Updated: 2026-07-21  
> Branch: `work/p2-03c-capture-sources`  
> Base Commit: `432ae059454cc7db8ab0ba4aaa63d24f5c9173e9`  
> Verified Commit: `NOT_EXECUTED`  
> Status: `IMPLEMENTED_NOT_TESTED`

## 1. 本轮返工覆盖

```text
Registry 默认不包装未知 Adapter
Codex/Web/Media 显式 structured_fallback=True
已有 structured_sources 不被替换
每条 StructuredMessage 使用自身 document_stable_id
Conversation document_stable_id 仅作为回退
单条 Memory 缺失不影响其他 Message Link
Pipeline enqueue 失败不污染去重记录
Pipeline execute 失败不污染去重记录
成功提交后第二次才返回 duplicate
process_later=True 强制 enqueue
metadata 不得覆盖保留 payload 字段
metadata 递归拒绝 Token/Cookie/API Key 等敏感键
platform/description/external_id 使用正式字段
旧 Markdown 输出保持兼容
结构化消息不泄漏本地绝对路径
```

## 2. 指定命令

```bash
python -m compileall src/capture src/extraction
python -m pytest \
  tests/test_capture_models.py \
  tests/test_capture_policy.py \
  tests/test_capture_service.py \
  tests/test_capture_adapters.py \
  tests/test_structured_ingestion.py \
  -v --tb=short
```

## 3. 实际执行结果

```text
compileall: NOT EXECUTED
pytest: NOT EXECUTED
passed: NOT EXECUTED
failed: NOT EXECUTED
skipped: NOT EXECUTED
```

原因：当前执行容器无法解析 `github.com`，不能克隆远程分支到本地运行 Python。代码通过 GitHub 仓库接口提交，未伪造测试通过结果。

## 4. 静态审查结果

- `AdapterRegistry.register()` 新参数有默认值，旧调用兼容。
- Bootstrap 仅为 Codex/Web/Media 显式开启回退。
- ChatGPT 未开启通用回退，继续使用自身结构化输出。
- Deduplicator 的 probe/check 不写 `_seen`，commit/remember 才写入。
- CaptureService 在 enqueue/execute 返回成功后才 commit。
- `process_later` 参与队列决策且优先级最高。
- metadata 放入 `payload["metadata"]`，不再通过 `**metadata` 覆盖合同字段。
- metadata 递归扫描 dict/list/tuple。
- StructuredReadModelSink 逐 Message 判断 Memory，不再使用单个 Conversation Link 状态覆盖所有消息。
- 未修改 Tauri、SourceReadModel、Control API、数据库 Schema 或正式分支。

## 5. 数据安全

```text
生产文件读取: NO
生产数据库写入: NO
生产 Qdrant 访问: NO
浏览器 Cookie 读取: NO
全局键盘监听: NO
文件系统轮询: NO
Capture Center UI: NOT STARTED
```

## 6. 当前状态

```text
COORDINATED_REVIEW_FIXES_IMPLEMENTED
IMPLEMENTED_NOT_TESTED
NOT_MERGED
```

等待协调审查，不领取新任务。
