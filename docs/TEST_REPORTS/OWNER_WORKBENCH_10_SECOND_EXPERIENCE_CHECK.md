# Owner Workbench 10 秒体验检查

## 目标

用户打开灵机后，应在 10 秒内知道：

- 灵机做了什么；
- 结果是什么；
- 下一步谁负责；
- 自己现在是否需要操作。

数据必须来自统一事实链：

```text
Capture → WorkItem → Outcome → NextAction → Memory/PendingAction
```

禁止静态文案制造工作、数量统计制造待办、路径猜测关联、发现来源冒充接管。

## 自动前置验收

Implementation SHA：`79955a09f42b7eb525fff1f11c454c373df8aa6c`

- [x] 首页展示真实 completed outcome。
- [x] 首页展示真实 running WorkItem。
- [x] 首页展示下一执行者。
- [x] Attention 只从真实候选对象创建 PendingAction。
- [x] Work 页面与 Home 使用同一个 `/api/capture/jobs → ownerWorkFeed` 投影。
- [x] Memory 展示“记住了什么 / 为什么能相信它 / 来源证据”。
- [x] Cmd+K 返回真实 capture/job identity，不提前宣称“已经记住”。
- [x] `owner-10-second-smoke.mjs` 已加入 `npm run test:smoke`。
- [x] Desktop exact-SHA smoke/build PASS。

## 主人真机检查

以下必须在新的同 SHA产品 Artifact 上由主人肉眼确认，自动测试不能代替：

- [ ] 打开首页 10 秒内能说出一项“刚完成/正在做”的真实工作，或明确知道当前没有 WorkItem。
- [ ] 能说出该工作结果和下一执行者。
- [ ] 首页“需要我”的数量与“需要我”页面真实卡片一致。
- [ ] 未形成永久记忆时 UI 不说“已经记住”；形成后能从“记忆”看到正文/摘要与来源证据。
- [ ] “发现工具/来源”不会被理解成“已经授权/接管/执行”。
- [ ] Home、Work、Attention 对同一对象不存在矛盾。

## 自动证据

`79955a09...`：

- tests `32391549495`: PASS
- macOS Desktop Gate `32391549584`: PASS
- acceptance-doc-sync `32391549523`: PASS
- local-execution-handoff `32391549512`: PASS

## 状态

`AUTOMATED_PRECHECK_PASS / PHYSICAL_OWNER_CHECK_PENDING`

本文件不得在主人真机肉眼确认前改成 `PASS`。
