import type { LingJiApi } from "../api";
import type {
  AuthorizedSource,
  DiscoveredSource,
  MemorySourcesSnapshot,
  RuntimeSummary,
  ScanRun,
  ScanSummary,
  SourceFact,
  SourceState,
} from "./memorySourcesTypes";

const stateLabels: Record<string, string> = {
  detected: "已发现",
  available: "已发现",
  consent_required: "需要确认",
  authorized: "已授权",
  scanning: "扫描中",
  current: "已接管",
  degraded: "需要检查",
  unsupported: "暂不支持",
  revoked: "已撤销",
  failed: "扫描失败",
};

export function sourceStateLabel(state: string | null | undefined): string {
  return stateLabels[String(state ?? "")] ?? "尚未获得";
}

export function canonicalSourceKey(kind: unknown, root: unknown): string {
  const normalizedKind = String(kind ?? "").trim().toLowerCase();
  const normalizedRoot = String(root ?? "")
    .trim()
    .replaceAll("\\", "/")
    .replace(/\/+/g, "/")
    .replace(/\/$/, "");
  return `${normalizedKind}|${normalizedRoot.toLowerCase()}`;
}

function rootName(root: string): string {
  const clean = root.replaceAll("\\", "/").replace(/\/$/, "");
  return clean.split("/").filter(Boolean).at(-1) || "来源目录";
}

function latestScansBySource(scans: ScanRun[]): Map<string, ScanRun> {
  const latest = new Map<string, ScanRun>();
  for (const scan of scans) {
    if (!scan?.source_id) continue;
    const previous = latest.get(scan.source_id);
    const stamp = Date.parse(String(scan.updated_at ?? ""));
    const previousStamp = Date.parse(String(previous?.updated_at ?? ""));
    if (!previous || (Number.isFinite(stamp) && (!Number.isFinite(previousStamp) || stamp > previousStamp))) {
      latest.set(scan.source_id, scan);
    }
  }
  return latest;
}

function describe(discovered: DiscoveredSource, state: SourceState, scan?: ScanRun): { detail: string; nextAction: string } {
  if (state === "current") return { detail: `已接管「${rootName(discovered.candidate_root)}」，最近一次扫描已完成。`, nextAction: "可查看本次扫描结果。" };
  if (state === "scanning") {
    const progress = scan?.progress != null && scan?.total != null ? `（${scan.progress}/${scan.total}）` : "";
    return { detail: `正在检查「${rootName(discovered.candidate_root)}」${progress}，完成后才会显示为已接管。`, nextAction: "等待扫描完成，或暂停后稍后继续。" };
  }
  if (state === "failed") return { detail: scan?.last_error ? `这次扫描没有完成：${scan.last_error}` : "这次扫描没有完成。", nextAction: "请重试；原授权仍保留。" };
  if (state === "revoked") return { detail: "主人已撤销接管，灵机不会再读取这个来源。", nextAction: "如需继续，请重新授权。" };
  if (state === "degraded") {
    const expired = scan?.last_error?.toLowerCase().includes("expired");
    return { detail: expired ? "授权已过期，需要重新授权。" : "来源或运行时需要检查，灵机会保留最近一次已知状态。", nextAction: expired ? "重新授权这个来源。" : "需要重启/检查后再试。" };
  }
  if (state === "unsupported") return { detail: discovered.reason || "当前没有可用的官方导出方式，灵机不会读取不透明存储。", nextAction: "请使用官方导出，或暂不接入。" };
  if (state === "consent_required") return { detail: discovered.reason || "这个来源需要主人明确确认后才能继续。", nextAction: "确认允许的来源目录后再授权。" };
  if (state === "authorized") return { detail: `已授权「${rootName(discovered.candidate_root)}」，尚未完成首轮扫描。`, nextAction: "立即扫描以完成接管。" };
  return { detail: discovered.reason ? `发现「${rootName(discovered.candidate_root)}」：${discovered.reason}` : `发现可接入的「${rootName(discovered.candidate_root)}」。`, nextAction: "确认来源后授权；灵机只会读取这个目录。" };
}

