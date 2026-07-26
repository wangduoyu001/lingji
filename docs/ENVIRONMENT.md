# ENVIRONMENT.md — Environment Boundary

The previous content was a machine snapshot, not a durable project contract. It copied one computer's GPU, model-installation state, virtual environment and obsolete PySide6 dependencies, so it must not be used as current setup guidance.

Use these authorities instead:

- General setup and validation entry: `README.md`
- Dependency ownership: `requirements*.txt` and `constraints/`
- Runtime defaults: `src/config.py::Settings`
- Current verified state: `docs/PROJECT_STATUS.md`
- Windows release environment: `.github/workflows/windows-desktop-release.yml`

Durable environment rules:

- Supported CI Python versions are defined by current workflows, not copied here.
- Desktop dependencies are owned by `desktop/lingji-control/package.json` and its lockfile.
- Tauri/Rust dependencies are owned by `desktop/lingji-control/src-tauri/Cargo.toml` and `Cargo.lock`.
- Models, databases, vectors, logs, caches and build helpers must use configurable locations, preferably under `D:\codex\` or an owner-selected path.
- Never write new runtime data into `C:\Users\Administrator\Documents\New project-ai`.
- Hardware and installed-model availability are runtime observations, not repository facts.

Historical machine details remain available in Git history.
