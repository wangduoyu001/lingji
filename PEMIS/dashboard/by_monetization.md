---
type: dashboard
version: "1.0"
title: "按变现类型分类"
role: generated_data
---

# 按变现类型分类

> 2026-06 PEMIS 生成快照；不是当前开发进度或正式 Opportunity Center。

## 工具型变现 (tool)

```dataview
TABLE score AS "评分", speed AS "速度", difficulty AS "难度"
FROM "PEMIS/opportunities"
WHERE type = "opportunity" AND monetization = "tool"
SORT score DESC
```

## SaaS型变现 (saas)

```dataview
TABLE score AS "评分", speed AS "速度", difficulty AS "难度"
FROM "PEMIS/opportunities"
WHERE type = "opportunity" AND monetization = "saas"
SORT score DESC
```

---
