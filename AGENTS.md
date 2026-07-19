# 灵机 (LingJi) - 项目执行规则

## 项目与仓库
- 灵机代码仓库：`wangduoyu001/lingji`
- Obsidian 知识库：`E:\obsidian\本地知识库`
- 只允许一个 Obsidian Vault，不为不同入口建立额外 Vault
- 旧 `PEMIS/` 目录迁移期间保持可读，禁止直接删除或批量移动

## 启动与停止
- 启动：在项目根目录执行 `python run_service.py`
- 服务 PID：`storage/lingji.pid`
- 停止：优先在服务窗口按 `Ctrl+C`，或执行 `python scripts/stop_lingji.py`
- 禁止使用 `Get-Process -Name python | Stop-Process -Force`，不得误杀 ComfyUI、Ollama 或其他 Python 服务

## 单仓库目录
- `00-System/`：Home、Bases、模板、规则、命令、反馈、看板和健康状态
- `01-Inbox/`：所有入口的待处理内容
- `02-Sources/`：保留原貌的对话、网页、文档和音视频来源
- `03-Knowledge/`：已蒸馏的长期知识
- `04-Projects/`：项目资料、状态与机会卡
- `05-Operations/`：任务、决策、工作报告、错误和复盘
- `06-Entities/`：人物、机构、工具、模型和平台
- `07-Assets/`：角色、场景、提示词、工作流和媒体索引
- `08-Private/`：高隐私内容，默认禁止普通索引、命令队列和云模型读取
- `09-Archive/`：失效、完成和冷归档内容
- `Attachments/`：Obsidian附件

## Obsidian 人工管理规则
1. 文件夹只表达来源、阶段和生命周期，不承担全部分类。
2. `memory_type`、`status`、`privacy`、`importance`、`review_status` 使用属性，不使用标签代替。
3. 项目、人物、工具、来源、任务和决策使用内部链接属性互联。
4. 标签只负责跨文件夹发现，允许一级：`domain/`、`topic/`、`source/`、`signal/`、`attention/`。
5. 每条笔记建议 3—7 个标签，最多 12 个；禁止同义标签和随意增加一级标签。
6. 手动管理优先使用 `00-System/Bases/`，复杂只读查询才允许使用 Dataview。
7. 反馈写入 `00-System/Feedback/Feedback Inbox.md`，控制中心只展示，不接收重要输入。
8. 批量修改和双向建链使用 `00-System/Commands/Queue/` 中的命令笔记。
9. 命令队列只允许：`set_properties`、`add_tags`、`link_note`、`mark_status`。
10. 系统生成文件只有包含 `lingji_managed: true` 时才能自动更新；主人自己的文件默认不覆盖。

## 记忆与安全规则
1. Obsidian 单一 Vault 是人类可读的权威记忆。
2. SQLite 保存调度、处理状态和审计事件，不与 Obsidian 争夺正式知识的权威。
3. 索引、全文搜索和向量库必须可从原始资料重建。
4. 原始资料只追加，不覆盖；AI草稿不得直接覆盖正式记忆。
5. `08-Private` 默认不进入普通索引，除非主人明确临时授权。
6. 删除、覆盖、对外发布、付款、账号和私密资料操作必须人工确认。
7. AI 建议关系先标记 `review_status: needs_review`，主人确认后才视为正式关系。
8. 所有派生结论必须保存 `source_id`、`source_path` 或 `sources`。

## 增量处理规则
- 文件索引哈希与处理哈希必须分开保存。
- 每个处理器使用：`source_id + processor + processor_version + content_hash` 判断是否需要重跑。
- 调度状态保存在 `storage/lingji_state.db`，重启后不得把所有定时任务立即重跑。
- 长任务不得阻塞反馈读取、命令处理和健康检查。
- 机会卡使用稳定来源 ID，禁止按 AI 标题作为唯一文件名。

## 开发规则
- 代码保持简洁、模块化，优先扩展现有服务，不重复建第二套架构。
- Python 写文件使用 UTF-8 无 BOM，读取兼容 `utf-8-sig`。
- 正式文件写入优先使用临时文件加原子替换。
- 不得在 C 盘新增项目数据、下载、缓存或临时文件。
- 现有历史项目路径未经确认不得移动。
- 每个新增功能必须有对应测试和 Markdown 报告。

## 常用入口
- 初始化单仓库：`python scripts/init_single_vault.py`
- 创建入口内容：`core.create_inbox_item(source_type, title, content, metadata)`
- 手动扫描：`core.manual_scan()`
- 手动处理命令：`core.process_manual_commands()`
- 管理首页：`00-System/Home.md`
- 控制中心：`00-System/Dashboard/Control Center.md`
- 标签字典：`00-System/Tag-Dictionary.md`
- 属性字典：`00-System/Property-Dictionary.md`
- 关系规则：`00-System/Relationship-Rules.md`

## 测试
- 全部测试：`python -m unittest discover -s tests -v`
- 编译检查：`python -m compileall -q main.py run_service.py src tests`
- 修改索引、调度、路由、标签、关系或隐私规则后必须运行全部测试
- GitHub Actions 必须在 Python 3.11 和 3.12 通过后才能将 PR 标记为可合并

## 磁盘规则
- D盘项目目录：`D:/codex/`
- 备份目录：`D:/codex/backups/pemis`
- 日志目录：项目内 `logs/`
