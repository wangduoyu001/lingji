import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { ApiError, type LingJiApi } from "../api";
import { Empty, Notice } from "../components/ui";
import type { CaptureInspectorTarget } from "./captureCenterTypes";
import {
  actionAvailability,
  actionEvidence,
  authorizationEvidence,
  canonicalSourceKey,
  countLabel,
  findInspectorSourceForAutomaticMemorySource,
  MemorySourcesApi,
  ownerSourceName,
  periodicReconciliationNotice,
  scanStatusLabel,
  sourceMetadataEvidence,
  sourceStateLabel,
} from "./memorySourcesApi";
import type { MemorySourcesSnapshot, ScanDetailResponse, SourceFact, SourceState } from "./memorySourcesTypes";
import { usePollingResource } from "../hooks/usePollingResource";

const stateTone: Record<SourceState, string> = {
  detected: "warning",
  consent_required: "warning",
  authorized: "warning",
  scanning: "warning",
  scan_completed: "warning",
  processing: "warning",
  imported: "ok",
  partial_failure: "warning",
  empty: "neutral",
  current: "ok",
  degraded: "warning",
  unsupported: "neutral",
  revoked: "neutral",
  failed: "error",
};

const DETAIL_LIMIT = 20;

function actionError(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.status === 0) return "当前无法连接灵机，请检查连接后重试。";
    if (error.status === 401 || error.status === 403) return "当前没有完成这项操作，请重新确认来源后重试。";
    if (error.status === 409) return "来源状态刚刚变化，请刷新后再试。";
  }
  return "来源操作没有完成，请稍后重试。";
}

function isPickerSource(source: SourceFact): boolean {
  return source.kind === "generic_ai_history" || source.kind === "chatgpt_export";
}

function sourceKey(source: SourceFact): string {
  return source.source_id ?? canonicalSourceKey(source.kind, source.root);
}

function actionKey(source: SourceFact, action: string): string {
  return `${action}:${sourceKey(source)}`;
}

function detailKey(source: SourceFact): string {
  return `detail:${sourceKey(source)}`;
}

function feedbackKey(source: SourceFact): string {
  return sourceKey(source);
}

type NoticeState = { kind: "info" | "warning" | "error"; text: string };
type SourceNoticeState = { kind: "info" | "success" | "error"; text: string };
type DetailState = { response: ScanDetailResponse; offset: number };

