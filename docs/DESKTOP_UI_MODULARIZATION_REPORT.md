# 灵机桌面 UI 模块化报告

> 模块：P1-0 桌面 UI 最小模块化  
> 分支：`refactor/desktop-ui-modular-foundation`  
> 堆叠基线：`test/real-environment-acceptance`  
> Draft PR：`#6`  
> 状态：`REVIEW_REQUIRED`  
> 代码验证 Run：`29696562955`  
> 目标：拆分前端结构、统一连接状态、正式接入环境验收、建立默认值可学习设置基础  
> 非目标：不修改后端 API、不新增业务模块、不重新设计视觉、不引入大型依赖

---

## Research Notes

### 官方文档

1. React Sharing State Between Components  
   https://react.dev/learn/sharing-state-between-components
   - 采用：连接状态和当前页面只保留一个权威来源。
2. React Reusing Logic with Custom Hooks  
   https://react.dev/learn/reusing-logic-with-custom-hooks
   - 采用：把 API 连接、初始化和轮询抽到 `useLingJiConnection`。
3. React Choosing the State Structure  
   https://react.dev/learn/choosing-the-state-structure
   - 采用：不复制可从已有状态计算出的 `dirty`、`overridden` 和筛选状态。
4. Tauri State Management  
   https://v2.tauri.app/develop/state-management/
   - 采用：Tauri 只负责桌面能力和安全凭据桥接，React 页面不直接操作系统状态。
5. Visual Studio Code Settings UX  
   https://code.visualstudio.com/api/ux-guidelines/settings
   - 采用：每项设置有默认值、明确说明、合适控件和恢复入口。

### 类似项目

1. Visual Studio Code  
   https://github.com/microsoft/vscode
   - 设置按类别、搜索、修改状态和 Reset 操作组织。
   - 借鉴设置页的信息结构，不复制 Electron 或整个工作台架构。
2. Open WebUI  
   https://github.com/open-webui/open-webui
   - Python 后端和独立前端通过 API 管理模型、连接和设置。
   - 借鉴功能页面与后台配置分离。
3. AnythingLLM  
   https://github.com/Mintplex-Labs/anything-llm
   - 桌面、本地优先、多个模型 Provider 和设置页面。
   - 借鉴“本地优先 + 可选 Provider”的页面分区，不复制其服务端和数据库结构。

### 采用

- 不新增 React Router，当前没有深链接或浏览器历史需求。
- 使用中央 `NAVIGATION` Registry。
- `App.tsx` 只负责 Shell、导航和页面组合。
- 每个业务页面进入 `pages/`。
- API 连接、初始化和 10 秒总览刷新进入 Hook。
- 通用展示组件进入 `components/`。
- 环境验收进入正式左侧导航。
- 设置页支持搜索、只看已修改、单项和分组恢复默认、取消未保存修改。
- `SettingDefinition` 预留推荐值、修改时机、风险、成本、存储、性能、隐私和生效方式字段。

### 拒绝

- 不引入 Redux、Zustand、React Router 或 UI 组件库。
- 不把后端默认值复制到前端常量。
- 不趁模块化重写视觉样式。
- 不改变 API 路径或请求格式。
- 不修改 Python Service。
- 不把 P2 硬件、P3 模型或 P4 向量功能提前塞入 P1。

### 许可证与兼容性

- React、Tauri 和 VS Code 官方资料仅用于架构参考。
- 本模块没有新增第三方依赖。
- 保持现有 React 19、Vite 7、Tauri 2 和 Windows 构建链。

---

## 实现前问题

1. `App.tsx` 同时包含 Shell、连接、轮询、八个页面、设置字段和通用组件。
2. `Root.tsx` 为环境验收复制了一份 API、Token 和连接状态。
3. 环境验收依赖右下角临时模式按钮，不在正式导航中。
4. 页面无法由不同分支安全并行开发。
5. 设置页只有默认值和已覆盖标识，没有搜索、单项恢复、取消修改和未来推荐/影响字段。
6. 前端 Smoke 只检查环境验收几个字符串，无法阻止 `App.tsx` 再次膨胀。

---

## 修改文件

### 新增

```text
desktop/lingji-control/src/types.ts
desktop/lingji-control/src/navigation.ts
desktop/lingji-control/src/hooks/useLingJiConnection.ts
desktop/lingji-control/src/components/ui.tsx
desktop/lingji-control/src/components/DataTable.tsx
desktop/lingji-control/src/components/settings/SettingField.tsx
desktop/lingji-control/src/pages/OverviewPage.tsx
desktop/lingji-control/src/pages/JobsPage.tsx
desktop/lingji-control/src/pages/CapturePage.tsx
desktop/lingji-control/src/pages/MediaPage.tsx
desktop/lingji-control/src/pages/StoragePage.tsx
desktop/lingji-control/src/pages/BackupsPage.tsx
desktop/lingji-control/src/pages/AcceptancePage.tsx
desktop/lingji-control/src/pages/SettingsPage.tsx
desktop/lingji-control/src/pages/LogsPage.tsx
desktop/lingji-control/scripts/ui-modular-smoke.mjs
```

### 修改

```text
desktop/lingji-control/src/App.tsx
desktop/lingji-control/src/Root.tsx
desktop/lingji-control/src/AcceptancePage.tsx
desktop/lingji-control/scripts/acceptance-smoke.mjs
desktop/lingji-control/package.json
```

