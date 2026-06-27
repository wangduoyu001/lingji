# 灵机 (LingJi) - PEMIS 项目配置

## 项目路径
- 灵机项目根目录: C:\Users\Administrator\Documents\New project-ai
- 启动命令: cd "C:\Users\Administrator\Documents\New project-ai" && python run_service.py
- 停止命令: Get-Process -Name "python" | Stop-Process -Force

## Git 仓库
- 灵机代码: https://github.com/wangduoyu001/lingji.git (origin)
- 知识库: https://github.com/wangduoyu001/obsidian.git (origin-obsidian)

## 本地知识库
- 路径: E:\obsidian\本地知识库 (唯一知识库，不要创建其他文件夹)
- Git拉取: cd "E:\obsidian\本地知识库" && git pull
- PEMIS目录: PEMIS/dashboard/ (Control Center.md), PEMIS/opportunities/

## API配置
- DeepSeek API Key 在 .env 文件中
- 主模型: deepseek-chat (通过 DeepSeek API)
- 备用模型: qwen3:8b-q4_K_M (本地Ollama)
- Embedding模型: nomic-embed-text (本地Ollama，当前未启用)

## 核心规则
1. Obsidian 是唯一 Source of Truth，禁止开发WebUI/Electron
2. 所有查询不依赖文件路径，只依赖metadata
3. 交互体验 > Agent能力 > 自动化能力
4. 用户在Obsidian内完成核心操作不超过3次点击
5. Capture First：新文件先自动分类/标签/总结，不直接分析赚钱机会
6. AI必须主动工作：自动分类、打标签、关联、总结
7. 灵机定位：AI编导 / AI运营 / AI研究员 / AI商业策划 / AI第二大脑
8. 向量数据库(Qdrant)保留代码但默认不启动

## 文件驱动执行
- PowerShell 不支持 && 和 << heredoc
- 写文件用 scripts/_exec.py: python scripts/_exec.py <target_file>
- 或通过 Node.js MCP 的 fs.writeFileSync 写文件
- 所有Python文件必须用 encoding="utf-8" (无BOM)
- 读文件用 encoding="utf-8-sig" 兼容旧BOM文件

## 系统架构 (4层)
- L1 Data Layer: Obsidian Vault (不可变source of truth)
- L2 Index Layer: pemis_index.json (可重建)
- L3 Logic Layer: Router + Safety Guard + Scheduler (轻量化)
- L4 Ops Layer: backup + journal + integrity + metrics

## 调度任务
- read_feedback: 每10分钟读取Control Center反馈
- daily_capture: 每24小时自动扫描新文件+打标签
- distill/distillation: 每24小时
- integrity: 每24小时
- full_check: 每24小时更新看板

## 交互接口
- 手动扫描新内容: core.manual_scan() 或通过我触发
- 反馈写在: PEMIS/dashboard/Control Center.md 底部的反馈区
- 控制中心: PEMIS/dashboard/Control Center.md (极简版，一屏看完)
