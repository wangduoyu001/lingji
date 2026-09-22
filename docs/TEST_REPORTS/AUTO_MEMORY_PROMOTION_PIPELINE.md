# TEST REPORT — 自动记忆晋升管线（AUTO_MEMORY_PROMOTION_PIPELINE）

- 日期：2026-09-22
- 分支/HEAD：`codex/owner-source-intake-mac-repair`（含 `43a7786a` 之后的本轮实现提交）
- 执行环境：macOS（darwin 25.5.0 arm64），仓库 worktree 直接运行 `python3 -m pytest`
- 结论：**代码完成，待本机验收**。局部测试全部通过；未做重打包装机与主人开开关真机实测。

## 范围

主人拍板的自动记忆晋升管线 + Evolving 迭代时间线（`docs/ACCEPTANCE/CHANGE_ACCEPTANCE_LOG.md` 同名条目）。实现细节见该条目"实现"段与 `docs/MODULES/CODE_MAP.md` "Owner auto promotion" 段。

## 测试执行记录

| 套件 | 结果 |
| --- | --- |
| `tests/test_auto_promotion_pipeline.py`（新增 13 例） | 13 passed |
| `tests/test_automatic_memory_distillation.py` + `tests/test_memory_lifecycle.py` + `tests/test_automatic_memory_runtime.py` | 34 passed |
| `tests/test_observability_api.py` + `tests/test_runtime_settings.py` + `tests/test_settings_governance.py` + `tests/test_settings_governance_api.py` | 26 passed |
| `tests/test_auto_review_core.py` + `tests/test_auto_review_ai_api.py` + `tests/test_auto_memory_promotion.py` + `tests/test_permanent_memory_gateway.py` | 71 passed |
| `tests/test_packaged_control_api.py` | 18 passed |

合计 162 passed, 0 failed。门禁：`python3 scripts/check_acceptance_sync.py` PASS。

## 新增单测覆盖（对应验收要求）

- 开关关闭=零写入：无审计事件、无 Core/Evolving 文件。
- 晋升正路：达标行经 lifecycle 进入 `Core-Memory/General`，frontmatter `memory_tier: core`，审计 `promoted` 且哈希链可验证。
- 门槛分支：类别不在白名单、置信度低于 0.90、置信度缺失（旧行）、通知类标题 → 均转 Evolving 并带原因码。
- 去重：全文/要点级重复判 `duplicate`（零文件写入）；语义相似度 ≥0.92 判 `duplicate`（测试注入相似度函数）。
- 冲突：同标题不同内容 → Evolving `title_conflict`，既有 Core 不增不改。
- 每日上限：达到上限即 `capped`，不再晋升。
- 幂等与迭代：同 conversation+revision 不重复处理；revision 升级重新评估，达标后晋升并在 Evolving 文件标记 `graduated`。
- 审计链：`verify_auto_promotion_chain` 对真实事件验证通过，篡改任一字段后验证失败。

## 限制与未验证

1. 未重打包装机：生产 sidecar 仍运行 9-22 16:26 的瘦身版（`0b066312…`），不含本管线。
2. 未真机实测开关：主人开启 `auto_promote_enabled` 后的一轮审计/vault/时间线观察待执行。
3. 语义去重在测试中用注入的相似度函数；真机依赖 bge-m3 嵌入，懒加载路径未在真实 Ollama 上验证。
4. 未重跑 2026-09-19 报告中的 229 项全量回归。
5. 生产库既有 54 条 ready 行 confidence 为空，按设计不会自动晋升；只有新提炼行携带置信度。

## 回滚

关闭 `auto_promote_enabled`（Desktop 设置页或 runtime_settings）。已晋升文件属于既有 Core，不做批量删除。