export default function MemorySourcesPage({ api, active, onOpenInspector }: { api: LingJiApi; active: boolean; onOpenInspector?: (target: CaptureInspectorTarget) => void }) {
  const sourceApi = useMemo(() => new MemorySourcesApi(api), [api]);
  const load = useCallback(() => sourceApi.snapshot(), [sourceApi]);
  const resource = usePollingResource<MemorySourcesSnapshot>({ fetcher: load, enabled: active, intervalMs: 8_000, staleAfterMs: 30_000 });
  const [busyKeys, setBusyKeys] = useState<Record<string, boolean>>({});
  const [pageNotice, setPageNotice] = useState<NoticeState | null>(null);
  const [sourceNotices, setSourceNotices] = useState<Record<string, SourceNoticeState>>({});
  const [scanDetails, setScanDetails] = useState<Record<string, DetailState>>({});
  const [verifiedSnapshot, setVerifiedSnapshot] = useState<MemorySourcesSnapshot | null>(null);
  const verifiedBaselineRef = useRef<string | null>(null);

  useEffect(() => {
    if (verifiedSnapshot && resource.lastSuccessAt !== verifiedBaselineRef.current) {
      setVerifiedSnapshot(null);
    }
  }, [resource.lastSuccessAt, verifiedSnapshot]);

  const setBusy = (key: string, value: boolean) => {
    setBusyKeys((prev) => {
      const next = { ...prev };
      if (value) next[key] = true;
      else delete next[key];
      return next;
    });
  };

  const setSourceNotice = (source: SourceFact, notice: SourceNoticeState) => {
    setSourceNotices((prev) => ({ ...prev, [feedbackKey(source)]: notice }));
  };

  const runAction = async (
    source: SourceFact,
    key: string,
    operation: () => Promise<unknown>,
    verify: (next: MemorySourcesSnapshot) => boolean,
    success: string,
  ) => {
    if (busyKeys[key]) return;
    setBusy(key, true);
    setPageNotice(null);
    try {
      await operation();
      const next = await sourceApi.snapshot();
      if (!verify(next)) throw new Error("后端还没有返回可确认的状态，请稍后查看。");
      verifiedBaselineRef.current = resource.lastSuccessAt;
      setVerifiedSnapshot(next);
      await resource.refresh({ force: true });
      setSourceNotice(source, { kind: "success", text: success });
    } catch (reason) {
      setSourceNotice(source, { kind: "error", text: actionError(reason) });
    } finally {
      setBusy(key, false);
    }
  };

  const chooseFolder = async (source: SourceFact): Promise<string | null> => {
    try {
      const { open } = await import("@tauri-apps/plugin-dialog");
      const selected = await open({ directory: true, multiple: false, title: `选择${source.display_name}目录` });
      if (typeof selected !== "string") {
        setPageNotice({ kind: "info", text: "未选择目录，本次未开始，原授权和数据没有变化。" });
        return null;
      }
      return selected;
    } catch (reason) {
      setPageNotice({ kind: "error", text: actionError(reason) });
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
    await runAction(
      source,
      actionKey(source, "authorize"),
      async () => {
        const result = await sourceApi.authorize(source, root);
        if (result && typeof result === "object" && "source_id" in result) returnedSourceId = String((result as { source_id: unknown }).source_id);
        return result;
      },
      (next) => authorizationEvidence({ kind: source.kind, root }, next.authorized, returnedSourceId),
      "已记录授权，正在准备首次检查。",
    );
  };

  const openScanDetail = async (source: SourceFact, offset = 0) => {
    const scan = source.latestScan;
    if (!scan?.scan_id) return;
    const key = detailKey(source);
    if (busyKeys[key]) return;
    setBusy(key, true);
    setPageNotice(null);
    try {
      const response = await sourceApi.detail(scan.scan_id, DETAIL_LIMIT, offset);
      setScanDetails((prev) => ({ ...prev, [sourceKey(source)]: { response, offset } }));
      setSourceNotice(source, { kind: "success", text: `已读取这次检查的第 ${Math.floor(offset / DETAIL_LIMIT) + 1} 页安全详情。` });
    } catch (reason) {
      setSourceNotice(source, { kind: "error", text: actionError(reason) });
    } finally {
      setBusy(key, false);
    }
  };

  const openImportedContent = async (source: SourceFact) => {
    if (!source.source_id) return;
    const key = actionKey(source, "imported-content");
    if (busyKeys[key]) return;
    setBusy(key, true);
    setPageNotice(null);
    try {
      if (!onOpenInspector) throw new Error("当前页面还没有连接到 Memory Inspector。");
      const inspectorSource = await findInspectorSourceForAutomaticMemorySource(api, source.source_id);
      if (!inspectorSource?.source_id) throw new Error("没有找到能精确对应这次导入的 Memory Inspector 来源。");
      onOpenInspector({ source_id: inspectorSource.source_id });
      setSourceNotice(source, { kind: "success", text: "已打开精确匹配的已导入具体内容。" });
    } catch (reason) {
      setSourceNotice(source, { kind: "error", text: actionError(reason) });
    } finally {
      setBusy(key, false);
    }
  };

  const snapshot = verifiedSnapshot ?? resource.data;
  if (!active) return <Empty text="连接灵机核心后才能查看记忆来源。" />;
  if (resource.loading && !snapshot) return <div className="empty-state" aria-busy="true">正在读取已发现的来源…</div>;
  if (resource.error && !snapshot) return <div className="stack"><Notice kind="error">暂时无法读取记忆来源。请确认灵机核心正在运行后重试。</Notice><button className="button secondary" onClick={() => void resource.refresh()}>现在检查</button></div>;
  if (!snapshot) return <Empty text="尚未获得来源信息。请稍后重试。" />;

  const periodicNotice = periodicReconciliationNotice(snapshot.runtime);

  return (
    <div className="stack memory-sources-page">
      <section className="memory-sources-intro">
        <div>
          <span className="section-kicker">自动接管</span>
          <h2>来源</h2>
          <p>这里显示灵机正在自动接管的记录。授权一次后，扫描、整理和更新都会自动进行。</p>
        </div>
        <span className="auto-refresh-note">{resource.refreshing ? "正在更新" : "自动更新"}</span>
      </section>

      {pageNotice && <Notice kind={pageNotice.kind}>{pageNotice.text}</Notice>}
      {resource.stale && <Notice kind="warning">当前显示的是上一次成功读取的结果，正在重试。请不要把过期状态当成当前状态。</Notice>}
      {resource.error && snapshot && <Notice kind="warning">暂时无法读取记忆来源，已保留上一次成功结果。灵机会自动重试。</Notice>}
      {periodicNotice && <Notice kind="info">{periodicNotice}</Notice>}
      {snapshot.runtime?.cleanup_pending && <Notice kind="error">临时文件清理失败：灵机会自动重试，可重试。</Notice>}
      <p className="memory-sources-summary" aria-label="来源总览">{sourceSummary(snapshot)}</p>

      {snapshot.sources.length === 0 ? (
        <Empty text="暂时没有可连接的记录来源。灵机会自动重试，不会自行扩大读取范围。" />
      ) : (
        <section className="memory-source-list" aria-label="记忆来源列表">
          {snapshot.sources.map((source) => (
            <SourceCard
              key={`${source.kind}:${source.root}`}
              source={source}
              busyKeys={busyKeys}
              notice={sourceNotices[feedbackKey(source)]}
              detail={scanDetails[sourceKey(source)] ?? null}
              onAuthorize={() => void authorize(source)}
              onOpenScanDetail={(offset) => void openScanDetail(source, offset)}
              onOpenImportedContent={() => void openImportedContent(source)}
              onAction={runAction}
              sourceApi={sourceApi}
            />
          ))}
        </section>
      )}
    </div>
  );
}

function sourceSummary(snapshot: MemorySourcesSnapshot): string {
  const sources = Array.isArray(snapshot.sources) ? snapshot.sources : [];
  const discoveredCount = countLabel(sources.length);
  const authorizedCount = countLabel(sources.filter((item) => ["authorized", "scanning", "scan_completed", "processing", "imported", "partial_failure", "empty", "current"].includes(item.state)).length);
  const scanCompletedCount = countLabel(sources.filter((item) => item.state === "scan_completed").length);
  const importedCount = countLabel(sources.filter((item) => item.state === "imported").length);
  const counts = `发现 ${discoveredCount} 个来源 · 已授权 ${authorizedCount} 个 · 扫描完成 ${scanCompletedCount} 个 · 已导入 ${importedCount} 个。`;
  const current = sources.filter((item) => item.state === "current").map(ownerSourceName);
  if (current.length) return `${counts}当前正在记住：${current.join("、")}。`;
  const connectable = sources.some((item) => {
    if (item.state === "unsupported") return false;
    if (item.kind === "claude_desktop" && !item.root && !["authorized", "current", "scanning", "degraded", "failed", "revoked"].includes(item.state)) return false;
    return Boolean(item.root || item.source_id || ["authorized", "current", "scanning", "degraded", "failed", "revoked"].includes(item.state));
  });
  if (connectable) return `${counts}已找到可连接的内容，完成选择和检查后才会开始记住。`;
  if (!Array.isArray(snapshot.sources)) return `${counts}来源状态尚未获得。`;
  return `${counts}暂时没有可连接的记录来源。`;
}

function scanDetailCopy(detail: ScanDetailResponse): string {
  const processingStatus = String(detail.processing_status ?? detail.status ?? "").toLowerCase();
  if (processingStatus === "running") return "这次检查正在进行。";
  if (processingStatus === "failed") return "这次检查没有完成，原来的记忆不会被删除。";
  if (processingStatus === "scan_completed") return "这次检查已经完成，但还没有看到导入完成证据。";
  if (processingStatus === "processing") return "正在提取来源内容，导入证据还在累积。";
  if (processingStatus === "imported") return "来源内容已导入完成，可以查看已导入具体内容。";
  if (processingStatus === "partial_failure") return "已经导入了一部分内容，但也有项目失败。";
  if (processingStatus === "empty") return "扫描完成了，但目录里没有可导入内容。";
  if (processingStatus === "unsupported_format") return "这个来源暂不支持当前格式。";
  return "这次检查的状态尚未获得。";
}

function detailPageLabel(detail: DetailState): string {
  const pagination = detail.response.items_pagination;
  const page = Math.floor(detail.offset / DETAIL_LIMIT) + 1;
  if (!pagination?.total) return `第 ${page} 页`;
  return `第 ${page} 页 / 共 ${Math.max(1, Math.ceil(pagination.total / DETAIL_LIMIT))} 页`;
}

function SourceCard({
  source,
  busyKeys,
  notice,
  detail,
  onAuthorize,
  onOpenScanDetail,
  onOpenImportedContent,
  onAction,
  sourceApi,
}: {
  source: SourceFact;
  busyKeys: Record<string, boolean>;
  notice: SourceNoticeState | undefined;
  detail: DetailState | null;
  onAuthorize: () => void;
  onOpenScanDetail: (offset: number) => void;
  onOpenImportedContent: () => void;
  onAction: (source: SourceFact, key: string, operation: () => Promise<unknown>, verify: (next: MemorySourcesSnapshot) => boolean, success: string) => Promise<void>;
  sourceApi: MemorySourcesApi;
}) {
  const scan = source.latestScan;
  const key = sourceKey(source);
  const actions = actionAvailability(source.state, { source_id: source.source_id, root: source.root, kind: source.kind, scan_status: scan?.status });
  const metadata = sourceMetadataEvidence(source);
  const currentNotice = notice ?? null;
  const canStop = actions.includes("revoke");
  const canScan = actions.includes("scan");
  const canPause = actions.includes("pause");
  const canResume = actions.includes("resume");
  const canRetry = actions.includes("retry");
  const canDetail = actions.includes("detail") || Boolean(scan?.scan_id);
  const canOpenImportedContent = source.state === "imported" && Boolean(source.source_id);
  const importedContentBusy = busyKeys[actionKey(source, "imported-content")];
  const canShowNextStep = source.state !== "unsupported" && !(source.kind === "claude_desktop" && source.nextAction.startsWith("暂不支持"));

  const openDetail = () => onOpenScanDetail(0);
  const actionDetailKey = detailKey(source);

  const renderScanDetail = () => {
    if (!detail) return null;
    const items = detail.response.items ?? [];
    const pagination = detail.response.items_pagination;
    const page = Math.floor(detail.offset / DETAIL_LIMIT) + 1;
    const totalPages = pagination?.total ? Math.max(1, Math.ceil(pagination.total / DETAIL_LIMIT)) : null;
    const previousOffset = Math.max(0, detail.offset - DETAIL_LIMIT);
    const nextOffset = detail.offset + DETAIL_LIMIT;
    const canPrev = detail.offset > 0;
    const canNext = Boolean(pagination?.has_more || (pagination?.total != null && nextOffset < pagination.total));

    return (
      <section className="memory-source-scan-panel" aria-live="polite">
        <div className="memory-source-scan-header">
          <div>
            <h4>这次检查</h4>
            <p>{scanDetailCopy(detail.response)}</p>
          </div>
          <span className="pill neutral">{detailPageLabel(detail)}</span>
        </div>
        <div className="memory-source-scan-meta">
          <span>结果：{scanStatusLabel(detail.response.status)}</span>
          <span>处理状态：{sourceStateLabel(String(detail.response.processing_status ?? "scan_completed"))}</span>
          <span>已检查：{countLabel(detail.response.progress)}</span>
          <span>总数：{countLabel(detail.response.total)}</span>
        </div>
        <div className="memory-source-scan-items">
          {items.length ? items.map((item) => (
            <article className="memory-source-scan-item" key={item.item_id}>
              <strong>{item.name ?? "尚未获得"}</strong>
              <span>阶段：{item.stage ?? "尚未获得"} · 结果：{item.result ?? "尚未获得"}</span>
              <span>来源：{item.source ?? "尚未获得"} · 更新：{item.updated_at ?? "尚未获得"}</span>
              <span>可重试：{item.retryable === true ? "是" : item.retryable === false ? "否" : "尚未获得"}</span>
              <small>
                {[
                  item.reason,
                  item.imported_sources != null ? `来源 ${item.imported_sources}` : null,
                  item.imported_conversations != null ? `对话 ${item.imported_conversations}` : null,
                  item.imported_messages != null ? `消息 ${item.imported_messages}` : null,
                ].filter(Boolean).join(" · ") || "安全详情尚未获得"}
              </small>
            </article>
          )) : <p className="memory-source-empty-detail">这次检查没有可显示的安全详情。</p>}
        </div>
        <div className="memory-source-scan-pagination">
          <button className="button secondary" disabled={!canPrev || busyKeys[actionDetailKey]} onClick={() => onOpenScanDetail(previousOffset)}>上一页</button>
          <span>{page}{totalPages ? ` / ${totalPages}` : ""}</span>
          <button className="button secondary" disabled={!canNext || busyKeys[actionDetailKey]} onClick={() => onOpenScanDetail(nextOffset)}>下一页</button>
        </div>
      </section>
    );
  };

  return (
    <article className={`memory-source-card memory-source-${stateTone[source.state]}`} data-source-kind={source.kind} data-source-id={source.source_id ?? key}>
      <div className="memory-source-card-header">
        <div>
          <span className="memory-source-kind">{source.display_name}</span>
          <h3>{sourceStateLabel(source.state)}</h3>
        </div>
        <span className={`pill ${stateTone[source.state] === "error" ? "danger" : stateTone[source.state]}`}>{sourceStateLabel(source.state)}</span>
      </div>

      <p className="memory-source-detail">{source.detail}</p>
      {source.kind === "codex_rollout" && (
        <div className="memory-source-metadata" aria-label="安全元数据">
          <span>文件数：{metadata.fileCount}</span>
          <span>占用空间：{metadata.byteCount}</span>
          <span>最早记录：{metadata.earliestMtime}</span>
          <span>最近记录：{metadata.latestMtime}</span>
        </div>
      )}
      <div className="memory-source-facts">
        <span>{source.state === "current" ? "已接管" : sourceStateLabel(source.state)}</span>
        {scan?.updated_at && <span>最近检查：{new Date(String(scan.updated_at)).toLocaleString()}</span>}
        {scan?.processing_status && <span>处理进度：{sourceStateLabel(scan.processing_status)}</span>}
        {scan?.status && <span>检查状态：{scanStatusLabel(scan.status)}</span>}
        {source.state === "imported" && scan?.processing_completed != null && <span>已导入 {scan.processing_completed} 项</span>}
        {source.state === "partial_failure" && scan?.processing_failed != null && <span>失败 {scan.processing_failed} 项</span>}
        {source.state === "processing" && scan?.processing_pending != null && <span>待处理 {scan.processing_pending} 项</span>}
      </div>

      {currentNotice && <p className={`memory-source-feedback memory-source-feedback-${currentNotice.kind}`} aria-live="polite">{currentNotice.text}</p>}
      {canShowNextStep && <p className="memory-source-next">下一步：{source.nextAction}</p>}

      <div className="memory-source-primary-actions">
        {actions.includes("authorize") && (
          <button className="button primary" disabled={Boolean(busyKeys[actionKey(source, "authorize")])} onClick={onAuthorize}>
            {busyKeys[actionKey(source, "authorize")] ? "准备中…" : source.kind === "codex_rollout" ? "允许接管 Codex" : source.kind === "chatgpt_export" ? "选择官方导出目录" : isPickerSource(source) ? "选择文件夹并开始记忆" : "开始记忆"}
          </button>
        )}
        {canStop && (
          <button
            className="button danger"
            disabled={Boolean(busyKeys[actionKey(source, "revoke")])}
            onClick={() => void onAction(source, actionKey(source, "revoke"), () => sourceApi.revoke(source.source_id!), (next) => next.sources.some((item) => item.source_id === source.source_id && item.state === "revoked"), "已停止记忆这个来源。")}
          >
            {busyKeys[actionKey(source, "revoke")] ? "停止中…" : "停止记忆"}
          </button>
        )}
        {canScan && (
          <button
            className="button secondary"
            disabled={Boolean(busyKeys[actionKey(source, "scan")])}
            onClick={() => void onAction(source, actionKey(source, "scan"), () => sourceApi.scan(source.source_id!), (next) => actionEvidence(next, source.source_id!, "scan"), "已开始新的检查。")}
          >
            {busyKeys[actionKey(source, "scan")] ? "检查中…" : "现在检查"}
          </button>
        )}
        {canDetail && (
          <button className="button secondary" disabled={Boolean(busyKeys[actionDetailKey])} onClick={openDetail}>
            {busyKeys[actionDetailKey] ? "读取中…" : "查看这次检查"}
          </button>
        )}
        {canOpenImportedContent && (
          <button className="button secondary" disabled={Boolean(importedContentBusy)} onClick={() => void onOpenImportedContent()}>
            {importedContentBusy ? "打开中…" : "查看已导入具体内容"}
          </button>
        )}
      </div>

      {(canPause || canResume || canRetry) && (
        <details className="memory-source-fallback-actions">
          <summary>备用操作</summary>
          <div className="memory-source-actions">
            {canPause && (
              <button className="button secondary" disabled={Boolean(busyKeys[actionKey(source, "pause")])} onClick={() => void onAction(source, actionKey(source, "pause"), () => sourceApi.pause(scan!.scan_id), (next) => actionEvidence(next, source.source_id!, "pause"), "已暂停这次检查。")}>
                {busyKeys[actionKey(source, "pause")] ? "暂停中…" : "暂停检查"}
              </button>
            )}
            {canResume && (
              <button className="button secondary" disabled={Boolean(busyKeys[actionKey(source, "resume")])} onClick={() => void onAction(source, actionKey(source, "resume"), () => sourceApi.resume(scan!.scan_id), (next) => actionEvidence(next, source.source_id!, "resume"), "已继续这次检查。")}>
                {busyKeys[actionKey(source, "resume")] ? "继续中…" : "继续检查"}
              </button>
            )}
            {canRetry && (
              <button className="button warning" disabled={Boolean(busyKeys[actionKey(source, "retry")])} onClick={() => void onAction(source, actionKey(source, "retry"), () => sourceApi.retry(scan!.scan_id), (next) => actionEvidence(next, source.source_id!, "retry"), "已重新检查。")}>
                {busyKeys[actionKey(source, "retry")] ? "重试中…" : "再次检查"}
              </button>
            )}
          </div>
        </details>
      )}

      {!canStop && source.state === "consent_required" && <small className="memory-source-reason">需要先确认一个受支持的目录；当前没有可安全授权的路径。</small>}

      {detail && renderScanDetail()}
    </article>
  );
}
