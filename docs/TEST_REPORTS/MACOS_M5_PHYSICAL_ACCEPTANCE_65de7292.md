# PR #88 macOS M5 真机验收报告

## 1. 当前结论

```text
Verdict: PENDING
Merge recommendation: DO NOT MERGE YET
Product commit: 65de729228b200869b118fd9c0798af6ad658bca
Artifact: lingji-macos-arm64 / 灵机_0.1.0_aarch64.dmg
Artifact ID: 9213728587
Report branch: acceptance/macos-m5-physical-acceptance-65de7292
```

本报告先固定被测身份和已完成的远程预检。M5 真机尚未进行 whole-bundle 安装、启动、主人肉眼确认、退出和清理，故不得写为 PASS。

## 2. 产品与 Artifact 身份预检

| 项目 | 预期 | 实际 | 结论 |
|---|---|---|---|
| Repository | `wangduoyu001/lingji` | `wangduoyu001/lingji` | PASS |
| PR | `#88` | `#88`（保持 Draft） | PASS |
| Product Commit | `65de729228b200869b118fd9c0798af6ad658bca` | 同左 | PASS |
| macOS Gate | `31786165138` | success @ `65de729` | PASS |
| Artifact ID | `9213728587` | `9213728587` | PASS |
| Artifact archive SHA256 | `cf288e34bc8510540397489df9661fa72f8f4c4ec12ecfae14596a353e13ffeaa0` | GitHub artifact digest 一致 | PASS |
| DMG SHA256 | `4666b0cda78baa81fc9150254f406f4c91faed520a2df850e4c8f52d2a1ff354` | 本地独立计算一致 | PASS |
| DMG size | `46311297` bytes | 本地独立读取一致 | PASS |
| Release Metadata Commit | 精确产品 Commit | 精确一致 | PASS |
| 主程序签名合同 | `codesign --verify --deep --strict` | 已对挂载 DMG 内 App 通过 | PASS |

## 3. CI 与治理门禁

| 检查 | Commit | 结果 |
|---|---|---|
| macOS Desktop Gate `31786165138` | `65de729` | PASS |
| P0 Windows Gate `31786165020` | `65de729` | PASS |
| Windows Desktop Release Baseline `31786165341` | `65de729` | PASS |
| tests `31786135735` | `65de729` | PASS |
| acceptance-doc-sync `31786135745` | `65de729` | PASS |
| local-execution-handoff `31786135834` | `65de729` | PASS |

## 4. 仍待完成的 M5 真机项目

- [ ] 环境与正式数据的只读盘点。
- [ ] whole-bundle replace、签名复验和失败回滚演练。
- [ ] task-scoped `LINGJI_ACCEPTANCE_DATA_ROOT` 下首次启动、8766 连通和二次启动。
- [ ] 自动资料目录、首页清晰度、自动接管与授权边界的主人肉眼确认。
- [ ] Runtime / Sidecar / 8766 / 8767 正常退出、无孤儿进程与 DMG 卸载。
- [ ] 正式数据污染检查、临时根清理、报告 Commit 推送和远程复读。

## 5. 约束

- 执行入口：`docs/ACCEPTANCE/MACOS_M5_LOCAL_EXECUTION_TASK.md`。
- 不得使用任何旧 Artifact 或以 CI 成功替代 M5 真机结论。
- 仅在任务单规定的全部项目通过、主人确认完成、清理与远程复读完成后，才可把 Verdict 改为 `PASS`。
