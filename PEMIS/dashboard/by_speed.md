---
type: dashboard
version: "1.0"
title: "按速度分类"
role: generated_data
---

# 按速度分类

> 2026-06 PEMIS 生成快照；不是当前开发进度或正式 Opportunity Center。

## 快速变现 (fast)

```dataview
TABLE score AS "评分", monetization AS "变现", difficulty AS "难度"
FROM "PEMIS/opportunities"
WHERE type = "opportunity" AND speed = "fast"
SORT score DESC
```

## 中期变现 (mid)

```dataview
TABLE score AS "评分", monetization AS "变现", difficulty AS "难度"
FROM "PEMIS/opportunities"
WHERE type = "opportunity" AND speed = "mid"
SORT score DESC
```

---
