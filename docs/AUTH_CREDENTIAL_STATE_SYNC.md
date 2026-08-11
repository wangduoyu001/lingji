# LingJi 认证凭据与状态同步规范

> 长期架构规则：**Secrets never sync. Secret state syncs.**
>
> 本文定义 LingJi 在 macOS / Windows 上保存 Token、API Key、Cookie、Refresh Token 等敏感凭据，以及把“认证做到哪一步”安全同步到仓库的统一合同。

## 1. 目标

解决两个问题：

1. 本机已经完成 GitHub / Codex / MCP / 第三方模型等认证，但 ChatGPT、Codex 和仓库无法可靠知道当前进度；
2. 不能为了同步进度而把 Token、Cookie、Authorization Header 或任何可复用秘密写进 Git。

最终链路：

```text
本机安全凭据存储
→ 本机认证验证
→ lingji_state.db 中的非敏感认证状态
→ Desktop / Health / Autopilot
→ 需要验收或交接时导出脱敏快照
→ GitHub acceptance / test report
```

GitHub 是**可审计状态回执**，不是 Secret 仓库，也不是认证实时数据库。

## 2. Secret 唯一边界

以下内容永远不得进入 Git、Markdown、JSON evidence、日志、PR 评论、SQLite 导出或诊断剪贴板：

```text
Access Token
Refresh Token
API Key
Cookie / Session Cookie
Authorization Header
用户名密码
可重放签名材料
Secret 的前后缀片段
Secret hash / fingerprint（默认禁止，除非以后有明确安全需求）
```

目标正式存储：

```text
macOS   → Keychain
Windows → Credential Manager
```

实现时必须复用一个跨平台 `CredentialStore` 抽象；禁止业务模块各自保存 `.env`、JSON、SQLite Secret 或自建第二套凭据库。

现有本地 Runtime Token 若暂时仍由既有安全路径管理，迁移必须保持兼容，不能因为本轮架构调整破坏 8766 / MCP 已通过的认证链。

## 3. 认证状态真值

`lingji_state.db` 只允许保存**非敏感状态**，用于恢复 UI / Autopilot / 验收进度。

统一状态机：

```text
not_configured
credential_present
verifying
verified
expired
permission_insufficient
invalid
error
```

每个 provider 至少支持以下非敏感字段：

```text
provider
auth_method
state
credential_present
credential_valid
permissions_ok
account_bound
last_verified_at
expires_at（仅时间，不含 Token）
last_error_code
last_error_at
```

允许增加 provider-specific 非敏感字段，但不得保存 Secret、Secret 片段或 Authorization 请求内容。

## 4. UI 与 Autopilot

普通主人只看结论：

```text
GitHub：已连接
Codex：已连接
MCP：已验证
OpenAI：需要重新登录
```

不得在普通 UI 展示：

```text
Token 文本
Token 长度
Token 前后几位
Credential 文件路径
Authorization Header
```

Autopilot 可以自动执行：

```text
检测 credential 是否存在
发起无副作用的认证验证
刷新 auth state
发现过期 / 权限不足后给出可理解结论
```

Autopilot 不得：

```text
自动导出 Secret
把 Secret 写入仓库
未经主人授权替换第三方认证
绕过系统权限或登录流程
```

## 5. 仓库同步格式

只有在验收、开发交接、故障报告或显式状态快照时才写入仓库，不做每秒/每分钟 Git 同步。

推荐快照路径：

```text
docs/TEST_REPORTS/evidence/LOCAL_AUTH_STATUS_<TASK_ID>.json
```

示例：

```json
{
  "schema_version": 1,
  "task_id": "PR88-M5-PHASE4-FAILURE-REPAIR-171091FE",
  "generated_at": "2026-08-11T22:20:00+08:00",
  "platform": "macos-arm64",
  "providers": {
    "github": {
      "credential_present": true,
      "state": "verified",
      "permissions_ok": true
    },
    "codex": {
      "credential_present": true,
      "state": "verified"
    },
    "local_control": {
      "credential_present": true,
      "state": "verified"
    }
  },
  "auth_blockers": 0,
  "secret_export_count": 0
}
```

`LOCAL_EXECUTION_RESULT.md` 只记录摘要与快照路径，不复制 Secret。

## 6. 脱敏与泄漏硬门禁

快照生成器必须有 allowlist schema，只序列化明确允许的字段；禁止“先 dump 全对象再 redact”。

提交前至少检查：

```text
Authorization:
Bearer 
Basic 
sk-
ghp_
gho_
ghu_
ghs_
ghr_
access_token
refresh_token
api_key
cookie
session
```

这只是最低关键字集。实现必须同时覆盖 provider 当前支持的真实 Secret 命名。

发现任何可能 Secret：

```text
快照生成 FAIL
Git 提交 FAIL
验收结果不得标记 PASS
```

最终硬指标：

```text
secret_export_count = 0
```

## 7. 测试合同

本功能至少需要：

1. `CredentialStore` 单元测试：读 / 写 / 删除 / 不存在 / 错误映射；测试使用 fake/in-memory backend，不在 CI 写真实系统钥匙串；
2. Auth 状态机测试：present → verifying → verified / expired / invalid / permission_insufficient；
3. Runtime 重启后非敏感状态可恢复；
4. 脱敏快照 allowlist 测试；
5. 构造包含 fake Token、Cookie、Authorization Header 的输入，证明导出器拒绝或完全剔除；
6. 仓库 evidence secret scan 测试；
7. Desktop 只显示认证结论，不显示秘密；
8. Windows / macOS 共享同一状态模型，不创建平台业务分叉。

真实系统 Keychain / Credential Manager 的物理测试只在对应本机验收进行，不要求 CI 接触主人真实 Secret。

## 8. 与当前 M5 修复的关系

PR #88 当前真实 M5 FAIL 的三个阻断仍然是：

```text
M5-IDENTITY-002
M5-UX-003
M5-ISOLATION-002
```

认证状态同步不是第四个失败原因，但作为当前修复周期的**必须完成架构增强**一起落地，因为它直接解决“本机已有 Token / 登录进度无法通过仓库可靠交接”的断层。

本增强不得延迟或弱化三个 M5 根因的关闭，也不得用“认证状态已同步”冒充 M5 真机 PASS。

## 9. 永久原则

```text
Secret 真值：本机安全存储
认证状态真值：lingji_state.db
仓库：脱敏、离散、可审计状态快照
主人：只在登录、授权、权限变化时参与
```

任何未来功能若需要把 Secret 放进 Git 才能工作，应视为架构错误，而不是配置步骤。
