# LingJi macOS / Apple Silicon 真机验收协议

> 本文件是 macOS Apple Silicon（含 M5）专项协议，**不是当前任务单**。
>
> 当前是否执行、task_id、产品 Commit、Artifact、哈希、报告路径和任务根，永远以 `docs/ACCEPTANCE/LOCAL_EXECUTION_TASK.md` 为准。任务为 `status: IDLE` 时不得执行任何真机验收。

## 1. 读取顺序

```text
AGENTS.md
→ docs/PROJECT_STATUS.md
→ docs/ACCEPTANCE/README.md
→ docs/ACCEPTANCE/LOCAL_EXECUTION_TASK.md
→ docs/ACCEPTANCE/LOCAL_EXECUTION_RESULT.md
→ 本文件
→ CODEX_ACCEPTANCE_INSTRUCTIONS.md
→ REPORT_TEMPLATE.md
```

历史报告、旧任务文件、PR 评论和聊天摘要只能作为证据，不能覆盖当前任务单。

## 2. 开始前只读盘点

必须记录：

```bash
sw_vers
uname -m
uname -a
python3 -c 'import platform; print(platform.machine())'
spctl --status
pgrep -fl 'LingJi|lingji-core|灵机' || true
lsof -nP -iTCP:8766 -sTCP:LISTEN || true
lsof -nP -iTCP:8767 -sTCP:LISTEN || true
```

硬门禁：

- `uname -m == arm64`；
- 不允许为了验收关闭 Gatekeeper / SIP；
- 只结束确认属于 LingJi 当前任务的精确进程；
- 禁止 `killall python`、`killall node`、`killall codex`、`pkill -f python`；
- 不删除 Production DataRoot、Vault、正式记忆、Codex/Claude/Obsidian/Ollama 配置或归属不明文件。

若任务要求检查既有 App，先盘点 `/Applications/灵机.app`、`/Applications/LingJi.app`、`~/Applications/灵机.app`、`~/Applications/LingJi.app`，记录已有版本、Commit、签名和是否存在多个副本。

## 3. Artifact 与身份

只能使用当前 ACTIVE 任务指定的 Artifact。

必须依次验证：

1. Artifact ID 与任务单一致；
2. ZIP / DMG 哈希与任务单一致；
3. DMG 内 App 的 release metadata 包含精确 40 位产品 Commit；
4. 主程序与 packaged Sidecar 均为 arm64；
5. `codesign --verify --deep --strict` 通过；
6. 安装后 App 的身份仍与任务单精确一致。

短 SHA、版本号、文件名相同或“看起来是同一版”均不能代替精确身份。

已经得到最终 FAIL 的 Artifact 不得重跑。新一轮必须使用新产品 Commit 与新 Artifact。

## 4. 安装与回滚

覆盖安装必须采用 whole-bundle 替换：

```text
记录旧 App
→ 整体移动到任务根备份
→ 完整复制新 App
→ 严格 codesign 验证
```

禁止 overlay copy。

若验收 FAIL：

```text
停止当前任务精确 Runtime
→ 释放任务涉及端口
→ 删除失败 App
→ 整体恢复旧 App 备份
→ 复核签名
→ 保存最小失败证据
```

若 PASS：按任务单保留新 App，并在远程报告确认后删除临时备份。

## 5. 数据物理隔离

所有 Acceptance Runtime 数据必须进入当前任务单指定的 task-scoped root。

至少覆盖：

- SQLite；
- Qdrant；
- logs；
- raw；
- vault/fixture；
- backup；
- runtime state；
- token / credential state 的非 Secret 部分。

不得把本轮验收数据散落到 Desktop、Documents、Downloads、Production DataRoot 或其他任务根外目录。

若任务开始前发现归属不明的历史 Acceptance 目录，不擅自删除，记录为环境问题并按任务规则处理。

## 6. Secret 与认证状态

强制边界：

```text
Credential Secret -> macOS Keychain / 系统安全凭据存储
UI / 日志 / 报告 -> 脱敏 AuthStatus
公开证据 -> allowlist 字段
secret_export_count -> 0
```

Token、Cookie、Authorization Header、Secret 长度、Secret 文件路径、私人绝对路径不得进入 UI、Markdown、JSON、日志或 Git 证据。

Provider 未配置时可以显示未配置，不得伪造 verified。

## 7. Runtime 生命周期

每个需要验证生命周期的任务至少完成：

```text
启动
→ authenticated health PASS
→ 记录当前实例 / Sidecar PID
→ 精确 stop
→ state 文件消失
→ 记录 PID 退出
→ 监听端口释放
```

若任务要求重启回归，再以同一任务根完成第二次启动与停止。

禁止仅凭 state 文件消失判断 Runtime 已退出，也禁止把全局 kill 当正常成功路径。

## 8. UI 与主人观察

所有 UI 验收先由代理自动完成可自动证明的部分，再让主人只判断机器无法可靠自动证明的体验。

至少关注：

- 首次打开是否无需理解底层技术配置；
- 首页是否明确说明系统已经自动做了什么、正在做什么、失败/重试与下一步；
- 是否把真正需要主人决定的事项置顶；
- 关键新功能是否在首屏与日常路径上形成明显可感知差异；
- 信息层级是否把技术指标下沉到高级诊断；
- 窗口恢复、菜单入口等交互是否真的可见且有效；
- 记忆/自动化进度不得用虚构“准确率”或无来源统计冒充真实进展。

主人明确判定不合格时必须 FAIL，自动测试不能覆盖主观产品体验结论。

## 9. PASS / FAIL

只有当前任务规定的所有 P0/P1 项、技术门禁、主人观察、远程报告和清理全部通过才允许 PASS。

任一关键项失败：

```text
verdict: FAIL
merge: DO NOT MERGE
不在验收分支修产品
不重跑当前失败 Artifact
恢复旧 App / 配置（任务要求时）
保留最小证据
```

未执行的项目必须写 `NOT_TESTED`，不得推断为 PASS。

## 10. 报告、远程复读与清理

最终至少提交：

- Markdown 验收报告；
- 脱敏公开摘要；
- 哈希清单；
- `LOCAL_EXECUTION_RESULT.md`。

第一次 push 后必须从远程重新确认：分支、报告 Commit、报告、证据、结果回执和 PR 评论均可读取。

随后完成当前任务临时目录、Artifact、解压、普通日志、截图、fixture、checkpoint、临时配置和备份的安全清理，再更新回执并再次远程复读。

产品 Artifact 对应的产品 Head 固定后，验收报告必须提交到独立 `acceptance/*` 分支，不能为了补报告移动产品 Commit。
