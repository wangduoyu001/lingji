# TEST REPORT — 自动记忆晋升管线（AUTO_MEMORY_PROMOTION_PIPELINE）

- 日期：2026-09-22（代码 + 真机验收同日完成）
- 分支/HEAD：`codex/owner-source-intake-mac-repair`，实现 `9a614cf1` + 修复 `4d6b42b0`/`f2a82fa0`/`52033dd9` + 文档提交
- 执行环境：macOS（darwin 25.5.0 arm64）；生产数据根 `~/LingJiAcceptance/osimr-7e7f0707/app-data/production`
- 最终装机：`/Applications/灵机.app` sidecar SHA-256 `6435ef10…`（182 运行时文件 + 80 个 .so/.dylib 逐个 ad-hoc 重签，`codesign --verify --deep --strict` 通过）
- 结论：**本机验收通过，待主人最终确认**。App 保持打开。

## 自动测试

| 套件 | 结果 |
| --- | --- |
| `tests/test_auto_promotion_pipeline.py`（14 例，含 limit 空转回归） | 14 passed |
| `tests/test_automatic_memory_distillation.py`（17 例，含 3 例饿死回归） | 17 passed |
| `tests/test_memory_lifecycle.py` + `tests/test_automatic_memory_runtime.py` | 通过 |
| `tests/test_observability_api.py` + settings 四件套 | 26 passed |
| `tests/test_auto_review_*` + `tests/test_auto_memory_promotion.py` + gateway | 71 passed |
| `tests/test_packaged_control_api.py` | 18 passed |

合计 166 passed, 0 failed。门禁 `scripts/check_acceptance_sync.py` PASS。

## 真机验收记录（production）

1. **装机**：三轮"构建→覆盖安装→codesign 全量重签→health 验证"迭代（0799ebcd → 9c542d53 → 6435ef10）。每轮 health 均为 degraded 且仅剩已知 ffprobe warning（与装机前基线一致）；`confidence` 列由 distill 首轮自动 ALTER 迁移成功。
2. **开关**：`PATCH /api/settings` 开启 `auto_promote_enabled`，runtime_settings.json 落盘确认；运行中切换 ≤15s 生效。
3. **Evolving 轨**：首轮 5 条旧行（confidence 为空）转 Evolving，原因码 `confidence_missing`；后续 `title_conflict`、`category_not_whitelisted + notification_like + confidence_below_threshold` 等分支真实触发。共 19 个带日期时间线文件，frontmatter（topic/status/confidence/updated/tags）齐全，幂等 marker 就位。
4. **晋升正路**：distill 修复后新行携带模型自评 confidence（首批 8 条：1.0×1、0.9×4、0.8×4）。真实晋升 1 条进 `03-Knowledge/Core-Memory/General/`：frontmatter `memory_tier: core`、`confidence: 0.9`、`proposed_by: lingji-auto`、来源追溯（conversation_id@revision + 模型名）齐全。
5. **审计**：`auto_promotion_decision` 事件 25 条（24 evolving + 1 promoted），`verify_auto_promotion_chain` 校验 True；篡改检测由单测覆盖。
6. **回滚**：关开关后 `run_once` 返回 `status: disabled`，审计事件 25→25 零写入；随后恢复开启（保持主人要的最终态）。
7. **附带修复的实证**：distill 修复前 finished 全部 0.0s 空转、ready 停在 54；修复后单条 9.5-11.5s 真实云端提炼，ready 54→61 并持续增长（549 个从未提炼的会话开始被消化）。

## 验收中发现并修复的回归

| 提交 | 问题 | 修复 |
| --- | --- | --- |
| `4d6b42b0` | 历史 ready 行 message_count 旧口径与实际不符 → 每轮满足候选条件却被秒跳且永不修正 | 秒跳路径无模型调用修正口径 |
| `f2a82fa0` | 秒跳判断 SELECT 漏取 status 列，取不到默认按 ready → superseded 终态行每轮空转占位，**549 个会话从未被提炼**（生产真根因） | 候选查询排除 superseded；真实读取 status 列 |
| `52033dd9` | 晋升管线 limit 截断在已决过滤之前 → 最老已决行占满每轮名额，首轮后 processed 恒 0 | 先过滤已决再截断 limit |

## 限制与已知事项

1. **存量消化规模**：54 条旧行 + 后续新行中未达标者将持续进 Evolving（当前 19 个文件，随管线轮转渐进增长）。这是"未达标不静默丢弃"的设计行为；主人可审阅后删除或整理，git 可回溯。
2. **门槛是确定性规则**：晋升质量取决于提炼模型自评置信度。首批已出现任务性内容（如"验收文档同步任务分配"）达标晋升——若觉得过宽，可在设置页调高"晋升置信度门槛"（如 0.95）或调低"每日自动晋升上限"。
3. 未重跑 2026-09-19 报告的 229 项全量回归；语义去重依赖 bge-m3（生产实测 1 条晋升经过真实嵌入比对）。
4. 旧格式行（confidence 空）按设计永不自动晋升；只有新提炼行参与门槛。

## 回滚

关闭 `auto_promote_enabled`（Desktop 设置页"记忆自动化"组或 `PATCH /api/settings`）。已晋升文件属既有 Core，不做批量删除。应用级回滚：`app-data/rollback-sidecar-20260922-auto-promote/`（上一版 sidecar 三件套，SHA `0b066312…`）。
