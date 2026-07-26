import { chromium } from "playwright";
import { spawn } from "node:child_process";
import { createServer } from "node:http";
import fs from "node:fs";
import path from "node:path";

const POLL_MS = 300;
const MAX_WAIT = 30_000;
const FRONTEND_PORT = 5199;
const API_PORT = 8766;
const DIST = path.resolve("desktop/lingji-control/dist");

async function main() {
  const apiServer = spawn("python", [
    "-m", "uvicorn", "control.api:create_control_app",
    "--host", "127.0.0.1", "--port", String(API_PORT), "--factory",
  ], { cwd: path.resolve("src"), stdio: ["ignore", "pipe", "pipe"], timeout: 10_000 });

  apiServer.stderr.on("data", (d) => {
    if (d.toString().includes("Uvicorn running")) console.log("API server up");
  });

  const frontendSrv = createServer((req, res) => {
    let p = (req.url || "/").split("?")[0];
    if (p === "/") p = "/index.html";
    let fp = path.join(DIST, p);
    if (!fs.existsSync(fp)) fp = path.join(DIST, "index.html");
    try {
      const c = fs.readFileSync(fp);
      const ext = path.extname(fp);
      const ct = ext === ".js" ? "application/javascript" : "text/html; charset=utf-8";
      res.writeHead(200, { "Content-Type": ct });
      res.end(c);
    } catch { res.writeHead(404); res.end("Not found"); }
  });
  frontendSrv.listen(FRONTEND_PORT, "127.0.0.1");
  console.log("Frontend on http://127.0.0.1:" + FRONTEND_PORT);

  const start = Date.now();
  while (Date.now() - start < MAX_WAIT) {
    try {
      const r = await fetch("http://127.0.0.1:" + API_PORT + "/api/brain/status");
      if (r.ok) { console.log("API ready"); break; }
    } catch {}
    await new Promise((r) => setTimeout(r, POLL_MS));
  }

  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1440, height: 920 } });
  const errors = [];
  page.on("console", (msg) => { if (msg.type() === "error") errors.push(msg.text()); });

  await page.goto("http://127.0.0.1:" + FRONTEND_PORT, { waitUntil: "networkidle" });

  const btns = await page.getByRole("button").all();
  let found = false;
  for (const b of btns) {
    const t = await b.textContent();
    if (t && t.includes("\u8111\u72b6\u6001")) { await b.click(); found = true; break; }
  }
  if (!found) {
    const els = await page.getByText("\u8111\u72b6\u6001").all();
    if (els.length > 0) await els[0].click();
  }
  await page.waitForTimeout(2000);

  await page.screenshot({ path: "_e2e_brain_status.png", fullPage: true });
  const body = await page.textContent("body") || "";

  const checks = [
    ["content renders", body.includes("\u8bb0\u5fc6\u6570\u91cf") || body.includes("\u5bf9\u8bdd\u6a21\u578b")],
    ["no api failure", !body.includes("\u8fde\u63a5\u5931\u8d25") && !body.includes("\u51fa\u9519")],
    ["min console errors", errors.filter(e => !e.includes("favicon")).length < 3],
  ];

  let passing = 0, failing = 0;
  for (const [n, ok] of checks) {
    console.log(ok ? "  \u2705 " + n : "  \u274c " + n);
    if (ok) passing++; else failing++;
  }

  console.log("\nResults: " + passing + " passed, " + failing + " failed");
  await browser.close();
  apiServer.kill();
  frontendSrv.close();
  process.exit(failing > 0 ? 1 : 0);
}

main().catch((e) => { console.error("E2E failed:", e.message); process.exit(1); });