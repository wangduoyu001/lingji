# LingJi 最终本地收尾总控计划

状态：`ACTIVE GOVERNANCE`

适用范围：PR #60、`feature/unified-ai-memory-connectors`、本机 Codex 最终开发与验收。

本文件负责回答一件事：从当前 `05376996` 产品提交开始，怎样由本机一次性完成剩余开发、测试、真机验收、主线收敛、文档、发布和清理，而不是每次失败后重新拼一份临时计划。

---

## 1. 当前远程事实

```text
Repository: wangduoyu001/lingji
master: dff85844ced40c42cd1becb5a15747e85eff3b33
Product PR: #60
Product branch: feature/unified-ai-memory-connectors
Product Head: 053769965cf767cfe5221ffa4334b189bedb4d7d
Pinned Artifact: lingji-windows-0.1.0-05376996
Artifact ID: 8832376546
Current task: PR60-MEMORY-QUALITY-TRIAL-05376996
Current result: PENDING / Day 0 NOT_RUN
PR #60: Draft / Do not merge
```

分支比较：

```text
feature/unified-ai-memory-connectors
  ahead of master: 185 commits
  behind master: 21 commits
  status: diverged
```

最近的产品修复链：

```text
1860fa17
  → packaged assistant import worker recovery
3739c42f
  → extraction worker moved under MCP owner
24f35704
  → packaged extraction and MCP ownership recovery
05376996
  → Control API project gateway disables embedded semantic runtime
```

当前已经修复到：

```text
只有 MCP Runtime 可以实时打开嵌入式 Qdrant。
Control API 只能使用 SQLite/Vault 的词法能力并读取 MCP 发布的向量状态快照。
```

当前尚未证明：

```text
05376996 Artifact 在真实 Windows 环境完成 Day 0；
授权合成导出包可以自动入队并完成处理；
MCP 发布的向量快照在导入后保持一致；
真实 Codex MCP 调用成功；
Windows 重启后恢复；
安全清理完成；
Stage 1 真实资料质量阈值通过；
产品分支与 master 完成最终收敛。
```

---

## 2. 本地接管原则

从本计划生效起：

```text
本机 Codex = 最终开发、测试、发包、真机验收、报告和清理执行者
ChatGPT / 云端 = 需求裁决、风险审查、主人决策和最终结果复核
```

不得再采用：

```text
本机只跑一次验收
→ 报一个失败
→ 云端零散改几处代码
→ 再生成一份新任务单
```

本机必须完整拥有修复循环：

```text
发现缺陷
→ 定位根因
→ 建立最小修复分支
→ 添加回归测试
→ 完成实现
→ 运行焦点与全量测试
→ 更新 Markdown 报告
→ 提交 PR 到产品分支
→ 验证精确 Head CI
→ 生成新 Artifact
→ 更新任务身份
→ 再次执行 Day 0
```

同一缺陷第二次出现时，不得只换 Artifact。必须先证明：

1. 根因与上次不同；或
2. 上次回归测试没有覆盖真实失败路径，并补齐测试；或
3. 验收环境/脚本本身存在缺陷，并修复验收合同。

---

## 3. Phase 0：读取并保护本机最新提交

本阶段必须在改动任何文件之前完成。

### 3.1 读取现场

在本机实际仓库执行并记录：

```powershell
git rev-parse --show-toplevel
git branch --show-current
git rev-parse HEAD
git status --short --branch
git log --oneline --decorate --graph -n 30
git branch -vv
git worktree list --porcelain
git reflog -n 30 --date=iso
```

执行：

```powershell
git fetch --all --prune
```

随后记录：

```powershell
git log --oneline origin/master..HEAD
git log --oneline HEAD..origin/master
git diff --stat
git diff --cached --stat
```

若当前分支有 upstream，还必须记录：

```powershell
git log --oneline @{upstream}..HEAD
git log --oneline HEAD..@{upstream}
```

### 3.2 保护规则

禁止：

```text
git reset --hard
git clean -fd / -fdx
强制移动已有分支
force push
删除未知 worktree
覆盖未提交文件
```

若存在未推送提交：

1. 创建安全分支：`backup/local-closeout-<timestamp>-<shortsha>`；
2. 推送安全分支；
3. 记录提交清单和远程 SHA；
4. 再决定合并、cherry-pick 或保留。

若存在未提交修改：

1. 只读记录文件列表和 diff stat；
2. 不查看私人数据文件正文；
3. 创建命名明确的 WIP 提交或 stash 前必须先记录；
4. 不把数据库、Qdrant、`.env`、Token、聊天正文、绝对私人路径提交到 Git。

