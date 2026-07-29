# PR #56 AI 助手中心与首次使用闭环实施报告

状态：代码完成，等待 CI 与 Owner 真机验收

## 1. 任务目标

把 PR #56 从“页面说明更清楚”升级为可执行的新手流程：

```text
扫描 AI
→ 导入已有资料
→ 查看处理
→ 审核永久记忆
```

## 2. 修改范围

### 后端

- 新增 `src/assistant_hub/discovery.py`；
- 在现有 `src/control/capture_api.py` 注册认证扫描接口；
- 未新增服务、端口、队列或数据库。

### Desktop

- 新增 `AssistantHubPage`；
- 首页第一步改为“连接与导入”；
- 主导航首页改名为“开始使用”；
- 全局使用说明改为首次设置流程；
- 每页说明增加 AI 连接与导入入口。

### 文档

- 更新快速上手；
- 新增 Assistant Hub 模块文档；
- 新增本报告。

## 3. API 变化

新增认证只读接口：

```text
GET  /api/assistant-hub/status
POST /api/assistant-hub/scan
```

继续复用：

```text
POST /api/capture/file
```

## 4. 当前真实支持状态

### 可直接使用

- ChatGPT Export ZIP/JSON 导入；
- Codex Report JSON 导入；
- Codex、Claude Code、WorkBuddy 安全扫描；
- 导入任务统一队列、去重、重试和审计；
- 导入后人工审核永久记忆。

### 尚未完成

- Claude Code 正文导入 Adapter；
- WorkBuddy 正文导入 Adapter；
- Codex 本地历史目录一键批量导入；
- 第三方 AI 自动实时同步；
- 一键修改第三方 AI 配置；
- 自动 Core Memory 写入。

UI 对这些能力显示 `planned`、`configuration_required` 或 `unavailable`，不得显示为已连接。

## 5. 安全决定

- 只扫描固定候选目录；
- 不读取聊天正文；
- 不跟随符号链接；
- 不返回真实绝对路径；
- 不读取浏览器登录态、Token、密码或 Cookie；
- 不自动修改第三方软件；
- 不自动写入 Core Memory；
- 永久记忆必须主人审核。

## 6. 数据流

```text
AssistantHubPage
→ authenticated 8766 scan API
→ safe metadata discovery

AssistantHubPage import
→ POST /api/capture/file
→ existing CaptureControlService
→ existing ExtractionPipeline / Queue
→ ChatGPTExportAdapter or CodexWorkReportAdapter
→ Raw / Structured Read Model / Candidate Memory
→ Human Memory Review
```

## 7. 测试

新增：

```text
tests/test_assistant_hub_discovery.py
tests/test_assistant_hub_api.py
desktop/lingji-control/scripts/assistant-hub-smoke.mjs
```

更新：

```text
desktop/lingji-control/scripts/run-smoke-suite.mjs
desktop/lingji-control/scripts/guided-usage-smoke.mjs
desktop/lingji-control/scripts/observation-first-ui-smoke.mjs
```

测试覆盖：

- Codex/Claude/WorkBuddy 临时目录发现；
- ChatGPT 手动 Export 状态；
- 路径脱敏；
- 不返回测试正文；
- 不把缺失工具标为 connected；
- 8766 Token 认证；
- Desktop 路由与入口；
- ChatGPT/Codex 导入复用 Capture API；
- UI 明示人工审核与禁止自动 Core Memory。

## 8. 待执行验证

```text
python -m pytest -q tests/test_assistant_hub_discovery.py tests/test_assistant_hub_api.py
cd desktop/lingji-control
npm run test:smoke
npm run build
```

最终还必须通过：

```text
tests workflow
P0 Windows Gate
Windows Desktop Release Baseline
Owner 安装版 UI 验收
```

## 9. Owner 验收标准

第一次接触灵机的用户必须能够：

1. 在首页找到“开始连接 AI”；
2. 理解扫描不会读取账号凭据或聊天正文；
3. 看懂“检测到 / 可导入 / 适配中 / 未检测到”的区别；
4. 导入 ChatGPT Export；
5. 导入 Codex Report；
6. 在活动记录看到导入进度；
7. 理解导入不等于自动永久记忆；
8. 进入人工记忆审核；
9. 不需要开发者解释即可复述完整流程。

缺少任何一项，PR #56 不得标记 PASS。

## 10. 回滚

本模块可独立回滚，不影响 PR #53 Windows 生命周期修复，不修改数据库 Schema，不触碰生产 Vault、Qdrant 或真实 AI 对话。

## 11. 下一步

1. CI 修复与最终锁定；
2. 生成新的 PR #56 Windows 安装包；
3. Owner 真机完成新手流程验收；
4. 验收通过后合并 PR #56；
5. 再启动 Issue #57 Qdrant/Embedding 主线。
