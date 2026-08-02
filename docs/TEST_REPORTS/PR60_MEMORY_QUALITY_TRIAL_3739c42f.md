# PR60-MEMORY-QUALITY-TRIAL-3739C42F 验收报告

## 1. 执行结论

```text
Verdict: FAIL
Merge recommendation: DO NOT MERGE
Product commit: 3739c42ffc44b5524a3231bc2fd7279ae43c11b1
Artifact: lingji-windows-0.1.0-3739c42f
Artifact ID: 8831573426
Report commit: PENDING
```

Day 0 的“一次授权后自动入队并完成”已通过；但运行时报告 Qdrant 嵌入式目录被另一实例占用，语义检索为不可用状态。这违反 MCP 为 SQLite/Qdrant 唯一实时拥有者的硬门禁，故立即停止后续步骤。Codex 真实 MCP 调用亦未执行：发现的 WindowsApps 可执行入口返回 Access Denied，未找到可启动替代命令。

## 2. 身份与环境

| 项目 | 实际 | 结论 |
|---|---|---|
| Product commit | `3739c42ffc44b5524a3231bc2fd7279ae43c11b1` | PASS |
| Artifact / ID | `lingji-windows-0.1.0-3739c42f` / `8831573426` | PASS |
| ZIP SHA256 | `96c106cd2107b6247d53ceaa6305499af9d0c185a0086a2d2cb1020c6246d387` | PASS |
| Installer / portable / Sidecar / manifest / metadata | 与任务单全部匹配 | PASS |
| DataRoot / workspace / binding | 任务隔离根 / `acceptance` / `PR60-3739c42f-DAY0` | PASS |
| Production 数据与真实资料 | 未读取、未写入 | PASS |

## 3. Day 0 测试

### D0-01 启动与绑定

- 方法：覆盖安装到隔离 D 盘目录，以启动契约启动 Desktop；读取认证 Runtime ping 与 Desktop 实际状态。
- 实际：控制服务和 MCP 分别监听本地端口；Desktop 显示精确 commit、验收 workspace、锁定绑定和隔离 DataRoot；Runtime ping 返回相同身份。
- 结论：PASS。

### D0-02 自动发现与一步导入

- 方法：仅在隔离 Downloads 放置有效的合成 ChatGPT 导出、合成 Codex Work Report、无关 JSON 与无关 ZIP。
- 实际：元数据扫描只识别两个支持来源，未暴露绝对路径，正文读取为 0；一次授权合成 ChatGPT 候选后，队列在 1 秒进入 running、2 秒 completed，无第二次提交。
- 结论：PASS。

### D0-03 Qdrant 单一所有权

- 方法：读取 MCP 发布的只读 `memory_status` 快照及 owner 诊断。
- 实际：MCP owner lock 存在，但快照为 `degraded`，向量状态为 `unavailable`，原因码为 `embedded_store_locked`；语义检索不可用。
- 结论：FAIL — `D0-QDRANT-SINGLE-OWNER-CONFLICT`。

### D0-04 真实 Codex MCP

- 方法：执行连接器实时探测。
- 实际：仅发现 WindowsApps 候选，两个候选均为 Access Denied；配置未写入，未发现可启动替代命令，因而未执行 `codex mcp list` 或真实 MCP 调用。
- 结论：NOT_RUN（受 D0-03 P0 失败停止）；阻塞信息为 `D0-CODEX-LAUNCH-BLOCKED`。

## 4. 未执行项目

合成候选批准/拒绝、Windows 重启、Stage 1、Stage 2、真实资料读取和真实资料质量题均未执行。`real_data_authorized = false`。

## 5. 阻塞缺陷

```text
Defect ID: D0-QDRANT-SINGLE-OWNER-CONFLICT
Severity: P0
Affected scope: packaged Sidecar import worker 与 MCP 实时索引所有权
Reproduction: 启动隔离 Artifact，完成一次合成导出导入后读取 MCP memory_status 快照。
Expected: MCP 为唯一 SQLite/Qdrant 实时拥有者；向量状态与检索能力一致。
Actual: embedded_store_locked，语义检索不可用。
Data/security impact: 不可把 degraded Qdrant 状态宣称为可用；继续测试会掩盖索引所有权冲突。
Required fix: 使打包导入工作进程复用 MCP 的唯一索引拥有者或经过受控 IPC 提交，禁止第二个嵌入式 Qdrant 客户端。
Retest scope: 全新 Artifact 的 Day 0、一次授权导入、Qdrant 状态一致性、真实 Codex MCP。
```

## 6. 结论

修复后的 Artifact 解决了此前的队列不消费问题，但当前 P0 索引所有权冲突仍阻止正式验收。PR #60 必须保持 Draft，不得合并到 master。
