const scripts = [
  "acceptance-smoke.mjs",
  "ui-modular-smoke.mjs",
  "vector-center-smoke.mjs",
  "hardware-smoke.mjs",
  "models-smoke.mjs",
  "memory-inspector-smoke.mjs",
  "capture-center-smoke.mjs",
  "obsidian-smoke.mjs",
  "codex-workspace-smoke.mjs",
  "memory-review-smoke.mjs",
  "obsidian-operations-smoke.mjs",
];

for (const script of scripts) {
  console.log(`\n[smoke] ${script}`);
  await import(new URL(script, import.meta.url));
}

console.log(`\n[smoke] PASS (${scripts.length} scripts)`);
