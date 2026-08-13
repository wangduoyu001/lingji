# PR #88 最终 Artifact 收口

## 任务目标

让 macOS、Windows、P0、全量 tests 与治理门禁绑定同一个最终产品 Commit，并在 M5 复验前完成产品树卫生检查。

## 已验证检查点

- `470ffd3e7802caeb13cc0e539423a81d6170674d` 的 macOS Desktop Gate 已完整通过最终 DMG 首启、二启、真实退出和卸载验证。
- Windows graceful managed-stop 已在前序候选通过。
- 开发期隐藏 staging marker 已从产品树删除。

## 最终要求

- 最终 Mac 与 Windows Artifact 必须来自同一个后续产品 Commit。
- 最终六条门禁全部 PASS 后再锁 Artifact。
- Artifact 下载后独立核验 ZIP、DMG/NSIS 哈希和内部 Commit。
- PR #88 在真实 M5 复验前保持 Draft，不合并。

## 回滚

本收口步骤不改变 Runtime 行为；若最终门禁异常，只回滚共同触发与发包治理变更，不回退已经验证通过的 Sidecar graceful shutdown、数据隔离和 macOS 三重退出合同。
