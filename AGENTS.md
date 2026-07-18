# 灵机 (LingJi) - PEMIS 项目配置

## 项目路径
- 灵机项目根目录: C:\Users\Administrator\Documents\New project-ai
- 启动命令: cd "C:\Users\Administrator\Documents\New project-ai" && python run_service.py
- 停止命令: Get-Process -Name "python" | Stop-Process -Force

## Git 仓库
- 灵机代码: https://github.com/wangduoyu001/lingji.git (origin)
- 知识库: https://github.com/wangduoyu001/obsidian.git (origin-obsidian)

## 本地知识库
- 路径: E:\obsidian\本地知识库
- 只允许一个 Obsidian Vault，不得为不同入口创建额外 Vault
- Git拉取: cd "E:\obsidian\本地知识库" && git pull
- 新目录结构由 `src/memory/vault_layout.py` 统一定义
- 旧 `PEMIS/` 目录迁移期间保持可读，禁止直接删除或批量移动

## 单仓库目录规则
- `00-System/`: 模板、规则、控制中心、日志和索引状态
- `01-Inbox/`: 手机、浏览器、微信、ChatGPT、Codex 等入口
- `02-Sources/`: 原始对话、网页、文档和音视频资料
- `03-Knowledge/`: 已蒸馏的长期知识
- `04-Projects/`: 项目资料与机会卡
- `05-Operations/`: 任务、决策、工作报告和错误
- `06-Entities/`: 人物、机构、工具、模型和平台
- `07-Assets/`: 角色、场景、提示词、工作流和媒体索引
- `08-Private/`: 高隐私内容，默认禁止普通索引和云端模型读取
- `09-Archive/`: 失效、完成和冷归档内容
- `Attachments/`: Obsidian附件

## API配置
- DeepSeek API Key 在 .env 文件中
- 主模型: deepseek-chat (通过 DeepSeek API)
- 备用模型: qwen3:8b-q4_K_M (本地Ollama)
- Embedding模型: nomic-embed-text (本地Ollama，当前未启用)

## 核心规则
1. Obsidian 单一 Vault 是人类可读的权威记忆，禁止开发独立 WebUI/Electron 取代它
2. 所有查询不依赖固定文件路径，只依赖 ID、metadata 和索引中的相对路径
3. 交互体验 > Agent能力 > 自动化能力
4. 用户在Obsidian内完成核心操作不超过3次点击
5. Capture First：新文件先进入 `01-Inbox`，自动分类/标签/总结，不直接写入正式知识
6. AI必须主动工作：自动分类、打标签、关联、总结
7. 灵机定位：AI编导 / AI运营 / AI研究员 / AI商业策划 / AI第二大脑
8. 向量数据库(Qdrant)保留代码但默认不启动
9. 原始资料只追加，不覆盖；AI草稿不得直接覆盖正式记忆
10. `08-Private` 默认不进入普通索引，除非主人明确授权并修改配置
11. 删除、覆盖、发布、付款和账号操作必须人工确认

## 文件驱动执行
- PowerShell 不支持 && 和 << heredoc
- 写文件用 scripts/_exec.py: python scripts/_exec.py <target_file>
- 或通过 Node.js MCP 的 fs.writeFileSync 写文件
- 所有Python文件必须用 encoding="utf-8" (无BOM)
- 读文件用 encoding="utf-8-sig" 兼容旧BOM文件
- 文件写入优先采用临时文件 + 原子替换，避免中途损坏

## 系统架构
- L1 Source Layer: 单一 Obsidian Vault + 原始文件（权威资料）
- L2 State Layer: SQLite/JSON 状态、任务、同步与审计记录
- L3 Index Layer: FTS/metadata/vector，可从原始资料重建
- L4 Logic Layer: Memory Gateway + Router + Safety Guard + Scheduler
- L5 Ops Layer: backup + journal + integrity + metrics

## 调度任务
- read_feedback: 每10分钟读取Control Center反馈
- daily_capture: 每24小时自动扫描新文件+打标签
- distill/distillation: 每24小时
- integrity: 每24小时
- full_check: 每24小时更新看板

## 交互接口
- 初始化单仓库目录: `python scripts/init_single_vault.py`
- 创建入口内容: `core.create_inbox_item(source_type, title, content, metadata)`
- 手动扫描新内容: `core.manual_scan()` 或通过我触发
- 反馈写在: `00-System/Dashboard/Control Center.md` 底部的反馈区
- 控制中心: `00-System/Dashboard/Control Center.md`

## 测试
- 单仓库结构测试: `python -m unittest tests.test_vault_layout -v`
- 索引测试: `python -m unittest tests.test_single_vault_index -v`
- 全部测试: `python -m unittest discover -s tests -v`
- 修改索引、路由或隐私规则后必须运行上述测试

## 磁盘规则
- 禁止在C盘创建任何新的项目数据、下载、缓存或临时文件
- 现有历史项目路径不得未经确认直接移动
- 所有下载、缓存、临时文件必须放在D盘
- D盘项目目录: D:/codex/
- 备份目录: D:/codex/backups/pemis
- 日志目录: logs/ (项目内)
