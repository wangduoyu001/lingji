# Owner Workbench 10 秒体验检查

## 目标

用户打开灵机后，应在 10 秒内知道：

- 灵机做了什么
- 结果是什么
- 下一步谁负责

## 当前实现基础

数据必须来自统一事实链：

Capture → WorkItem → Outcome → NextAction → Memory/PendingAction

禁止：

- 使用静态文案制造工作状态
- 使用数量统计制造待办
- 使用路径猜测工作关联

## 验收检查项

- [ ] 首页展示真实完成结果
- [ ] 首页展示真实进行中任务
- [ ] 首页展示下一执行者
- [ ] Attention 仅展示真实 PendingAction
- [ ] Work 页面与 Home 使用同一 WorkItem 投影
- [ ] Memory 展示来源证据

## 状态

IN_PROGRESS
