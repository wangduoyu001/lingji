# Drama Memory V1 Implementation Report

## 1. Scope

本报告是 PR #54 的实现与自动测试权威，覆盖首个可用 Drama Memory 垂直闭环：

```text
单部与目录批量剧本导入
原始文件与标准化正文保存
分集 / 场景 / 人物确定性解析
原文来源定位
Drama SQLite 结构化读模型
独立 Drama Qdrant Collection
词法 + 语义混合检索
认证的 8766 API
Tauri 短剧编剧工作台
```

不包含：

```text
Writer Agent
一致性检查 Agent
高频叙事模式挖掘
OCR 执行
视频生产
投流
资产管理
```

这些能力必须等待真实剧本检索验收，不能先做一个会大量生成垃圾的按钮。

## 2. Branch and dependency

```text
Pull request: #54
Branch: feature/drama-memory-v1
Base: work/windows-gui-low-token-validation
Validated code commit: 28d31bb21369a5416bf962bbe8e46e6f9e24f093
```

PR #54 是堆叠 Draft，依赖未合并 PR #53。不得先于 PR #53 和其主人安装版 UI 验收合并。

## 3. Architecture decisions

```text
src/plugins/drama_intelligence/
= Drama 领域实现

src/control/drama_api.py
= 8766 认证 API

desktop/lingji-control/src/pages/DramaPage.tsx
= 唯一正式 UI
```

强制边界：

- 不修改通用 Memory Engine schema。
- 不创建第二个 MemoryGateway。
- 不创建第二套 Embedding 配置。
- 不修改 `second_brain/`。
- Drama 不自动进入个人永久记忆。
- Desktop 不直连 SQLite、Qdrant 或 Ollama。
- production / acceptance 使用不同路径和不同 Drama Collection。

## 4. Data flow

```text
用户选择剧本
→ load_script()
→ 格式适配与标准化
→ parse_script()
→ 原始文件复制到 raw/drama
→ full_text.md + source_map.json
→ drama.json 派生快照
→ DramaRepository
→ Drama Qdrant upsert
→ 8766 API
→ DramaPage
```

数据权威：

```text
<workspace>/raw/drama/<drama_id>/original.<ext>
= 原始剧本来源权威

<workspace>/derived/drama/normalized/<drama_id>/
= 标准化正文与来源映射

<workspace>/derived/drama/knowledge/<drama_id>/drama.json
= 可重建结构化导出

<workspace>/storage/index/drama_read_model.db
= 可重建结构化/词法读模型

lingji_drama_<workspace>
= 可重建语义索引
```

Embedding 数组不写入 Drama JSON。

## 5. Import adapters

支持：

```text
txt
md
docx
pdf
srt
vtt
ass
```

实现合同：

- 文本支持 UTF-8 BOM、UTF-8 和 GB18030。
- DOCX 按文档顺序读取段落与表格行。
- PDF 按页提取文本。
- SRT/VTT/ASS 删除格式控制文本并保留字幕时间码。
- 扫描或纯图片 PDF 明确返回 OCR required。
- 同一源文件 SHA256 重复导入保持幂等。
- 目录导入按稳定顺序处理。
- 单文件失败不取消整批。
- 批量文件数量有硬上限。

## 6. Parsing and identity

确定性对象：

```text
Drama
Episode
Scene
Character
DramaChunk
```

稳定身份：

```text
drama_id = source SHA256
source_ref = drama + episode + scene + part
chunk_id = drama + source_ref + normalized offsets
```

每个可检索 chunk 包含：

```text
chunk_type
heading
text
episode_number
scene_number
characters
tags
source_ref
source_locator
start_offset
end_offset
```

来源定位示例：

```text
line:12
page:8
block:23
cue:15@00:01:03.200-00:01:06.400
```

跨多个来源单元时返回起止 locator。自动测试验证：

```text
normalized_text[start_offset:end_offset] == retrieved_text
```

## 7. Structured repository

`DramaRepository` 提供：

- Drama、Episode、Scene、Character、Chunk 表。
- SHA256 唯一约束。
- schema version 与 revision。
- FTS5 索引。
- 中文长句3/4/2字 n-gram 与 substring fallback。
- Drama 和 chunk_type 过滤。
- 按 chunk ID 有界回读。
- 旧 schema 增量列迁移。

修复记录：

- 初版中文长句只使用前12个 n-gram，导致真正可命中的“继承人”排在候选范围外。
- 修复后优先生成3字词，并使用最多32个有界候选。
- 不降低测试断言。

## 8. Semantic indexing

复用：

```text
src/model_center EmbeddingProvider
src/retrieval/QdrantSemanticProvider
```

Collection：

```text
lingji_drama_production
lingji_drama_acceptance
```

Payload 包含：

```text
kind=drama_chunk
memory_id=drama_id
chunk_id
project=drama_id
chunk_type
heading
episode_number
scene_number
source_ref
source_locator
characters
tags
```

强制重建同一 Drama 时，先按 `memory_id` 删除旧 points，再写入当前 chunks，防止已删除桥段继续被召回。

## 9. Hybrid retrieval

```text
FTS5
+
中文 substring / n-gram fallback
+
Qdrant semantic recall
+
Drama / chunk_type metadata filter
+
RRF
=
source-traceable results
```

每条结果返回：

