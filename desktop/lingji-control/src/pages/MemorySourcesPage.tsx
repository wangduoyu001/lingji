import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { ApiError, type LingJiApi } from "../api";
import { actionAvailability, actionEvidence, authorizationEvidence, MemorySourcesApi, periodicReconciliationNotice, scanStatusLabel, sourceStateLabel } from "./memorySourcesApi";
import type { MemorySourcesSnapshot, RuntimeSummary, SourceFact, SourceState } from "./memorySourcesTypes";
import { usePollingResource } from "../hooks/usePollingResource";
import { Empty, Notice } from "../components/ui";
import { activeAuthorizedCount } from "./codexWorkspaceContract";

const stateTone: Record<SourceState, string> = {
  detected: "warning",
  consent_required: "warning",
  authorized: "warning",
  scanning: "warning",
  current: "ok",
  degraded: "warning",
  unsupported: "neutral",
  revoked: "neutral",
  failed: "error",
};

function actionError(error: unknown): string {
  if (error instanceof ApiError) return error.message;
  return error instanceof Error ? error.message : "操作没有完成，请稍后重试。";
}

function scanProgress(source: SourceFact): string {
  const scan = source.latestScan;
  if (!scan) return "尚未获得";
  if (scan.progress == null || scan.total == null) return "处理中";
  return `${scan.progress}/${scan.total}`;
}

function isPickerSource(source: SourceFact): boolean {
  return source.kind === "generic_ai_history" || source.kind === "chatgpt_export";
}

