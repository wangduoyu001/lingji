# 灵机 Obsidian 交互、属性、标签与关系设计

## 1. 定位

Obsidian 不是灵机的被动文件展示器，而是主人直接管理记忆、项目、任务、决策和关系的主界面。

系统采用：

- Obsidian：人类可读、可编辑的权威记忆
- SQLite：调度、处理状态、命令和审计事件
- JSON/FTS/Vector：可重建索引
- Memory Gateway/MCP：AI 访问入口

## 2. 同类项目研究结论

### Obsidian Bases

适合作为灵机人工管理的默认入口：

- 原生读取 Markdown 属性
- 支持表格、列表、卡片、筛选、分组、排序
- 可直接新建和修改笔记属性
- Base 文件本身仍保存在 Vault 中

结论：核心管理页面使用 Bases，不把 Dataview 作为必需依赖。

### Obsidian Copilot

值得借鉴：

- Vault QA 与项目上下文
- 项目和记忆继续保存为 Markdown
- 通过文件、标签和链接选择上下文

结论：灵机的 Context Pack 从明确项目、来源和实体关系生成，不把整个 Vault 塞给模型。

### Smart Connections

值得借鉴：

- 本地嵌入
- 文件变化后增量更新
- 排除隐私目录
- 相似内容只用于发现，不冒充正式关系

结论：向量相似度只能生成 `related` 建议，并标记 `needs_review`。

### Khoj

值得借鉴：

- 自托管和本地优先
- 自然语言检索
- 增量索引
- Obsidian 与多来源统一查询

结论：灵机搜索必须融合全文、元数据和向量，不只依赖向量库。

### Local REST API / MCP

值得借鉴：

- 有认证的受控接口
- 针对属性、标题、段落和块进行局部修改
- 不要求 AI 读取并重写整份文件

结论：灵机写入工具采用受控命令，不开放任意脚本、任意路径覆盖和私密目录读取。

### QuickAdd

值得借鉴：

- 模板
- Capture
- Macro
- 快速创建不同类型笔记

结论：第一版先使用原生模板和 Base 新建；后续可选 QuickAdd 优化入口，但核心功能不得依赖插件才能恢复。

### Omnisearch

值得借鉴：

- BM25 全文检索
- PDF 与 OCR 搜索
- 搜索结果排序

结论：灵机自己的搜索服务应实现 FTS5/BM25，Omnisearch 可作为 Obsidian 内补充，而不是系统唯一索引。

## 3. 四层组织模型

### 3.1 文件夹：表示位置和生命周期

文件夹只回答：内容从哪里来、目前处于什么阶段、最终属于哪类长期区域。

例如：

```text
01-Inbox/ChatGPT
02-Sources/Conversations/ChatGPT
03-Knowledge/AI
04-Projects/LingJi
05-Operations/Decisions
```

禁止仅靠文件夹表达项目、状态、人物和主题，否则同一笔记只能被迫选择一个身份。

### 3.2 属性：表示结构化状态

核心属性：

```yaml
id:
title:
aliases:
memory_type:
status:
project:
privacy:
importance:
confidence:
review_status:
created_at:
updated_at:
```

关系属性：

```yaml
people:
organizations:
tools:
models:
sources:
tasks:
decisions:
related:
related_ids:
```

### 3.3 内部链接：表示正式关系

使用内部链接表达：

- 一条知识属于哪个项目
- 一项决策来自哪些来源
- 一个任务依赖哪些决定
- 某个人、工具和模型参与了哪些项目

示例：

```yaml
project:
  - "[[04-Projects/LingJi/LingJi]]"
sources:
  - "[[02-Sources/Conversations/ChatGPT/某次对话]]"
tools:
  - "[[06-Entities/Tools/Obsidian]]"
related:
  - "[[03-Knowledge/AI/本地优先架构]]"
```

链接必须有业务含义。为了让图谱更密而乱连，只会得到一团很努力的面条。

### 3.4 标签：表示跨目录发现

允许的一级标签：

```text
domain/
topic/
source/
signal/
attention/
```

示例：

```yaml
tags:
  - domain/ai
  - topic/obsidian
  - source/chatgpt
  - signal/decision
  - attention/review
```

标签不表达：

- 项目
- 状态
- 类型
- 隐私
- 人物或工具

这些内容由属性和链接表达。

每条笔记建议 3—7 个标签，最多 12 个。新增一级标签必须修改标签字典。

## 4. 人工管理入口

系统自动生成以下 Base：

```text
00-System/Bases/Inbox.base
00-System/Bases/Projects.base
00-System/Bases/Tasks.base
00-System/Bases/Decisions.base
00-System/Bases/Knowledge.base
00-System/Bases/Sources.base
00-System/Bases/Entities.base
00-System/Bases/Commands.base
00-System/Bases/Memory Health.base
```

主人从 `00-System/Home.md` 进入管理系统。

日常操作：

1. 在 Inbox Base 查看新内容。
2. 修改项目、重要性、审核状态和标签。
3. 有价值的来源移动到 Sources。
4. 蒸馏结论进入 Knowledge。
5. 项目、任务、决策和实体使用对应模板创建。
6. 批量修改或双向链接使用命令模板。

## 5. 命令队列

命令目录：

```text
00-System/Commands/Queue
```

允许命令：

```text
set_properties
add_tags
link_note
mark_status
```

每条命令经历：

```text
queued → running → done
                 ↘ failed
```

命令会记录开始、结束、结果和错误，并写入 SQLite 事件日志。

禁止命令：

- 删除笔记
- 任意脚本
- 对外发布
- 付款
- 账号操作
- 未授权读取或修改 `08-Private`

## 6. AI 与人工协作

### AI 可以自动完成

- 为 Inbox 内容建议类型和标签
- 提取人物、工具、项目和来源
- 生成 `related` 建议
- 创建知识草稿
- 发现缺来源、断链、重复和冲突
- 生成 Context Pack

### 必须由主人确认

- 正式决策
- 覆盖人工内容
- 将 AI 关系升级为正式关系
- 删除和归档重要内容
- 对外发布
- 私密资料授权

## 7. 插件策略

### 默认依赖

只依赖 Obsidian 核心功能：

- Properties
- Bases
- Internal Links
- Backlinks
- Search
- Templates

### 可选增强

- QuickAdd：快速采集和宏
- Omnisearch：Obsidian 内全文搜索补充
- Dataview：复杂只读查询
- Local REST API：本地受控集成，必须启用认证

### 不作为系统核心

- 只能靠插件私有数据库恢复的功能
- 会无审计批量改写笔记的插件
- 无法限制私密目录访问的 AI 插件
- 许可证不适合直接复制或嵌入的代码

## 8. 验收标准

1. 主人从 Home 三次点击内到达 Inbox、项目或任务。
2. Base 中可以修改常用属性。
3. 标签不出现同义词泛滥。
4. 项目、来源、任务、决定和实体可以互相跳转。
5. AI 能读取与主人看到相同的关系属性。
6. 控制中心刷新不会覆盖反馈和命令。
7. 私密目录默认不进入索引和命令系统。
8. 文件移动后稳定 ID 保持不变。
9. 断链、缺来源和孤立笔记能被健康检查发现。
10. 不安装社区插件时，核心资料仍可打开、搜索和维护。
