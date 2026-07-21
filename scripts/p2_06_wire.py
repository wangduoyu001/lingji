from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def write(path: str, content: str) -> None:
    (ROOT / path).write_text(content, encoding="utf-8")


def replace_once(path: str, old: str, new: str) -> None:
    text = read(path)
    if new in text:
        return
    if old not in text:
        raise RuntimeError(f"patch marker not found in {path}: {old[:80]!r}")
    write(path, text.replace(old, new, 1))


def patch_app_pages() -> None:
    replace_once(
        "desktop/lingji-control/src/AppPages.tsx",
        'import ModelsPage from "./pages/ModelsPage";\nimport OverviewPage from "./pages/OverviewPage";',
        'import ModelsPage from "./pages/ModelsPage";\nimport ObsidianPage from "./pages/ObsidianPage";\nimport OverviewPage from "./pages/OverviewPage";',
    )
    replace_once(
        "desktop/lingji-control/src/AppPages.tsx",
        '      {page === "capture_center" && (\n        <CaptureCenterPage api={api} active={connected} onOpenInspector={onOpenInspector} />\n      )}\n      {page === "vector_center" && <VectorCenterPage api={api} active={connected} />}',
        '      {page === "capture_center" && (\n        <CaptureCenterPage api={api} active={connected} onOpenInspector={onOpenInspector} />\n      )}\n      {page === "obsidian" && <ObsidianPage api={api} active={connected} />}\n      {page === "vector_center" && <VectorCenterPage api={api} active={connected} />}',
    )


def patch_types() -> None:
    replace_once(
        "desktop/lingji-control/src/types.ts",
        '  | "capture_center"\n  | "vector_center"',
        '  | "capture_center"\n  | "obsidian"\n  | "vector_center"',
    )
    obsidian_types = '''export type ObsidianIssueStatus = {\n  code: string;\n  message: string;\n};\n\nexport type ObsidianStatus = {\n  as_of?: string;\n  state: RuntimeState;\n  enabled: boolean;\n  available: boolean;\n  version?: string | null;\n  vault_name?: string | null;\n  cli_configured: boolean;\n  vault_configured: boolean;\n  cli_path_display: string;\n  vault_path_display: string;\n  cli_discovery_source: string;\n  vault_discovery_source: string;\n  timeout_seconds: number;\n  dry_run: boolean;\n  persisted?: boolean;\n  capabilities: {\n    status: boolean;\n    read: boolean;\n    write: boolean;\n    dry_run: boolean;\n    compatibility_forwarding: boolean;\n  };\n  issues: ObsidianIssueStatus[];\n};\n\n'''
    replace_once(
        "desktop/lingji-control/src/types.ts",
        "export type SettingDefinition = {",
        obsidian_types + "export type SettingDefinition = {",
    )


def patch_settings_page() -> None:
    replace_once(
        "desktop/lingji-control/src/pages/SettingsPage.tsx",
        '  extraction: "采集与提取",\n  hardware_compute: "系统与算力",',
        '  extraction: "采集与提取",\n  obsidian: "Obsidian",\n  hardware_compute: "系统与算力",',
    )


def patch_package_json() -> None:
    path = ROOT / "desktop/lingji-control/package.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    scripts = payload.setdefault("scripts", {})
    scripts["test:obsidian"] = "tsx scripts/obsidian-smoke.mjs"
    smoke = str(scripts.get("test:smoke") or "")
    command = "tsx scripts/obsidian-smoke.mjs"
    if command not in smoke:
        scripts["test:smoke"] = smoke + " && " + command
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def patch_runtime_settings() -> None:
    block = '''            # Obsidian CLI integration. Workspace Vault remains authoritative.\n            "obsidian_cli_enabled": self._boolean(\n                "obsidian", "启用 Obsidian CLI", "启用正式 src.obsidian CLI 状态和命令能力。", True\n            ),\n            "obsidian_cli_path": self._string(\n                "obsidian", "Obsidian CLI 路径", "留空时按环境变量、PATH 和平台标准位置自动发现。", "", 2048\n            ),\n            "obsidian_vault_path": self._string(\n                "obsidian", "Obsidian Vault 路径", "当前 Workspace Vault 优先；此值仅作为显式兼容回退。", "", 2048\n            ),\n            "obsidian_vault_name": self._string(\n                "obsidian", "Obsidian Vault 名称", "留空时从 Vault 路径或 OBSIDIAN_VAULT_NAME 推导。", "", 256\n            ),\n            "obsidian_cli_timeout_seconds": self._integer(\n                "obsidian", "Obsidian CLI 超时（秒）", "单次 CLI 调用的最长等待时间。", 15, 1, 300\n            ),\n            "obsidian_cli_dry_run": self._boolean(\n                "obsidian", "Obsidian Dry Run", "开启后写命令只记录不执行，状态和只读命令仍可验证。", False\n            ),\n'''
    replace_once(
        "src/control/runtime_settings.py",
        "            # Backup defaults.\n",
        block + "            # Backup defaults.\n",
    )


def patch_control_service() -> None:
    replace_once(
        "src/control/service.py",
        "from src.model_center import LocalModelInventoryService\nfrom src.storage import BackupManager, StateDatabase, StorageLifecycleManager",
        "from src.model_center import LocalModelInventoryService\nfrom src.obsidian.service import ObsidianService\nfrom src.storage import BackupManager, StateDatabase, StorageLifecycleManager",
    )
    replace_once(
        "src/control/service.py",
        "        self.runtime_settings = RuntimeSettingsStore(settings, state_db=self.state_db)\n        self.health_checker = StartupHealthChecker(settings)",
        "        self.runtime_settings = RuntimeSettingsStore(settings, state_db=self.state_db)\n        self.obsidian = ObsidianService(\n            settings, runtime_settings=self.runtime_settings, state_db=self.state_db\n        )\n        self.health_checker = StartupHealthChecker(settings)",
    )
    replace_once(
        "src/control/service.py",
        "        self._sync_hardware_settings()\n        return snapshot\n\n    def hardware_capabilities",
        "        self._sync_hardware_settings()\n        return snapshot\n\n    def obsidian_status(self) -> dict[str, Any]:\n        return self.obsidian.status()\n\n    def validate_obsidian_settings(self, values: Mapping[str, Any]) -> dict[str, Any]:\n        return self.obsidian.validate_configuration(values)\n\n    def hardware_capabilities",
    )


def patch_control_api() -> None:
    replace_once(
        "src/control/api.py",
        "from .memory_inspector import build_memory_inspector\nfrom .service import LocalControlService",
        "from .memory_inspector import build_memory_inspector\nfrom .obsidian_api import register_obsidian_routes\nfrom .service import LocalControlService",
    )
    replace_once(
        "src/control/api.py",
        "    register_capture_routes(app, settings, control, token=token)\n    return app",
        "    register_obsidian_routes(\n        app, control, dependencies=secured, translate_error=translate_error\n    )\n    register_capture_routes(app, settings, control, token=token)\n    return app",
    )


def main() -> None:
    patch_app_pages()
    patch_types()
    patch_settings_page()
    patch_package_json()
    patch_runtime_settings()
    patch_control_service()
    patch_control_api()


if __name__ == "__main__":
    main()
