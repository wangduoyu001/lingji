# GETTING_STARTED.md — Current Entry

The original parallel-worktree setup instructions in this file are obsolete. They referenced the old project directory, PySide6 Desktop, the 8765 compatibility API and the retired second-brain startup scripts.

Use the canonical repository landing page instead:

```text
README.md
```

Development and AI agents should then follow:

```text
AGENTS.md
-> relevant docs/PROJECT_STATUS.md section
-> relevant docs/MODULES/CODE_MAP.md section
-> directly affected code and tests
```

Current validation entry:

```powershell
.\scripts\validate.ps1 -Mode focused -Area <area>
.\scripts\validate.ps1 -Mode full
.\scripts\validate.ps1 -Mode release
```

Do not restore clone paths, old-project startup commands, machine-specific model status or duplicated configuration defaults here. Historical instructions remain available in Git history.
