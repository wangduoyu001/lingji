# OWNER_SOURCE_INTAKE_MAC_REPAIR — Mac 技术验收报告

> 报告日期：2026-09-05。执行者：ZCode（GLM）。主人确认：**待定**（App 保持打开中）。

## 1. Executive Verdict

```text
Verdict: PASS (technical) / owner observation PENDING
Merge recommendation: DO NOT MERGE until owner confirmation
Product commit (product/tests head): 234690b89f671e328bd610966af73e74684434bd
Artifact source tree: 460e9011 (product content; 234690b8 adds test-only alignment)
Artifact: 灵机_0.1.0_aarch64.dmg
Report path: docs/TEST_REPORTS/OWNER_SOURCE_INTAKE_MAC_REPAIR.md
```

技术验收通过：packaged 双轮 GREEN、arm64 产物签名/哈希锁定、整包覆盖安装、全新隔离数据根、
真实 UI 全分区遍历、8766 仅 loopback、8765/8767 关闭。主人体验确认尚未给出；确认前不合并、
不启动 Windows、不做结束清理。

## 2. Artifact Identity

| 项目 | 值 |
|---|---|
| DMG SHA-256 | `0e1d75134f4e3087a5fe462e869448068037f352e9200e614c5e47a931103e46` |
| 主程序 lingji-control-center SHA-256 | `f05098871155f979e4c401197147ef581fe318d9583ec9e414aca112fe196dae` |
| sidecar lingji-core SHA-256 | `e0ea69b19c2cae08fd87b4dd33c5f034e544c0b344708fdf5dc3409964941edb` |
| 签名 | codesign --verify --strict OK（ad-hoc，identifier com.lingji.controlcenter） |
| 架构 | 主程序与 sidecar 均 Mach-O arm64 |
| 安装方式 | 整包替换 /Applications/灵机.app（旧包备份见 §5） |

## 3. Packaged Gate（双轮，全新隔离根）

- Round 1：`2 passed, 1 warning`，411.71s。
- Round 2：`2 passed, 1 warning`，410.14s。
- 覆盖十个场景（metadata-only 发现、授权启动扫描、事件/周期摄取、版本 supersede、幂等无重复、
  加速核对、30%/70% 真实 sidecar 崩溃恢复、生命周期、到期撤销、Gateway/Hybrid 检索）。
- 阻断修复（本轮，归因基线 `3471db1a` 同样失败后执行）：
  1. 场景 3 按 Task8E 已发布的 Darwin 周期核对契约分支（watcher 关闭时断言加速核对摄取同一事实，
     30 秒事件 SLA 继续记录为不适用/未满足，不冒充通过）；机制根因含配置 60 秒下限钳制。
  2. 崩溃矩阵 pause 提前至恢复终态确认后，消除 60 秒周期 tick 与 post-drain pause 的竞态
     （该竞态会多产生一个零变化扫描信封）。

## 4. Runtime / Ports / Data Root

- 新候选 sidecar 绑定 `127.0.0.1:8766`（仅 loopback）；8765/8767 无监听。
  本机 AutoClaw.app 以通配方式监听 `*:8766`（主人另一应用，未触碰）；特定绑定优先，未影响本候选。
- 数据根：全新隔离 `/tmp/LingJiAcceptance/osimr-7e7f0707/app-data`（workspace=acceptance）。
  桌面 bootstrap 配置已从旧 TASK8E 根切换并备份原文件。
- 健康真实值：`degraded`（ffmpeg/ollama 两项 warning，环境事实，如实显示）；`/api/brain/status`
  为 `configuration_required`（全新根尚未建索引，预期）；无 Token 访问 401。

## 5. Install / Backup / 既往实例

- 退出旧实例：osascript 正常退出；先前误判测试残留而终止过旧 sidecar（PID 15127）一次，
  旧 App 受监管地自动重启了它（行为本身验证了监管恢复），随后正常退出；如实记录。
- 安装前 /Applications/灵机.app 实为今日早间已安装的 7e7f0707 代构建（其 sidecar 哈希与本轮一致，
  主程序不同），已整包备份至
  `/tmp/LingJiAcceptance/osimr-7e7f0707/installed-app-backup/`（含旧哈希清单）。
- 本轮安装后主程序哈希 `f0509887…`，与备份包不同（含首页事实板等新前端）。

## 6. 真实 UI 遍历（真实机器数据）

- 首页"现在的事实"板（零点击）：记忆来源 5 个逐项状态与最近检查；本机 AI 软件发现 6 个、
  **正在运行：ChatGPT、Codex、ZCode**（真实进程）；模型状态（暂无运行中模型，兼容 0/0）；
  健康三值（自检 尚未获得 / 系统 需要检查 / 记忆 尚未获得——真实降级状态的诚实回退）；
  接收文件夹已就绪。另有"查看全部来源与明细"单一跳转。
- 来源页：Codex 双根真实元数据（451 文件/1.7GB、17 文件，真实 UTC 时间）、Obsidian 已发现、
  ChatGPT 需要确认、Claude 需要确认且无授权按钮（正确拒绝）。
- 本机 AI 软件分区：ChatGPT（支持自动读取/正在运行/版本 26.825.51511/能力标签）、Codex（支持/运行中）、
  Claude、LM Studio、VS Code、ZCode（暂不支持/未运行或运行中如实显示）。
- 模型与进程分区：运行进程 5 行（ChatGPT 64908、Codex×3、ZCode 58084），PID 仅在折叠"高级信息"。
- 官方导出接收文件夹：自动创建、打开/使用此文件夹按钮在位。
- 缺字段一律"尚未获得"，未发现伪造 0 或假成功。

## 7. Known Non-Blocking Notes

- `/api/brain/status` 真实响应无 `self_check` 键，首页"灵机自检"回退为"尚未获得"（诚实回退，
  字段对齐可后续收口）。
- 30 秒事件 SLA（watcher 事件）在 Darwin 周期模式下按 Task8E 设计不适用，维持全局 BLOCKED 记录。
- `test:smoke` 23 脚本套件 Node v24 基线问题沿用历史记录。

## 8. Owner Confirmation

App 与 sidecar 保持打开，等待主人肉眼确认：首页数据是否一眼可读、来源明细是否可信、
本机 AI 软件与进程是否与实际一致。主人确认前：不合并、不 push/PR、不做 Windows、不清理验收证据。