export function mergeSourceFacts(
  discovered: DiscoveredSource[],
  authorized: AuthorizedSource[],
  scans: ScanRun[],
): SourceFact[] {
  const latest = latestScansBySource(scans);
  const authorizedByKey = new Map(authorized.map((source) => [canonicalSourceKey(source.kind, source.root), source]));
  const seen = new Set<string>();
  const facts: SourceFact[] = [];
  const candidates = [...discovered];
  for (const source of authorized) {
    if (!candidates.some((candidate) => canonicalSourceKey(candidate.kind, candidate.candidate_root) === canonicalSourceKey(source.kind, source.root))) {
      candidates.push({ kind: source.kind, display_name: source.kind, candidate_root: source.root, status: source.status, capability: source.capability, reason: null });
    }
  }
  for (const candidate of candidates) {
    const key = canonicalSourceKey(candidate.kind, candidate.candidate_root);
    if (seen.has(key)) continue;
    seen.add(key);
    const source = authorizedByKey.get(key);
    const scan = source ? latest.get(source.source_id) : undefined;
    let state: SourceState;
    if (source?.status === "revoked") state = "revoked";
    else if (source?.status === "expired") state = "degraded";
    else if (source?.status === "degraded") state = "degraded";
    else if (scan?.status === "running" || scan?.status === "paused") state = "scanning";
    else if (scan?.status === "failed") state = "failed";
    else if (source && scan?.status === "completed") state = "current";
    else if (source) state = "authorized";
    else if (candidate.status === "unsupported") state = "unsupported";
    else if (candidate.status === "consent_required") state = "consent_required";
    else state = "detected";
    const copy = source?.status === "expired"
      ? { detail: "授权已过期，需要重新授权。", nextAction: "重新授权这个来源。" }
      : describe(candidate, state, scan);
    facts.push({ ...candidate, state, source_id: source?.source_id, root: source?.root ?? candidate.candidate_root, latestScan: scan, ...copy });
  }
  return facts;
}

export class MemorySourcesApi {
  constructor(private readonly api: Pick<LingJiApi, "get" | "post">) {}

  async snapshot(): Promise<MemorySourcesSnapshot> {
    const [discovered, authorized, scans, summary, runtime] = await Promise.all([
      this.api.get<DiscoveredSource[]>("/api/automatic-memory/discovered"),
      this.api.get<AuthorizedSource[]>("/api/automatic-memory/sources"),
      this.api.get<ScanRun[]>("/api/automatic-memory/scans"),
      this.api.get<ScanSummary>("/api/automatic-memory/summary"),
      this.api.get<RuntimeSummary>("/api/automatic-memory/runtime"),
    ]);
    return { discovered, authorized, scans, summary, runtime, sources: mergeSourceFacts(discovered, authorized, scans) };
  }

  authorize(source: SourceFact, selectedRoot = source.root): Promise<unknown> {
    const root = selectedRoot.trim();
    const random = globalThis.crypto?.randomUUID?.() ?? `fallback-${Date.now()}-${Math.random().toString(16).slice(2)}`;
    return this.api.post("/api/automatic-memory/authorize", {
      grant_id: `grant-${random}`,
      source_kinds: [source.kind],
      roots: [root],
      granted_at: new Date().toISOString(),
      owner_confirmed: true,
      kind: source.kind,
      root,
    });
  }

  revoke(sourceId: string): Promise<unknown> { return this.api.post("/api/automatic-memory/revoke", { source_id: sourceId }); }
  scan(sourceId: string): Promise<unknown> { return this.api.post("/api/automatic-memory/scan", { source_id: sourceId }); }
  pause(scanId: string): Promise<unknown> { return this.api.post("/api/automatic-memory/pause", { scan_id: scanId }); }
  resume(scanId: string): Promise<unknown> { return this.api.post("/api/automatic-memory/resume", { scan_id: scanId }); }
  retry(scanId: string): Promise<unknown> { return this.api.post("/api/automatic-memory/retry", { scan_id: scanId }); }
  detail(scanId: string): Promise<unknown> { return this.api.get(`/api/automatic-memory/scans/${encodeURIComponent(scanId)}`); }
}

export function countLabel(value: unknown): string {
  return typeof value === "number" && Number.isFinite(value) ? String(value) : "尚未获得";
}

export function scanStatusLabel(status: string | null | undefined): string {
  return ({ running: "扫描中", paused: "已暂停", completed: "已完成", failed: "失败", cancelled: "已取消" } as Record<string, string>)[String(status ?? "")] ?? "尚未获得";
}

export function actionEvidence(snapshot: MemorySourcesSnapshot, sourceId: string, action: "authorize" | "scan" | "revoke" | "pause" | "resume" | "retry"): boolean {
  const source = snapshot.sources.find((item) => item.source_id === sourceId);
  if (!source) return false;
  if (action === "authorize") return ["authorized", "scanning", "current"].includes(source.state);
  if (action === "revoke") return source.state === "revoked";
  if (action === "scan") return ["completed", "failed", "running", "paused"].includes(String(source.latestScan?.status));
  if (action === "pause") return source.latestScan?.status === "paused";
  if (action === "resume") return ["running", "completed", "failed"].includes(String(source.latestScan?.status));
  return ["running", "completed", "failed"].includes(String(source.latestScan?.status));
}

export function scanTerminalEvidence(snapshot: MemorySourcesSnapshot, sourceId: string): boolean {
  const source = snapshot.sources.find((item) => item.source_id === sourceId);
  return source?.latestScan?.status === "completed";
}
