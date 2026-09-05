import type { LingJiApi } from "../api";
import type {
  AuthorizedSource,
  DiscoveredSource,
  MemorySourcesSnapshot,
  RuntimeSummary,
  ScanDetailResponse,
  ScanRun,
  ScanSummary,
  SourceFact,
  SourceState,
} from "./memorySourcesTypes";
import type { PageResponse, SourceItem } from "./memoryInspectorTypes";
import type { AppSoftwareRow, ExportInboxRow, ModelHealthPanel, OwnerIntakePanels, ProcessRow } from "./memorySourcesTypes";

const stateLabels: Record<string, string> = {
  detected: "已发现",
  available: "已发现",
  consent_required: "需要确认",
  authorized: "已授权",
  scanning: "扫描中",
  scan_completed: "扫描完成",
  processing: "处理中",
  imported: "已导入",
  partial_failure: "部分失败",
  empty: "空目录",
  current: "已接管",
  degraded: "需要检查",
  unsupported: "未识别支持格式",
  revoked: "已撤销",
  failed: "扫描失败",
};

export function sourceStateLabel(state: string | null | undefined): string {
  return stateLabels[String(state ?? "")] ?? "尚未获得";
}

export function canonicalSourceKey(kind: unknown, root: unknown): string {
  const normalizedKind = String(kind ?? "").trim().toLowerCase();
  let normalizedRoot = String(root ?? "")
    .trim()
    .replaceAll("\\", "/")
    .replace(/\/+/g, "/")
    .replace(/\/$/, "");
  // macOS exposes /tmp and /var through lexical /private aliases. Collapse
  // only those POSIX aliases; Windows path semantics remain untouched.
  normalizedRoot = normalizedRoot.replace(/^\/private\/(tmp|var)(?=\/|$)/i, "/$1");
  return `${normalizedKind}|${normalizedRoot.toLowerCase()}`;
}

function rootName(root: string): string {
  // Ordinary owner-facing copy must not expose filesystem names.  The exact
  // path remains available in the technical details/API for diagnostics.
  return root.trim() ? "你选择的目录" : "来源目录";
}

function metadataNumber(value: unknown, integer = false): string {
  if (typeof value !== "number" || !Number.isFinite(value) || value < 0 || (integer && !Number.isInteger(value))) return "尚未获得";
  return String(value);
}

function metadataTime(value: unknown): string {
  if (typeof value !== "number" || !Number.isFinite(value) || value < 0) return "尚未获得";
  const date = new Date(value * 1000);
  if (!Number.isFinite(date.getTime())) return "尚未获得";
  return date.toISOString().replace("T", " ").replace(".000Z", " UTC").replace("Z", " UTC");
}

/**
 * Convert discovered metadata into owner-safe display values.  This adapter
 * deliberately has no path, source-id, body, or raw DTO representation.
 */
export function sourceMetadataEvidence(source: Pick<DiscoveredSource, "file_count" | "byte_count" | "earliest_mtime" | "latest_mtime">): {
  fileCount: string;
  byteCount: string;
  earliestMtime: string;
  latestMtime: string;
} {
  const fileCount = metadataNumber(source.file_count, true);
  const byteCount = metadataNumber(source.byte_count);
  return {
    fileCount,
    byteCount: byteCount === "尚未获得" ? byteCount : `${byteCount} 字节`,
    earliestMtime: metadataTime(source.earliest_mtime),
    latestMtime: metadataTime(source.latest_mtime),
  };
}

