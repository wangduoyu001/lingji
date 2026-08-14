# PROJECT_STATUS.md — LingJi 当前状态

> Updated: 2026-08-15
> Formal/default branch: `master`
> Current product PR: `#88`
> Current product candidate: `2c96b3ec54b066204cad8db75455be24822852a9`
> Architecture: `docs/ARCHITECTURE.md`
> Code entry points: `docs/MODULES/CODE_MAP.md`
> Acceptance authority: `docs/ACCEPTANCE/README.md`

## 1. 当前结论

PR #88 的云端代码门禁和同 SHA macOS / Windows Artifact 构建已经完成，但真实 M5 验收最终为：

```text
FAIL / DO NOT MERGE
```

当前不是发布完成状态，也不是“待主人点一下确认”的状态。阻塞已经明确收敛到产品体验层：

- `M5-UX-003`：首页看不出系统自动执行了什么；
- `M5-UX-004`：新 UI 与旧版没有形成明显、可感知差异；
- `M5-UX-005`：信息层级不友好，重点、进度和下一步不清楚；
- “找回主窗口”未获得主人通过；
- Memory Progress Dashboard 未获得主人通过。

因此当前本机任务已经转为 `IDLE`。不得继续重跑失败 Artifact，必须先进入新的产品修复周期。

## 2. 已通过的技术边界

当前候选 `2c96b3ec54b066204cad8db75455be24822852a9` 已验证：

- 六道同 SHA 远程门禁通过；
- macOS Artifact / DMG / 内嵌 Commit 身份一致；
- Apple Silicon arm64；
- whole-bundle 安装与 codesign；
- Acceptance Runtime 数据物理隔离；
- Secret 不导出，`secret_export_count=0`；
- 第二次启动与精确停止通过；
- 失败后恢复原先安装 App；
- Production 数据未被删除或污染；
- 本轮临时验收数据已清理。

这些通过项不等于产品整体 PASS。UI 主人验收为 P1 blocker，足以阻止合并。

## 3. 权威失败证据

```text
Task ID:
PR88-M5-REACCEPTANCE-2C96B3EC

Report branch:
acceptance/pr88-m5-reacceptance-2c96b3ec

Report commit:
9fdbacf52c22ecaac7eab3a4676f80a81e0dfa95

Cleanup receipt commit:
33982e1d5d3d567369e56484ade733a8b7228408

Report:
docs/TEST_REPORTS/MACOS_M5_PHYSICAL_ACCEPTANCE_2c96b3ec.md

PR #88 result comment:
5295519058
```

最近一次结果以 `docs/ACCEPTANCE/LOCAL_EXECUTION_RESULT.md` 为准；当前是否存在可执行任务以 `docs/ACCEPTANCE/LOCAL_EXECUTION_TASK.md` 为准。

## 4. 当前产品主线

```text
src/
= 长期平台主线

desktop/lingji-control/
= 唯一正式 Desktop UI

second_brain/
= Compatibility / Migration Runtime
```

规则不变：

- 新正式能力进入 `src/`；
- 新正式 Desktop 能力进入 `desktop/lingji-control/`；
- Desktop 只通过认证的 `127.0.0.1:8766` Local Control API 访问后端；
- MCP 默认 stdio，可选 HTTP 使用 8767；
- 8765 仅为迁移期兼容 API；
- `second_brain/` 不接收新的正式产品能力。

## 5. 数据与安全权威

```text
Obsidian Vault + Git
= 永久记忆与正式知识正文

storage/raw
= 原始导入材料

lingji_state.db
= 任务、队列、运行状态与审计事件

lingji_memory.db
= 可重建全文与元数据索引

Qdrant
= 可重建语义索引
```

长期安全边界：

- AI 不静默修改 Core Memory；
- 不自动删除或重建 Production Qdrant；
- 不自动下载大型模型；
- 默认只绑定 `127.0.0.1`；
- Production 与 Acceptance 必须物理隔离；
- Secret 只进入系统安全凭据存储，UI/日志/报告只使用脱敏状态；
- 停止 Runtime 只处理精确实例/PID/端口，不全局杀进程。

## 6. 当前必须做的产品修复

下一轮不是继续堆统计卡片，而是重构首页信息架构，让自动化过程成为产品主结构。

最低要求：

1. 首页顶部先回答“现在有没有必须由我决定的事”；
2. 明确显示系统已经自动完成什么、正在处理什么、哪里失败/重试、下一步是什么；
3. 用真实事件和状态串起来源发现、收纳、解析、候选、确认、索引、取回、更新；
4. 技术指标、端口、数据库、向量细节下沉到高级诊断；
5. 新 UI 在首屏结构、交互路径和视觉层级上必须与旧版有明显差异；
6. “找回主窗口”必须变成主人能发现、能理解、能验证的真实入口；
7. Memory Progress Dashboard 必须表达真实工作进度，不能只是静态统计。

## 7. 下一轮发布条件

必须按新周期执行：

```text
修复产品 UI / 信息架构
→ 新产品 Commit
→ focused + full + CI
→ 同一精确 SHA 的 macOS / Windows Artifact
→ Artifact 哈希锁定
→ 更新 CHANGE_ACCEPTANCE_LOG.md
→ 创建新的 LOCAL_EXECUTION_TASK.md（status: ACTIVE）
→ M5 真机复验
→ 报告 / 结果回执 / 清理
→ 只有 PASS 后才进入最终合并判断
```

失败候选：

```text
Artifact 9224368022: DO NOT RETRY
Artifact 9102748834: DO NOT RETRY
```

## 8. 文档治理状态

当前文档职责：

- `README.md`：仓库落地页；
- `AGENTS.md`：开发者与 AI 最小入口；
- `docs/PROJECT_STATUS.md`：只维护当前状态、阻塞和下一步；
- `docs/ARCHITECTURE.md`：稳定架构边界；
- `docs/MODULES/CODE_MAP.md`：代码入口和局部测试；
- `docs/ACCEPTANCE/README.md`：验收治理；
- `LOCAL_EXECUTION_TASK.md`：唯一当前本机任务；
- `LOCAL_EXECUTION_RESULT.md`：最近一次权威回执；
- `docs/TEST_REPORTS/`：历史与当前验收证据。

历史计划与旧验收任务不再承担当前状态职责。