export default function MemorySourcesPage({ api, active }: { api: LingJiApi; active: boolean }) {
  const sourceApi = useMemo(() => new MemorySourcesApi(api), [api]);
  const load = useCallback(() => sourceApi.snapshot(), [sourceApi]);
  const resource = usePollingResource<MemorySourcesSnapshot>({ fetcher: load, enabled: active, intervalMs: 8_000, staleAfterMs: 30_000 });
  const [busy, setBusy] = useState<string | null>(null);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [detail, setDetail] = useState<Record<string, unknown> | null>(null);
  const [verifiedSnapshot, setVerifiedSnapshot] = useState<MemorySourcesSnapshot | null>(null);
  const verifiedBaselineRef = useRef<string | null>(null);

  useEffect(() => {
    if (verifiedSnapshot && resource.lastSuccessAt !== verifiedBaselineRef.current) {
      setVerifiedSnapshot(null);
    }
  }, [resource.lastSuccessAt, verifiedSnapshot]);

  const runAction = async (key: string, operation: () => Promise<unknown>, verify: (next: MemorySourcesSnapshot) => boolean, success = "") => {
    if (busy) return;
    setBusy(key);
    setMessage("");
    setError("");
    try {
      await operation();
      // Refresh from the server again and verify that fresh snapshot.  The
      // polling hook intentionally keeps its previous data while refreshing,
      // so reading resource.data here would verify a stale closure.
      const next = await sourceApi.snapshot();
      if (!verify(next)) throw new Error("后端还没有返回可确认的状态，请稍后查看。");
      // Hold the verified post-action facts in the rendered state until the
      // polling hook has completed its own fresh read. This prevents an older
      // in-flight poll from briefly replacing a confirmed action result.
      verifiedBaselineRef.current = resource.lastSuccessAt;
      setVerifiedSnapshot(next);
      await resource.refresh({ force: true });
      if (success) setMessage(success);
    } catch (reason) {
      setError(actionError(reason));
    } finally {
      setBusy(null);
    }
  };

  const chooseFolder = async (source: SourceFact): Promise<string | null> => {
    try {
      const { open } = await import("@tauri-apps/plugin-dialog");
      const selected = await open({ directory: true, multiple: false, title: `选择${source.display_name}目录` });
      return typeof selected === "string" ? selected : null;
    } catch (reason) {
      setError(actionError(reason));
      return null;
    }
  };

  const authorize = async (source: SourceFact) => {
    let root = source.root;
    if (isPickerSource(source)) {
      const selected = await chooseFolder(source);
      if (!selected) return;
      root = selected;
    }
    let returnedSourceId: string | undefined;
    await runAction(`authorize:${source.kind}`, async () => {
      const result = await sourceApi.authorize(source, root);
      if (result && typeof result === "object" && "source_id" in result) returnedSourceId = String((result as { source_id: unknown }).source_id);
      return result;
    }, (next) => authorizationEvidence({ kind: source.kind, root }, next.authorized, returnedSourceId), "已记录授权，正在准备首轮扫描。请等待扫描状态变为“已接管”。");
  };

  const snapshot = verifiedSnapshot ?? resource.data;
  if (!active) return <Empty text="连接灵机核心后才能查看记忆来源。" />;
  if (resource.loading && !snapshot) return <div className="empty-state" aria-busy="true">正在读取已发现的来源…</div>;
  if (resource.error && !snapshot) return <div className="stack"><Notice kind="error">暂时无法读取记忆来源：{resource.error.message}。请确认灵机核心正在运行后重试。</Notice><button className="button secondary" onClick={() => void resource.refresh()}>重新读取</button></div>;
  if (!snapshot) return <Empty text="尚未获得来源信息。请稍后重试。" />;
  const periodicNotice = periodicReconciliationNotice(snapshot.runtime);

  return (
    <div className="stack memory-sources-page">
      <section className="memory-sources-intro">
        <div>
          <span className="desktop-eyebrow">FIRST RUN · MEMORY SOURCES</span>
          <h2>让灵机知道哪些内容可以接管</h2>
          <p>灵机只读取你明确授权的目录。先看见来源，再决定是否授权；“已发现”不等于“已接管”。</p>
        </div>
        <button className="button secondary" disabled={resource.refreshing} onClick={() => void resource.refresh()}>{resource.refreshing ? "读取中…" : "重新读取"}</button>
      </section>
      {resource.stale && <Notice kind="warning">当前显示的是上一次成功读取的结果，正在重试。请不要把过期状态当成当前状态。</Notice>}
      {resource.error && snapshot && <Notice kind="warning">暂时无法读取记忆来源：{resource.error.message}。已保留上一次成功结果，请点击“重新读取”恢复。</Notice>}
      {error && <Notice kind="error">{error}</Notice>}
      {message && <Notice kind="info">{message}</Notice>}
      {snapshot.runtime?.cleanup_pending && <Notice kind="error">临时文件清理失败：灵机会自动重试，可重试。</Notice>}
      {periodicNotice && <Notice kind="info">{periodicNotice}</Notice>}
      <section className="memory-sources-summary" aria-label="来源总览">
        <div><span>已发现来源</span><strong>{snapshot.discovered.length}</strong><small>已授权 {activeAuthorizedCount(snapshot.authorized)} 个</small></div>
        <div><span>当前接管</span><strong>{snapshot.sources.filter((item) => item.state === "current").length}</strong><small>扫描完成后才算接管</small></div>
        <div><span>最近活动</span><strong>{snapshot.summary?.latest?.status ? scanStatusLabel(snapshot.summary.latest.status) : "尚未获得"}</strong><small>{runtimeHeartbeatLabel(snapshot.runtime)}</small></div>
      </section>
      {snapshot.sources.length === 0 ? <Empty text="尚未发现可接入的来源。可以稍后重新读取；灵机不会自行扩大读取范围。" /> : (
        <section className="memory-source-list" aria-label="记忆来源列表">
          {snapshot.sources.map((source) => <SourceCard key={`${source.kind}:${source.root}`} source={source} busy={busy} onAuthorize={() => void authorize(source)} onAction={runAction} sourceApi={sourceApi} onDetail={setDetail} />)}
        </section>
      )}
      {detail && <section className="panel memory-scan-detail" aria-live="polite"><h2>扫描结果</h2><div className="panel-body"><p>这是后端返回的本次扫描结果，可用于核对新增、复用和错误。</p><dl className="memory-detail-grid">{Object.entries(detail).filter(([key]) => ["status", "progress", "total", "queued", "reused", "last_error"].includes(key)).map(([key, value]) => <div key={key}><dt>{key === "status" ? "状态" : key === "progress" ? "进度" : key === "total" ? "总数" : key === "queued" ? "新增" : key === "reused" ? "复用" : "错误"}</dt><dd>{value == null || value === "" ? "尚未获得" : String(value)}</dd></div>)}</dl><details><summary>技术详情</summary><pre className="json-panel">{JSON.stringify(detail, null, 2)}</pre></details></div></section>}
    </div>
  );
}

