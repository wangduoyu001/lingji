---
type: dashboard
version: "5.0"
updated: "2026-06-23 02:15"
description: "灵机控制中心 - 全部基于 frontmatter metadata，无路径依赖"
state: NORMAL
opp_count: 109
decision_count: 3
---

# 灵机 控制中心

> **Obsidian = 编辑器 | 所有数据来自 frontmatter metadata**

---

## Top 3 最优机会

```dataview
TABLE score AS "评分", speed AS "速度", monetization AS "变现", difficulty AS "难度"
FROM "PEMIS/opportunities"
WHERE type = "opportunity" AND score > 0
SORT score DESC
LIMIT 3
```

---

## 快速变现机会 (speed=fast)

```dataview
TABLE score AS "评分", monetization AS "变现", difficulty AS "难度"
FROM "PEMIS/opportunities"
WHERE type = "opportunity" AND speed = "fast"
SORT score DESC
LIMIT 10
```

---

## 优质工具型变现

```dataview
TABLE score AS "评分", speed AS "速度", difficulty AS "难度"
FROM "PEMIS/opportunities"
WHERE type = "opportunity" AND monetization = "tool"
SORT score DESC
LIMIT 10
```

---

## 系统状态

```dataview
TABLE state AS "当前状态", updated AS "更新时间"
FROM "PEMIS/status"
WHERE type = "status"
```

---

## 统计

- 总机会数: `= length(filter(rows, (r) => r.type = "opportunity"))`
- 快速变现: `= length(filter(rows, (r) => r.speed = "fast"))`
- 工具类: `= length(filter(rows, (r) => r.monetization = "tool"))`

---
