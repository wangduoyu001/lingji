# P2-01 Tauri Vector Center UI Test Report

> Updated（更新时间）: 2026-07-20  
> Formal Branch（正式分支）: `feature/second-brain-memory`  
> Validated Code Commit（已验证代码提交）: `8a4860553edfbb698665c7dcb1f8bfaf3f556eba`  
> Original Development Branch（原开发分支）: `work/p2-01-vector-center-ui`  
> Status（状态）: `MERGED_AND_VALIDATED`  
> Evidence（证据来源）: 本机 Codex 验收汇总、正式分支代码和构建结果

## 1. 任务目标

在唯一正式 Desktop UI（桌面用户界面）`desktop/lingji-control/` 中增加只读 Vector Center（向量中心）。

页面通过 authenticated Local Control API（带认证的本地控制接口）读取 Memory Index（记忆索引）、Embedding Provider（向量嵌入提供器）、Qdrant（向量数据库）和 Vector Coverage（向量覆盖率）状态。

本任务不提供模型切换、Collection（向量集合）创建、重建、删除或生产数据写操作。

## 2. 开发与合并信息

```text
Repository: wangduoyu001/lingji
Original baseline: 9ab3c55074b0e56dac9ac8adccba934627bedd90
Original branch HEAD: 9a81c5be082420800158f2af79b050435ff1da30
Validated formal commit: 8a4860553edfbb698665c7dcb1f8bfaf3f556eba
Merge state: merged into feature/second-brain-memory
```

P2-01 开发时与正式分支分叉，随后完成同步、本机构建和正式分支合并。

未执行 Force Push（强制推送）。

## 3. 修改文件

```text
desktop/lingji-control/package.json
desktop/lingji-control/scripts/ui-modular-smoke.mjs
desktop/lingji-control/scripts/vector-center-smoke.mjs
desktop/lingji-control/src/App.tsx
desktop/lingji-control/src/navigation.ts
desktop/lingji-control/src/types.ts
desktop/lingji-control/src/pages/BrainStatusPage.tsx
desktop/lingji-control/src/pages/VectorCenterPage.tsx
desktop/lingji-control/src/pages/VectorCenterPage.css
docs/TEST_REPORTS/P2_01_VECTOR_CENTER_UI_TEST_REPORT.md
```

统计：

```text
10 files changed
674 insertions
17 deletions
```

未修改 `src/` 后端、Qdrant 数据、Ollama 模型、Vault（知识库目录）或正式生产配置。

## 4. 页面能力

已实现：

1. 导航新增“向量中心”。
2. Memory Index 路径、大小、文档、Chunk（文本分块）、Core Memory（核心记忆）和 Revision（修订号）。
3. Embedding Provider、配置模型、实际模型、备用模型和实际维度。
4. Embedding 请求次数、失败次数和最近错误。
5. Qdrant 模式、Collection、Ready（就绪状态）、向量数量、维度和距离算法。
6. `rebuild_required` 明显警告，但无危险的立即重建按钮。
7. Expected、Indexed、Missing 和 Coverage。
8. 纯 CSS（层叠样式表）覆盖率进度条。
9. 缺失 Chunk ID 默认显示前 20 个并支持展开。
10. live、snapshot、unavailable 和 stale 状态说明。
11. Runtime Warning（运行时警告）。
12. 首次加载、手动刷新和 15 秒自动刷新。
13. 页面切走和标签不可见时停止请求。
14. `Promise.allSettled()` 部分失败降级。
15. 刷新失败保留旧数据。
16. `null` 显示为 `-`，真实零显示为 `0`。
17. 修复 Brain Status 将未知向量数量显示成假零的问题。

`App.tsx` Smoke Test（冒烟测试）计数为 63 行，低于 100 行限制。

## 5. API 合同

页面只通过现有 `LingJiApi.get()` 调用：

```text
GET /api/memory/status
GET /api/vector/status
GET /api/vector/coverage
GET /api/brain/status
```

前三个接口是正式详细数据源。

`/api/brain/status` 只补充顶部一致性信息和 Runtime Warning。

页面没有：

```text
POST
PATCH
Qdrant direct connection（直连）
Ollama direct connection（直连）
SQLite direct connection（直连）
8765
8767
hard-coded local service URL（硬编码本地服务地址）
```

## 6. 错误和刷新合同

四个请求使用 `Promise.allSettled()` 独立处理。

行为：

- 部分接口失败时继续显示成功面板。
- 刷新失败时保留上一次成功数据。
- 401 错误显示后端认证信息，不伪造成功状态。
- 页面卸载时清理 Interval（定时器）和 Visibility Listener（可见性监听器）。
- `inFlight` 防止并发刷新。

## 7. 测试结果

### 7.1 页面专属 Smoke Test

开发阶段执行：

```text
node scripts/vector-center-smoke.mjs
```

结果：

```text
Vector Center smoke passed; App.tsx=63 lines
```

### 7.2 完整本机验证

最终本机 Codex 汇总：

```text
5 项 Smoke Test 通过
npm run build 通过
```

验证范围包括：

- Vector Center 页面装配
- 共享 TypeScript（类型脚本）类型
- 模块化结构检查
- 正式前端 Build（构建）

本报告没有保存完整 Token（令牌）、私人数据或本地绝对路径。

## 8. 数据安全

本任务：

- 不修改 Vault。
- 不修改 `lingji_memory.db`。
- 不创建、删除或重建 Qdrant Collection。
- 不调用生产 Ollama 写操作。
- 不修改生产模型配置。
- 不增加 POST/PATCH 写接口。

## 9. 已知限制

1. 当前页面只读，不支持安全 Collection 重建。
2. 当前不支持 Embedding 模型切换。
3. Runtime Warning 仍通过 `/api/brain/status` 获取。
4. Snapshot（状态快照）时效取决于 Gateway 发布频率。
5. 本报告不证明 `bge-m3` 已成为生产默认模型。
6. Memory Inspector（记忆检查器）尚未实现。

## 10. 最终结论

```text
P2_01_MERGED_AND_VALIDATED
```

P2-01 已合并正式分支，无需再次重复执行同一组本机验证，除非相关 Tauri、API 合同或依赖发生变化。

下一步：P2-03 Structured Read Model（结构化读取模型）。
