# Owner Autopilot UI Phase 2 实施与验收报告

日期：2026-08-11
分支：`feature/owner-autopilot-ui-codexpp`
基线：`fdaeaad4882ea80645083a70a1a6970421f9a348`
状态：实现完成，等待 GitHub 全量 CI 与新 M5 真机体验复验。

## 目标

继续收敛灵机桌面端的主人交互。参考 Codex++ 的 silent launcher / manager、Doctor、Repair、Watcher 思路，但不复制其注入架构：日常状态由后台自行扫描、诊断、重试和恢复；只有权限、永久记忆、删除或重建等不可逆操作才进入主人决策区。

## 本轮变化

1. 首页把“系统异常”与“主人决策”拆开：技术异常显示为后台处理状态，不再计入“需要你决定”。
2. 自动发现区域从多块统计卡压缩为一行来源摘要；详细来源、安全边界和手动导入默认折叠。
3. 自动发现结果会把“等待读取授权”的来源数量回传首页，成为真实主人决策计数。
4. 当前工作区域压缩为项目、Codex 工作记录和必要的记忆审核提示；分支、检查点、索引等信息默认折叠。
5. “需要你决定”页面新增 ChatGPT/Codex 导入授权，并把向量 Collection 重建明确归类为不可逆决策。
6. 失败任务、健康错误、低磁盘等技术问题移入“系统异常与自动处理”，不再冒充主人决策。

## 安全边界

- 未改变 Runtime、Qdrant、SQLite、MCP、Sidecar 所有权和生命周期。
- 自动发现仍只读取已知位置与文件元数据。
- 未授权前不读取真实 ChatGPT/Codex 导出正文。
- 不自动批准永久记忆。
- 不自动删除或重建向量 Collection。
- 不为 macOS 创建独立业务逻辑；Windows/macOS 继续共享同一前端和 Python 核心。

## 本地静态验证

- TypeScript `transpileModule`：4 个修改 TSX 文件全部 PASS。
- Node `--check`：2 个修改 smoke 脚本 PASS。

## GitHub 验收门禁

本提交推送后必须重新通过：

- `tests`
- `P0 Windows Gate`
- `Windows Desktop Release Baseline`
- `macOS Desktop Gate`
- `acceptance-doc-sync`
- `local-execution-handoff`

任何一项失败均保持 PR #88 Draft，不进入合并或 M5 主人体验结论。

## M5 真机重点

1. 首页第一屏不应再出现四块自动发现统计卡。
2. 用户应能明确区分“灵机自己处理的异常”和“必须由我决定”。
3. 发现 ChatGPT/Codex 导出候选时，只出现一个明确授权动作。
4. 无主人决策时，即使后台存在技术异常，也应明确显示“现在不用做决定”。
5. Codex 工作记录仍应保持来源解释，不得退回“项目对话 / Session 数字”式含糊表达。
