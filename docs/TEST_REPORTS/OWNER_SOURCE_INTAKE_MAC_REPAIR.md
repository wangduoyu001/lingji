# OWNER_SOURCE_INTAKE_MAC_REPAIR — Mac 技术验收报告

> 报告日期：2026-09-05。执行者：ZCode（GLM）。主人确认：**待定**（App 保持打开中）。

## 1. Executive Verdict

```text
Verdict: PASS (technical) / owner observation PENDING
Merge recommendation: DO NOT MERGE until owner confirmation
Product commit (product/tests head): 234690b89f671e328bd610966af73e74684434bd
Artifact source tree: 460e9011 (product content; 234690b8 adds test-only alignment)
Artifact: 灵机_0.1.0_aarch64.dmg
Report path: docs/TEST_REPORTS/OWNER_SOURCE_INTAKE_MAC_REPAIR.md
```

技术验收通过：packaged 双轮 GREEN、arm64 产物签名/哈希锁定、整包覆盖安装、全新隔离数据根、
真实 UI 全分区遍历、8766 仅 loopback、8765/8767 关闭。主人体验确认尚未给出；确认前不合并、
不启动 Windows、不做结束清理。

## 2. Artifact Identity

| 项目 | 值 |
|---|---|
| DMG SHA-256 | `0e1d75134f4e3087a5fe462e869448068037f352e9200e614c5e47a931103e46` |
| 主程序 lingji-control-center SHA-256 | `f05098871155f979e4c401197147ef581fe318d9583ec9e414aca112fe196dae` |
| sidecar lingji-core SHA-256 | `e0ea69b19c2cae08fd87b4dd33c5f034e544c0b344708fdf5dc3409964941edb` |
| 签名 | codesign --verify --strict OK（ad-hoc，identifier com.lingji.controlcenter） |
| 架构 | 主程序与 sidecar 均 Mach-O arm64 |
| 安装方式 | 整包替换 /Applications/灵机.app（旧包备份见 §5） |

## 3. Packaged Gate（双轮，全新隔离根）

- Round 1：`2 passed, 1 warning`，411.71s。
- Round 2：`2 passed, 1 warning`，410.14s。
- 覆盖十个场景（metadata-only 发现、授权启动扫描、事件/周期摄取、版本 supersede、幂等无重复、
  加速核对、30%/70% 真实 sidecar 崩溃恢复、生命周期、到期撤销、Gateway/Hybrid 检索）。
- 阻断修复（本轮，归因基线 `3471db1a` 同样失败后执行）：
  1. 场景 3 按 Task8E 已发布的 Darwin 周期核对契约分支（watcher 关闭时断言加速核对摄取同一事实，
     30 秒事件 SLA 继续记录为不适用/未满足，不冒充通过）；机制根因含配置 60 秒下限钳制。
  2. 崩溃矩阵 pause 提前至恢复终态确认后，消除 60 秒周期 tick 与 post-drain pause 的竞态
     （该竞态会多产生一个零变化扫描信封）。

## 4. Runtime / Ports / Data Root

- 新候选 sidecar 绑定 `127.0.0.1:8766`（仅 loopback）；8765/8767 无监听。
  本机 AutoClaw.app 以通配方式监听 `*:8766`（主人另一应用，未触碰）；特定绑定优先，未影响本候选。
- 数据根：全新隔离 `/tmp/LingJiAcceptance/osimr-7e7f0707/app-data`（workspace=acceptance）。
  桌面 bootstrap 配置已从旧 TASK8E 根切换并备份原文件。
- 健康真实值：`degraded`（ffmpeg/ollama 两项 warning，环境事实，如实显示）；`/api/brain/status`
  为 `configuration_required`（全新根尚未建索引，预期）；无 Token 访问 401。

## 5. Install / Backup / 既往实例

- 退出旧实例：osascript 正常退出；先前误判测试残留而终止过旧 sidecar（PID 15127）一次，
  旧 App 受监管地自动重启了它（行为本身验证了监管恢复），随后正常退出；如实记录。
