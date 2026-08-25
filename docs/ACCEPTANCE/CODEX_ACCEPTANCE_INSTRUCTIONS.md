# Codex 真机全面验收指令

> 本文件是 Codex 拉取灵机仓库后直接执行的统一指令。
>
> 每次验收必须以当前分支的 `CHANGE_ACCEPTANCE_LOG.md` 最新条目为增量要求，以本文件为基础要求。聊天中的旧指令一律失效。

## 0. 任务性质

这是独立验收，不是开发。

禁止：

- 修改产品代码来让验收通过；
- 修改、删除或弱化测试；
- 更换被测 Commit 或 Artifact；
- 把未执行写成 PASS；
- 把“检测到”写成“已连接”；
- 把配置存在写成真实调用通过；
- 泄露 Token、Authorization、API Key、私人聊天、数据库正文或完整个人路径；
- 未经主人确认合并产品 PR。

发现失败时保存证据并继续执行不受影响的只读验收。最终给出 `PASS / FAIL / BLOCKED`。

## 1. 必须先解析的身份

从当前 PR、分支、构建元数据和 `CHANGE_ACCEPTANCE_LOG.md` 获取：

```text
repository
pull_request
product_commit
base_commit
artifact_name
artifact_id
installer_name
expected_hashes
required_ci
report_branch
report_path
```

必须把产品 Commit、Artifact、安装器和 CI 对齐到同一代码树。任何身份不一致立即判定：

```text
BLOCKED_WRONG_IDENTITY
```

不得拿旧 Artifact 验收新 Head，也不得为补报告移动产品 Head。

## 2. 读取顺序

只读取必要上下文：

```text
AGENTS.md
docs/PROJECT_STATUS.md 相关章节
docs/MODULES/CODE_MAP.md 相关模块
docs/ACCEPTANCE/README.md
docs/ACCEPTANCE/CODEX_ACCEPTANCE_INSTRUCTIONS.md
docs/ACCEPTANCE/CHANGE_ACCEPTANCE_LOG.md 最新相关条目
docs/ACCEPTANCE/REPORT_TEMPLATE.md
直接受影响代码和测试
相关 GitHub Workflow
```

历史测试报告只用于核对历史承诺和回归项。

## 3. 干净环境和磁盘规则

### 3.1 创建单一临时目录

使用非系统盘：

```text
D:\codex\LingJiAcceptance\<pr-or-task>-<short-commit>
```

如果目录已存在，确认不含主人正式数据后整体删除重建。

只创建本轮需要的：

```text
repo
artifact
logs
evidence-private
evidence-public
fixtures
checkpoint
temp-config-backup
report
```

### 3.2 清理旧进程

优先正常退出 LingJi，等待退出。

只结束确认属于 LingJi 的残留进程。禁止结束全部 Python、Node、Codex 或 Claude 进程。

确认：

```text
没有 LingJi Desktop 残留
没有 lingji-core 残留
没有孤儿 MCP
8766 已释放
8767 已释放
```

### 3.3 覆盖安装

默认直接覆盖安装，不卸载，不删除用户数据。

禁止删除：

```text
Production DataRoot
主人已有 Acceptance 数据
Obsidian Vault
正式记忆
用户自己的 AI 客户端配置
```

### 3.4 临时备份

连接器回滚测试需要时，只允许保存一个临时配置副本：

```text
temp-config-backup
```

回滚验证完成后立即删除。报告只记录前后 SHA256，不上传配置正文。

### 3.5 验收结束清理

报告提交后删除：

```text
artifact
fixtures
checkpoint
temp-config-backup
普通成功日志
普通成功截图
临时解压内容
```

保留：

```text
最终报告
脱敏公开证据
哈希清单
报告 Commit
主人要求保留的失败证据
```

## 4. 仓库、Commit、CI 和 Artifact

必须核验：

