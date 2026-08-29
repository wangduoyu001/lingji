const scripts = [
  "acceptance-smoke.mjs",
  "ui-modular-smoke.mjs",
  "native-desktop-ui-smoke.mjs",
  "memory-workspace-ui-smoke.mjs",
  "windows-release-smoke.mjs",
  "runtime-sidecar-smoke.mjs",
  "automatic-memory-sources-smoke.mjs",
  "automatic-memory-sources-repair-smoke.mjs",
  "observation-first-ui-smoke.mjs",
  "vector-center-smoke.mjs",
  "hardware-smoke.mjs",
  "models-smoke.mjs",
  "memory-inspector-smoke.mjs",
  "capture-center-smoke.mjs",
  "obsidian-smoke.mjs",
  "codex-workspace-smoke.mjs",
  "memory-review-smoke.mjs",
  "obsidian-operations-smoke.mjs",
  "polling-data-smoke.mjs",
  "auto-review-shadow-smoke.mjs",
  "settings-governance-smoke.mjs",
  "task8e-contract-behavior-smoke.mjs",
];

// Task6's rendered owner flow is the single maintained E2E surface. Keep it
// in the smoke registry so focused landing validation cannot silently omit UI
// coverage; the flow owns its temporary fixture server and browser lifecycle.
scripts.push("../tests/e2e_owner_memory_flow.mjs");

for (const script of scripts) {
  console.log(`\n[smoke] ${script}`);
  await import(new URL(script, import.meta.url));
}

console.log(`\n[smoke] PASS (${scripts.length} scripts)`);