- 安装前 /Applications/灵机.app 实为今日早间已安装的 7e7f0707 代构建（其 sidecar 哈希与本轮一致，
  主程序不同），已整包备份至
  `/tmp/LingJiAcceptance/osimr-7e7f0707/installed-app-backup/`（含旧哈希清单）。
- 本轮安装后主程序哈希 `f0509887…`，与备份包不同（含首页事实板等新前端）。

## 6. 真实 UI 遍历（真实机器数据）

- 首页"现在的事实"板（零点击）：记忆来源 5 个逐项状态与最近检查；本机 AI 软件发现 6 个、
  **正在运行：ChatGPT、Codex、ZCode**（真实进程）；模型状态（暂无运行中模型，兼容 0/0）；
  健康三值（自检 尚未获得 / 系统 需要检查 / 记忆 尚未获得——真实降级状态的诚实回退）；
  接收文件夹已就绪。另有"查看全部来源与明细"单一跳转。
- 来源页：Codex 双根真实元数据（451 文件/1.7GB、17 文件，真实 UTC 时间）、Obsidian 已发现、
  ChatGPT 需要确认、Claude 需要确认且无授权按钮（正确拒绝）。
- 本机 AI 软件分区：ChatGPT（支持自动读取/正在运行/版本 26.825.51511/能力标签）、Codex（支持/运行中）、
  Claude、LM Studio、VS Code、ZCode（暂不支持/未运行或运行中如实显示）。
- 模型与进程分区：运行进程 5 行（ChatGPT 64908、Codex×3、ZCode 58084），PID 仅在折叠"高级信息"。
- 官方导出接收文件夹：自动创建、打开/使用此文件夹按钮在位。
- 缺字段一律"尚未获得"，未发现伪造 0 或假成功。

## 7. Known Non-Blocking Notes

- `/api/brain/status` 真实响应无 `self_check` 键，首页"灵机自检"回退为"尚未获得"（诚实回退，
  字段对齐可后续收口）。
- 30 秒事件 SLA（watcher 事件）在 Darwin 周期模式下按 Task8E 设计不适用，维持全局 BLOCKED 记录。
- `test:smoke` 23 脚本套件 Node v24 基线问题沿用历史记录。

## 8. Owner Confirmation

App 与 sidecar 保持打开，等待主人肉眼确认：首页数据是否一眼可读、来源明细是否可信、
本机 AI 软件与进程是否与实际一致。主人确认前：不合并、不 push/PR、不做 Windows、不清理验收证据。

## 9. 2026-09-16 主人视角全面复检与修复（本轮追加）

主人要求"再次全面检查灵机并修复已知问题，重点是普通人视角的 UI 清晰美观；其他检测项按之前
项目核验"。执行者：ZCode（GLM）。

### 9.1 复检环境结论（沿用第 4/6 节口径，全部 PASS）

- 装机 App 主程序/sidecar 哈希与本分支 9-13 打包产物逐字节一致后才开检；本轮修复后整包替换安装，
  新主程序 SHA-256 `3a6c5547…`、sidecar 不变 `fe98100e…`（Python 零改动，复用同哈希产物）。
- 8766 仅 loopback、8765/8767 关闭；数据根为隔离验收根；无 Token 访问 401。
- 大屏四瓷片与 `/api/memory/inspector/cards-summary` 真实值一致（458/10624/10202/0）；
  时间线、检查记录、处理流水计数与 API 一致；缺字段一律"尚未获得"。

### 9.2 发现并修复（RED→GREEN）