- 当前仓库和 PR；
- 当前产品 Commit；
- 工作区无无法解释的修改；
- 精确产品 Commit 上的必需 CI；
- Artifact 名称和 ID；
- ZIP、安装器、Desktop EXE、Sidecar EXE、Manifest 和 `SHA256SUMS.txt`；
- 构建元数据中的 Commit、版本、目标、安装格式和安全合同。

任何哈希不一致：

```text
FAIL_ARTIFACT_INTEGRITY
```

## 5. 自动测试

先运行局部验证，再按变更范围运行最终门禁：

```powershell
.\scripts\validate.ps1 -Mode focused -Area <area>
.\scripts\validate.ps1 -Mode full
.\scripts\validate.ps1 -Mode release
```

规则：

- `release` 已包含 `full` 时，不重复运行；
- 使用仓库统一入口，不创建第二套命令；
- 成功只读取 summary；
- 失败读取失败日志尾部；
- 不保留多轮重复成功日志；
- 任一强制测试失败，最终不得 PASS。

必须额外执行 `CHANGE_ACCEPTANCE_LOG.md` 当前条目声明的测试。

## 6. 安装和升级

覆盖安装必须确认：

- 安装成功；
- 版本和 Commit 正确；
- 旧主人数据仍在；
- DataRoot 未迁回 C 盘；
- Workspace 保持；
- Vault 保持；
- 没有 PowerShell、CMD 或黑色控制台窗口；
- 安装后只有一套受管 Runtime。

窗口行为必须由主人肉眼确认。

## 7. Runtime、进程和端口

必须确认：

```text
connection_state=connected
control_service=connected
runtime_state=healthy
runtime_healthy=true
runtime_managed=true
runtime_binary_available=true
```

端口：

```text
8766 只监听 127.0.0.1
8767 只监听 127.0.0.1（启用 MCP HTTP 时）
8765 只允许兼容用途
```

进程：

```text
一个 Desktop
一个受管 Core
一个预期的受管 MCP 子进程
无重复 Core
无孤儿 MCP
```

不得把验收工具自身启动的 PowerShell 当成产品黑窗。必须检查进程祖先链和主人观察。

## 8. Workspace、DataRoot 和 Vault

必须确认：

- UI 明确显示 Production、Acceptance 或 unknown；
- unknown 不伪造成 production；
- Production 与 Acceptance 物理隔离；
- DataRoot、Vault、数据库、Qdrant、日志、设置和 Token 不串用；
- 不静默向 C 盘写运行数据；
- 测试内容只进入 Acceptance；
- Production 只允许只读验证，除非主人明确批准写入。

## 9. Desktop UI 通用验收

所有新增或受影响页面必须：

- 使用真实发布版启动；
- 遍历所有可见控件；
- 每个按钮、选择器、刷新、复制、导入、回滚和跳转都有真实效果；
- 不存在死按钮、假成功、占位页或纯外观空壳；
- loading、empty、error、degraded、unknown 和 success 状态真实；
- 未知值不显示为 0、healthy、connected 或 completed；
- 长任务显示阶段、进度、失败、耗时和当前活动；
- 窄窗口和常用分辨率可操作；
- 错误信息可理解并指向下一步。

主人必须确认：

```text
第一次打开是否知道下一步
关键页面是否看得懂
是否出现黑窗
是否存在无法点击或无法理解的操作
```

## 10. 记忆和永久知识边界

必须验证：

```text
原始输入
→ 可追溯原文
→ 提取和去重
→ 候选记忆
→ 人工审核
→ 正式永久记忆
```

强制规则：

- AI 只能 `propose`，不能自动批准；
- 未批准前 Core Memory 不增加；
- 拒绝候选不进入正式记忆；
- Obsidian 正式知识不能静默蒸馏为个人记忆；
- 正式正文权威仍是 Obsidian Vault + Git；
- SQLite 和 Qdrant 必须可重建；
- 来源、时间、Agent、Workspace 和审计可追溯。

## 11. Capture、导入和队列

