# LingJi 历史测试与验收证据入口

本目录保存特定 Commit、分支、Artifact、测试命令或真实机器验收的历史证据。

报告中的 `PASS`、`FAIL`、`BLOCKED`、测试数量、分支和路径只对报告明确绑定的对象有效。历史报告不能覆盖：

- 当前阶段与阻塞：`docs/PROJECT_STATUS.md`；
- 当前本机任务：`docs/ACCEPTANCE/LOCAL_EXECUTION_TASK.md`；
- 当前/最近结果回执：`docs/ACCEPTANCE/LOCAL_EXECUTION_RESULT.md`；
- 当前架构：`docs/ARCHITECTURE.md`；
- 当前代码入口：`docs/MODULES/CODE_MAP.md`。

以下内容不得为“清理文档”而删除或改写结论：

- Owner 验收失败和 `DO NOT RETRY` 证据；
- Artifact、Commit、哈希与远程复读记录；
- Production/Acceptance 隔离与 Secret 边界证据；
- 本机清理回执；
- P0/P1/P2 模块测试报告；
- 当前 SB-0 增量实施记录。

新报告必须写清精确身份、实际执行命令、通过/失败/跳过、未执行范围和限制。测试文件存在或旧 CI 曾通过都不能替代当前树上的新验证。