### 3.3 发现报告

生成：

```text
docs/TEST_REPORTS/LOCAL_FINAL_CLOSEOUT_DISCOVERY_<local-short-sha>.md
```

至少包含：

```text
本机仓库路径（脱敏）
当前分支
本机 HEAD
远程 master
远程产品 Head
未推送提交
未提交修改
worktree 列表
安全备份分支
采用的对齐策略
不得丢失的本机工作
```

Phase 0 未完成，不得安装 Artifact，不得修改产品代码。

---

## 4. Phase 1：执行当前 05376996 Day 0

权威入口：

```text
docs/ACCEPTANCE/LOCAL_EXECUTION_TASK.md
```

固定身份：

```text
Product Head: 053769965cf767cfe5221ffa4334b189bedb4d7d
Artifact ID: 8832376546
```

必须从当前产品提交的隔离 worktree 调用修复后的安全清理工具，不得使用旧 master 脚本推断行为。

### 4.1 Day 0 必须证明

```text
首次恢复 <= 45 秒；
精确 DataRoot / workspace / binding 验证；
真实资料正文读取数 = 0；
合成 ChatGPT/Codex 导出包被自动发现；
一次授权后直接入队，无路径输入和二次提交；
任务从 queued 进入处理中并完成或给出可解释失败；
只有 MCP Runtime 持有 SQLite/Qdrant；
Control API 不打开第二个嵌入式 Qdrant；
向量状态 empty / locked / stale / rebuilding / healthy 一致；
全文检索与语义检索状态分别真实显示；
Codex 跳过不可启动 WindowsApps 别名；
真实 codex mcp list 可见 lingji-memory；
真实 MCP 调用命中 acceptance Runtime；
合成候选批准一个、拒绝一个；
Desktop/Core/MCP 多轮重启恢复；
Windows 重启恢复；
Production 污染 = 0；
清理 dry-run = DRY_RUN_READY；
execute 后唯一任务根不存在。
```

### 4.2 主人只参与六个检查点

```text
A：首启、DataRoot、UI 是否一眼可懂
B：授权读取任务生成的合成导出包
C：确认一键导入、Codex MCP、Qdrant 证据
D：指定一个合成候选批准、一个拒绝
E：允许 Windows 重启
F：确认重启、清理、远程报告结果
```

不得要求主人：

```text
填写路径
手工刷新
手工运行命令
手工启停服务
手工上传报告
手工删除目录
```

---

## 5. Phase 2：本地修复循环

仅在 Phase 1 未通过时进入。

### 5.1 缺陷分类

每个失败必须归入一个主类：

```text
RUNTIME_BINDING
FIRST_RECOVERY_TIMEOUT
IMPORT_DISCOVERY
IMPORT_QUEUE_WORKER
MCP_AUTH_OR_CLIENT
QDRANT_OWNERSHIP
VECTOR_SNAPSHOT_TRUTH
CANDIDATE_REVIEW
RESTART_RECOVERY
CLEANUP_LIFECYCLE
ACCEPTANCE_CONTRACT
```

报告必须包含：

```text
首次失败时间
触发路径
真实日志证据
根因
为何现有测试未拦截
最小修复边界
新增回归测试
不在范围
回滚方式
```

### 5.2 分支与实现

从当前精确产品 Head 建立：

```text
codex/pr60-<defect-name>-<shortsha>
```

架构边界：

```text
正式能力只进入 src/
正式 UI 只进入 desktop/lingji-control/
second_brain/ 只做兼容、迁移、只读或诊断
Obsidian Vault + Git 是永久记忆权威
SQLite/Qdrant 是可重建索引
不得新增第二个事实源
不得新增第二个正式 UI
不得新增第二个 Qdrant 实时拥有者
```

实现要求：

```text
先定位根因再改代码；
每个修复只解决一个主缺陷；
不做无关重构；
错误处理和降级路径必须一起完成；
UI 必须展示真实状态和证据；
禁止用文案掩盖运行时失败；
禁止把失败测试改成 skip；
禁止降低断言；
禁止只靠 mock 证明真实 Windows 行为。
```

### 5.3 测试层级

每个修复至少完成：

```powershell
python -m pytest -q <focused-tests>
python -m pytest -q --tb=short
```

Desktop：

```powershell
cd desktop/lingji-control
npm ci
npm run test:smoke
npm run build
```

Rust/Tauri：

```powershell
cd desktop/lingji-control/src-tauri
cargo test
cargo check
```

