# 灵机单一 Obsidian 仓库结构

## 决策

灵机只使用一个 Obsidian Vault。入口、处理阶段、内容类型和隐私范围通过文件夹与元数据区分，不再创建多个 Vault。

## 目录职责

- `00-System`：模板、规则、看板、日志和索引状态。
- `01-Inbox`：手机、浏览器、微信、ChatGPT、Codex 等入口的待处理内容。
- `02-Sources`：保留原貌的对话、网页、文档、音视频和 GitHub 来源。
- `03-Knowledge`：已蒸馏的长期知识。
- `04-Projects`：项目目标、状态和项目资料。
- `05-Operations`：任务、决策、工作报告、错误和复盘。
- `06-Entities`：人物、机构、工具、模型和平台。
- `07-Assets`：角色、场景、提示词、工作流和媒体资产索引。
- `08-Private`：高隐私内容。默认不进入普通索引，也不交给云端模型。
- `09-Archive`：失效、完成或冷归档内容。
- `Attachments`：Obsidian 嵌入附件。

## 兼容策略

现有 `PEMIS/` 目录不会被自动移动或删除。新版控制中心写入 `00-System/Dashboard/Control Center.md`，机会卡写入 `04-Projects/Money-Experiments/Opportunities/`。旧目录在迁移期间保持可读。

## 初始化

```powershell
python scripts/init_single_vault.py
```

也可以显式指定仓库：

```powershell
python scripts/init_single_vault.py --vault "E:\obsidian\本地知识库"
```

脚本只创建缺失文件夹，不移动、覆盖或删除已有笔记。

## 配置

`.env` 支持：

```text
VAULT_DIR=E:/obsidian/本地知识库
VAULT_AUTO_INIT=true
INDEX_PRIVATE=false
```

`INDEX_PRIVATE=false` 是默认值。即使 `08-Private` 位于同一个 Vault，普通索引和后续 MCP 搜索也不会返回其中内容。

## 程序入口

`PEMISCore.create_inbox_item(source_type, title, content, metadata)` 会把内容路由到对应入口文件夹，并生成带统一 ID、来源类型、状态、隐私级别和内容哈希的 Markdown 原始记录。

当前支持的入口包括：`mobile_share`、`browser`、`local_file`、`wechat`、`chatgpt`、`codex`、`github`、`video`、`audio`、`image` 和 `manual`。
