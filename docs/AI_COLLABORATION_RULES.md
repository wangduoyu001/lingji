# AI_COLLABORATION_RULES.md — AI 协作入口

> Updated: 2026-08-25
> Status: ROUTING GUIDE
> 执行权威：`AGENTS.md`、`docs/DEVELOPMENT_RULES.md`

本文件不再维护独立的开发顺序、分支策略、模型分工或完成条件，避免与仓库当前规则分叉。

AI、Codex 和人工开发者统一遵守：

1. 开始时核对远程默认分支、本地 HEAD、上游和工作区，不把旧验收分支当成当前项目状态。
2. 按 `AGENTS.md` 的最小读取顺序加载上下文，不默认通读或复活旧计划。
3. 当前进度只看 `docs/PROJECT_STATUS.md`；代码入口只看 `docs/MODULES/CODE_MAP.md`。
4. 多代理并行时文件所有权不得重叠；接受结果前重新检查 diff、测试证据和数据边界。
5. 未执行测试不得写成 PASS；子代理的完成声明必须由主代理在最终树上复核。
6. 不覆盖未提交的他人修改，不 force push，不修改 Production、真实 Vault、真实数据库或凭据。
7. 产品变化同步 `docs/ACCEPTANCE/CHANGE_ACCEPTANCE_LOG.md`；历史报告不覆盖当前任务和结果回执。
8. 合并、push、PR、发布和破坏性清理必须按当前任务授权与 `docs/DEVELOPMENT_RULES.md` 执行。

历史协作流程保留在 Git 历史；当前不再读取已删除的上下文文件、旧统一记忆 Roadmap 或旧阶段“下一任务”。
