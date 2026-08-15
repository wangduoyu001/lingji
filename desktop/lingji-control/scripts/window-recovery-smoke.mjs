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
assert.match(main, /MenuItemBuilder/);
assert.match(main, /SubmenuBuilder/);
assert.match(main, /recover-main-window/);
assert.match(main, /将灵机带到当前屏幕/);
assert.match(main, /\.accelerator\("CmdOrCtrl\+Shift\+L"\)/);
assert.match(main, /SubmenuBuilder::new\(&app, "窗口"\)/);
assert.match(main, /tauri::RunEvent::Reopen/);
assert.match(main, /recover_main_window\(app_handle\)/);

console.log("window-recovery-smoke: PASS");