- 剧名
- 集数与场次
- 标题与人物
- 正文片段
- 页码、时间码、段落或行号
- 标准化偏移
- lexical / semantic 通道
- 分通道分数
- 命中原因
- citation
- warning

Embedding 或 Qdrant 不可用时继续词法检索，并返回 `semantic_unavailable`，不得把降级显示成语义健康。

## 10. API changes

```text
GET  /api/drama/status
GET  /api/drama/library
GET  /api/drama/library/{drama_id}
POST /api/drama/import
POST /api/drama/import-directory
POST /api/drama/search
```

所有路由使用现有 8766 Token 认证。

## 11. UI changes

新增正式入口：

```text
短剧编剧
```

已实现控件：

- 单部文件选择和导入。
- 剧本目录选择和批量导入。
- Drama Memory 与语义状态。
- Workspace、revision 和 Collection 显示。
- 剧本库选择。
- 按剧本和 chunk 类型过滤。
- 精准参考检索。
- 页码、字幕时间码、DOCX 段落和文本行号显示。
- 标准化原文偏移显示。
- lexical / semantic 通道显示。
- 扫描 PDF、批量失败和语义降级提示。

Writer Agent 按钮禁用并明确标注等待检索验收，不存在假成功逻辑。

## 12. Low-context local validation

统一入口：

```powershell
.\scripts\validate.ps1 -Mode focused -Area drama
```

只运行：

```text
python -m pytest -q --tb=short tests/test_drama_memory.py
npm run test:drama
```

成功日志只落盘并读取 `latest-summary`；失败先读取尾部。开发阶段不重复运行 full/release。

## 13. Automated tests

Python 覆盖：

- 5万字以上剧本导入。
- 10部合成剧本批量导入。
- 批量重复导入不产生重复 Drama。
- 分集、场景和人物解析。
- 原文偏移精确回切。
- 文本行 locator。
- DOCX block locator。
- SRT 时间码 locator。
- 扫描 PDF OCR-required。
- 中文长句词法降级。
- Drama Collection payload 与 metadata filters。
- 强制重建调用旧语义 points 清理。
- 认证的单部导入、批量导入和搜索 API。

Desktop smoke 覆盖：

- 导航与页面路由。
- 单部和批量导入控件。
- 支持格式。
- 8766 Drama 路由。
- 独立 Collection。
- source locator 与 citation UI。
- 语义降级 UI。
- Drama focused validation 入口。
- Writer Agent 禁用边界。

## 14. Automated result

验证代码：

```text
28d31bb21369a5416bf962bbe8e46e6f9e24f093
```

GitHub Actions：

```text
tests workflow #904: SUCCESS
browser-capture-smoke: SUCCESS
desktop-ui-smoke + TypeScript/Vite build: SUCCESS
mcp-smoke-test: SUCCESS
obsidian-plugin-smoke: SUCCESS
Python 3.11 full suite: SUCCESS
Python 3.12 full suite: SUCCESS
Windows Python 3.12 full suite: SUCCESS
```

前一代码树出现1项失败：中文长句词法回退为空。根因和修复记录在第7节；最终验证树已全绿。

## 15. Not yet validated

以下内容没有证据，不得宣称完成：

```text
10部真实爆款短剧导入
50–100万字真实资料吞吐
100道真实剧情/来源问题
检索准确率 ≥85%
人物解析准确率 ≥90%
分集事件准确率 ≥85%
真实 Ollama + Qdrant 大批量耗时
导入 <30分钟
检索 <3秒
安装版 Drama UI 全控件验收
```

## 16. Known limitations

- 批量导入当前是同步 API 请求，UI 有超时和结果摘要，但尚未接入现有 extraction queue 的结构化进度、取消和重试。
- V1 人物、分集和场景解析是确定性启发式，不等于 AI 审核后的 Drama Profile。
- PDF 不执行 OCR。
- 尚未建立 Qdrant payload indexes 性能策略。
- 尚未建立模式人工校正、项目圣经和一致性事实表。
- PR #54 依赖 PR #53，不能单独合并或发布安装包。

## 17. Rollback

回滚时删除：

```text
src/plugins/drama_intelligence/
src/control/drama_api.py
Drama API 注册
Desktop drama 页面、样式、导航和 smoke
Drama 依赖
validate.ps1 drama area
```

派生数据只存在于 active workspace 的 Drama 路径和独立 Qdrant Collection，不需要修改通用 Memory Engine 数据。

## 18. Next stage

```text
将批量导入接入现有任务队列
→ 真实10部剧本 acceptance workspace 导入
→ 100题来源与桥段检索评测
→ 人工修正解析结构
→ 模式库
→ 项目圣经与状态快照
→ 一致性检查
→ Writer Agent
```

## 19. Status

```text
V1_CODE_IMPLEMENTED
AUTOMATED_CROSS_PLATFORM_VALIDATION_PASSED_AT_28D31BB2
SOURCE_TRACEABILITY_IMPLEMENTED
LEXICAL_AND_SEMANTIC_RETRIEVAL_IMPLEMENTED
WRITER_AGENT_DISABLED_BY_DESIGN
OWNER_DATA_RETRIEVAL_ACCEPTANCE_REQUIRED
INSTALLED_UI_ACCEPTANCE_REQUIRED
STACKED_DRAFT_PR_UNMERGED
```
