# LingJi 未来开发 Backlog

> Updated: 2026-08-22
> Status: FUTURE BACKLOG ONLY
> Formal branch: `master`
> Current execution authority: `docs/PROJECT_STATUS.md`
> Architecture authority: `docs/ARCHITECTURE.md`
> Acceptance authority: `docs/ACCEPTANCE/README.md`

## 0. 本文职责

本文只保存**尚未进入当前执行阶段的未来需求**，不维护当前完成率、当前分支、当前 Commit、当前 CI 或当前开发顺序。

当前正在做什么，唯一看 `docs/PROJECT_STATUS.md`。

硬规则：

1. 当前 Phase 1 是“第二大脑完整闭环与验收”。
2. Phase 1 未取得最终 PASS 前，不启动机会面板产品开发。
3. 机会系统现有代码可以做必要回归修复，但不得扩展页面、评分体系、数据模型或自动化产品能力。
4. 本文中的项目只有被 `PROJECT_STATUS.md` 提升为当前阶段后才允许进入正式开发。
5. 已实现的基础能力不再以 `[ ]` 形式伪装成未开发任务。

---

# 1. 当前 Phase 1 的边界说明

Phase 1 的详细任务不在本文重复维护。它包含完整第二大脑所需的：

- 单一永久记忆权威：Obsidian Vault + Git；
- Capture / Extraction / Source / Conversation / Message 真实来源链；
- WorkItem / ExecutionEvent / Outcome / PendingAction 真实工作事实链；
- Memory lifecycle、候选、主人审核、Core / supersede 等正式行为；
- `lingji_memory.db` + Qdrant + HybridRetriever + Embedding 的真实检索链；
- MemoryGateway / Context Pack / MCP / AI 权限统一访问；
- Obsidian 正式集成；
- Tauri 唯一 Desktop 中 Home / Work / Attention / Capture / Memory / Diagnostics 的一致投影；
- Production / Acceptance 隔离、Sidecar、双平台构建和真实验收。

以下基础已经存在，不再作为未来 Backlog 重新开发：

- `src/` 长期主线；
- `desktop/lingji-control/` 唯一正式 UI；
- Qdrant semantic provider 基础；
- Embedding provider / model-center 基础；
- Source / Conversation / Message read model；
- Capture / Extraction 基础；
- Memory Inspector 基础；
- Memory review / lifecycle 基础；
- MCP / Context Pack 基础；
- Obsidian CLI 正式迁移；
- Windows Sidecar / Tauri 发布基础。

这些能力是否“产品完成”仍由 Phase 1 端到端验收决定，不能因为代码存在就自动标记产品 PASS。

---

# 2. Phase 2：机会面板 / Opportunity Center

> Gate: **只有 Phase 1 第二大脑最终验收 PASS 后才能开始。**

Phase 2 是第二大脑之后的第一产品阶段，不允许被每日简报、LLM Router、外部搜索或其他功能插队。

## 2.1 先复用，不重写现有机会系统

现有入口包括 `src/opp_generator.py`、`src/opportunities/` 及相关旧机会能力。

进入 Phase 2 后第一步必须先审计：

- 哪些机会数据模型仍有效；
- 哪些评分逻辑仍有效；
- 哪些字段只是旧 PEMIS 遗留；
- 哪些流程已经能写入 Vault / state；
- 哪些 UI / dashboard 属于旧实现，不能直接复活成第二套产品；
- 如何让机会发现和验证过程进入统一 Work Fact 链。

禁止为了“做新机会面板”复制一套新 scheduler、数据库、任务系统或第二套 UI。

## 2.2 Opportunity Score 2.0

重新定义面向真实变现的评分，而不是新闻热度分：

- 市场需求强度；
- 明确购买意图；
- 痛点强度；
- 竞品收入模式；
- 获客渠道清晰度；
- 最小验证成本；
- 可自动化程度；
- 可收费性；
- 可复制性；
- 时间窗口；
- 平台 / 法律 / 账户风险；
- 与主人现有能力和资源匹配度。

普通 AI 新闻默认不进入机会池。没有真实需求、付费信号或可验证动作的内容只能作为情报来源。

## 2.3 机会对象合同

至少支持：

- opportunity_id；
- source / evidence；
- problem / target_customer；
- demand_strength；
- purchase_intent；
- competitor_revenue_model；
- acquisition_channel；
- validation_action；
- validation_cost；
- expected_time_to_signal；
- risk；
- score + score_explanation；
- status；
- owner_feedback；
- actual_conversion；
- actual_revenue；
- next_action + actor；
- linked_work_id。

