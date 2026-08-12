# LingJi 认证凭据与状态同步规范

> 长期架构规则：**Secrets never sync. Secret state syncs.**

## 真值与边界

```text
macOS Keychain / Windows Credential Manager = Secret 唯一存储
lingji_state.db = 可恢复的非敏感认证状态
GitHub = 脱敏、离散、可审计的验收回执
```

禁止 Token、Refresh Token、API Key、Cookie、Authorization Header、密码、Secret 片段或 hash 进入 SQLite、日志、Markdown、JSON evidence、Git 或 PR 评论。Runtime 既有 token 继续由原路径管理，本规范不得破坏 8766 / MCP 的认证链。

## 状态合同

统一状态为 `not_configured`、`credential_present`、`verifying`、`verified`、`expired`、`permission_insufficient`、`invalid`、`error`。

`lingji_state.db` 仅可保存：`provider`、`auth_method`、`state`、`credential_present`、`credential_valid`、`permissions_ok`、`account_bound`、`last_verified_at`、`expires_at`、`last_error_code`、`last_error_at`。

Desktop 与 Autopilot 仅显示“已连接 / 需重新认证 / 权限不足”等结论，不显示凭据文本、长度、路径或请求头。Autopilot 可以检查凭据是否存在和刷新无副作用的验证状态，但不得导出、替换或绕过第三方认证。

## 验收快照

验收快照仅在需要交接时生成，使用 `export_auth_snapshot` 的 allowlist，路径为 `docs/TEST_REPORTS/evidence/LOCAL_AUTH_STATUS_<TASK>.json`。允许字段只包括 provider 的 `credential_present`、`state`、`permissions_ok`，以及顶层任务和计数元数据；禁止先完整 dump 再 redact。

提交与验收前须拒绝 `Authorization:`、`Bearer `、`Basic `、`sk-`、`ghp_`、`gho_`、`ghu_`、`ghs_`、`ghr_`、`access_token`、`refresh_token`、`api_key`、`cookie`、`session` 等疑似秘密。发现任何一项时快照生成与验收必须失败；硬指标是 `secret_export_count = 0`。

CI 只能使用 in-memory fake backend；真实 Keychain / Credential Manager 仅在对应 macOS / Windows 真机验收中验证。两平台必须复用同一状态模型。
