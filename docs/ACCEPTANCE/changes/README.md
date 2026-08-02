# 独立验收变更条目

`CHANGE_ACCEPTANCE_LOG.md` 是历史兼容日志，不再要求所有 PR 修改同一个巨型文件。

新产品变更优先新增一个独立 Markdown：

```text
docs/ACCEPTANCE/changes/YYYY-MM-DD-<task-or-pr>-<slug>.md
```

文件名必须：

- 以 `YYYY-MM-DD-` 开头；
- 只使用字母、数字、点、下划线和连字符；
- 以 `.md` 结尾。

每个条目必须包含：

- 产品分支与 Commit；
- 影响模块和风险；
- 用户可感知变化；
- 数据与安全边界；
- 自动验收；
- 真机验收；
- 主人肉眼确认；
- 回归项；
- 清理与回滚；
- 不在范围；
- 最终报告路径。

同步门禁继续兼容对 `CHANGE_ACCEPTANCE_LOG.md` 的修改，但推荐独立条目，避免多个 PR 同时修改同一文件导致冲突、历史覆盖和无意义重打包。
