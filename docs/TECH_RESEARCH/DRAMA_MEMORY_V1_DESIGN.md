# Drama Memory V1 设计说明

状态：Draft PR 开发与自动验证中  
范围：短剧剧本记忆与精准参考，不包含视频生产、投流或资产管理

## 1. 产品目标

在不修改 LingJi 通用 Memory Engine 的前提下，增加正式领域插件 `Drama Intelligence`：

```text
剧本文件
→ 安全导入与标准化
→ 分集 / 场景 / 人物确定性解析
→ 原文来源定位
→ Drama SQLite 读模型
→ 独立 Drama Qdrant Collection
→ 词法 + 语义混合检索
→ 8766 API
→ Tauri 短剧编剧工作台
```

V1 先验证：

> 能否把十部短剧变成可长期保存、可定位原文、可精准调用的编剧参考库。

Writer Agent、一致性检查和模式挖掘在检索质量通过真实资料验收后进入后续阶段。

## 2. 强制架构边界

```text
src/plugins/drama_intelligence/
= Drama 领域插件

src/control/drama_api.py
= 认证的 8766 API

desktop/lingji-control/
= 唯一正式 UI

second_brain/
= 不修改
```

复用现有：

- Workspace 与 production / acceptance 隔离
- Embedding Provider
- Qdrant Provider
- 8766 Token 认证
- Tauri Desktop
- 低上下文本地验证入口

禁止新增：

- 第二套 MemoryGateway
- 第二条通用 Extraction Pipeline
- 第二个永久记忆事实源
- 第二套 Embedding 配置
- 平行桌面应用

## 3. 数据权威

```text
<workspace>/raw/drama/<drama_id>/original.<ext>
= 原始剧本来源权威

<workspace>/derived/drama/normalized/<drama_id>/
= 标准化 UTF-8 正文与 source_map.json

<workspace>/derived/drama/knowledge/<drama_id>/drama.json
= 可重建结构化导出快照

<workspace>/storage/index/drama_read_model.db
= 可重建 Drama 结构化读模型与词法索引

lingji_drama_<workspace>
= 可重建语义索引
```

SQLite 和 Qdrant 都不是永久事实源。向量数组不写进 Drama JSON。

## 4. 支持格式

V1 支持：

```text
txt
md
docx
pdf
srt
vtt
ass
```

行为：

- 文本支持 UTF-8 BOM、UTF-8、GB18030。
- DOCX 保留段落或表格行定位。
- PDF 保留页码定位。
- SRT、VTT、ASS 保留字幕序号和时间码定位。
- 扫描或纯图片 PDF 返回 `OCR required`，不把空文本当成功。
- 同一源文件 SHA256 重复导入保持幂等。

## 5. 领域对象

### Drama

```text
drama_id
title
source_format
source_sha256
character_count
episode_count
scene_count
chunk_count
status
revision
```

### Episode

```text
episode_id
number
title
start_offset
end_offset
scene_ids
```

### Scene

```text
scene_id
episode_number
scene_number
heading
characters
start_offset
end_offset
```

### DramaChunk

```text
chunk_id
drama_id
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

`source_locator` 根据来源格式返回：

```text
line:12
page:8
block:23
cue:15@00:01:03.200-00:01:06.400
```

跨多个来源单元的片段返回起止定位。

## 6. 稳定身份与幂等

```text
drama_id = drama_<source_sha256[:12]>
source_ref = drama_id + episode + scene + part
chunk_id = sha1(drama_id + source_ref + normalized offsets)
```

同一输入重复解析必须得到相同 ID。

强制重建同一 Drama 时：

1. 删除该 Drama 的旧 Qdrant points。
2. 更新 SQLite 派生结构。
3. 重新建立当前 chunks。

禁止残留已经不存在的“幽灵桥段”。

## 7. 解析策略

V1 使用确定性解析建立最低可信结构：

1. 规范换行与空白。
2. 识别中文/英文分集标题。
3. 识别场次、地点、内景和外景标题。
4. 识别对白前缀人物。
5. 过滤旁白、镜头、字幕等非人物名称。
6. 按 episode / scene 语义边界切块。
7. 超长段落按 1800 字附近切分并保留重叠。
8. 保存标准化偏移和原始来源定位。

后续 AI Analyzer 只能补充 Profile、标签和模式，不得覆盖确定性来源映射。

## 8. 检索策略

```text
SQLite FTS5
+
中文长句 n-gram / substring fallback
+
Qdrant semantic search
+
Drama / chunk_type metadata filter
+
RRF 与通道分数
=
来源可追溯的 Drama Search Result
```

结果必须包含：

- 剧名
- 集数
- 场次
- 标题
- 人物
- 原文片段
- 页码、时间码、段落或行号
- 标准化偏移
- lexical / semantic 通道
- 命中原因
- citation
- warning

当 Embedding 或 Qdrant 不可用时：

```text
继续词法检索
+
返回 semantic_unavailable warning
```

禁止整次搜索失败或显示假语义结果。

## 9. API

```text
GET  /api/drama/status
GET  /api/drama/library
GET  /api/drama/library/{drama_id}
POST /api/drama/import
POST /api/drama/import-directory
POST /api/drama/search
```

所有接口复用现有 8766 Token 认证。Desktop 不直连 SQLite、Qdrant 或 Ollama。

## 10. UI

正式入口：

```text
短剧编剧
```

V1 提供：

- Drama Memory 状态和 workspace
- 单部文件选择与导入
- 目录批量导入
- 剧本库
- 按 Drama 和片段类型过滤
- 精准参考检索
- 原文引用和检索通道
- 扫描 PDF 与语义降级提示

Writer Agent 明确禁用并标注后续开放，不提供空壳成功按钮。

## 11. 低 Token 验收

开发阶段只运行：

```powershell
.\scripts\validate.ps1 -Mode focused -Area drama
```

该入口只执行：

```text
tests/test_drama_memory.py
npm run test:drama
```

最终合并前依赖仓库完整 CI。成功日志只落盘并读取摘要；失败先读取尾部。

## 12. V1 验收

自动覆盖：

- 5 万字剧本导入
- 10 部合成剧本批量导入
- 重复导入幂等
- 分集、场景、人物解析
- 原文偏移精确回切
- 文本行、DOCX 段落、字幕时间码定位
- 扫描 PDF 拒绝
- 中文长句词法降级
- Drama Qdrant Collection 隔离
- 强制重建清除旧向量
- 认证 API
- Desktop 导航、控件和状态合同

真实资料验收仍需：

```text
10 部真实短剧
50–100 万字
100 道来源与剧情问题
检索准确率 ≥ 85%
所有结果可定位原文
```

## 13. 后续阶段

### Phase 2

```text
Drama Profile
Character Profile
Episode Card
Scene Card
高频叙事模式提取
人工修正与版本记录
```

### Phase 3

```text
项目圣经
人物状态
秘密知情表
伏笔台账
一致性检查
检索增强 Writer Agent
```

## 14. 回滚

删除以下接线即可回滚功能：

- `src/control/drama_api.py` 注册
- Desktop `drama` 页面和导航
- Drama 专项依赖

领域数据仅存在于 workspace 的 `raw/drama`、`derived/drama`、`storage/index/drama_read_model.db` 和独立 Qdrant Collection，不修改通用 Memory Engine 数据。