### 未修改但复用

```text
desktop/lingji-control/src/api.ts
desktop/lingji-control/src/styles.css
src/control/api.py
src/control/service.py
src/control/runtime_settings.py
```

---

## 结构

```text
src/
├── App.tsx                    # Shell 和页面组合
├── Root.tsx                   # 单一 App 入口
├── api.ts                     # 现有 API Client
├── navigation.ts              # 中央导航 Registry
├── types.ts                   # 共享类型
├── hooks/
│   └── useLingJiConnection.ts
├── components/
│   ├── ui.tsx
│   ├── DataTable.tsx
│   └── settings/
│       └── SettingField.tsx
└── pages/
    ├── OverviewPage.tsx
    ├── JobsPage.tsx
    ├── CapturePage.tsx
    ├── MediaPage.tsx
    ├── StoragePage.tsx
    ├── BackupsPage.tsx
    ├── AcceptancePage.tsx
    ├── SettingsPage.tsx
    └── LogsPage.tsx
```

---

## 默认值 UI 基础

设置字段现在支持：

- 当前有效值；
- 系统默认值；
- 推荐值，后端暂未返回时使用默认值作为显示回退；
- 使用系统默认、主人已修改、等待保存；
- 最小值、最大值和单位；
- 为什么推荐；
- 什么时候修改；
- 性能、存储、费用和隐私影响；
- 风险等级；
- 是否需要重启或后台任务；
- 单项恢复默认。

设置页支持：

- 搜索；
- 只显示已修改；
- 保存修改；
- 恢复本组默认；
- 取消未保存修改；
- 原始设置分组导航。

P2-P7 必须从后端 Setting Registry 返回完整定义，前端禁止手写另一份默认值。

---

## 测试优先证据

### 实现前会失败的约束

新增 Smoke 要求：

1. 页面、Hook、共享组件和类型文件真实存在；
2. `App.tsx` 使用中央导航和连接 Hook；
3. 环境验收进入正式导航；
4. 设置页面包含搜索、已修改筛选、恢复和取消；
5. 设置字段显示默认状态、推荐解释和单项恢复；
6. `App.tsx` 不得超过 100 行。

原结构无法满足这些断言。

### 首轮真实失败

Run `29696505774` 的桌面构建失败。原因不是业务页面错误，而是旧验收 Smoke 仍要求“环境验收”文字硬编码在 `App.tsx`，与中央导航 Registry 冲突。

修复：验收 Smoke 改为分别检查：

- `App.tsx` 的页面组合；
- `navigation.ts` 的中文入口和 `acceptance` ID；
- `pages/AcceptancePage.tsx` 的真实 API；
- `main.tsx` 的 Root 挂载。

没有为了通过测试把导航文字重新硬编码回 `App.tsx`。

---

## 最终测试结果

GitHub Actions Run：`29696562955`

| 检查 | 结果 |
|---|---|
| Desktop UI Smoke | success |
| TypeScript Build | success |
| Vite Build | success |
| Tauri Configuration | success |
| Ubuntu Python 3.11 | success |
| Ubuntu Python 3.12 | success |
| Windows Python 3.12 | `113 tests / OK` |
| MCP Smoke | success |
| Browser Capture Smoke | success |
| Obsidian Plugin Smoke | success |

命令：

```powershell
cd desktop/lingji-control
npm install --no-audit --no-fund
npm run test:smoke
npm run build
```

---

## UI 验收路径

1. 启动 `python run_control_api.py`。
2. 启动桌面前端。
3. 左侧导航应显示原有页面和“环境验收”。
4. 切换页面，确认连接状态不重新创建。
5. 打开“设置”。
6. 搜索设置名称或参数键。
7. 勾选“只显示已修改”。
8. 修改一个值，应显示“等待保存”。
9. 取消未保存修改。
10. 再次修改并保存，应显示“主人已修改”。
11. 使用单项恢复默认。
12. 使用恢复本组默认。

当前 CI 无法代替主人对页面排版和交互的人工截图验收。

---

## 风险

1. 页面移动可能产生导入路径或类型错误，已由 TypeScript 和 Vite 构建验证。
2. 现有 CSS 是全局样式，本阶段不拆 CSS，避免视觉回归扩大。
3. 当前连接轮询仍为 10 秒，P5 WebSocket 前不在 P1 改变。
4. SettingDefinition 新字段为可选，旧后端返回仍兼容。
5. P1 分支堆叠在 PR #4 上，P0-B 验收前不得直接合入最终基线。
6. 推荐值和影响说明只有在后端 Setting Registry 返回对应字段后才显示真实内容；P1 不伪造这些值。

---

## 回滚

本模块没有数据库迁移和后端变更。回滚该分支即可恢复原单文件 UI。Runtime Settings、Vault、任务、备份和验收报告均不受影响。

---

## 当前结论

P1-0 代码和自动 CI 已通过，状态保持 `REVIEW_REQUIRED`，原因：

1. 需要主人对页面排版、导航和设置交互做一次桌面人工验收；
2. P0-B 主人电脑真实环境验收尚未完成；
3. PR #6 仍堆叠在 PR #4 上，不能直接合入最终稳定基线；
4. 完成 P0-B 后需要重新基于 `integration/lingji-v1` 整理并验证。