每个新增或受影响 Adapter 必须验证：

- 合法最小 fixture；
- 真实 UI 或正式 API 入口；
- raw 快照；
- provenance；
- adapter version；
- input hash；
- idempotency key；
- 重复导入不重复生成正式内容；
- 队列状态、失败、重试和审计；
- 无效文件失败路径；
- 失败不产生脏正式记忆；
- 导入不等于自动永久记忆；
- 不做全盘扫描；
- 不读取未授权正文或浏览器秘密。

### 11.1 Automatic Memory 首次授权与第三方不干扰

自动化第二大脑的首次验收必须从一次中文主人授权开始。记录授权的 source kind、精确 allowlist root、授权时间、有效期和 owner confirmation；发现、watch、reconciliation、raw capture 与解析均只能访问该范围。未授权路径必须显示拒绝原因，不得通过相邻目录、全盘扫描或环境猜测扩大范围。

必须分别验证：

- ChatGPT 只接受官方导出 ZIP；浏览器资料、Cookie、Token、凭证和私有数据库不得读取。
- Codex transcript 先 schema-detect；未知或损坏 schema 必须 fail closed，并保留可审计失败事件。
- Claude Desktop 不抓不透明内部存储；没有官方导出时明确显示 `unsupported` 或 `consent_required`，不得通过进程注入、应用目录读取或网络上传绕过。
- 第三方客户端验收不得干扰客户端进程、配置、应用目录或主人会话；不得把“检测到”写成“已连接”。

增量变更必须在 30 秒内进入既有 Extraction Queue；watcher 使用 5 秒防抖，但 15 分钟 reconciliation 和每日完整性检查才是正确性来源。验收须证明 watcher 静默不会阻止 reconciliation，也不得把 watcher 事件数当作完整性事实。

### 11.2 Obsidian 自动记忆范围

自动记忆验收默认不读取或索引普通 Obsidian 文档。仅 `_LingJi/Memory Inbox`、`_LingJi/Memory Library` 或 frontmatter `lingji_memory: true` 合格；`lingji_memory: false` 永远优先。必须验证 dry-run、路径边界、Production/Acceptance 隔离和 Git 安全，不得静默写入、移动、删除或把普通/正式知识蒸馏进 Core Memory。

## 12. 检索、Embedding 和 Qdrant

受影响时必须验证：

- lexical 可用；
- semantic 可用时真实返回；
- Qdrant 不可用时 lexical 继续；
- degraded 状态真实；
- inactive Embedding 不把整个系统显示为崩溃；
- 维度或模型变化显示 rebuild required；
- 不自动删除 Production collection；
- metadata、privacy、time 和 Agent Scope 过滤应用于所有通道；
- normal search 与 traced search 排序一致；
- 结果带来源和匹配理由；
- 数量来自后端事实而不是 UI 推算。
- Current 模式默认排除 `superseded`、`invalidated`、`archived`；历史模式必须显式选择并保留 validity/replacement 证据。
- lexical、Qdrant、hybrid、Core、ContextPack 和 MCP 必须使用同一 current predicate；ContextPack 不超过 12,000 字符且每条结论有 citation。
- 自动 derived current memory 只有在无冲突、低风险且置信度 `>= 0.90` 时可激活；Core、身份、高风险和正式永久知识必须由主人明确确认。

## 13. Local Control API 和 MCP

受影响时必须验证：

- 8766 使用认证；
- 8767 使用声明的认证；
- 无 Token 和错误 Token 被拒绝；
- 正确 Token 可用；
- Token 不出现在预览、日志、截图和 Git；
- 无任意命令执行；
- 无任意配置路径写入；
- 不使用 `shell=True`；
- 工具列表与文档一致；
- 工具在真实客户端中实际调用，而不是只用 HTTP 脚本冒充；
- 写入工具保持候选和主人批准边界。

## 14. AI 客户端连接器

每个受支持客户端必须分别验证：

