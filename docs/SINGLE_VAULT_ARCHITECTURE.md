# 灵机单一 Obsidian 仓库结构

## 决策

灵机只使用一个 Obsidian Vault。入口、处理阶段、内容类型和隐私范围通过文件夹、属性、标签和内部链接区分，不再创建多个 Vault。

## 目录职责

- `00-System`：管理首页、Bases、模板、规则、命令、反馈、看板、日志和健康状态。
- `01-Inbox`：手机、浏览器、微信、ChatGPT、Codex 等入口的待处理内容。
- `02-Sources`：保留原貌的对话、网页、文档、音视频和 GitHub 来源。
- `03-Knowledge`：已蒸馏的长期知识。
- `04-Projects`：项目目标、状态、资料和机会卡。
- `05-Operations`：任务、决策、工作报告、错误和复盘。
- `06-Entities`：人物、机构、工具、模型和平台。
- `07-Assets`：角色、场景、提示词、工作流和媒体资产索引。
- `08-Private`：高隐私内容，默认不进入普通索引、命令队列和云模型。
- `09-Archive`：失效、完成或冷归档内容。
- `Attachments`：Obsidian 嵌入附件。

## 四层组织方式

1. 文件夹：来源与生命周期。
2. 属性：类型、状态、项目、重要性、审核和隐私。
3. 内部链接：项目、来源、任务、决策、人物和工具之间的正式关系。
4. 标签：跨文件夹发现，不承担项目、状态和实体关系。

详细规则见 `docs/OBSIDIAN_INTERACTION_AND_METADATA.md`。

## 人工管理入口

启动后自动创建：

```text
00-System/Home.md
00-System/Bases/*.base
00-System/Templates/*.md
00-System/Tag-Dictionary.md
00-System/Property-Dictionary.md
00-System/Relationship-Rules.md
00-System/Manual-Management-Guide.md
00-System/Feedback/Feedback Inbox.md
```

主人从 `00-System/Home.md` 进入 Inbox、项目、任务、决策、知识、来源、实体、命令和记忆健康页面。

控制中心是只读展示页，不再承载反馈输入，避免自动刷新覆盖人工内容。

## 命令队列

批量修改和双向建链使用：

```text
00-System/Commands/Queue
```

允许：

```text
set_properties
add_tags
link_note
mark_status
```

不允许删除、发布、付款、账号操作、任意脚本或访问 `08-Private`。

## SQLite 状态库

运行状态写入：

```text
storage/lingji_state.db
```

保存：

- 持久化调度状态
- 每种处理器独立的内容哈希
- 命令结果
- 服务、任务和处理事件

SQLite 不保存正式知识正文，正式记忆仍以 Obsidian 为准。

## 兼容策略

现有 `PEMIS/` 目录不会被自动移动或删除。新版控制中心写入 `00-System/Dashboard/Control Center.md`，机会卡写入 `04-Projects/Money-Experiments/Opportunities/`。旧目录在迁移期间保持可读。

## 初始化

```powershell
python scripts/init_single_vault.py
```

显式指定仓库：

```powershell
python scripts/init_single_vault.py --vault "E:\obsidian\本地知识库"
```

脚本只创建缺失文件夹，不移动、覆盖或删除已有笔记。系统管理文件只有包含 `lingji_managed: true` 时才允许自动更新，主人自己的同名文件默认保留。

## 配置

```text
VAULT_DIR=E:/obsidian/本地知识库
VAULT_AUTO_INIT=true
OBSIDIAN_INTERACTION_AUTO_INIT=true
INDEX_PRIVATE=false
STATE_DB_NAME=lingji_state.db
SCHEDULER_POLL_SECONDS=60
SCHEDULER_WORKERS=2
MANUAL_COMMAND_INTERVAL_MINUTES=2
```

`INDEX_PRIVATE=false` 是默认值。即使 `08-Private` 位于同一个 Vault，普通索引、命令队列和后续 MCP 搜索也不会返回其中内容。

## 程序入口

`PEMISCore.create_inbox_item(source_type, title, content, metadata)` 会把内容路由到对应入口文件夹，并生成带统一 ID、来源类型、状态、隐私级别和内容哈希的 Markdown 原始记录。

`PEMISCore.process_manual_commands()` 处理安全命令。

`PEMISCore.manual_scan()` 只处理内容哈希变化且对应处理器尚未成功完成的来源。

当前入口包括：`mobile_share`、`browser`、`local_file`、`wechat`、`chatgpt`、`codex`、`github`、`video`、`audio`、`image` 和 `manual`。
