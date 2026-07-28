# Drama Memory V1 设计说明

状态：开发中

## 目标

在不修改 LingJi 核心 Memory Engine 的前提下，新增一个正式的领域插件 `Drama Intelligence`，完成首个可运行闭环：

```text
剧本导入
→ 文本标准化
→ 分集 / 场景 / 人物初步解析
→ 原文位置映射
→ Drama SQLite 读模型
→ 独立 Drama Qdrant Collection
→ 词法 + 语义混合检索
→ 8766 API
→ Tauri 短剧编剧工作台
```

本阶段不实现完整编剧 Agent、爆款因果判断或长篇一致性 Agent。

## 架构边界

```text
src/plugins/drama_intelligence/
= 领域插件主线

desktop/lingji-control/
= 唯一正式 UI

second_brain/
= 不修改
```

插件复用：

- Workspace 与路径隔离
- 统一 Embedding Provider
- 同一 Qdrant 服务
- Local Control API 8766
- Tauri Desktop

插件不创建：

- 第二套 MemoryGateway
- 第二套通用 Extraction Pipeline
- 第二个永久记忆事实源
- 平行桌面应用

## 数据权威

```text
原始剧本文件
= <workspace>/raw/drama/<drama_id>/original.<ext>

标准化文本与结构化 JSON
= <workspace>/derived/drama/<drama_id>/

Drama SQLite
= 可从原始剧本重新生成的读模型

Drama Qdrant Collection
= 可从 Drama SQLite 与标准化文本重建的语义索引
```

原始文件是剧本来源权威；SQLite 和 Qdrant 都是派生数据。

## 工作空间路径

```text
<workspace>/raw/drama/
<workspace>/derived/drama/
<workspace>/index/drama_read_model.db
```

Qdrant Collection：

```text
lingji_drama_production
lingji_drama_acceptance
```

不得跨 workspace 共享 collection。

## 支持格式

V1 支持：

- `.txt`
- `.md`
- `.docx`
- `.pdf`
- `.srt`
- `.vtt`
- `.ass`

DOCX 使用 `python-docx`。PDF 使用 `pypdf`，只处理包含可提取文本的 PDF；扫描 PDF 返回明确 `ocr_required`，不伪造空解析结果。

## 结构化对象

### Drama

- drama_id
- title
- source_file
- source_hash
- format
- character_count
- episode_count
- scene_count
- chunk_count
- import_status
- index_status
- created_at
- updated_at

### Episode

- episode_id
- episode_number
- title
- start_offset
- end_offset
- summary

### Scene

- scene_id
- episode_id
- scene_number
- heading
- location
- start_offset
- end_offset

### Character

- character_id
- name
- mention_count
- first_episode

### Chunk

- chunk_id
- drama_id
- episode_id
- scene_id
- chunk_type
- heading
- text
- source_start
- source_end
- tags

向量本身不写入领域 JSON。

## 解析策略

V1 使用确定性解析，不让模型输出成为唯一结构来源：

1. 统一换行和 Unicode 空白。
2. 根据格式保留页码、字幕序号或时间码来源。
3. 用中文/英文集标题规则识别分集。
4. 用场景标题、地点、内外景标记识别场景。
5. 用对白前缀和高频姓名模式识别人物。
6. 以 episode / scene / beat 三层切块。
7. 保存字符偏移与来源引用。

后续 AI Analyzer 只能补充结构和标签，不能破坏确定性来源映射。

## 检索策略

```text
SQLite FTS5 / LIKE fallback
+
Qdrant semantic search
+
metadata filter
+
RRF
=
Drama Search Result
```

返回必须包含：

- 剧名
- 集数
- 场景
- chunk 类型
- 原文片段
- source_start / source_end
- retrieval_channels
- lexical / semantic 分数
- citation
- warning

Qdrant 或 Embedding 不可用时继续返回词法结果，并附 `semantic_unavailable` warning。

## API

```text
GET  /api/drama/status
GET  /api/drama/library
POST /api/drama/import
POST /api/drama/search
GET  /api/drama/{drama_id}
GET  /api/drama/{drama_id}/episodes
```

所有接口使用现有 8766 token 认证。

## UI

新增导航分组：

```text
专业工作台
└── 短剧编剧
```

V1 页面包含：

- 状态摘要
- 文件路径导入
- 剧本库
- 检索框
- 结果来源定位
- 解析错误与语义降级提示

未实现的“生成剧本”和“一致性检查”明确显示为后续阶段，不提供假按钮。

## 测试

至少覆盖：

- TXT / Markdown / SRT / VTT / ASS 导入
- DOCX / PDF 适配器合同
- 扫描 PDF 明确返回 OCR required
- 5 万字输入
- 稳定 drama_id / episode_id / scene_id / chunk_id
- 重复导入幂等
- 原文偏移可追溯
- FTS 检索
- semantic 不可用降级
- RRF 合并
- workspace collection 隔离
- 8766 API
- Desktop 导航、加载、空数据、失败和结果展示

## 回滚

删除插件路由注册、Desktop 页面入口和依赖即可回滚。插件数据全部位于 workspace 的 `raw/drama`、`derived/drama` 与 `index/drama_read_model.db`，不会修改通用 Memory Engine 数据。