```text
检测
预览
精确确认
配置写入或官方 CLI
连接测试
新会话真实工具调用
候选提交
回滚
再次连接
```

配置规则：

- 写入前临时备份；
- 保留用户其他设置；
- 同名外部配置拒绝覆盖；
- 预览脱敏；
- 回滚只删除 LingJi 管理内容；
- 回滚后配置语法有效；
- 未安装客户端标记 `SKIPPED_NOT_INSTALLED`，不得写 PASS。

## 15. 生命周期

受影响的 Desktop、Sidecar、Core、MCP、启动和设置变更必须验证：

- 连续三轮 Core 重启；
- PID 符合预期；
- Runtime 恢复 healthy/managed；
- 端口恢复；
- 客户端连接恢复；
- Workspace、DataRoot、Vault 保持；
- 无重复 Core；
- 无孤儿 MCP；
- 无 PowerShell、CMD 或黑窗；
- 一次 Windows 重启后恢复；
- Windows 重启后再做一轮 Core 重启。

Windows 重启前写 checkpoint，重启后继续，不重复前面全部步骤。

Phase 1 自动记忆的真实机器顺序是 macOS M5 first：先完成 macOS focused/full/release、同 SHA macOS Artifact、主人观察、清理和远程复读，再进入 Windows。Opportunity Center 在 Phase 1 最终 PASS 前保持冻结。

## 16. 安全和隐私

必须检查：

- `.env`、Key、Token、Cookie 和 Authorization 未提交；
- 私人聊天、真实数据库、真实日志和未脱敏截图未提交；
- 不硬编码个人绝对路径；
- 不静默向 C 盘写数据；
- Production/Acceptance 隔离；
- 批量写 Vault 前有预览、限制和 Git checkpoint；
- 高风险操作有明确确认；
- 公开报告只包含脱敏证据；
- 私有证据只在主人本机临时保存。

## 17. 回归矩阵

每轮正式真机验收至少检查：

```text
黑窗
Runtime 未受管
重启不恢复
Windows 重启不恢复
重复 Core
孤儿 MCP
C 盘写入
Workspace 丢失
DataRoot 丢失
Vault 丢失
覆盖安装破坏数据
按钮无响应
假成功
未知值伪造
Token 泄露
导入自动写 Core Memory
回滚破坏用户配置
Production 被测试污染
```

并追加当前 `CHANGE_ACCEPTANCE_LOG.md` 指定的历史 Bug。

## 18. 证据和报告

私有证据可包含：

- 原始日志；
- 本机配置临时副本；
- 私人截图；
- 进程树；
- 调用 transcript。

公开证据只能包含：

- 哈希；
- 脱敏摘要；
- 测试 ID 和结果；
- 不含秘密的局部截图；
- CI 和 Commit 身份。

报告必须使用 `REPORT_TEMPLATE.md`，每项包含：

```text
ID
前置条件
执行方法
预期结果
实际结果
证据
结论
```

## 19. 最终判定

`PASS` 需要：

- 身份和哈希正确；
- 强制自动测试通过；
- 强制真机测试通过；
- 主人观察项确认；
- 无 P0/P1 阻塞；
- Production 未污染；
- 报告已提交；
- 临时数据已清理；
- 验收文档已与代码同步。

任何强制项已执行且失败：

```text
FAIL
```

环境、客户端、Artifact 或证据导致关键项无法执行：

```text
BLOCKED
```

## 20. 报告提交

验收报告从被测产品 Commit 创建独立分支，只添加：

```text
最终 Markdown 报告
脱敏公开证据 JSON
公开哈希清单
```

不得修改产品代码，不得移动产品 Head，不得合并产品 PR。

提交后在产品 PR 评论：

```text
被测产品 Commit
报告分支
报告 Commit
报告路径
最终结论
阻塞缺陷
未覆盖客户端
```

最后只向主人报告上述结果，等待主人或上层审查读取报告并决定是否合并。
