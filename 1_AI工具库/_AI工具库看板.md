---
title: "AI 工具库看板"
date: 2026-06-22
---

# 🧰 AI 工具库看板

> 你的 AI 工具收藏总览。点击项目名查看详情，标记你想要尝试的工具。

---

## 📊 概览

```dataview
TABLE 
    length(filter(rows, (r) => r.interest = 3)) AS "⭐ 必装",
    length(filter(rows, (r) => r.interest = 2)) AS "🔥 想试",
    length(filter(rows, (r) => r.interest = 1)) AS "👀 观望",
    length(filter(rows, (r) => r.interest = 0)) AS "⏭️ 跳过",
    length(rows) AS "共收录"
FROM "1_AI工具库/AI编程工具" OR "1_AI工具库/AI Agent框架" OR "1_AI工具库/AI生产力工具" OR "1_AI工具库/OPC一人公司"
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
FROM "1_AI工具库/AI编程工具" OR "1_AI工具库/AI Agent框架" OR "1_AI工具库/AI生产力工具" OR "1_AI工具库/OPC一人公司"
WHERE interest >= 2
SORT interest DESC, stars DESC
```

---

## 📂 全部分类

### AI 编程工具

```dataview
TABLE 
    interest AS "兴趣",
    status AS "状态",
    usable AS "实用度",
    stars AS "⭐ Stars",
    实际用途 AS "适用场景"
FROM "1_AI工具库/AI编程工具"
SORT interest DESC, stars DESC
```

### AI Agent 框架

```dataview
TABLE 
    interest AS "兴趣",
    status AS "状态",
    usable AS "实用度",
    stars AS "⭐ Stars"
FROM "1_AI工具库/AI Agent框架"
SORT interest DESC, stars DESC
```

### AI 生产力工具

```dataview
TABLE 
    interest AS "兴趣",
    status AS "状态",
    usable AS "实用度",
    stars AS "⭐ Stars"
FROM "1_AI工具库/AI生产力工具"
SORT interest DESC, stars DESC
```

### OPC 一人公司

```dataview
TABLE 
    interest AS "兴趣",
    status AS "状态",
    usable AS "实用度",
    stars AS "⭐ Stars"
FROM "1_AI工具库/OPC一人公司"
SORT interest DESC, stars DESC
```

---

## 📝 最近更新

```dataview
TABLE date AS "记录日期"
FROM "1_AI工具库" AND #AI项目
SORT date DESC
LIMIT 10
```

---

## 🔍 快速查找

- **按名称搜索**：`Ctrl+Shift+F` 输入项目名
- **按标签过滤**：右侧标签面板点击对应标签
- **按状态筛选**：在 Dataview 查询中加 `WHERE status = "已安装"`
