# OWNER_UI_EXPERIENCE_FAST_CLOSEOUT

## 当前结论

本报告记录主人界面快速收口候选的 focused 代码与自动化证据，以及 Mac 真机验收交接状态。
产品提交为 `a0a996636c2a4799952c3381148fbb04978952ab`。当前结论是：

> focused 技术证据通过，Mac packaged/安装/真实 UI 尚未执行；Windows 禁止启动。

这不是 release、Phase 1、主人体验通过或可合并结论。Mac 技术验收通过后必须保持发布版 App 打开，
等待主人体验确认；主人确认前只能表述“技术验收通过，等待主人体验”。

## 范围

- 普通导航收敛为 `首页`、`我的记忆`、`来源`。
- 真实待办存在时由首页提供上下文入口；无待办时不占普通主菜单。
- 首页优先展示具体自动成果、来源规模和当前状态。
- 普通记忆列表只展示 `current`，详情展示正文、变化过程、当前结论、来源原文和四层状态。
- 来源页降噪，高级路由保留并归入高级诊断。
- 未新增后端、数据库、API、队列、检索器、向量索引或状态源。

## 代码与审查

| 项目 | 结果 | 证据 |
|---|---|---|
| 产品提交 | PASS | `a0a996636c2a4799952c3381148fbb04978952ab` |
| Task B 实现 | PASS | 11 个 Desktop 文件；139 additions / 105 deletions |
| Task C 独立阻断审查 | APPROVED | Blocking findings: none |
| 必要修复轮数 | 0 | 无阻断问题，不启动额外修复轮 |

非阻断 Minor 记录：来源页“已导入”未来可改成“本次处理”以避免把 reused 计入新导入；来源卡存在少量重复状态文案；首页 current 过滤与我的记忆存在防御性差异。
这些不阻断本轮 Mac 验收。

## focused 自动化验证

运行目录：`desktop/lingji-control`（除仓库级 diff 检查外）。

| 命令 | 结果 |
|---|---|
| `node tests/e2e_owner_memory_flow.mjs` | PASS |
| `npm run build` | PASS，97 modules transformed |
| `node scripts/observation-first-ui-smoke.mjs` | PASS |
| `node scripts/ui-modular-smoke.mjs` | PASS，App.tsx 76 lines |
| `node scripts/owner-ui-menu-fast-track-smoke.mjs` | PASS |
| `git diff --check` | PASS |

自动化后已确认 8765、8766、8767 无监听，且无 LingJi core/control、Playwright 或 Chromium 残留进程。

旧版 `run-smoke-suite.mjs` 在 Node v24 下会因既有 `automatic-memory-sources-smoke.mjs` 使用
TypeScript 参数属性而触发 `ERR_UNSUPPORTED_TYPESCRIPT_SYNTAX`。该工具链基线问题未归因本轮 UI，
也未通过删除、skip 或降低断言隐藏。

## Mac 验收交接

状态：`IN_PROGRESS / NOT_TESTED`。下一步必须使用全新、隔离的 Acceptance root，从精确产品 SHA
构建 Mac arm64，核验 main/sidecar 架构、strict codesign 和 hash，备份后整包覆盖安装，并使用
隔离 DataRoot/Vault/source fixture 启动真实发布版。随后遍历首页、我的记忆、来源、高级诊断，
点击可见 enabled 控件，至少打开五条不同类型记忆核对正文、发展、当前结论、来源原文及
raw/structured/vector/permanent 四层状态。

验收必须证明：current-only 普通列表、空待办不占主菜单、自动扫描不依赖主人逐条点击、真实导入与重复扫描通过、Production/Vault pollution 为 0。
技术验收通过后保持 `/Applications/灵机.app` 打开，等待主人确认；确认前不得进行结束清理、合并或 Windows 验收。

## 未执行与限制

- packaged automatic-memory clean-root 双轮：NOT TESTED。
- Mac arm64 package/build/install/真实发布版 UI：NOT TESTED。
- Windows：`FORBIDDEN_UNTIL_MAC_OWNER_CONFIRMATION`。
- Production、真实 Vault、真实聊天、真实数据库和主人数据：未触碰。
- 旧 full/release/Task4R2/Task7 结果：保留原结论，不被本报告改写。
