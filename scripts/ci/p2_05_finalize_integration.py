from __future__ import annotations

from pathlib import Path


def read(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def write(path: str, text: str) -> None:
    Path(path).write_text(text, encoding="utf-8")


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if old not in text:
        raise RuntimeError(f"missing integration contract: {label}")
    return text.replace(old, new, 1)


def fold_api() -> None:
    extension_path = Path("src/control/api.py")
    core_path = Path("src/control/_api_core.py")
    if not core_path.exists():
        if Path("src/control/capture_api.py").exists():
            return
        raise RuntimeError("neither temporary API core nor finalized capture API exists")

    extension = read(str(extension_path))
    core = read(str(core_path))
    capture_api = extension
    for line in (
        "from ._api_core import *  # noqa: F401,F403\n",
        "from ._api_core import create_control_app as _create_control_app\n",
        "from .service import LocalControlService\n",
    ):
        capture_api = capture_api.replace(line, "", 1)
    wrapper_at = capture_api.rfind("\ndef create_control_app(")
    if wrapper_at < 0:
        raise RuntimeError("capture API wrapper not found")
    capture_api = capture_api[:wrapper_at].rstrip() + "\n"
    capture_api = replace_once(
        capture_api,
        "def _register_capture_routes(",
        "def register_capture_routes(",
        "capture route registrar",
    )
    write("src/control/capture_api.py", capture_api)

    capture_import = """from .capture_api import (
    CaptureCommonRequest,
    CaptureFileRequest,
    CaptureMediaRequest,
    CaptureShareRequest,
    CaptureTextRequest,
    CaptureWebRequest,
    register_capture_routes,
)
"""
    core = replace_once(
        core,
        "from .service import LocalControlService\n",
        "from .service import LocalControlService\n" + capture_import,
        "main API capture import",
    )
    final_return = core.rfind("    return app\n")
    if final_return < 0:
        raise RuntimeError("main API final return not found")
    core = (
        core[:final_return]
        + "    register_capture_routes(app, settings, control, token=token)\n"
        + core[final_return:]
    )
    write(str(extension_path), core)
    core_path.unlink()


def fold_queue() -> None:
    queue_path = Path("src/extraction/queue.py")
    core_path = Path("src/extraction/_queue_core.py")
    if not core_path.exists():
        if "class _SQLiteExtractionQueueBase:" in read(str(queue_path)):
            return
        raise RuntimeError("neither temporary queue core nor finalized queue exists")

    core = read(str(core_path))
    extension_text = read(str(queue_path))
    core = replace_once(
        core,
        "class SQLiteExtractionQueue:",
        "class _SQLiteExtractionQueueBase:",
        "queue base class",
    )
    extension_at = extension_text.find("CANCELLABLE_STATUSES =")
    if extension_at < 0:
        raise RuntimeError("queue extension marker not found")
    extension = extension_text[extension_at:]
    extension = replace_once(
        extension,
        "class SQLiteExtractionQueue(_SQLiteExtractionQueue):",
        "class SQLiteExtractionQueue(_SQLiteExtractionQueueBase):",
        "formal queue class",
    )
    write(str(queue_path), core.rstrip() + "\n\n\n" + extension)
    core_path.unlink()


def align_manual_methods() -> None:
    path = "src/control/capture.py"
    text = read(path)
    if 'capture_method=str(payload.get("capture_method") or "manual_text")' in text:
        return
    text = replace_once(
        text,
        'self._envelope(payload, source_type=str(payload.get("source_type") or "web"), text=text),',
        'self._envelope(\n                payload,\n                source_type=str(payload.get("source_type") or "web"),\n                capture_method=str(payload.get("capture_method") or "manual_text"),\n                text=text,\n            ),',
        "manual text method",
    )
    text = replace_once(
        text,
        'source_type=str(payload.get("source_type") or "web"),\n                url=url,',
        'source_type=str(payload.get("source_type") or "web"),\n                capture_method=str(payload.get("capture_method") or "manual_web"),\n                url=url,',
        "manual web method",
    )
    text = replace_once(
        text,
        '''    def submit_file(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        return self._submit_path(payload, str(payload.get("source_type") or "web"))
''',
        '''    def submit_file(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        source_type = str(payload.get("source_type") or "web")
        adapter_name = str(payload.get("adapter_name") or "")
        capture_method = str(payload.get("capture_method") or "")
        if not capture_method:
            if source_type == "chatgpt_export":
                capture_method = "manual_chatgpt_export"
            elif source_type == "codex_report" or adapter_name == "codex_work_report":
                capture_method = "manual_codex_report"
            else:
                capture_method = "manual_file"
        return self._submit_path(payload, source_type, capture_method=capture_method)
''',
        "manual file method",
    )
    text = replace_once(
        text,
        '            "media",\n            options={',
        '            "media",\n            capture_method=str(payload.get("capture_method") or "manual_media"),\n            options={',
        "manual media method",
    )
    text = replace_once(
        text,
        'def _submit_path(self, payload: Mapping[str, Any], source_type: str, *, options: Mapping[str, Any] | None = None) -> dict[str, Any]:',
        'def _submit_path(\n        self,\n        payload: Mapping[str, Any],\n        source_type: str,\n        *,\n        capture_method: str = "manual_file",\n        options: Mapping[str, Any] | None = None,\n    ) -> dict[str, Any]:',
        "submit path signature",
    )
    text = replace_once(
        text,
        'self._envelope(payload, source_type=source_type, capture_method="manual_upload", title=',
        'self._envelope(payload, source_type=source_type, capture_method=capture_method, title=',
        "submit path envelope method",
    )
    write(path, text)


def fix_cross_platform_contracts() -> None:
    obsidian_path = "second_brain/obsidian_cli.py"
    obsidian = read(obsidian_path)
    if "PureWindowsPath" not in obsidian:
        obsidian = replace_once(
            obsidian,
            "from pathlib import Path\n",
            "from pathlib import Path, PureWindowsPath\n",
            "portable Vault path import",
        )
    old_name = "            name = Path(vault_path).name\n"
    if old_name in obsidian:
        obsidian = obsidian.replace(
            old_name,
            '            name = PureWindowsPath(vault_path).name if "\\\\" in vault_path else Path(vault_path).name\n',
            1,
        )
    write(obsidian_path, obsidian)

    test_name = "test_cpu_snapshot_uses_powershell_cim_on_windows"
    cpu_test_file: Path | None = None
    for candidate in Path("tests").rglob("*.py"):
        candidate_text = candidate.read_text(encoding="utf-8")
        if test_name in candidate_text:
            cpu_test_file = candidate
            break
    if cpu_test_file is None:
        raise RuntimeError("Windows CPU contract test not found")
    cpu_test = cpu_test_file.read_text(encoding="utf-8")
    if "from unittest.mock import patch" not in cpu_test:
        cpu_test = replace_once(
            cpu_test,
            "import unittest\n",
            "import unittest\nfrom unittest.mock import patch\n",
            "CPU patch import",
        )
    old_call = '''        runner = SafeRunner(command_runner=MockRunner())
        snapshot = cpu_snapshot(None, runner=runner)
'''
    if old_call in cpu_test:
        cpu_test = cpu_test.replace(
            old_call,
            '''        runner = SafeRunner(command_runner=MockRunner())
        with patch("src.hardware.system_detectors.platform.system", return_value="Windows"):
            snapshot = cpu_snapshot(None, runner=runner)
''',
            1,
        )
    cpu_test_file.write_text(cpu_test, encoding="utf-8")


def remove_scaffolding() -> None:
    Path(".github/workflows/p2-05-integrated-gate.yml").unlink(missing_ok=True)


def main() -> None:
    fold_api()
    fold_queue()
    align_manual_methods()
    fix_cross_platform_contracts()
    remove_scaffolding()
    print("P2-05 integration cleanup applied")


if __name__ == "__main__":
    main()