export function ownerSourceName(source: { kind?: string | null; display_name?: string | null }): string {
  const kind = String(source.kind ?? "").trim().toLowerCase();
  const displayName = String(source.display_name ?? "").trim();
  if (kind === "obsidian" || displayName.toLowerCase().includes("managed obsidian")) return "Obsidian 长期记忆区";
  if (kind === "claude_desktop") return "Claude";
  if (kind === "codex" || kind.includes("codex")) return "Codex聊天记录";
  if (kind === "chatgpt_export") return "ChatGPT导出记录";
  if (kind === "generic" || kind === "generic_ai_history") return "其他AI聊天投递箱";
  return "其他聊天来源";
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

function scanStateFromProcessing(scan?: ScanRun): SourceState | null {
  if (!scan || scan.status !== "completed") return null;
  const explicit = String(scan.processing_status ?? "").trim();
  if (explicit === "scan_completed" || explicit === "processing" || explicit === "imported" || explicit === "partial_failure" || explicit === "empty" || explicit === "unsupported_format") {
    return explicit === "unsupported_format" ? "unsupported" : explicit as SourceState;
  }
  if (typeof scan.processing_failed === "number" && scan.processing_failed > 0 && typeof scan.processing_completed === "number" && scan.processing_completed > 0) return "partial_failure";
  if (typeof scan.processing_pending === "number" && scan.processing_pending > 0) return "processing";
  if (typeof scan.processing_completed === "number" && scan.processing_completed === 0 && typeof scan.processing_total === "number" && scan.processing_total === 0) return "empty";
  if (typeof scan.processing_completed === "number" && scan.processing_completed > 0) return "imported";
  return "scan_completed";
}

function describe(discovered: DiscoveredSource, state: SourceState, scan?: ScanRun): { detail: string; nextAction: string } {
  if (state === "detected" && discovered.kind === "codex_rollout") {
    const count = typeof discovered.file_count === "number" ? discovered.file_count : null;
    return {
      detail: count === null ? "已发现 Codex 本机记录目录。" : `发现 ${count} 个本机对话文件。灵机尚未读取对话正文。`,
      nextAction: "允许接管 Codex。",
    };
  }
  if (state === "current") return { detail: `已接管「${rootName(discovered.candidate_root)}」，最近一次扫描已完成。`, nextAction: "可查看本次扫描结果。" };
  if (state === "scan_completed") return { detail: "这次检查已经完成，但还没有看到导入完成证据。", nextAction: "查看这次检查，确认是否需要继续处理。" };
  if (state === "processing") return { detail: "扫描已完成，灵机正在把导入的内容整理成可搜索的记忆（自动进行，无需等待）。", nextAction: "整理完成后会自动显示，无需任何操作。" };
  if (state === "imported") return { detail: "来源内容已导入完成，可以查看已导入具体内容。", nextAction: "查看已导入具体内容。" };
  if (state === "partial_failure") return { detail: "已经导入了一部分内容，但也有项目失败。", nextAction: "查看这次检查，确认失败项是否需要重试。" };
  if (state === "empty") return { detail: "扫描完成了，但目录里没有可导入内容。", nextAction: "查看这次检查，确认是否选择了正确目录。" };
  if (state === "scanning") {
    const progress = scan?.progress != null && scan?.total != null ? `（${scan.progress}/${scan.total}）` : "";
    if (scan?.status === "paused") return { detail: `扫描已暂停，已保留「${rootName(discovered.candidate_root)}」的授权。`, nextAction: "继续扫描，完成后才会显示为已接管。" };
    return { detail: `正在检查「${rootName(discovered.candidate_root)}」${progress}，完成后才会显示为已接管。`, nextAction: "等待扫描完成，或暂停后稍后继续。" };
  }
  if (state === "failed") return { detail: "这次检查没有完成，原来的记忆不会被删除。", nextAction: "再次检查；原来的记忆不会被删除。" };
  if (state === "revoked") return { detail: "主人已撤销接管，灵机不会再读取这个来源。", nextAction: "如需继续，请重新授权。" };
  if (state === "degraded") {
    const expired = scan?.last_error?.toLowerCase().includes("expired");
    return { detail: expired ? "授权已过期，需要重新授权。" : "来源或运行时需要检查，灵机会保留最近一次已知状态。", nextAction: expired ? "重新授权这个来源。" : "需要重启/检查后再试。" };
  }
  if (state === "unsupported") {
    if (discovered.kind === "claude_desktop") return { detail: "Claude 暂不支持自动导入旧记录；灵机不会读取它的内部数据库。", nextAction: "暂不支持 · 目前没有可执行操作" };
    return { detail: discovered.reason || "当前没有可用的官方导出方式，灵机不会读取不透明存储。", nextAction: "请使用官方导出，或暂不接入。" };
  }
  if (state === "consent_required") {
    if (discovered.kind === "claude_desktop") return { detail: "Claude 暂不支持自动导入旧记录；灵机不会读取它的内部数据库。", nextAction: "暂不支持 · 目前没有可执行操作" };
    return { detail: discovered.reason || "这个来源需要主人明确确认后才能继续。", nextAction: "确认允许的来源目录后再授权。" };
  }
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
    if (candidate.status === "not_found" && !authorizedByKey.has(key)) continue;
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
    else if (source?.status === "current") state = "current";
    else if (source && scan?.status === "completed") state = scanStateFromProcessing(scan) ?? "scan_completed";
    else if (source) state = "authorized";
    else if (candidate.status === "unsupported") state = "unsupported";
    else if (candidate.status === "consent_required") state = "consent_required";
    else state = "detected";
    const copy = source?.status === "expired"
      ? { detail: "授权已过期，需要重新授权。", nextAction: "重新授权这个来源。" }
      : describe(candidate, state, scan);
    facts.push({ ...candidate, display_name: ownerSourceName(candidate), state, source_id: source?.source_id, root: source?.root ?? candidate.candidate_root, latestScan: scan, ...copy });
  }
  return facts;
}

