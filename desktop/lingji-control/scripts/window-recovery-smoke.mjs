import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const main = await readFile(resolve(here, "../src-tauri/src/main.rs"), "utf8");

assert.match(main, /fn recover_main_window\(/);
assert.match(main, /get_webview_window\("main"\)/);
assert.match(main, /window\.unminimize\(\)/);
assert.match(main, /window\.show\(\)/);
assert.match(main, /window\.center\(\)/);
assert.match(main, /window\.set_focus\(\)/);
assert.match(main, /MenuBuilder/);
assert.match(main, /recover-main-window/);
assert.match(main, /找回主窗口/);

console.log("window-recovery-smoke: PASS");
