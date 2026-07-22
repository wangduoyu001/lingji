const scripts = [
  "acceptance-smoke.mjs",
  "ui-modular-smoke.mjs",
  "native-desktop-ui-smoke.mjs",
  "memory-workspace-ui-smoke.mjs",
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
];

for (const script of scripts) {
  console.log(`\n[smoke] ${script}`);
  await import(new URL(script, import.meta.url));
}

console.log(`\n[smoke] PASS (${scripts.length} scripts)`);
