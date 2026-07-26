# PROJECT_STATUS.md — LingJi 当前状态

> Updated: 2026-07-26
> Formal branch: `feature/second-brain-memory`
> Formal head: `7e53fc29fb308b73031b39f9a2a000122653674f`
> Architecture: `docs/ARCHITECTURE.md`
> Code entry points: `docs/MODULES/CODE_MAP.md`
> Validation evidence: `docs/TEST_REPORTS/`

## 1. 当前结论

LingJi 的第二大脑主线、Windows 打包 Sidecar 和 Observation-first Desktop UI 已进入正式功能分支。

```text
PR #47  P2-11B Packaged Runtime Sidecar Manager   MERGED_AND_VALIDATED
PR #48  P2-12A Observation-first Desktop UI       MERGED_AND_VALIDATED
```

关键合并提交：

```text
PR #47: 6720d0cd76c8ff9e9bc38ef2df52793c0ab0f4c5
PR #48: 7e53fc29fb308b73031b39f9a2a000122653674f
```

最终验收事实来源：

```text
docs/TEST_REPORTS/PR47_PR48_FINAL_ACCEPTANCE_REPORT.md
docs/TEST_REPORTS/P2_11B_LOCAL_WINDOWS_ACCEPTANCE_REPORT.md
docs/TEST_REPORTS/P2_11B_RUNTIME_SIDECAR_TEST_REPORT.md
docs/TEST_REPORTS/P2_12A_OBSERVATION_FIRST_DESKTOP_UI_TEST_REPORT.md
```

## 2. 当前治理任务

状态：`IN_PROGRESS`

分支：

```text
work/repository-governance-cleanup
```

目标：

- 删除确定的重复执行和过期触发入口。
- 让架构、项目状态、代码地图、开发规则和测试证据各自只维护一种事实。
- 不新增总结文档，不复制现有实现，不进行无证据的大重构。
- 保持 P2-11B/P2-12A 行为和安全边界不变。

完成条件：

- 定向 Desktop smoke/build 通过。
- Windows Sidecar release workflow 通过。
- Python、Desktop、Rust 和插件完整门禁通过。
- CI 必需检查全部通过。
- 合并后更新本页的正式 head 与治理状态。

## 3. 产品与代码主线

```text
src/
= 长期平台主线

desktop/lingji-control/
= 唯一正式 Desktop UI

second_brain/
= Compatibility / Migration Runtime
```

规则：

- 新正式能力进入 `src/`。
- Desktop 只通过认证的 8766 Local Control API 访问后端。
- `second_brain/` 不接收新的正式产品能力。
- Obsidian CLI 正式实现位于 `src/obsidian/`。
- MCP 默认使用 stdio；可选 HTTP 使用 8767。

## 4. 数据权威

```text
Obsidian Vault + Git
= 永久记忆与正式知识正文

storage/raw
= 原始导入材料

lingji_state.db
= 任务、队列、运行状态与审计事件

lingji_memory.db
= 可重建 Lexical/Metadata Index 与 Structured Read Model

Qdrant
= 可重建 Semantic Index
```

SQLite 索引、Qdrant 和 Structured Read Model 均为派生数据，不得取代 Obsidian Vault + Git 的正式知识权威。

## 5. 已验证能力

```text
P0 Workspace / Port / Engineering Hygiene
P1 Unified Semantic Memory
P2 Vector Center / Structured Read Model / Capture / Inspector
P2 Obsidian CLI Formal Migration
P2 Codex-first Local Memory Loop
P2 Auto Review SHADOW
P2 Runtime/Desktop Reliability
P2 Owner-visible Settings Governance
P2 Windows Packaged Runtime Sidecar
P2 Observation-first Desktop UI
```

当前安全边界：

- Auto Review 仅 OFF/SHADOW，ACTIVE 继续拒绝。
- 不自动批准、拒绝、删除或覆盖正式记忆。
- 不自动删除或重建生产 Qdrant Collection。
- 不自动下载大型模型。
- 默认只绑定 `127.0.0.1`。
- Desktop 不直连数据库、Qdrant、Ollama 或兼容 API。
- Windows 打包版尚不宣称自动更新或代码签名。

## 6. 当前风险与阻塞

```text
P0 blocking defects: none recorded after PR #47/#48 acceptance
Updater: not implemented
Code signing: not implemented
second_brain retirement: not eligible until migration parity and rollback conditions pass
Repository governance cleanup: awaiting CI and merge
```

## 7. 下一步

```text
完成 repository governance cleanup
-> 运行最终完整门禁
-> 合并治理分支
-> 更新正式 head
-> 冻结稳定基线
-> 再选择下一项产品开发任务
```
