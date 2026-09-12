# 实施设计：手机内容捕获（任务③，优先）

> 状态：APPROVED-DESIGN（主人已批准实施）。核心结论：iOS 快捷指令够不到
> Mac 的 127.0.0.1:8766，因此**不开网络端口**，走 iCloud Drive 文件桥——
> 任何网络环境可用、零端口暴露、天然离线兜底。

## 通路

```
手机（抖音/小红书/视频号/浏览器）
  → 分享面板 → iOS 快捷指令"存入灵机"
      （内容 = 分享文本/链接 + 主人一句话笔记 + 可选截图）
  → 写入 iCloud Drive/LingJiInbox/<时间戳>.json
  → [Mac] CaptureInboxWatcher（15 秒轮询）
      → 解析 JSON → capture.submit_share()（复用现有捕获管线）
      → 成功移入 processed/，失败移入 failed/（人工可查）
  → 捕获管线 → 网页正文抓取/OCR → 记忆层 → 脱敏 → 向量化 → 提炼
```

## 组件

1. **LingJiInbox 目录**：`~/Library/Mobile Documents/com~apple~CloudDocs/LingJiInbox/`
   （iCloud Drive 根）。启动时自动创建 `processed/`、`failed/` 子目录。
2. **CaptureInboxWatcher**（runtime 内 daemon，15s 轮询）：
   - 支持 `.json`：`{"text": "...", "url": "...", "note": "...", "source_app": "douyin", "captured_at": "..."}`
   - 支持 `.txt`：整文件视为 text（最简配方）。
   - 调 `CaptureService.submit_share()`（现有统一入口，自动分 text/web/file）。
   - JSON 解析失败 → 移入 failed/（不静默丢）。
3. **iOS 快捷指令配方**（文档提供，主人手机上 2 分钟搭建）：
   【接收 分享面板/文本】→【询问输入：为什么收藏？（可跳过）】→【文本：JSON 组装】
   →【存储文件：iCloud Drive/LingJiInbox/时间戳.json】
4. **电脑上兜底**：手动把文件丢进 LingJiInbox 同样生效。

## 边界与安全

- 端口零暴露：全程不经网络调用灵机。
- 捕获内容入记忆层前过统一脱敏（API Key 等已由管线红线处理）。
- 不自动下载视频本体；只存链接+文本+截图（截图走 OCR）。

## 切片

- P0（本次）：Watcher + 目录引导 + 快捷指令配方文档 + 测试。
- P1：capture source_type 增加 `mobile_share`，UI 捕获中心显示来源计数。
- P2："稍后学习/实操"页签（按 action_type 聚合）。