| # | 问题（普通人视角） | 修复 |
|---|---|---|
| 1 | 托盘"打开灵机"后前端轮询保持暂停：首页数据冻结、永远显示"正在确认待办" | Rust 托盘 open/左键路径追加 App 级 `show()`（main.rs `show_main_window`），真机复验轮询恢复 |
| 2 | 托盘"暂停/恢复自动整理"是假按钮（只开窗） | 复用后端 `pause-runtime/resume-runtime`，托盘菜单直调并回写 tooltip；真机实测 state running→paused→running |
| 3 | 首页芯片"0 来源在线"与"458 对话已接管"矛盾 | 改为"按授权事实"计数，文案"N 个来源已接入"；真机显示"3 个来源已接入" |
| 4 | 来源页总览"扫描完成 0 个 · 已导入 0 个"误导 | 扫描完成含全部完成态、已导入含 imported/partial_failure/current；新文案"灵机正在自动记住：…" |
| 5 | "1659110953 字节 / 2026-08-07 16:21:24.575 UTC" 不可读 | `1.5 GB/372 MB` 人读格式 + `toLocaleString()` 本地化时间 |
| 6 | 记忆库要点卡标题/要点泄漏绝对路径 | 列表与详情统一套 `redactAbsolutePaths`（smoke 锁定契约） |
| 7 | 记忆卡"技术详情"折叠层因 `display:flex` 误用于 `<details>` 导致折叠失效 | CSS 拆分选择器：details 保持 block，flex 仅作用于内层芯片行 |

### 9.3 连带发现并修复的测试债（隐藏回归）

`tests/e2e_owner_memory_flow.mjs` 与 `scripts/owner-ui-menu-fast-track-smoke.mjs` 自 9-12 菜单/文案
重构（0daece79、132b0aaa）起即未对齐、实际处于 RED 状态，但近期交付记录声称"e2e PASS"。本轮已
全部对齐当前产品契约：主导航六项、健康三值位于来源页、卡片机器字段折叠、向量注释文案、
cards-summary `vectors` 字段、检查记录九步流水行。同时为首页大屏芯片与语义索引瓷片补上首条
渲染断言（stash 取证 RED → 恢复实现 GREEN）。

### 9.4 Focused 验证结果（本轮全绿）

- `test:e2e:memory` PASS（含 1024/1280 无横向溢出断言）
- `test:memory-sources` PASS、`test:memory-sources-repair` PASS
- `test:owner-ui-menu-fast-track` PASS
- `test:work-fact` PASS、`test:inspector` PASS
- `npm run build` PASS；`cargo check` PASS（仅历史 dead_code 警告）

### 9.5 真机复验（重打包安装后）

- 托盘"暂停自动整理"：runtime `running→paused`；"恢复自动整理"：`paused→running`（API 实证）。
- 关窗隐藏 35 秒：轮询保持鲜活；托盘"打开灵机"：窗口恢复、8 秒级轮询节奏持续、
  首页"目前不需要你处理"而非"正在确认待办"。
- 首页芯片"3 个来源已接入"；原始数据页"1.5 GB / 372 MB / 2026/8/8 00:21:24"本地化格式。

### 9.6 保持不修（诚实回退/边界）

- `/api/brain/status` 无 `self_check` 键 →"灵机自检：尚未获得"维持（ACTIVE 任务约束自检链路原样保留）。
- smoke 套件 Node v24 基线问题沿用历史记录。
- `AutoClaw.app` 通配监听 `*:8766` 为主人另一应用，未触碰（特定绑定优先）。

## 10. 2026-09-16 WorkBuddy 复检 P0 修复（追加轮）

任务：`OWNER_WORKBUDDY_RECHECK_PIPELINE_RECALL_REPAIR`（任务单 0B 节，主人指令）。
WorkBuddy 只读自检报告指控经 API 逐条复核属实后修复。

### 10.1 根因（实测定位）

- **提取回归 P0-1**：Codex 桌面版 0.154.0-alpha（9-13 起）新会话写入新信封
  `token_usage_record`，`CodexRolloutAdapter` 严格白名单按设计整文件拒绝 → 9-13 起
  全部 automatic_memory_snapshot 提取 failed（brain/status recent_tasks 9 failed/1 completed
  实证），记忆库冻结在 458 会话/10624 消息。
