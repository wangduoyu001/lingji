# AUDIT_RESPONSE_20260927 验证报告（外部优化审计响应）

- 分支：`codex/owner-source-intake-mac-repair`；任务单：`LOCAL_EXECUTION_TASK.md`（status: ACTIVE）
- 依据：外部优化建议书评审（2026-09-27/28）+ 主人逐项拍板

## 已实现并测试

| 批 | 项 | commit | 验证 |
|---|---|---|---|
| 一 | 挂死恢复+日志归位+证据归档；全量基线 diff（零新增回归）；MCP citation/slim search 契约修复；健康看门狗（SIGTERM→SIGKILL）；提炼 DNS 探针；扫描移出 HTTP 线程池；file_digest；密钥脱敏；Vault git 自动提交 | d67661a6…2f552f0b | 真机 ping 1-5ms；/api/settings 零泄漏；扫描 912ms |
| 二 | 资源收敛：自适应快照节流（大源 124min）、小文件保护 6h、raw 上限 2GiB | addbfef8 | 静止 CPU 1%（前 23-33%） |
| 二 | 看门狗二次修正（首次探活成功才武装，启动期 600s 死限） | 9959148d→6de829d8 | 误杀复现并修复 |
| 三 | 3.2.1 证据独立检索通道 | d188fe24 | 回归 2 例 + 检索扩面 154 过 |
| 三 | 2.2 失败按源聚合 + PendingAction(owner) + /api/work/failures | c81af7e2 | 1,284 次同因失败→1 行；1,291 旧格式行迁移合并 |
| 三 | 4.3 Ollama 拉起 + 796 chunk 缺口→0（fast-path 待命）；Qdrant 双集合核实非冗余 | 运维 | 6 轮回填实测 |
| 三 | 5.2 master 本地 fast-forward 收敛（736 超集，零冲突）；**推送被网络阻断 BLOCKED_PUSH_NETWORK** | 本地 3f0ee2c2 | 性能测试收集正常 |
| 三 | 5.4 卫生：删 work_api.py 死代码、.zcodeignore、移除 stale worktree | c67d4986 | api 导入正常 |
| 四 | ①work_items 历史失败行回溯归并（merged 路线，1,298→3 条） | 8417f44d | 回归 8 例 + 223 过 |
| 四 | ②价值门延伸证据入库（会话级判定+信号保底+可逆归档；库默认关、生产 .env 开） | 2e3a3b46 | 回归 7 例 + 证据扩面全绿 |
| 四 | ③交接门禁修复（任务单 18 字段补齐、RESULT 当前对+旧 RUNNING 收尾） | 本提交 | check_local_execution_handoff: PASS |

## 部署

最终 sidecar SHA 见 LOCAL_EXECUTION_RESULT.md 当前回执更新；生产数据根 `.env` 追加 `VALUE_GATE_EVIDENCE_ENABLED=true`。

## 已知限制

- master 推送待网络恢复（本地已收敛）。
- 挂死微观成因（系统解析器卡死 100 分钟）未钉死，看门狗已把不可用时长约束在 ~90s；下次发生用 sudo py-spy 取证。
- 14 项基线既有失败已修 2，余 12 项按清单排期；Qdrant >20k 点容量决策（Docker/外部）未做。
- 价值门证据层首次全量 sync 会批量归档低价值会话证据（预期 active 证据数大幅下降），属主人拍板的信噪比收敛。

## 第五批：界面重做 + 后台静默（主人 2026-09-28 反馈"界面垃圾看不懂"+ "后台运行不弹窗"）

| 项 | 内容 | 验证 |
|---|---|---|
| 导航瘦身 | 主菜单 6→3 项（首页/记忆库/需要我），时间线等 4 页移入高级诊断抽屉 | 截图确认侧栏 3 项 |
| 首页产品叙事 | 监控面板 → 三段式（记住什么/需要拍板/一行状态），全大白话 | 构建通过+截图 |
| 后台静默 | 主窗口启动不可见（托盘常驻）；移除自动弹出提醒条；点关闭=隐藏回托盘；Dock 点击可唤回 | 启动 0 窗口实测；随机查看路径实测 |
| raw 主动逐出 | 逐出原是采集路径被动行为，超限会无限滞留——每次核对后主动检查超限并逐出 | 代码+测试 |
| 窗口 bug | 点关闭即销毁且 Dock 无法唤回（未处理 Reopen/CloseRequested）→ 两处 Rust 修复 | 截图/行为实测 |

部署：control-center 与 sidecar 均已替换重启；代码推送 master。
