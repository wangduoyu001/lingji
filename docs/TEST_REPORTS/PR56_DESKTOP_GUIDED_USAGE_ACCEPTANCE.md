# PR #56 Desktop Guided Usage Owner Acceptance

Status: PENDING

PR: `#56`

Branch: `feature/desktop-guided-usage`

## 1. Acceptance target

Confirm that the owner can understand and complete the normal LingJi workflow without reading source code or guessing technical page meanings.

This acceptance is about product comprehensibility, not only click responsiveness.

## 2. Exact artifact identity

Complete after the Windows workflow succeeds:

```text
Product commit:
Artifact name:
Artifact ID:
Artifact ZIP SHA256:
Installer SHA256:
```

## 3. Environment boundary

Use an isolated non-system-drive `acceptance` workspace.

Do not access or mutate production Vault, SQLite, Qdrant or owner files during UI acceptance.

## 4. Required checks

### 4.1 First impression

After opening LingJi, answer without external help:

- Can you identify whether the system is running?
- Can you identify the first action for adding new material?
- Can you identify where processing progress is shown?
- Can you identify where candidate memories are reviewed?
- Can you identify where owner-only decisions appear?

Result: `PASS / FAIL`

Notes:

```text

```

### 4.2 Overview daily flow

Verify the four visible steps:

```text
1. 投喂资料
2. 查看处理
3. 审核记忆
4. 处理异常
```

Click each card and confirm it opens the correct page.

Result: `PASS / FAIL`

### 4.3 Page-level guidance

On each primary page, confirm the guide explains:

- what the page is for;
- when to use it;
- the operating sequence;
- the next recommended action.

Primary pages:

```text
运行状态
活动记录
需要我处理
高级诊断
```

Result: `PASS / FAIL`

### 4.4 Persistent help

Open “怎么使用” from:

- sidebar;
- top toolbar.

Confirm the drawer:

- explains the daily workflow;
- routes model issues correctly;
- routes vector issues correctly;
- routes compute issues correctly;
- routes storage issues correctly;
- closes normally;
- navigates to the chosen page.

Result: `PASS / FAIL`

### 4.5 Complete owner workflow

Complete one full isolated workflow:

```text
手动投喂中心
→ 活动记录
→ 人工记忆审核
→ 需要我处理
```

The owner must be able to explain what happened at each step.

Result: `PASS / FAIL / BLOCKED`

### 4.6 Advanced pages

Sample at least these pages:

```text
AI 与模型
向量中心
系统与算力
存储
日志
环境验收
```

Confirm the guide does not encourage destructive action and clearly states when the page is needed.

Result: `PASS / FAIL`

### 4.7 Layout and readability

Check at the installed window size:

- no guide text is clipped;
- buttons remain visible;
- the guide does not cover required page controls;
- the drawer scrolls;
- the daily-flow cards remain readable;
- wording is understandable without developer terminology.

Result: `PASS / FAIL`

## 5. Required owner feedback

```text
最容易理解的部分：

最难理解的部分：

仍然不知道怎么操作的页面：

需要删除或缩短的说明：

缺少的下一步提示：

最终结论：PASS / FAIL / BLOCKED
```

## 6. Merge rule

PR #56 remains Draft and unmerged until:

- all required CI succeeds;
- exact Windows artifact identity is recorded;
- the installed UI remains open for owner review;
- the owner explicitly confirms the workflow is understandable.

Click responsiveness alone is not sufficient for PASS.
