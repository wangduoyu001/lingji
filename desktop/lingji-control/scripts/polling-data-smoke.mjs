import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";

import { normalizeBrainStatus } from "../src/contracts/brainStatus.ts";

const here = dirname(fileURLToPath(import.meta.url));
const hookSource = await readFile(resolve(here, "../src/hooks/usePollingResource.ts"), "utf8");

assert.match(hookSource, /AbortController/);
assert.match(hookSource, /inFlightRef/);
assert.match(hookSource, /setTimeout/);
assert.match(hookSource, /visibilitychange/);
assert.match(hookSource, /failureCount/);
assert.match(hookSource, /lastSuccessAt/);

const unavailable = normalizeBrainStatus({
  memory_count: null,
  vector_count: null,
  installed_models: null,
  gpus: [{ name: "RTX 4060", utilization_percent: null }],
});
assert.equal(unavailable.memory_count, null);
assert.equal(unavailable.vector_count, null);
assert.equal(unavailable.installed_models, null);
assert.equal(unavailable.gpus[0].utilization_percent, null);

const measuredZero = normalizeBrainStatus({
  memory_count: 0,
  vector_count: 0,
  installed_models: 0,
  gpus: [{ name: "RTX 4060", utilization_percent: 0 }],
});
assert.equal(measuredZero.memory_count, 0);
assert.equal(measuredZero.vector_count, 0);
assert.equal(measuredZero.installed_models, 0);
assert.equal(measuredZero.gpus[0].utilization_percent, 0);

console.log("polling-data-smoke: PASS");
