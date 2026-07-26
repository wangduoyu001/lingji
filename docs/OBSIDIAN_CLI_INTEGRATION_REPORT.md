# Obsidian CLI 集成报告

## 1. 环境摘要

| 项目 | 值 |
|------|-----|
| 系统 | Windows |
| Obsidian 版本 | 1.12.7 (installer 1.12.7) |
| CLI 路径 | D:\Program Files (x86)\Obsidian\Obsidian.com |
| Vault 名称 | 本地知识库 |
| Vault 路径 | E:\obsidian\本地知识库 |
| Vault 笔记总数 | 326 |
| 项目根目录 | D:\codex\lingji-second-brain |
| Git 分支 | feature/second-brain-memory |
| CLI 是否可用 | 是 (obsidian 命令通过 PATH 可用，同时有默认探测路径) |
| CLI 设置要求 | 需在 Obsidian 设置 -> 编辑器 -> 高级 -> 启用命令行接口 |

## 2. 测试笔记

- **路径**: 系统测试/Obsidian-CLI/Codex-CLI-冒烟测试.md
- **状态**: 已创建并验证 (481 字符)
- **包含**: 测试时间、Obsidian 版本、Vault 信息、CLI 状态、Git 分支、测试结论

## 3. 修改文件清单

| 文件 | 操作 | 说明 |
|------|------|------|
| second_brain/obsidian_cli.py | 新增 | Obsidian CLI 统一操作层 (ObsidianCli 类) |
| tests/test_obsidian_cli.py | 新增 | 20 个测试用例 |
| docs/OBSIDIAN_CLI_AUDIT.md | 新增 | CLI 审计报告 |
| .env.second-brain | 修改 | 添加 5 个 OBSIDIAN_CLI_* 环境变量 |
| AGENTS.md | 修改 | 追加 14 条 Obsidian CLI 安全规则 |

## 4. A 类: 改用 CLI 的操作

| 操作 | 方法 | 说明 |
|------|------|------|
| 创建笔记 | cli.create() | 写入后自动验证 |
| 追加内容 | cli.append() | 写入后自动验证 |
| 搜索笔记 | cli.search() | 中文搜索支持 |
| 读取笔记 | cli.read() | 不存在时抛出异常 |
| 查询标签 | cli.list_tags() | 整个 Vault 或单文件 |
| 查询任务 | cli.list_tasks() | 支持 todo/done 过滤 |
| Daily Note 读写 | cli.read_daily() / append_daily() | 每日笔记操作 |
| 文件列表 | cli.list_files() / file_count() | 按文件夹/扩展名过滤 |
| Vault 信息 | cli.get_vault_info() | 名称 + 路径 |
| 健康检查 | cli.health() | 完整性验证 |

## 5. B 类: 保留直接读取 Markdown

| 场景 | 原因 |
|------|------|
| 向量索引 | 全量扫描场景，直接读文件更快 |
| Git 差异检测 | 直接读 Git 对象 |
| 备份 | 文件级操作 |
| 批量只读统计 | 数量大，CLI 不是数据库 |
| 离线分析 | 不需要实时 CLI |

## 6. C 类: 保留 Python 后端

| 功能 | 位置 |
|------|------|
| AI 模型调用 | second_brain/ (distillation/context) |
| 数据库 (SQLite) | data/ |
| 定时任务 | AsyncIOScheduler |
| API 服务 | FastAPI (8765 端口) |
| 系统监控 | health/service_monitor |
| 队列处理 | second_brain/scheduler |

## 7. 测试结果

tests/test_obsidian_cli.py - 20 passed in 1.12s

覆盖场景:
- CLI 不存在时抛出 ObsidianCliNotFound
- CLI 超时抛出 ObsidianCliTimeout
- CLI 返回非零码抛出 ObsidianCliErrorResult
- 异常继承链 (Error / NotFound / Timeout / ErrorResult)
- 中文文件名和正文 (搜索/创建/读取)
- 路径包含空格 (Control Center.md)
- 搜索无结果返回空列表
- 读取不存在的笔记抛出异常
- dry-run 模式不产生真实写入
- 参数注入防护 (路径遍历攻击检测)
- 文件名安全化 (Windows 非法字符替换)
- 真实 CLI 创建笔记并重新读取验证

已有项目测试:
- tests/test_second_brain.py - 6/7 passed (1 个预存失败: 工作树不含原始 start_lingji.py)

## 8. 已知问题和修复

| 问题 | 原因 | 修复 |
|------|------|------|
| shlex.quote(中文) 产生多余引号 | Windows 下 shlex 对非 ASCII 字符加单引号 | 移除所有 shlex.quote() 调用，subprocess.run(list) 不需要 shell 引用 |
| CLI 输出使用 UTF-8 但 text=True 用 cp936 解码 | Python 默认编码在中文 Windows 为 cp936 | 改用 text=False + 手动 UTF-8 解码 |
| Obsidian CLI 路径含空格和中文时参数传递 | 需用 list 模式避免 shell 解释 | 全程使用 list 模式 + CREATE_NO_WINDOW |
| GBK 子进程线程警告 | Python 3.11 子进程 readerthread 默认用 GBK | 设置 PYTHONUTF8=1 环境变量 |

## 9. 架构图

    ObsidianCli 类 (second_brain/obsidian_cli.py)
    |
    +-- _run(args) -> (rc, stdout, stderr)
    |   +-- vault=xxx 自动注入
    |   +-- subprocess.run(list, text=False)
    |   +-- UTF-8 手动解码
    |   +-- 超时控制 + dry-run
    |   +-- 操作日志记录
    |
    +-- 公开方法
        +-- get_version / get_help / get_vault_info
        +-- search / read / create / append
        +-- list_tags / list_tasks / list_files
        +-- read_daily / append_daily / get_daily_path
        +-- health / sanitize_filename / validate_path

## 10. 下一步 MCP 接入建议

1. 将 second_brain/obsidian_cli.py 的接口暴露为 FastAPI 路由
2. 通过标准 MCP 协议封装以下操作:
   - obsidian_search - 搜索笔记
   - obsidian_read - 读取笔记
   - obsidian_create - 创建笔记
   - obsidian_append - 追加内容
   - obsidian_tags - 查询标签
   - obsidian_tasks - 查询任务
3. 保持 localhost 部署，不搭建公网服务
4. 遵循本项目隔离规则: MCP 不应修改 C:\\...\\New project-ai 下的文件
