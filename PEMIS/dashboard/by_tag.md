---
type: dashboard
version: "1.0"
title: "按标签分类"
---

# 按标签分类

## AI / 智能体 (agent, agentic, ai)

```dataview
TABLE score AS "评分", speed AS "速度", monetization AS "变现"
FROM "PEMIS/opportunities"
WHERE type = "opportunity" AND (contains(tags, "ai") OR contains(tags, "agent") OR contains(tags, "agentic"))
SORT score DESC
```

## 自动化 (automation)

```dataview
TABLE score AS "评分", speed AS "速度", monetization AS "变现"
FROM "PEMIS/opportunities"
WHERE type = "opportunity" AND contains(tags, "automation")
SORT score DESC
```

## CLI / 开发工具 (cli, dashboard)

```dataview
TABLE score AS "评分", speed AS "速度", monetization AS "变现"
FROM "PEMIS/opportunities"
WHERE type = "opportunity" AND (contains(tags, "cli") OR contains(tags, "dashboard"))
SORT score DESC
```

## 商业 (business)

```dataview
TABLE score AS "评分", speed AS "速度", monetization AS "变现"
FROM "PEMIS/opportunities"
WHERE type = "opportunity" AND contains(tags, "business")
SORT score DESC
```

---
