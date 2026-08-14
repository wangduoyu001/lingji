# PR #88 macOS M5 真机验收报告

## 1. 当前结论

```text
Verdict: FAIL
Merge recommendation: DO NOT MERGE
Product commit: 65de729228b200869b118fd9c0798af6ad658bca
Artifact: lingji-macos-arm64 / 灵机_0.1.0_aarch64.dmg
Artifact ID: 9213728587
Report branch: acceptance/macos-m5-physical-acceptance-65de7292
```

本报告已完成首次 M5 本机执行。Artifact 身份、整包替换、签名、隔离启动和本地 API 均通过；但主人确认主窗口容易丢失且无法找回，随后验收观察工具触发了一次无 task-scoped 环境的正常启动并创建新的 Production 根目录。该 Artifact 不得继续验收或合并。

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

## 4. M5 真机执行结果

- [x] 环境盘点：原生 arm64、Gatekeeper 开启、端口空闲、验收前 `Documents/acceptance` 不存在。
- [x] Artifact：DMG 哈希、挂载、arm64 主程序/Sidecar、签名和内部 Commit 全部通过。
- [x] 安装：whole-bundle replace 与安装后 `codesign --verify --deep --strict` 通过；原 App 已保留为任务专属备份。
- [x] 隔离首启：Runtime、SQLite、Qdrant、日志和 Vault 均位于 task-scoped root；8766 仅监听 `127.0.0.1`。
- [x] 自动资料目录：正常首启不要求主人选择目录。
- [x] 首页、正在做什么、需要我决定和高级工具可打开；无主人事项时能显示“暂时不需要你决定”。
- [x] 旧 Runtime 已正常退出，8766/8767 已释放。
- [ ] task-scoped root 清理：保留至失败报告远程复读后执行。

## 5. 阻塞缺陷

### M5-WINDOW-001 · P1 · 主窗口丢失后没有找回入口

- 复现：将部分页面或主窗口移出可见区域后，主人无法在界面中找到并恢复窗口。
- 预期：有固定、容易发现的入口将主窗口取消最小化、显示、居中和置前。
- 实际：产品仅配置首次 `center`，没有后续找回动作。
- 主人观察：FAIL。
- 修复：产品提交 `661ae4d286fecbc90b2e815479dbb7d0f94d4062` 新增 macOS 菜单栏“找回主窗口”；必须由新 Artifact 重新真机验证。

### M5-ISOLATION-002 · P0 · 验收观察过程创建新的 Production 根目录

- 复现：task-scoped App 退出后，外部窗口观察工具按普通启动路径再次打开 App。
- 预期：验收期间不得创建新的 Production 根目录。
- 实际：验收前不存在的 Production 根目录被创建；随后已正常退出该实例并释放端口。
- 数据影响：未读取或删除主人既有资料；新根目录未擅自删除，等待主人确认。
- 结论：`production_pollution_count = 1`；本轮 Artifact 验收 FAIL。

## 6. 后续处理

- 新产品 Commit `661ae4d` 正在通过 macOS/Windows/P0/测试门禁。
- 只有新 macOS Artifact 的身份、隔离、窗口找回和主人观察全部通过，才能生成新的 M5 任务单。
- 旧 Artifact `9213728587` 禁止复用。

## 7. 约束

- 执行入口：`docs/ACCEPTANCE/MACOS_M5_LOCAL_EXECUTION_TASK.md`。
- 不得使用任何旧 Artifact 或以 CI 成功替代 M5 真机结论。
- 仅在任务单规定的全部项目通过、主人确认完成、清理与远程复读完成后，才可把 Verdict 改为 `PASS`。