export class MemorySourcesApi {
  constructor(private readonly api: Pick<LingJiApi, "get" | "post">) {}

  async snapshot(): Promise<MemorySourcesSnapshot> {
    const [discovered, authorized, scans, summary, runtime, panels] = await Promise.all([
      this.api.get<DiscoveredSource[]>("/api/automatic-memory/discovered"),
      this.api.get<AuthorizedSource[]>("/api/automatic-memory/sources"),
      this.api.get<ScanRun[]>("/api/automatic-memory/scans"),
      this.api.get<ScanSummary>("/api/automatic-memory/summary"),
      this.api.get<RuntimeSummary>("/api/automatic-memory/runtime"),
      loadOwnerIntakePanels(this.api),
    ]);
    return {
      discovered, authorized, scans, summary, runtime,
      sources: mergeSourceFacts(discovered, authorized, scans),
      apps: panels.apps,
      processes: panels.processes,
      inboxes: panels.inboxes,
    };
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
  detail(scanId: string, limit = 20, offset = 0): Promise<ScanDetailResponse> {
    const query = new URLSearchParams({ limit: String(limit), offset: String(offset) });
    return this.api.get(`/api/automatic-memory/scans/${encodeURIComponent(scanId)}?${query.toString()}`);
  }
}

export async function findInspectorSourceForAutomaticMemorySource(
  api: Pick<LingJiApi, "get">,
  automaticMemorySourceId: string,
): Promise<SourceItem | null> {
  const query = new URLSearchParams({ q: automaticMemorySourceId, limit: "20", offset: "0" });
  const response = await api.get<PageResponse<SourceItem>>(`/api/memory/inspector/sources?${query.toString()}`);
  return response.items?.find((item) => String(item.metadata?.automatic_memory_source_id ?? "") === automaticMemorySourceId) ?? null;
}

export function countLabel(value: unknown): string {
  return typeof value === "number" && Number.isFinite(value) ? String(value) : "尚未获得";
}

const scanCountKeys = new Set(["created", "queued", "reused", "updated", "skipped", "failed"]);

/**
 * A zero from the legacy ScanRun dataclass is not evidence: queued/reused are
 * defaulted by the model when StateDB has no such measurement. Positive
 * values are evidence, and zero is trusted only when the DTO explicitly
 * marks that field as present.
 */
export function scanCountValue(scan: unknown, key: string): number | undefined {
  if (!scanCountKeys.has(key)) return undefined;
  if (!scan || typeof scan !== "object") return undefined;
  const record = scan as Record<string, unknown>;
  const value = record[key];
  if (typeof value !== "number" || !Number.isFinite(value)) return undefined;
  if (value !== 0) return value;
  const present = record.counts_present;
  return Array.isArray(present) && present.includes(key) ? 0 : undefined;
}

export function scanStatusLabel(status: string | null | undefined): string {
  return ({ running: "扫描中", paused: "已暂停", completed: "已完成", failed: "失败", cancelled: "已取消" } as Record<string, string>)[String(status ?? "")] ?? "尚未获得";
}

export function periodicReconciliationNotice(runtime: RuntimeSummary | null | undefined): string {
  if (runtime?.automation_mode !== "periodic_reconciliation") return "";
  const seconds = Number(runtime.next_reconciliation_seconds ?? runtime.reconciliation_interval_seconds);
  if (!Number.isFinite(seconds) || seconds <= 0) return "打开灵机时会检查，之后自动检查一次；检查时间尚未获得。";
  const minutes = seconds / 60;
  const label = Number.isInteger(minutes) ? String(minutes) : minutes.toFixed(1);
  return `打开灵机时会检查，之后每${label}分钟自动检查一次。`;
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

export function decideOnboardingRoute(input: {
  page: string;
  checked: boolean;
  readsSucceeded: boolean;
  authorized: Array<{ status?: string }>;
  discovered: Array<{ status?: string }>;
}): "memory_sources" | null {
  if (input.checked || !input.readsSucceeded || input.page !== "overview") return null;
  const hasActive = input.authorized.some((item) => ["authorized", "current"].includes(String(item.status)));
  const needsAction = input.discovered.some((item) => ["available", "consent_required"].includes(String(item.status)));
  return !hasActive && needsAction ? "memory_sources" : null;
}

export function authorizationEvidence(
  selection: { kind: string; root: string },
  authorized: Array<{ source_id?: string; kind?: string; root?: string; status?: string }>,
  returnedSourceId?: string,
): boolean {
  return authorized.some((item) => canonicalSourceKey(item.kind, item.root) === canonicalSourceKey(selection.kind, selection.root)
    && ["authorized", "scanning", "current"].includes(String(item.status))
    && (!returnedSourceId || item.source_id === returnedSourceId));
}

export function actionAvailability(state: SourceState, source: { source_id?: string; root?: string; kind?: string; scan_status?: string }): string[] {
  const picker = ["generic_ai_history", "chatgpt_export"].includes(String(source.kind));
  const actions: string[] = [];
  if (["detected", "consent_required", "degraded", "revoked"].includes(state) && (Boolean(source.root) || picker)) actions.push("authorize");
  if (source.source_id && !["revoked", "unsupported"].includes(state)) actions.push("revoke");
  if (source.source_id && ["authorized", "current", "scan_completed", "processing", "imported", "partial_failure", "empty"].includes(state)) actions.push("scan");
  if (source.source_id && source.scan_status === "running") actions.push("pause");
  if (source.source_id && source.scan_status === "paused") actions.push("resume");
  if (source.source_id && source.scan_status === "failed") actions.push("retry");
  if (source.scan_status) actions.push("detail");
  return actions;
}

const CAPABILITY_LABELS: Record<string, string> = {
  auto_discovery: "自动发现",
  requires_authorization: "需要授权",
  official_export_inbox: "官方导出接收",
  session_read: "会话读取",
  message_body_view: "正文查看",
  model_process_status: "模型与进程状态",
};

export function appCapabilityLabels(row: AppSoftwareRow): string[] {
  const capabilities = row.capabilities ?? {};
  return Object.entries(capabilities)
    .filter(([, value]) => value === true)
    .map(([key]) => CAPABILITY_LABELS[key] ?? key);
}

export function appStatusLabel(row: AppSoftwareRow): string {
  return row.supported ? "支持自动读取" : "暂不支持自动读取";
}

export function runningLabel(value: boolean | null | undefined): string {
  return value === true ? "正在运行" : value === false ? "未运行" : "尚未获得";
}

export async function revealInbox(inboxPath: string): Promise<void> {
  const opener = await import("@tauri-apps/plugin-opener");
  await opener.revealItemInDir(inboxPath);
}

export async function loadOwnerIntakePanels(api: Pick<LingJiApi, "get">): Promise<OwnerIntakePanels> {
  const [apps, processes, inboxes] = await Promise.all([
    api.get<AppSoftwareRow[]>("/api/automatic-memory/apps").catch(() => null),
    api.get<ProcessRow[]>("/api/automatic-memory/processes").catch(() => null),
    api.get<ExportInboxRow[]>("/api/automatic-memory/export-inbox").catch(() => null),
  ]);
  return {
    apps: Array.isArray(apps) ? apps : [],
    processes: Array.isArray(processes) ? processes : [],
    inboxes: Array.isArray(inboxes) ? inboxes : [],
  };
}

function healthText(value: unknown): string {
  const normalized = String(value ?? "").trim().toLowerCase();
  if (["healthy", "ok", "pass", "passed", "true"].includes(normalized)) return "正常";
  return normalized ? "需要检查" : "尚未获得";
}

export async function loadModelHealthPanel(api: Pick<LingJiApi, "get">): Promise<ModelHealthPanel> {
  const [inventory, health, brain, memoryStatus] = await Promise.all([
    api.get<Record<string, unknown>>("/api/models").catch(() => null),
    api.get<Record<string, unknown>>("/api/health").catch(() => null),
    api.get<Record<string, unknown>>("/api/brain/status").catch(() => null),
    api.get<Record<string, unknown>>("/api/memory/status").catch(() => null),
  ]);
  const models = Array.isArray(inventory?.models) ? (inventory?.models as Array<Record<string, unknown>>) : null;
  return {
    models: models
      ? models.map((model) => ({
          display_name: String(model.display_name ?? "尚未获得"),
          installed: typeof model.installed === "boolean" ? model.installed : null,
          running: typeof model.running === "boolean" ? model.running : null,
          compatibility_status: String((model.compatibility as Record<string, unknown> | undefined)?.status ?? "") || null,
          parameter_size: (model.parameter_size as string | null) ?? null,
        }))
      : null,
    self_check: healthText((brain?.self_check as Record<string, unknown> | undefined)?.passed),
    system_health: healthText(health?.status),
    memory_health: healthText(memoryStatus?.health),
  };
}

export function compatibilityLabel(status: string | null | undefined): string {
  const normalized = String(status ?? "").trim().toLowerCase();
  if (normalized === "verified") return "已验证";
  if (normalized === "unverified") return "未验证";
  return "尚未获得";
}
