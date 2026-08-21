# LingJi 文档清理报告

## 目标

降低 Codex 开发时的上下文噪音，明确权威文档入口，避免 AI 将历史资料误认为当前开发任务。

## 当前检查结论

保留核心入口：

- `AGENTS.md`
- `docs/ARCHITECTURE.md`
- `docs/PROJECT_STATUS.md`
- `docs/MODULES/CODE_MAP.md`
- `docs/ACCEPTANCE/`
- `docs/DEVELOPMENT_RULES.md`
- `docs/CHANGELOG.md`
- `docs/TEST_REPORTS/`

## 已确认问题

1. docs 目录包含较多阶段性报告和专项说明。
2. 部分历史分析文档可能影响 Codex 上下文判断。
3. 当前没有直接删除必要，应先归档，避免丢失架构演进依据。

## 后续整理原则

- 权威文档只保留一个来源。
- 历史方案移动到 archive/。
- 临时分析、重复总结不参与默认开发上下文。
- 不删除架构、验收、测试依据。

## 待执行

- [ ] 完成历史文档分类
- [ ] 建立 docs/archive/
- [ ] 更新 README 文档入口
- [ ] 验证 Codex 最小读取路径
