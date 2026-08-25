# 灵机第二阶段：Obsidian 人工管理与关系层开发报告

> 文档角色：历史实施/验证快照，不是当前进度或当前架构权威。
> 当前状态看 `docs/PROJECT_STATUS.md`；当前代码入口看 `docs/MODULES/CODE_MAP.md`。

## 状态

- 分支：`feature/single-vault-memory-foundation`
- PR：Draft PR #1
- 阶段：Obsidian 手动管理、持久化状态与关系索引已完成第一版
- 合并状态：暂不自动合并，必须先在主人电脑与尚未推送的 `second_brain/lingji_tools.py` 集成

## 本阶段目标

1. 让 Obsidian 不只是 AI 写入目标，而是主人可直接管理的主界面。
2. 建立文件夹、属性、标签、链接和向量之间的明确边界。
3. 修复调度重启、处理哈希、反馈覆盖和机会卡覆盖等逻辑问题。
4. 为后续 Memory Gateway、MCP 和全文搜索建立稳定状态层。

## 已完成

### 1. Obsidian 人工管理首页

新增自动生成：

- `00-System/Home.md`
- Inbox Base
- Projects Base
- Tasks Base
- Decisions Base
- Knowledge Base
- Sources Base
- Entities Base
- Commands Base
- Memory Health Base

Base 支持筛选、分组、排序、直接修改属性和按模板新建笔记。

### 2. 模板体系

新增：

- 通用笔记模板
- 项目模板
- 任务模板
- 决策模板
- 来源模板
- 实体模板
- 命令模板

模板统一使用 YAML 属性，并区分正式状态、审核状态、隐私和关系字段。

### 3. 标签和属性规范

标签只允许：

```text
domain/
topic/
source/
signal/
attention/
```

每条笔记最多 12 个标签。项目、状态、类型、隐私、人物和工具不再用标签冒充，改用属性和内部链接。

### 4. 类型化关系

索引已支持：

```text
project
people
organizations
tools
models
sources
tasks
decisions
related
related_ids
```

主人和 AI 读取相同的关系属性，不再出现 Obsidian 中有链接、AI 索引里却没有的两套世界观。

### 5. 安全命令队列

命令目录：

```text
00-System/Commands/Queue
```

支持：

- 修改非保护属性
- 添加标签
- 建立双向关系
- 修改状态

不支持：

- 删除
- 任意脚本
- 对外发布
- 付款
- 账号操作
- 未授权私密内容

命令状态、结果和错误写入 Markdown 与 SQLite 事件日志。

### 6. 反馈防覆盖

反馈从控制中心拆出：

```text
00-System/Feedback/Feedback Inbox.md
```

控制中心改为只读展示页。系统刷新不会覆盖主人输入。

### 7. SQLite 状态库

新增：

```text
storage/lingji_state.db
```

保存：

- 调度任务状态
- 下次执行时间
- 处理器独立哈希
- 命令事件
- 服务事件
- 错误与处理结果

### 8. 调度器重构

修复：

- 服务重启后全部任务立即运行
- `last_run` 仅存内存
- 长任务阻塞其他任务
- 任务失败仍显示成功
- `min_mode` 不生效

新调度器使用 SQLite 和线程池，任务状态可跨重启恢复。

### 9. 独立处理哈希

每个处理器按以下组合判断是否需要重跑：

```text
source_id + processor + processor_version + content_hash
```

文件进入索引后，不会再错误地被判断为“已经完成摘要或机会分析”。

### 10. 机会卡可追溯

机会卡改为：

- 稳定来源 ID
- 稳定文件名
- 同名机会不覆盖
- 保存来源路径和内容哈希
- 保存模型与提示词版本
- 默认 `verification_status: unverified`
- 默认 `review_status: needs_review`

### 11. 记忆健康检查

新增检测：

- 缺少来源
- 断开的内部链接
- 私密内容误入普通索引
- 未知状态
- 孤立笔记
- 重复内容哈希

### 12. 服务启动与停止

修复项目根目录识别和日志目录创建。

新增 PID 文件：

```text
storage/lingji.pid
```

新增：

```text
python scripts/stop_lingji.py
```

禁止通过杀死全部 Python 进程停止灵机。

## 测试与 CI

新增测试覆盖：

- 单仓库目录与入口路由
- 私密目录排除
- YAML 属性读写
- Base 文件生成与保护用户文件
- 标签规范与数量限制
- 双向关系
- 安全命令白名单
- 持久化调度
- 启动时任务策略
- 独立处理哈希
- 追加式事件日志
- 机会卡稳定 ID 与同名防覆盖
- 类型化关系索引
- 反馈防覆盖与防重复
- 缺来源、断链和私密泄漏检测

GitHub Actions：

- Python 3.11
- Python 3.12
- 依赖安装
- Python 编译检查
- 全部单元测试

## 同类项目研究吸收

借鉴：

- Obsidian Bases：原生人工管理
- Obsidian Copilot：项目上下文和 Markdown 记忆
- Smart Connections：本地嵌入、增量处理和排除目录
- Khoj：本地优先和自然语言检索
- Local REST API / MCP：受控局部写入
- QuickAdd：模板、Capture 和 Macro
- Omnisearch：BM25、PDF 和 OCR 搜索

不直接复制或强依赖这些项目。灵机保持自己的统一 ID、权限、状态和可恢复架构。

## 尚未完成

1. SQLite FTS5 全文搜索。
2. PDF、Word、Excel、PPT 解析与页码定位。
3. Context Pack 和 Memory Gateway API。
4. 与本机未推送 `lingji_tools.py` 合并。
5. 手机分享和浏览器 Capture。
6. Obsidian 内 QuickAdd 可选快捷入口。
7. 标签同义词自动检测和合并建议。
8. 关系建议审核页面。
9. 本机 Windows 服务级启动、重启和恢复测试。
10. 现有真实 Vault 的迁移预览与回滚测试。

## 合并前必做

1. 主人电脑拉取当前分支。
2. 安装更新后的依赖。
3. 在测试 Vault 执行初始化。
4. 检查 Base 是否在当前 Obsidian 版本正确显示。
5. 与本机 `second_brain` 代码集成。
6. 运行全部测试和一次服务启动冒烟测试。
7. 创建真实 Vault 快照后再迁移。

## 结论

本阶段已经把灵机从“AI 自动写一堆 Markdown”推进到“主人和 AI 共用一套结构、关系和操作规则”。

当前适合版本：

```text
LingJi Personal Memory OS v0.2-alpha
```

仍不应标记为正式 v1.0。全文搜索、真实 Vault 迁移和本机集成完成之前，任何“生产可用”声明都属于营销部门的文学创作。
