---
tags:
  - 仪表盘
---

# 直播话术仪表盘

> 自动汇总所有话术。安装 Dataview 插件后生效。

---

## 所有完整原文

```dataview
TABLE 主播, 日期, 主题, 字数, status
FROM "直播话术稿/1_完整文档"
SORT 日期 DESC
```

## 按动作类型统计

```dataview
TABLE file.size as 大小
FROM "直播话术稿/2_动作话术"
SORT file.name ASC
```

## 最近新增的原文（近7天）

```dataview
TABLE 主播, 日期, 主题
FROM "直播话术稿/1_完整文档"
WHERE file.ctime >= date(today) - dur(7 days)
SORT file.ctime DESC
```

## 待处理的原文

```dataview
TABLE 主播, 日期, 主题
FROM "直播话术稿/1_完整文档"
WHERE status = "待拆分"
```

## 全部标签

```dataview
LIST
FROM #话术 OR #来源
SORT file.name ASC
```
