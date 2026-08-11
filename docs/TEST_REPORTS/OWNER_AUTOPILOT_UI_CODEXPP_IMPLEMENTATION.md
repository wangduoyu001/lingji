# 灵机 Owner Autopilot UI / Codex++ 参考优化实施报告

## 1. 目标

本轮针对 M5 真机验收中的 `M5-UX-001` 和主人补充反馈进行第一阶段修复：

- 功能按钮基本可用，但日常 UI 仍像工程控制台；
- 灵机没有把“自动发现、自动判断、只在关键边界询问主人”作为主体验；
- Codex 页面显示会话数量，但没有解释这些数字的来源和用途；
- 首次启动把 DataRoot、工作空间等技术概念直接暴露给主人。

参考 Codex++ 的产品思路，本轮不复制视觉皮肤，只采用以下交互原则：

```text
能安全扫描的先自动扫描。
能安全判断的先自动判断。
能自动重试和恢复的不要要求主人反复点击。
UI 首先解释“发现了什么 / 正在做什么 / 需要你决定什么”。
技术细节放到高级工具。
读取真实内容、永久记忆和不可逆操作继续要求明确授权。
```

## 2. 实施范围

### 2.1 自动发现

新增只读元数据扫描：

```text
src/assistant_hub/discovery.py
```

自动识别已知位置中的：

- Codex；
- Claude Code；
- WorkBuddy；
- ChatGPT 官方导出能力边界。

扫描只读取路径存在性、文件数量、修改时间等元数据：

- 不读取对话正文；
- 不跟随符号链接；
- 不修改外部 AI 配置；
- 不自动写入永久记忆；
- 本地绝对路径对前端做脱敏。

### 2.2 自动导入候选规划

新增：

```text
src/assistant_hub/imports.py
```

仅扫描：

- `Downloads`；
- `Desktop`；
- LingJi `assistant_hub/import_inbox`。

规则：

- 最大深度 2；
- 最大候选数 20；
- 不跟随符号链接；
- 只识别明确命名的 ChatGPT 导出 ZIP/JSON 和 Codex Work Report JSON；
- 候选阶段不读取正文、不暴露绝对路径；
- 真正读取前必须主人一次明确授权；
- 授权时重新扫描候选，失效候选不能继续使用。

### 2.3 首页自动驾驶界面

新增 `AssistantDiscoveryPanel`，并调整 Overview：

日常首页优先显示：

1. 灵机自动发现了什么；
2. 正在做什么；
3. 哪些事情必须由主人决定；
4. 系统技术细节。

模型、向量、算力、磁盘等工程信息不删除，但折叠到“系统健康细节”。

### 2.4 Codex 工作记录解释

原“项目与对话 / 项目对话 / Session 详情”改为主人可理解的：

```text
Codex 工作记录
工作记录详情
已识别工作记录
```

页面明确说明：

```text
这些是灵机从本机识别出的 Codex Session 工作记录，
不是灵机新建的聊天窗口。
```

工作记录列表每 15 秒自动更新，手工刷新不再作为日常主动作。

### 2.5 首次启动

不修改 Runtime / DataRoot 底层合同，只调整主人界面：

- 默认进入“日常使用”工作空间；
- 主流程只要求“选择一个位置存放灵机资料”；
- Mac 不再出现“非 C 盘”这种 Windows 专属主文案；
- DataRoot、实际路径、验收工作空间等信息移入“高级设置与验收信息”；
- 主要动作改成“开始使用灵机”。

## 3. 未修改范围

本轮刻意不修改：

- Qdrant 所有权；
- SQLite 数据模型；
- Embedding 实现；
- MCP 协议；
- Runtime 生命周期架构；
- macOS / Windows Sidecar 构建链；
- 永久记忆批准规则；
- Production 数据。

因此本轮主要是把已有能力以更自动、更易懂的方式暴露出来，而不是重写灵机核心。

## 4. 本地验证

在提交前执行：

```text
Python py_compile:
PASS

TypeScript transpile syntax:
PASS
- AssistantDiscoveryPanel.tsx
- OverviewPage.tsx
- CodexWorkspacePage.tsx
- RuntimeBoundary.tsx
- navigation.ts

assistant-autopilot-smoke.mjs:
PASS

pytest:
9 passed
- tests/test_assistant_hub_discovery.py
- tests/test_assistant_hub_imports.py
```

## 5. CI 与真机边界

当前本地验证只能证明：

```text
代码可解析
自动发现单元规则通过
新 UI 合同 smoke 通过
```

仍必须通过仓库正式 CI：

```text
Desktop smoke suite
React / TypeScript production build
Python full tests
macOS gate
Windows regression gate
```

并生成新 macOS Artifact 后重新做 M5 主人体验验收，才能关闭 `M5-UX-001`。

## 6. 验收标准

下一版主人打开灵机后应能在不理解技术名词的情况下回答：

```text
灵机发现了什么？
灵机现在正在做什么？
灵机已经自动处理了什么？
现在有什么事情必须由我决定？
```

对于“2 个对话”类数字，必须直接解释来源、对象和用途，不允许只显示技术计数让主人猜测。
