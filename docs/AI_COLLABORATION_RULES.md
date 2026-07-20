# AI Collaboration Rules — LingJi

## Purpose

Define collaboration rules when multiple AI agents, Codex, and development environments work on the same repository.

## 1. GitHub Remote Is The Source Of Truth

GitHub remote branch is the only project baseline.

Before any development task:

1. Confirm repository.
2. Confirm target branch exists on remote.
3. Confirm remote HEAD commit.
4. Compare local HEAD with remote HEAD.
5. Do not develop when branch state is unknown.

Local worktrees are development environments, not authoritative project sources.

## 2. Branch Synchronization Before Development

Required flow:

```
GitHub remote
    ↓
fetch
    ↓
confirm branch and commit
    ↓
sync local workspace
    ↓
develop
    ↓
test
    ↓
commit
    ↓
push
```

When branches diverge:

- inspect diff first
- identify changed files
- decide merge strategy
- never force overwrite without approval

## 3. Multi AI Development Rules

Different AI sessions may work in parallel.

Before accepting changes:

- verify commit source
- verify changed files
- verify tests
- verify documentation

Do not assume another AI workspace represents the latest project state.

## 4. Development Task Routing

Use the simplest capable tool:

- Documentation, planning, review, and small repository changes: complete directly.
- Local testing, hardware validation, building, and runtime debugging: use Codex.
- Independent code modules: use separate development agents when appropriate.

Avoid unnecessary tool switching.

## 5. Safe Merge Requirement

Before merge:

1. Compare common ancestor.
2. Check file conflicts.
3. Review whether changes are compatible.
4. Preserve valuable work from all environments.

Never merge blindly.

## 6. Final Acceptance

Every completed task requires:

- code or document changes recorded in Git
- test result recorded
- current branch status confirmed
- next development step documented