发布链：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\validate.ps1 -Mode release
```

并验证：

```text
Python 3.11
Python 3.12
Windows Python
Desktop smoke
React/TypeScript production build
Rust/Tauri
packaged Sidecar auth/lifecycle
NSIS
release artifact contract
acceptance-doc-sync
local-execution-handoff
```

### 5.4 文档与提交

每个功能或大段代码必须更新或新增 Markdown：

```text
docs/TEST_REPORTS/<FIX_REPORT>.md
docs/ACCEPTANCE/changes/<PR_OR_TASK>.md
docs/MODULES/CODE_MAP.md
docs/PROJECT_STATUS.md
docs/CHANGELOG.md
```

报告至少包含：

```text
任务目标
代码入口
修改文件
架构决定
数据流
配置/API/UI变化
测试命令
测试结果
已知限制
回滚方式
下一步
提交 SHA
```

提交必须按逻辑拆分：

```text
fix(...) / feat(...)
test(...)
docs(...)
```

不得提交：

```text
数据库
Qdrant 数据
.env / Token
私人聊天或剧本正文
node_modules / dist
缓存
真实绝对路径
临时截图和未脱敏日志
```

### 5.5 PR、CI、Artifact、复验

1. PR 只合入 `feature/unified-ai-memory-connectors`；
2. PR #60 保持 Draft；
3. 合入前验证修复分支精确 Head；
4. 合入后只认新的产品 Head；
5. 等待精确 Head 的五套门禁；
6. 生成新的 Windows Artifact；
7. 独立核验 ZIP、Installer、Portable、Sidecar、Manifest、build-metadata；
8. 通过 docs PR 更新 master 任务身份和回执；
9. 清理上一轮任务根；
10. 回到 Phase 1。

不得复用旧失败 Artifact。

---

## 6. Phase 3：Day 0 通过后的 Stage 1

只有以下全部满足才进入：

```text
Day 0 = PASS
主人检查点 A-F = PASS
真实资料正文读取数在 Day 0 = 0
Production 污染 = 0
清理 = PASS
远程报告复读 = PASS
```

随后暂停并向主人列出具名范围，获得一次明确授权。

建议 Stage 1 最小范围：

```text
1 部剧本
1 份 Codex 报告
少量 ChatGPT 历史
1 个明确 Obsidian 子目录
```

不得读取未点名目录。

### 6.1 质量题

至少 20 道：

```text
精确事实 >= 8
跨文档比较 >= 4
来源核验 >= 4
负面边界 >= 4
主人抽查 >= 10
```

阈值：

```text
quality_score >= 90%
source_accuracy >= 95%
false_positive_rate <= 5%
Codex MCP success >= 95%
duplicate formal content = 0
Production pollution = 0
candidate approval boundary = 100%
```

### 6.2 失败处理

Stage 1 失败不得扩大数据范围。

按类型回到 Phase 2：

```text
解析器
分块
去重
全文检索
Embedding
向量索引
权限过滤
来源引用
Context Pack
候选审核
```

剧本人物、剧情和台词不得进入主人个人事实。

---

## 7. Phase 4：Stage 2 扩展验证

Stage 1 PASS 后才允许扩大到：

```text
最多 10 部授权剧本
更多明确授权的 ChatGPT/Codex 内容
更多明确授权的 Obsidian 子目录
```

Stage 2 重点：

```text
批量导入稳定性
重复采集为 0
来源隔离
人物与主人事实隔离
跨文档检索
大量数据分页和 UI 性能
重建 SQLite/Qdrant
备份恢复
中断续跑
多次重启和 Windows 重启
```

Stage 2 不得自动扩大到整个磁盘或整个 Vault。

---

## 8. Phase 5：产品分支与 master 收敛

当前产品分支领先 185、落后 21，必须显式收敛。

### 8.1 时机

只有当前产品 Head 完成 Day 0 和 Stage 1 后再执行，避免在验收过程中移动固定身份。

### 8.2 策略

在隔离 worktree：

1. 创建 `backup/pr60-pre-final-sync-<shortsha>`；
2. fetch 最新 `master` 与产品分支；
3. 使用普通 merge 将 `master` 合入产品分支；
4. 不对 185 个产品提交整体 rebase；
5. 不 force push；
6. 冲突逐文件审查，不接受整侧覆盖。

重点冲突：

```text
docs/ACCEPTANCE/LOCAL_EXECUTION_TASK.md
docs/ACCEPTANCE/LOCAL_EXECUTION_RESULT.md
docs/ACCEPTANCE/CHANGE_ACCEPTANCE_LOG.md
docs/PROJECT_STATUS.md
docs/CHANGELOG.md
docs/MODULES/CODE_MAP.md
scripts/check_acceptance_sync.py
scripts/check_local_execution_handoff.py
```

### 8.3 收敛后验证

收敛提交会改变产品 Head，即使代码逻辑未变，也必须：

```text
重新运行全部自动门禁
重新生成精确 Head Artifact
重新执行合成 Day 0
至少复跑 Stage 1 核心 20 题和主人抽查
重新核验覆盖安装、重启、清理和回滚
```

不得拿收敛前 Artifact 支持收敛后提交。

---

## 9. Phase 6：最终发布候选验证

最终候选必须同时通过：

### 9.1 自动验证

```text
完整 Python 测试
Windows Python
Desktop 全部 smoke
React/TypeScript build
Rust/Tauri test/check
packaged Sidecar
MCP auth/lifecycle
NSIS
release artifact contract
clean-install contract
acceptance sync
local handoff
```

### 9.2 真机验证

```text
全新安装
覆盖安装
卸载后重装但保留主人数据边界
首次启动 <= 45 秒
无黑窗
DataRoot/Workspace 自证
一键合成导入
真实 Codex MCP
Qdrant 单一所有权
全文/语义降级
Core/MCP/Desktop 重启
Windows 重启
断网/模型缺失/Qdrant不可用降级
备份与恢复
回滚到上一个可用安装包
安全清理
```

### 9.3 安全检查

```text
无 Token
无主人正文
无数据库/Qdrant 数据
无 C盘静默运行数据
无任意路径读取
无 shell=True
无公网 MCP
无未授权外部客户端修改
无自动永久记忆批准
```

---

## 10. Phase 7：文档和 PR #60 收尾

必须更新：

```text
README.md
docs/PROJECT_STATUS.md
docs/CHANGELOG.md
docs/MODULES/CODE_MAP.md
docs/ARCHITECTURE.md
docs/DEVELOPMENT_RULES.md
对应模块实施文档
所有最终测试报告
PR #60 正文
最终 Artifact 身份与哈希
```

文档必须反映：

```text
src/ 是长期主线
second_brain/ 是兼容迁移来源
Tauri 是唯一正式 UI
Obsidian Vault + Git 是永久记忆权威
lingji_state.db 是运行状态
lingji_memory.db 是可重建全文/元数据索引
Qdrant 是可重建语义索引
MCP 是嵌入式 Qdrant 唯一实时拥有者
Control API 只读 MCP 状态快照
```

PR #60 只有在以下全部满足后才可转 Ready：

```text
最终精确 Head CI 全绿
最终 Artifact 哈希核验
最终合成 Day 0 PASS
Stage 1 PASS
主人质量抽查 PASS
Production 污染 0
重复正式内容 0
主人配置保留 PASS
安全清理 PASS
远程报告复读 PASS
master 收敛完成
回滚方案验证
```

PR #60 合并到 master、创建版本标签或公开 Release 前，必须再次获得主人明确批准。

---

## 11. 最终本地交付物

本机 Codex 必须交付：

```text
1. 本机现场发现报告
2. 每个修复的实现与测试报告
3. 每轮 Day 0 报告与公开摘要/哈希
4. Stage 1 质量报告
5. Stage 2 扩展报告（执行时）
6. master 收敛报告
7. 最终 Release 报告
8. 最终安装包身份与哈希
9. 回滚验证报告
10. LOCAL_EXECUTION_RESULT.md 最终回执
11. PR #60 权威评论
12. 本地临时目录清理证明
```

最终结果只能是：

```text
PASS
FAIL_WITH_ACTIONABLE_ROOT_CAUSE
BLOCKED_BY_OWNER_AUTHORIZATION
BLOCKED_BY_EXTERNAL_ENVIRONMENT
```

不得使用“基本完成”“大概可用”“CI绿了所以完成”等模糊结论。

---

## 12. Definition of Done

只有同时满足以下条件，灵机本轮才能称为完成：

```text
架构边界正确
没有重复系统和第二事实源
功能、错误处理和降级路径完成
UI 状态真实可见
单元、集成、UI、Windows、Rust、Release测试通过
真实 Day 0 和 Stage 1通过
旧测试未减少
每项大功能有 Markdown报告
Code Map / Project Status / Changelog更新
精确提交与Artifact可追踪
无秘密、数据库和运行数据进入Git
Production污染为0
安全清理和回滚完成
PR #60仍由主人决定最终合并
```

缺少任何一项，只能标记为：

```text
开发中
部分完成
等待主人授权
等待外部环境
```
