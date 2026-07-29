# LingJi 最终验收报告模板

> 报告必须对应一个精确产品 Commit 和一个精确 Artifact。不得使用模糊版本描述。

# <PR / 任务> Owner + Codex Full Acceptance Report

## 1. Executive Verdict

```text
Verdict: PASS / FAIL / BLOCKED
Merge recommendation: ALLOW / DO NOT MERGE
Product commit:
Artifact:
Artifact ID:
Report commit:
```

简述结论、阻塞缺陷和未覆盖范围。

## 2. Product and Artifact Identity

| 项目 | 预期 | 实际 | 结论 |
|---|---|---|---|
| Repository | | | |
| PR | | | |
| Product Commit | | | |
| Artifact | | | |
| Artifact ID | | | |
| ZIP SHA256 | | | |
| Installer SHA256 | | | |
| Build metadata Commit | | | |

## 3. Change Acceptance Source

- `docs/ACCEPTANCE/CODEX_ACCEPTANCE_INSTRUCTIONS.md` 版本：
- `docs/ACCEPTANCE/CHANGE_ACCEPTANCE_LOG.md` 对应条目：
- 受影响模块：
- 风险等级：
- 明确不在范围：

## 4. Environment Cleanup

记录：

- 旧验收目录是否清理；
- 旧 LingJi 进程是否退出；
- 8766/8767 是否释放；
- 是否使用覆盖安装；
- 是否保留正式 DataRoot、Vault 和用户配置；
- 临时配置副本是否在验证后删除；
- 验收结束是否清理 Artifact、日志、截图和 fixture。

## 5. Environment and Workspace

```text
OS:
LingJi version:
Workspace:
DataRoot: <脱敏>
Vault: <脱敏>
Runtime state:
Runtime managed:
Control port:
MCP port:
```

## 6. CI and Automated Tests

| 测试 | Commit | 结果 | 证据 |
|---|---|---|---|
| Required CI | | | |
| Focused validation | | | |
| Full validation | | | |
| Release validation | | | |
| Change-specific tests | | | |
| Acceptance-doc sync | | | |

## 7. Installation and Upgrade

记录覆盖安装、数据保留、路径保持、版本身份和主人窗口观察。

## 8. Runtime, Processes and Ports

记录 Desktop、Core、MCP 子进程、8766/8767 回环监听、重复进程和孤儿进程检查。

## 9. Desktop and First-Time UX

记录受影响页面、全部可见控件、状态真实性、唯一下一步、错误提示、窄窗口和主人理解结果。

## 10. Workspace, DataRoot and Vault Isolation

记录 Production/Acceptance 隔离、C 盘写入、Vault 保持和测试污染检查。

## 11. Memory and Permanent-Knowledge Boundary

记录候选、人工审核、批准、拒绝、Core Memory 数量和来源审计。

## 12. Capture, Import and Queue

记录合法 fixture、无效 fixture、幂等、队列、失败、重试、来源和清理。

## 13. Retrieval, Embedding and Qdrant

仅在受影响时填写；否则写 `NOT_APPLICABLE`，并说明依据。

## 14. Local Control API and MCP

记录认证、工具列表、真实客户端调用、Token 脱敏和安全边界。

## 15. AI Client Connectors

每个客户端单独列出：

```text
Detected:
Configured:
Live tested:
New session real call:
Candidate submitted:
Rollback:
Reconnect:
Verdict:
```

未安装必须写 `SKIPPED_NOT_INSTALLED`，不得写 PASS。

## 16. Core Restart and Windows Reboot

记录三轮 Core 重启、一次 Windows 重启、重启后恢复和主人黑窗观察。

## 17. Regression Matrix

| 回归项 | 结果 | 证据/说明 |
|---|---|---|
| PowerShell/CMD/黑窗 | | |
| Runtime 未受管 | | |
| 重启不恢复 | | |
| Windows 重启不恢复 | | |
| 重复 Core | | |
| 孤儿 MCP | | |
| C 盘写入 | | |
| Workspace/DataRoot/Vault 丢失 | | |
| 覆盖安装破坏数据 | | |
| UI 按钮无响应 | | |
| 假成功或未知值伪造 | | |
| Token 泄露 | | |
| 自动写 Core Memory | | |
| 回滚破坏用户配置 | | |
| Production 被污染 | | |
| Change log 指定回归项 | | |

## 18. Security and Secret-Redaction Audit

记录：

- Git diff secret scan；
- 公开报告脱敏；
- 私有证据本机保存范围；
- Token/API Key/Authorization 检查；
- 个人绝对路径检查；
- 任意命令和任意路径接口检查。

## 19. Evidence Index and Hashes

仅列脱敏公开证据路径和私有证据包 SHA256。不要上传私有证据包。

## 20. Test Cases

每个测试项使用以下固定格式：

```text
ID:
Name:
Preconditions:
Method:
Expected:
Actual:
Evidence:
Verdict: PASS / FAIL / BLOCKED / NOT_TESTED / SKIPPED_NOT_INSTALLED
```

## 21. Known Non-Blocking Limitations

只列真实存在且不阻止本次交付的限制。

## 22. Blocking Defects

每个阻塞缺陷包含：

```text
Defect ID:
Severity:
Affected scope:
Reproduction:
Expected:
Actual:
Evidence:
Data/security impact:
Required fix:
Retest scope:
```

没有阻塞缺陷时明确写 `None`。

## 23. Final Merge Recommendation

固定格式：

```text
Product commit:
Verdict:
Merge recommendation:
Owner observation complete: YES / NO
Required clients covered:
Skipped clients:
Blocking defects:
Acceptance docs synchronized: YES / NO
Temporary evidence cleaned: YES / NO
```

## 24. Sign-off

```text
Codex executor:
Owner confirmation:
Acceptance date:
Report branch:
Report commit:
```