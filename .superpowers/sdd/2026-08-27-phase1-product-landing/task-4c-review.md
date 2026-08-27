# Task 4C 独立只读审查

日期：2026-08-28

审查范围：Task4C bounded Home fact closure

- 触发审查：`f3d70084e8dfb8a07e2fe46f7e1008e11cdf7c2d`
- 产品/测试提交：`4aa0b7841dab76fed5c784008c2449808e3648f2`
- 当前审查基线：`7521f56d46e08920a05fd562ea1cf72cf042e75e`
- Task4C 仅涉及产品提交中的 Home DTO/UI、既有观察 smoke 与渲染 E2E；没有后端、API、队列、CurrentWorkPanel、其他页面、检索/向量、发布或本机任务单变更。

## 结论

- Spec Compliance：`PASS`
- Task Quality：`PASS`
- 最终裁定：`ACCEPT_FOR_TASK5`

未发现 Critical、Important 或 Minor 阻塞项。

## 核验结果

### Home 事实显示

- Home 明确显示 `本次新增`、`本次更新`、`本次跳过`、`本次失败`。
- 后端提供数值时，渲染 fake server 的 `1 / 2 / 3 / 0`，并保持 `本次复用` 为独立指标；没有把 reused 改名为 skipped。
- 后端缺少 `updated` 或 `skipped` 时，两个问题仍显示，值为 `尚未获得`，不虚构 0。
- `queue.running` 缺失时显示 `尚未获得`，不再显示 `后台自动运行`、0 或其他正常状态。
- 已有新增、失败、复用事实显示保持有效。

### 渲染 E2E

`tests/e2e_owner_memory_flow.mjs` 使用 fake authenticated 8766-like server 和本地 Vite/Chrome，实际执行以下路径：

- 首次来源授权、扫描中和扫描完成；
- 从来源页进入 Home/运行状态页并读取本次新增、更新、跳过、失败数值；
- 删除更新/跳过字段后重新读取，确认两项均为 `尚未获得`；
- fake server 缺少 `queue.running` 时确认 live-state 仅显示一个 `尚未获得`；
- 再次返回来源页并继续已有九态来源覆盖。

渲染 E2E 最终输出：`e2e_owner_memory_flow: PASS`。

### 自动验证

在 `desktop/lingji-control` 执行：

```text
npm run build                                      PASS
npm run test:memory-sources                        PASS
npm run test:memory-sources-repair                PASS
npm run test:work-fact                             PASS
npm run test:runtime                               PASS
npm run test:inspector                             PASS
npm exec -- tsx scripts/observation-first-ui-smoke.mjs PASS
npm run test:e2e:memory                            PASS
```

完整 `npm run test:smoke` 在所有本轮新增来源/观察检查通过后，仍于未修改的 `codex-workspace-smoke.mjs` 失败：既有断言要求 `CurrentWorkPanel.tsx` 包含“当前项目”，实际文件不含该文案。该失败属于既有 Work Fact UI 基线，不由 Task4C 引入；本轮没有删除、跳过、削弱或隐藏该失败。

仓库检查：

```text
git diff --check f3d70084e8dfb8a07e2fe46f7e1008e11cdf7c2d..4aa0b7841dab76fed5c784008c2449808e3648f2 PASS
./.venv/bin/python scripts/check_acceptance_sync.py PASS
./.venv/bin/python scripts/check_local_execution_handoff.py PASS
```

工作树在审查报告写入前干净；`LOCAL_EXECUTION_TASK.md` 仍为 `IDLE`。

## 边界与限制

- 未启动真实 8766、Sidecar 或打包 Artifact。
- 未访问 Production/Vault、主人数据或任何第三方 AI 软件。
- 未进行真实安装、窗口肉眼观察或主人验收。
- 本报告不把确定性 UI/build/E2E 结果扩大为发布或 Phase 1 最终验收。

Task4C 在其限定范围内满足要求，可进入 Task5。Task1 质量 runner 与 Task2 scheduler cleanup-state 的既有隔离/阻塞仍按项目状态保留，不被本裁定解除。