- **召回失效 P0-2**：`/api/observability/recall` 的 kNN 对无关查询也返回"最近的 N 个"，
  且存量退化点（零范数/跨点重复向量）恒回满分——"桃园结义"→1.000 命中"什么情况"
  （WorkBuddy 与我方双重复现）。
- **连带发现**：向量化 scroll 单页 10000 截断，集合超 1 万点后尾部点永远进不了
  existing_ids，其消息每轮被当作未向量化重嵌（embedded=200/轮空转、计数不增）。

### 10.2 修复内容（TDD RED→GREEN）

1. `CodexRolloutAdapter._KNOWN_TOP_LEVEL` 增加 `token_usage_record`（仅识别+跳过，遥测
   不入对话流；fail-closed 语义不变——扫描 487 个源文件确认无其他未知类型）。
2. 召回护栏 `observability_api._plausible_recall_hits`：分数 <0.70 丢弃（实测相关命中
   ≥0.717、无关噪声 ≤0.683）；满分 ≥0.999 仅当查询词与命中内容互为子串才保留。
3. `VectorBackfill.run_once` 三项：scroll 失败（并发锁竞争）时中止本轮而非盲目重嵌；
   集合翻页扫描消除 1 万点截断；零范数/跨点重复（不同内容同向量）的点直接出索引并记入
   进程级放弃名单（重嵌无法修复提供方级坍缩）；空内容消息不再进入向量化。
4. 测试：新增 3 个 RED→GREEN（token_usage_record 接受、召回护栏契约、退化点移除），
   修正 FakeProvider 为跨进程稳定种子；`test_vector_backfill`+`test_observability_api`+
   `test_owner_codex_rollout_adapter`+`test_automatic_memory_control_api` 共 54 passed。

### 10.3 真机复验（sidecar `4bb36edf…` 整包重装后）

- **导入恢复**：cards 458→462+、messages 10624→10881+ 且持续增长；requeue 的回归受害者
  job 全部成功，仅剩 19-20 个"混多会话"文件按既有安全规则拒绝（UI 有大白话解释，属设计）。
- **向量化恢复**：总量 10202→11612 并追平（embedded=0 收敛），422 积压与新导入全部补齐。
- **召回正确**：无关查询（桃园结义/直播话术）返回空集，相关查询（comfyui）正常命中 0.839/0.811。
- 附带证明：requeue 通过 `SQLiteExtractionQueue.retry` 完成——该能力未暴露 HTTP 路由，
  孤儿失败任务（所属扫描已被滚动保留删除）当前无主人可用的重试入口，记为已知缺口。

### 10.4 明确不修（记录）

- chat_model=qwen3:8b 空挂配置（主人裁定不纠结；仅状态展示字段，无链路消费）。
- settings 明文 Key：复核 `/api/settings` 不回显敏感值，无修复项。
- ffprobe 缺失、Obsidian CLI 未发现：环境事项；备份/验收报告为 0：沙箱预期。
- cards-summary 在提取队列满载时偶发超时（SQLite 写锁竞争）：队列排干后恢复，记为观察项。

## 11. bge-m3 主嵌入模型安装与向量层重建（2026-09-16 深夜追加）

主人查出中文召回失效的真正根因：设计主嵌入模型 `bge-m3` 从未安装（config.py 主/备结构与
P2_09A 文档无误），系统静默降级英文备胎 nomic。本轮完成：

- **模型安装**：Ollama registry 网络干扰无法 pull；改从 ModelScope 镜像下载
  gpustack/bge-m3-GGUF F16（1104MB/128 秒），`ollama create bge-m3` 导入。
- **集合重建**：旧 768 维集合备份移出（`storage/qdrant.bak-768`），新集合按 1024 维重建，
  11703 点全部重嵌（56 轮收敛，embedded=0）。
- **护栏校准**：召回分数下限 0.70→0.55（bge-m3 实测：无关噪声 ≤0.44、语义相关 ≥0.55；
  nomic 时代 0.70 会误杀中文相关命中）。测试夹具同步。
