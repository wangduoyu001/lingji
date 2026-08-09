#!/usr/bin/env bash
set -euo pipefail

TARGET_TRIPLE="${1:-aarch64-apple-darwin}"
OUTPUT_ROOT="${LINGJI_SIDECAR_OUTPUT_ROOT:-build/sidecar-macos}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
ENTRYPOINT="$REPO_ROOT/run_packaged_control_api.py"
BUILD_ROOT="$REPO_ROOT/$OUTPUT_ROOT"
DIST_ROOT="$BUILD_ROOT/dist"
WORK_ROOT="$BUILD_ROOT/work"
SPEC_ROOT="$BUILD_ROOT/spec"
TAURI_BINARIES="$REPO_ROOT/desktop/lingji-control/src-tauri/binaries"
PREPARED_EXE="$TAURI_BINARIES/lingji-core-$TARGET_TRIPLE"
PREPARED_RUNTIME="$TAURI_BINARIES/lingji_core_lib"
PYTHON_BIN="${LINGJI_SIDECAR_PYTHON:-python3}"

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "build_macos_sidecar.sh must run on macOS" >&2
  exit 1
fi

if [[ "$TARGET_TRIPLE" == "aarch64-apple-darwin" ]]; then
  PY_ARCH="$($PYTHON_BIN -c 'import platform; print(platform.machine())')"
  case "$PY_ARCH" in
    arm64|aarch64) ;;
    *)
      echo "Apple Silicon build requires an arm64 Python. Current Python architecture: $PY_ARCH" >&2
      echo "Do not build the M5 sidecar through Rosetta." >&2
      exit 1
      ;;
  esac
fi

mkdir -p "$BUILD_ROOT" "$TAURI_BINARIES"
rm -rf "$DIST_ROOT" "$WORK_ROOT" "$SPEC_ROOT" "$PREPARED_RUNTIME"
rm -f "$PREPARED_EXE"

ARGS=(
  -m PyInstaller
  --noconfirm
  --clean
  --onedir
  --name lingji-core
  --contents-directory lingji_core_lib
  --distpath "$DIST_ROOT"
  --workpath "$WORK_ROOT"
  --specpath "$SPEC_ROOT"
  --paths "$REPO_ROOT"
  --collect-submodules src
  --exclude-module PySide6
  --exclude-module torch
  --exclude-module tensorflow
  --exclude-module paddleocr
  --exclude-module faster_whisper
  --exclude-module scenedetect
  "$ENTRYPOINT"
)

echo "Building LingJi macOS sidecar for $TARGET_TRIPLE..."
"$PYTHON_BIN" "${ARGS[@]}"

BUNDLE_ROOT="$DIST_ROOT/lingji-core"
SOURCE_EXE="$BUNDLE_ROOT/lingji-core"
SOURCE_RUNTIME="$BUNDLE_ROOT/lingji_core_lib"

[[ -f "$SOURCE_EXE" ]] || { echo "Missing PyInstaller executable: $SOURCE_EXE" >&2; exit 1; }
[[ -d "$SOURCE_RUNTIME" ]] || { echo "Missing PyInstaller runtime directory: $SOURCE_RUNTIME" >&2; exit 1; }

cp "$SOURCE_EXE" "$PREPARED_EXE"
chmod +x "$PREPARED_EXE"
cp -R "$SOURCE_RUNTIME" "$PREPARED_RUNTIME"

CHECK_ROOT="$BUILD_ROOT/contract-check"
rm -rf "$CHECK_ROOT"
mkdir -p "$CHECK_ROOT"
CONTRACT_PATH="$CHECK_ROOT/contract.json"
"$SOURCE_EXE" \
  --data-root "$CHECK_ROOT" \
  --check-config \
  --check-config-output "$CONTRACT_PATH"

"$PYTHON_BIN" - "$CONTRACT_PATH" <<'PY'
import json
import sys
from pathlib import Path

contract = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
assert contract["mode"] == "packaged_sidecar", contract
assert contract["host"] == "127.0.0.1", contract
assert contract["owner_data_outside_install_dir"] is True, contract
PY

EXE_HASH="$(shasum -a 256 "$PREPARED_EXE" | awk '{print $1}')"
RUNTIME_FILE_COUNT="$(find "$PREPARED_RUNTIME" -type f | wc -l | tr -d ' ')"
RUNTIME_BYTES="$(find "$PREPARED_RUNTIME" -type f -exec stat -f '%z' {} + | awk '{s+=$1} END {print s+0}')"
EXE_BYTES="$(stat -f '%z' "$PREPARED_EXE")"
MANIFEST_PATH="$TAURI_BINARIES/lingji-core-manifest.json"

"$PYTHON_BIN" - "$MANIFEST_PATH" "$TARGET_TRIPLE" "$PREPARED_EXE" "$EXE_BYTES" "$EXE_HASH" "$RUNTIME_FILE_COUNT" "$RUNTIME_BYTES" "$CONTRACT_PATH" <<'PY'
import json
import sys
from pathlib import Path

manifest_path, target, executable, exe_bytes, exe_hash, file_count, runtime_bytes, contract_path = sys.argv[1:]
contract = json.loads(Path(contract_path).read_text(encoding="utf-8"))
payload = {
    "schema_version": 1,
    "target_triple": target,
    "executable": {
        "path": f"binaries/{Path(executable).name}",
        "bytes": int(exe_bytes),
        "sha256": exe_hash,
    },
    "runtime_directory": {
        "path": "binaries/lingji_core_lib",
        "file_count": int(file_count),
        "bytes": int(runtime_bytes),
    },
    "pyinstaller_mode": "onedir",
    "contents_directory": "lingji_core_lib",
    "optional_media_providers_bundled": False,
    "contract": contract,
}
Path(manifest_path).write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
PY

rm -f \
  "$REPO_ROOT/desktop/lingji-control/src-tauri/target/release/lingji-core" \
  "$REPO_ROOT/desktop/lingji-control/src-tauri/target/$TARGET_TRIPLE/release/lingji-core"

echo "Prepared Tauri sidecar: $PREPARED_EXE"
echo "Runtime files: $RUNTIME_FILE_COUNT"
echo "Executable SHA-256: $EXE_HASH"
