# 灵机记忆调取指南（权威）

> 本文是"如何从灵机高效取回记忆"的唯一权威文档。所有记忆的权威正文在
> Obsidian Vault + Git；本机 API/向量索引是可重建的检索层。

## 三条调取路径

### 1. 在任意 AI 对话里调取（推荐，第二大脑的正确用法）

灵机自带 MCP 服务器（stdio）。把它配置进 Codex / Claude / Cursor 等 AI 工具后，
AI 即可在对话中直接调取你的记忆，无需打开灵机界面：

```json
{
  "mcpServers": {
    "lingji": {
      "command": "<灵机安装目录>/Resources/lingji-core.exe",
      "args": ["--mcp"]
    }
  }
}
```

可用工具：

| 工具 | 用途 |
| --- | --- |
| `search_memory` | 按意思搜索全部记忆（本地 768 维向量 + 关键词混合召回） |
| `fetch_memory` | 取回某条记忆的完整正文（含分块） |
| `lingji_resolve_project` / `lingji_start_session` 等 | 项目上下文与工作会话 |

示例：在 Codex 里问"我之前 Chrome 掉线是怎么解决的？"，AI 通过
`search_memory("Chrome 掉线 解决")` 取回当时的结论与原文链接。

### 2. 本机 HTTP API（脚本/自动化）

- 语义召回：`GET /api/observability/recall?q=<一句话>&limit=10`
  返回相似度排序的消息片段（含 conversation_id，可回溯原文）。
- 结构化检索：`GET /api/memory/inspector/conversations?q=`、
  `/api/memory/inspector/memories?memory_type=structured_evidence`。
- 知识要点：`GET /api/observability/knowledge?q=&category=`。
  认证头：`X-LingJi-Token: <storage/control_api_token>`。

### 3. 灵机界面（人工浏览）

- 记忆库 · 知识要点：按分类/关键词浏览灵机提炼的结论，点开可看对话原文。
- 记忆库 · 对话原文：关键词搜索 + 语义召回面板。
- 永久记忆(确认)：已确认进长期记忆的条目（权威正文同步在 Vault）。

## RAG 是什么（大白话）

灵机把每条消息变成一个"意思向量"存进本地 Qdrant；你提问时，问题也被变成
向量，最相近的记忆被取回给 AI 参考。全过程在本机完成，不上传任何内容。
关键词搜索找不到的（换了说法的），语义搜索能找到。

## 记忆的层级

| 层级 | 在哪 | 怎么进 |
| --- | --- | --- |
| 原始对话 | 记忆层（lingji_memory.db） | 自动导入（append-only） |
| 知识要点 | distilled_knowledge + 记忆库 UI | 本机小模型自动提炼 |
| 永久记忆 | Vault 笔记 + memory_documents（confirmed） | 主人确认或自动固化 |
| 语义索引 | 本地 Qdrant | 自动向量化（可重建） |