function runtimeHeartbeatLabel(runtime: RuntimeSummary | null): string {
  if (!runtime) return "尚未获得后台状态";
  if (runtime.state === "degraded" || runtime.scheduler_heartbeat_state === "degraded") {
    return runtime.scheduler_heartbeat_reason || runtime.scheduler_heartbeat_last_error || "需要检查后台状态";
  }
  if (runtime.state === "stopped" || runtime.scheduler_heartbeat_state === "stopped") return "后台已停止";
  if (runtime.state === "paused" || runtime.scheduler_heartbeat_state === "paused") return "后台已暂停，仍在确认状态";
  if (runtime.state === "running" && runtime.scheduler_heartbeat_age != null) return "后台状态持续更新";
  return "尚未获得后台状态";
}

function SourceCard({ source, busy, onAuthorize, onAction, sourceApi, onDetail }: { source: SourceFact; busy: string | null; onAuthorize: () => void; onAction: (key: string, operation: () => Promise<unknown>, verify: (next: MemorySourcesSnapshot) => boolean, success?: string) => Promise<void>; sourceApi: MemorySourcesApi; onDetail: (detail: Record<string, unknown>) => void }) {
  const scan = source.latestScan;
  const key = source.source_id || source.kind;
  const actions = actionAvailability(source.state, { source_id: source.source_id, root: source.root, kind: source.kind, scan_status: scan?.status });
  const canAuthorize = actions.includes("authorize");
  const canScan = actions.includes("scan");
  const canPause = actions.includes("pause");
  const canRetry = actions.includes("retry");
  const canRevoke = actions.includes("revoke");
  const invoke = (action: string, operation: () => Promise<unknown>, verify: (next: MemorySourcesSnapshot) => boolean, success?: string) => onAction(`${action}:${key}`, operation, verify, success);
  const showDetail = async () => {
    if (!scan?.scan_id) return;
    try { onDetail(await sourceApi.detail(scan.scan_id) as Record<string, unknown>); } catch (reason) { onDetail({ status: "failed", last_error: actionError(reason) }); }
  };
  return <article className={`memory-source-card memory-source-${stateTone[source.state]}`} data-source-kind={source.kind}>
    <div className="memory-source-card-header"><div><span className="memory-source-kind">{source.display_name}</span><h3>{sourceStateLabel(source.state)}</h3></div><span className={`pill ${stateTone[source.state]}`}>{sourceStateLabel(source.state)}</span></div>
    <p className="memory-source-detail">{source.detail}</p>
    <div className="memory-source-facts"><div><span>找到什么</span><strong>{source.display_name}</strong></div><div><span>本次进度</span><strong>{scanProgress(source)}</strong></div><div><span>下一步</span><strong>{source.nextAction}</strong></div></div>
    <div className="memory-source-actions">
      {canAuthorize && <button className="button primary" disabled={Boolean(busy)} onClick={onAuthorize}>{busy?.startsWith("authorize:") ? "授权中…" : isPickerSource(source) ? "选择文件夹并授权" : "授权"}</button>}
      {canRevoke && <button className="button danger" disabled={Boolean(busy)} onClick={() => void invoke("revoke", () => sourceApi.revoke(source.source_id!), (next) => next.sources.some((item) => item.source_id === source.source_id && item.state === "revoked"), "已撤销授权；灵机不会再读取这个来源。")}>撤销</button>}
      {canScan && <button className="button secondary" disabled={Boolean(busy)} onClick={() => void invoke("scan", () => sourceApi.scan(source.source_id!), (next) => actionEvidence(next, source.source_id!, "scan"))}>立即扫描</button>}
      {canPause && <button className="button secondary" disabled={Boolean(busy)} onClick={() => void invoke("pause", () => sourceApi.pause(scan!.scan_id), (next) => actionEvidence(next, source.source_id!, "pause"))}>暂停</button>}
      {actions.includes("resume") && <button className="button secondary" disabled={Boolean(busy)} onClick={() => void invoke("resume", () => sourceApi.resume(scan!.scan_id), (next) => actionEvidence(next, source.source_id!, "resume"))}>继续</button>}
      {canRetry && <button className="button warning" disabled={Boolean(busy)} onClick={() => void invoke("retry", () => sourceApi.retry(scan!.scan_id), (next) => actionEvidence(next, source.source_id!, "retry"))}>重试</button>}
      {actions.includes("detail") && <button className="button secondary" disabled={Boolean(busy)} onClick={() => void showDetail()}>查看结果</button>}
    </div>
    {!canAuthorize && source.state === "consent_required" && <small className="memory-source-reason">需要先确认一个受支持的目录；当前没有可安全授权的路径。</small>}
    {source.latestScan?.last_error && <small className="memory-source-error">后端原因：{source.latestScan.last_error}</small>}
  </article>;
}