- **终验**：中文语义命中（Gmail 简报 0.716、电商选品 0.677）；语料外查询正确空集；
  vectors=messages=11703 全覆盖；cards=468 持续增长。sidecar `7aae839d…` 已装机。
- **遗留**：装机器清单需补 bge-m3；qdrant.bak-768 待主人确认后清理；registry 大模型
  拉取需国内镜像路径；cards-summary 满载超时为暂态观察项。

## 12. MCP 检索链路修复（2026-09-17 凌晨追加，任务 0C）

WorkBuddy v3 复检报告 R1/R5 经逐条源码+实测复核属实后修复（提交 031bba96）：

- **词法通道**：trigram 分词器对 2 字中文词恒 0 命中——把既有 history 模式的子串兜底
  推广到全部读取模式，并补 current/why 的 status 过滤。
- **语义通道**：正式集合从未被灌入 chunk 向量。新增 `ChunkVectorBackfill`
  （src/retrieval/chunk_backfill.py），按 chunk_id 幂等补齐正式集合（bge-m3 1024 维），
  重嵌 15,645/15,645（coverage 1.0）；vectorize 端点同时驱动消息层与 chunk 层回填，
  控制进程自建 provider 复用共享 Qdrant 客户端避免同路径双锁。
- **诊断诚实化**：hybrid diagnostics 增加每通道命中数（lexical_hits/semantic_hits），
  双 0 时 reason_code=no_matches。
- **状态真实化**：/api/vector/status 与 /api/vector/coverage 改为控制进程实时计算
  （source=live、stale=false），快照不可用时回退。
- **端到端实证**：离线驱动完整 HybridRetriever（副本+真 bge-m3）——agent=codex 时
  comfyui 返回 3 条结果；agent 无身份时 0 条为设计内代理隔离（agent_scope）。
- **R3 更正**：20 个失败任务实为"混多会话"按设计拒绝（伞形报错易误读），非缺适配器。

### 已知遗留（下轮候选）

1. R2 升格链输入端从未产出 candidate（自动激活被检疫隔离是设计；执行链未接线）——命门，需独立排查轮。
2. R4 数据全部在 acceptance 沙箱、production 从未创建——主人数据主权决策（搬 or 认账）。
3. MCP 客户端接线（Claude Desktop/Codex 配置段）+ search_memory 需带 agent_id 的使用说明。
4. reranker 精排、coverage 分母口径细化、UI 降级警示条、qwen3:8b 空挂配置清理。

## 13. 升格链接通 + production 迁移（2026-09-17 追加，提交 64a89b48）

- **升格链**：确认/编辑/拒绝动作对无 vault 候选文件的 DB 记忆，现在按记忆库权威内容
  物化候选文件（01-Inbox/AI-Memory/）再走 promote/reject 生命周期；全 vault 身份扫描
  防重复升格；会话卡（LJ-CONV）从会话记录组装候选内容。真机升格一张真实会话卡 →
  vault/03-Knowledge/Core-Memory/General/ 产出 memory_tier=core 文件（项目首份永久记忆）。
- **迁移**：acceptance→production 整体 mv（同卷、硬链接 inode 抽检一致）；chunk 集合以
  正确名称（lingji_memory_production）经 ChunkVectorBackfill 全量重嵌 15,648 点收敛；
  desktop-bootstrap active_workspace=production；Codex MCP --data-root 同步。
- **双工作区终验**：production 全功能（coverage 1.0 live、中文召回命中、永久记忆在位、
  workspace=production）；acceptance 重置为空沙箱（按需自动建目录）。
- sidecar `129df847` 已装机。已知限制：卡片流投影未读 vault 状态（升格成功的会话卡仍在
  流中显示，重复确认诚实报 ALREADY_REVIEWED）；qdrant 本地模式单进程锁——MCP 子进程与
  sidecar 回填互斥（幂等重试可收敛，长期方案=MCP 语义检索走 sidecar HTTP）。