所有关键判断必须可回到来源证据。

## 2.4 最小验证闭环

机会不能停在“看起来能赚钱”。每条进入候选池的机会都必须能形成：

```text
发现
-> 证据
-> 评分
-> 最小验证动作
-> WorkItem
-> 执行 / 主人确认
-> 结果
-> 是否继续
-> 实际转化 / 收入
```

失败机会也要保留验证结果，避免系统重复推荐同一种已经证伪的路子。

## 2.5 Opportunity Center UI

只在 Tauri 主应用中开发。

第一版页面必须回答：

1. 今天最值得看的机会是什么？
2. 为什么值得看？
3. 证据是什么？
4. 验证成本和风险是什么？
5. 灵机已经自动做了什么？
6. 哪一步真的需要主人？
7. 历史验证结果和实际收入如何？

页面不得展示没有后端证据的“高分”“热门”“预计收益”。

## 2.6 Phase 2 验收

至少证明：

- 同一机会在 Source / Work / Opportunity UI 中 ID 和状态一致；
- 评分可解释且有来源；
- PendingAction 只在确需主人决定时出现；
- 验证动作可产生真实 Outcome；
- 失败和低分机会不会被伪装成成功；
- Opportunity Center 不建立第二事实源；
- Production / Acceptance 隔离不被破坏；
- focused + full + release 门禁通过；
- 主人能在真机上理解机会、证据、成本、下一步和实际结果。

---

# 3. Phase 3：主动情报与每日简报

Phase 2 稳定后再进入。

候选方向：

- 每日 AI / 自媒体 / 电商 / 跨境 / 模型 / 工具变化简报；
- 重要平台规则与 API 变化；
- 与主人项目相关的风险、机会和行动建议；
- 周度回顾：哪些机会被验证、哪些失败、哪些产生收入；
- 简报只作为来源和情报，不直接写 Core Memory；
- 值得长期沉淀的内容走正式 Memory candidate / owner review。

不要创建第二套 `DAILY_BRIEF` 权威状态系统。简报本质上是来源对象和可检索产物。

---

# 4. Phase 4：外部搜索与工具编排

候选方向：

- MCP 外部工具权限与诊断增强；
- Web / GitHub / 本地文件等搜索工具统一接入；
- AnySearch 或同类工具只能作为可替换 Provider 候选，不能成为架构硬依赖；
- 搜索结果进入 LingJi 后必须记录来源、时间、去重和可信度；
- 外部搜索不得直接写入 Core Memory 或 Opportunity 结论。

---

# 5. Phase 5：模型能力矩阵与 LLM Router

在第二大脑和机会闭环都稳定以后再做自动路由。

候选能力：

- model capability matrix；
- coding / writing / vision / reasoning / context / speed / cost / local_support；
- `last_verified` 和真实基准来源；
- 云端 / 本地模型混合路由；
- 成本上限；
- 失败降级；
- fallback；
- 任务类型路由；
- 主人可覆盖自动选择。

模型能力不能靠长期手写印象，必须有可更新证据。

---

# 6. Phase 6：跨项目 Context 接口

LingJi 可以向其他项目提供：

- Context Pack；
- 项目记忆检索；
- 工具 / 模型情报；
- 商业机会和平台风险提示；
- 工作事实与结果摘要。

LingJi 不实现其他项目的内部业务数据结构。

例如 AI 导演系统内部的 Story Beat、Shot Schema、资产锁定、视频 Provider、QC、自动返修、ComfyUI 执行层等，仍属于对应项目仓库。

---

# 7. Backlog 晋级规则

未来任何功能从本文进入正式开发前必须满足：

1. 前一 Phase 的规定验收已经 PASS；
2. `PROJECT_STATUS.md` 明确把它提升为当前阶段；
3. 审计现有代码，禁止重复实现；
4. 在 `docs/ACCEPTANCE/CHANGE_ACCEPTANCE_LOG.md` 定义变化级验收；
5. 明确数据权威、Work Fact、API、UI、隐私和回滚边界；
6. focused 测试先行；
7. 不创建第二个当前计划文档。

本文永远只是 Backlog。它不能覆盖 `PROJECT_STATUS.md`、`ARCHITECTURE.md` 或 `docs/ACCEPTANCE/`。