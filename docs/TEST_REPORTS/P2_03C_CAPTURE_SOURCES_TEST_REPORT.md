# P2-03C Capture Sources Test Report（信息入口基础框架测试报告）

> Updated（更新时间）: 2026-07-21  
> Branch（分支）: `work/p2-03c-capture-sources`  
> Base Commit（基础提交）: `432ae059454cc7db8ab0ba4aaa63d24f5c9173e9`  
> Verified Commit（已验证提交）: `NOT_EXECUTED`  
> Status（状态）: `IMPLEMENTED_NOT_TESTED`

## 1. 测试代码

新增：

```text
tests/test_capture_models.py
tests/test_capture_policy.py
tests/test_capture_service.py
tests/test_capture_adapters.py
```

覆盖：

- CaptureEnvelope 不可变。
- 纯文本入口不要求 URL。
- 默认 LOW_POWER 为低风险策略。
- PAUSED 模式停止处理。
- LOW_POWER 不允许 OCR 或视频转写。
- 全局键盘监听默认禁用。
- 全屏截图监听默认禁用。
- FolderWatcher 拒绝文件系统根目录。
- 网页 URL 规范化去重。
- 剪贴板内容变化去重。
- 文件内容哈希去重。
- 文件变化后允许再次提交。
- CaptureService 对轻任务选择 execute，对低功耗和媒体选择 enqueue。
- metadata 敏感字段拒绝。
- Codex Adapter 产生 StructuredSource。
- Web Adapter 产生 StructuredSource。
- Media Adapter 产生 StructuredSource。
- 旧 Markdown 文档继续存在。
- 本地路径不进入结构化 metadata。
- 已有 ChatGPT structured_sources 不被覆盖。

## 2. 指定测试命令

```bash
python -m pytest \
  tests/test_capture_models.py \
  tests/test_capture_policy.py \
  tests/test_capture_service.py \
  tests/test_capture_adapters.py \
  -v --tb=short
```

静态编译命令：

```bash
python -m compileall src/capture src/extraction
```

## 3. 实际执行结果

```text
pytest: NOT EXECUTED
compileall: NOT EXECUTED
passed: NOT EXECUTED
failed: NOT EXECUTED
skipped: NOT EXECUTED
xfailed: NOT EXECUTED
```

原因：当前运行环境无法解析 `github.com`，无法克隆固定提交到本地执行。代码、测试和文档通过 GitHub 仓库接口直接提交。未安装依赖，未访问生产环境，也没有冒充测试通过。

## 4. 静态审查

确认：

- 没有创建第二套任务队列。
- CaptureService 只调用现有 ExtractionPipeline 的 enqueue/execute。
- 没有创建第二套 SourceReadModel。
- Registry 装饰器不重复解析 Adapter 输入。
- ChatGPT 已有结构化输出时直接保留。
- 没有 Pipeline source_type 特殊分支。
- 没有无限循环轮询。
- 没有注册键盘 Hook。
- 没有默认监听 C 盘或文件系统根目录。
- 没有读取浏览器 Cookie。
- 没有执行 OCR、ASR、Qdrant 或模型调用。

## 5. 数据安全

```text
读取生产文件: NO
读取生产 ChatGPT 正文: NO
修改 Production Vault: NO
修改 Production SQLite: NO
访问 Production Qdrant: NO
启用全局键盘监听: NO
执行全盘扫描: NO
执行高频文件扫描: NO
默认截图: NO
读取浏览器 Cookie: NO
```

## 6. 未验证内容

- 聚焦 pytest 的实际结果。
- compileall 的实际结果。
- 三个真实 Adapter 与仓库全部既有测试的回归兼容。
- Windows、macOS、Linux 文件系统根目录判断差异。
- CaptureService 接入正式 Control API 后的认证与响应合同。
- 真实 Workspace 下 CaptureEnvelope 到 StructuredReadModel 的端到端链路。

## 7. 当前状态

```text
IMPLEMENTED_NOT_TESTED
NOT_MERGED_AWAITING_COORDINATED_REVIEW
```

不得标记为聚焦测试通过。
