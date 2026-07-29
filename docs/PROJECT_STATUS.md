# PROJECT_STATUS.md — LingJi 当前状态

> Updated: 2026-07-28  
> Formal and default branch: `master`  
> Current master baseline: `b576a65f85c36f6481ed0be02e500f6c9431141f`  
> Architecture: `docs/ARCHITECTURE.md`  
> Code entry points: `docs/MODULES/CODE_MAP.md`  
> Validation evidence: `docs/TEST_REPORTS/`

## 1. 当前结论

LingJi 的统一第二大脑主线、Windows 打包 Sidecar、Observation-first Desktop UI、仓库治理和默认分支收口已经进入 `master`。

当前有两项按顺序堆叠的 Draft 开发：

```text
PR #53  Windows Desktop lifecycle / bootstrap / zero-Shell acceptance
PR #54  Drama Memory V1
```

依赖关系：

```text
master
→ work/windows-gui-low-token-validation (PR #53)
→ feature/drama-memory-v1 (PR #54)
```

PR #54 不得先于 PR #53 合并。PR #53 仍需要主人安装版 UI 验收；PR #54 仍需要真实剧本资料与安装版 UI 验收。

## 2. 已合并主线

```text
PR #47  P2-11B Packaged Runtime Sidecar Manager    MERGED_AND_VALIDATED
PR #48  P2-12A Observation-first Desktop UI        MERGED_AND_VALIDATED
PR #49  Repository Governance Cleanup              MERGED_AND_VALIDATED
PR #50  Context Routing and Local Validation       MERGED_AND_VALIDATED
PR #51  Mainline History Convergence               MERGED_AND_VALIDATED
PR #52  Master CI and Validation Finalization      MERGED_AND_VALIDATED
```

正式规则：

- `master` 是唯一正式开发主线。
- `src/` 接收新正式能力。
- `desktop/lingji-control/` 是唯一正式 UI。
- `second_brain/` 只保留兼容、迁移与验收职责。
- Tauri 只通过认证的 8766 Local Control API 访问后端。
- MCP 默认 stdio，可选 HTTP 使用 8767；8765 只属于迁移兼容。

## 3. 数据权威

```text
Obsidian Vault + Git
= 永久记忆与正式知识正文

storage/raw
= 原始导入材料

lingji_state.db
= 任务、队列、运行状态与审计

lingji_memory.db
= 可重建 Lexical/Metadata Index 与 Structured Read Model

Qdrant
= 可重建 Semantic Index
```

SQLite 索引、Qdrant 和 Structured Read Model 不得成为第二份永久记忆事实源。

## 4. PR #53 Windows Desktop 状态

状态：

```text
DRAFT
AUTOMATED_VALIDATION_PASSED
OWNER_MACHINE_UI_ACCEPTANCE_REQUIRED
UNMERGED
```

已实现：

- Desktop 与 Sidecar 使用 Windows GUI 子系统。
- Sidecar 直接由 Rust 管理，运行链路不依赖 PowerShell。
- 首次启动要求主人确认非 C 盘 Runtime 数据根。
- production / acceptance 物理隔离。
- 应用内零 Shell 验收。
- PowerShell 5.1 原生命令退出码处理与低上下文验证。

仍需：

- 主人安装版启动、重启与零 Shell 观察。
- 完整真实 UI 控件验收。
- 明确回复 `UI 验收通过`。

代码签名和自动更新仍未实现，产物只能定义为内部验收构建。

## 5. PR #54 Drama Memory V1 状态

状态：

```text
DRAFT
STACKED_ON_PR53
V1_CODE_IMPLEMENTED
AUTOMATED_VALIDATION_IN_PROGRESS
OWNER_DATA_ACCEPTANCE_REQUIRED
UNMERGED
```

V1 已实现代码范围：

```text
单部与目录批量剧本导入
支持 txt / md / docx / pdf / srt / vtt / ass
5万字级输入
分集 / 场景 / 人物确定性解析
文本行 / PDF页 / DOCX段落 / 字幕时间码来源定位
原始文件与标准化正文保留
Drama SQLite 结构化读模型与 FTS5
中文长句词法回退
独立 lingji_drama_<workspace> Qdrant Collection
词法 + 语义 RRF 检索
语义不可用时词法降级
认证的 8766 Drama API
Tauri 短剧编剧工作台
```

架构边界：

- Drama 领域代码位于 `src/plugins/drama_intelligence/`。
- 不修改通用 Memory Engine schema。
- 不写入个人永久记忆。
- 原始剧本位于 active workspace 的 `raw/drama`。
- 标准化与结构化派生内容位于 `derived/drama`。
- Drama SQLite 和 Qdrant 均可重建。
- Writer Agent、一致性检查和模式挖掘尚未开放。

真实验收仍需：

```text
10部真实短剧
50–100万字
100道随机剧情与来源问题
检索准确率 ≥85%
原文定位完整
安装版 UI 全控件验收
```

缺少真实资料验收前不得宣称 Drama Memory V1 完成或开放自动编剧。

## 6. 当前安全边界

- Auto Review 仅 OFF/SHADOW，ACTIVE 继续拒绝。
- AI 不自动批准、拒绝、删除或覆盖正式个人记忆。
- 不自动删除或重建生产 Qdrant Collection。
- Drama 强制重建只清理对应 Drama 的独立语义 points。
- 不自动下载大型模型。
- 默认只绑定 `127.0.0.1`。
- Desktop 不直连数据库、Qdrant、Ollama 或兼容 API。
- Production 与 Acceptance 必须物理隔离。
- Windows Runtime 数据不得静默写入 C 盘。

## 7. 当前风险与阻塞

```text
PR #53 owner UI acceptance: blocking merge
PR #54 depends on PR #53: blocking merge
PR #54 real 10-script retrieval evaluation: not run
Drama Writer Agent: intentionally disabled
Drama continuity checker: deferred
Drama pattern mining: deferred
OCR execution: not implemented
Updater: not implemented
Code signing: not implemented
second_brain retirement: not eligible
```

## 8. 下一步

```text
完成 PR #54 自动 CI
→ 安装 PR #53 验收构建并完成主人 UI 验收
→ 合并 PR #53
→ 将 PR #54 更新到 master
→ 构建 Drama 安装版
→ 使用 acceptance workspace 导入10部真实短剧
→ 执行100题来源与剧情检索评测
→ 代理完成全部 Drama UI 控件自验
→ 主人确认 UI
→ 才允许合并 PR #54
```
