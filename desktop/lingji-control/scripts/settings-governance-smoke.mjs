import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const source = (path) => readFile(resolve(here, path), "utf8");

const [page, field, api, controller, types] = await Promise.all([
  source("../src/pages/SettingsPage.tsx"),
  source("../src/components/settings/SettingField.tsx"),
  source("../src/pages/settingsApi.ts"),
  source("../src/pages/useSettingsController.ts"),
  source("../src/pages/settingsTypes.ts"),
]);

assert.equal(page.includes("GROUP_LABELS"), false, "Frontend must not duplicate backend group labels");
assert.match(page, /snapshot\.groups/);
assert.match(page, /snapshot\.summary/);
assert.match(page, /只看已修改/);
assert.match(page, /只看高风险/);
assert.match(page, /只看不可用/);
assert.match(api, /\/api\/settings\/preview/);
assert.match(api, /\/api\/settings\/commit/);
assert.match(controller, /dirtyValues/);
assert.match(controller, /preview\.requires_confirmation/);
assert.match(controller, /window\.confirm/);
assert.match(controller, /beforeunload/);
assert.match(field, /availability_state/);
assert.match(field, /performance_impact/);
assert.match(field, /privacy_impact/);
assert.match(types, /confirmation_required/);
assert.match(types, /high_risk_changes/);

console.log("settings-governance-smoke: PASS");
