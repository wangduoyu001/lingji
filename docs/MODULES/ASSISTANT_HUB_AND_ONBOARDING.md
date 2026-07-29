# AI 助手中心与首次使用引导

状态：PR #56 开发与验收中

## 1. 目标

让第一次接触灵机的用户，不阅读源码、不理解 Runtime、Qdrant 或 Extraction，也能完成：

```text
扫描 AI 工具
→ 导入已有资料
→ 查看处理进度
→ 审核永久记忆
```

UI 不得把“检测到安装目录”显示成“已连接”或“已同步”。

## 2. 代码入口

后端：

```text
src/assistant_hub/discovery.py
src/control/capture_api.py
```

Desktop：

```text
desktop/lingji-control/src/pages/AssistantHubPage.tsx
desktop/lingji-control/src/pages/AssistantHubPage.css
desktop/lingji-control/src/pages/OverviewPage.tsx
desktop/lingji-control/src/components/PageGuide.tsx
desktop/lingji-control/src/components/UsageGuideDrawer.tsx
```

测试：

```text
tests/test_assistant_hub_discovery.py
tests/test_assistant_hub_api.py
desktop/lingji-control/scripts/assistant-hub-smoke.mjs
```

## 3. 架构边界

唯一正式链路：

```text
Tauri Desktop
→ authenticated 127.0.0.1:8766
→ Assistant discovery / existing Capture API
→ existing Extraction Queue
→ existing Adapters
→ Raw / Structured Read Model / Memory candidates
→ Human Memory Review
```

没有新增：

- 第二套 API；
- 第二套队列；
- 第二套导入数据库；
- 第二套永久记忆事实源；
- 后台自动 Core Memory 写入。

## 4. 当前能力矩阵

| 工具 | 扫描 | 文件导入 | 自动同步 | 说明 |
|---|---:|---:|---:|---|
| ChatGPT | 手动导出 | 可用 | 不可用 | 支持官方 ZIP/JSON Export |
| Codex | 可用 | Codex Report 可用 | 需正式 Connector | 已有项目、Session 和结构化读取能力 |
| Claude Code | 可用 | 规划中 | 规划中 | 检测 `~/.claude` 和用户记忆文件元数据 |
| WorkBuddy | 安装检测 | 规划中 | 规划中 | 不猜测未公开的会话数据库位置 |

## 5. 安全扫描合同

扫描器只允许：

- 检查固定候选目录是否存在；
- 统计允许扩展名的文件数量；
- 读取文件大小或修改时间等元数据；
- 返回脱敏路径。

扫描器禁止：

- 读取聊天正文；
- 读取 Token、密码、Cookie 或浏览器登录态；
- 跟随符号链接；
- 扫描整块磁盘；
- 返回用户真实绝对路径；
- 自动修改第三方工具配置。

## 6. 状态语义

必须区分：

```text
detection_state
connection_state
import_state
sync_state
```

例如：

```text
Claude Code detection_state = detected
Claude Code import_state = planned
```

不能因此显示“Claude 已连接”。

## 7. 导入合同

当前可用导入：

```text
ChatGPT Export
→ source_type=chatgpt_export
→ adapter_name=chatgpt_export

Codex Report
→ source_type=codex_report
→ adapter_name=codex_work_report
```

两者都调用现有：

```text
POST /api/capture/file
```

并且：

- `process_later=true`；
- 默认 `privacy=private`；
- 使用现有幂等、队列、重试与审计；
- 导入成功只代表进入处理链，不代表已经成为永久记忆。

## 8. 永久记忆合同

```text
导入资料
→ 原始来源与结构化索引
→ 候选记忆
→ 主人审核
→ 正式永久记忆
```

强制规则：

- `automatic_core_memory_write=false`；
- `review_required_for_permanent_memory=true`；
- AI 可以生成候选，不能替主人批准；
- UI 必须持续显示这条边界。

## 9. 后续扩展方式

Claude Code、WorkBuddy 和其他 AI 必须新增正式 Adapter/Connector，而不是把目录遍历逻辑塞进 UI。

新增工具时至少交付：

1. 稳定来源合同；
2. 安全发现规则；
3. 导出或实时 Connector；
4. 幂等键；
5. Agent Scope；
6. 隐私设置；
7. 单元、集成和 Desktop Smoke；
8. Markdown 测试报告。

## 10. 回滚

回滚本模块不会影响已有 Capture、Codex Workspace、Memory Review 或 Runtime 生命周期。

移除顺序：

```text
Desktop AssistantHub 路由
→ assistant scan API
→ src/assistant_hub
```

已导入的原始资料和候选记忆继续由现有正式链路管理。
