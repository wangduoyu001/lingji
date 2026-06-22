---
title: "AI 工具库看板"
date: 2026-06-22
---

# 🧰 AI 工具库看板

你的 AI 工具收藏总览。点击项目名查看详情，标记你想要尝试的工具。

> **提示**：如果看板显示空白，按 `Ctrl+P` 输入 "Dataview: Refresh all views" 刷新一下

---

## 📊 概览

```dataview
TABLE 
    length(filter(rows, (r) => r.interest = 3)) AS "⭐ 必装",
    length(filter(rows, (r) => r.interest = 2)) AS "🔥 想试",
    length(filter(rows, (r) => r.interest = 1)) AS "👀 观望",
    length(filter(rows, (r) => r.interest = 0)) AS "⏭️ 跳过",
    length(rows) AS "共收录"
FROM #AI工具
WHERE interest
GROUP BY category AS "分类"
SORT category ASC
```

---

## 🚀 推荐尝试（interest >= 2）

```dataview
TABLE 
    interest AS "兴趣",
    status AS "状态",
    usable AS "实用度",
    stars AS "⭐ Stars"
FROM #AI工具
WHERE interest >= 2
SORT interest DESC, stars DESC
```

---

## 📂 AI 编程工具

```dataview
TABLE 
    interest AS "兴趣",
    status AS "状态",
    usable AS "实用度",
    stars AS "⭐ Stars",
    实际用途 AS "适用场景"
FROM #AI工具
WHERE category = "AI编程工具"
SORT interest DESC, stars DESC
```

## AI Agent 框架

```dataview
TABLE 
    interest AS "兴趣",
    status AS "状态",
    usable AS "实用度",
    stars AS "⭐ Stars",
    实际用途 AS "适用场景"
FROM #AI工具
WHERE category = "AI Agent框架"
SORT interest DESC, stars DESC
```

## AI 生产力工具

```dataview
TABLE 
    interest AS "兴趣",
    status AS "状态",
    usable AS "实用度",
    stars AS "⭐ Stars",
    实际用途 AS "适用场景"
FROM #AI工具
WHERE category = "AI生产力工具"
SORT interest DESC, stars DESC
```

## OPC 一人公司

```dataview
TABLE 
    interest AS "兴趣",
    status AS "状态",
    usable AS "实用度",
    stars AS "⭐ Stars",
    实际用途 AS "适用场景"
FROM #AI工具
WHERE category = "OPC一人公司"
SORT interest DESC, stars DESC
```

---

## 📝 最近更新

```dataview
TABLE date AS "记录日期"
FROM #AI工具
SORT date DESC
LIMIT 10
```
