import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { ReactNode } from "react";
import { Empty, Metric, Notice, Panel, bytes } from "../components/ui";
import type { BrainStatusSummary, EmbeddingStatus, MemoryStatus, PageProps, RuntimeWarning, VectorCoverage, VectorStatus } from "../types";

const REFRESH_INTERVAL_MS = 15_000;
const DEFAULT_MISSING_LIMIT = 20;
const STATE_LABELS: Record<string, string> = {
  healthy: "健康", ready: "Ready", degraded: "降级", stale: "快照过期", disabled: "未启用",
  configuration_required: "需要配置", unavailable: "不可用", failed: "失败", rebuild_required: "需要重建",
};

function text(value: unknown, fallback = "-"): string { return value === undefined || value === null || value === "" ? fallback : String(value); }
function count(value: number | null | undefined): string { return value === null || value === undefined ? "-" : value.toLocaleString(); }
function time(value: string | null | undefined): string {
  if (!value) return "-";
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? value : parsed.toLocaleString();
}
function percentage(value: number | null | undefined): string { return value === null || value === undefined ? "-" : `${(value * 100).toFixed(2)}%`; }
function stateTone(value: string | null | undefined): string {
  if (value === "healthy" || value === "ready") return "success";
  if (value === "degraded" || value === "stale" || value === "configuration_required") return "warning";
  if (value === "unavailable" || value === "failed" || value === "rebuild_required") return "error";
  return "neutral";
}
function StatusBadge({ value }: { value: string | null | undefined }) {
  const normalized = value || "unknown";
  return <span className={`pill ${stateTone(normalized)}`}>{STATE_LABELS[normalized] || normalized}</span>;
}
function BooleanBadge({ value, trueLabel = "是", falseLabel = "否" }: { value: boolean | undefined; trueLabel?: string; falseLabel?: string }) {
  if (value === undefined) return <span className="pill neutral">未知</span>;
  return <span className={`pill ${value ? "success" : "neutral"}`}>{value ? trueLabel : falseLabel}</span>;
}
function DetailList({ items }: { items: Array<{ label: string; value: ReactNode }> }) {
  return <dl className="detail-list">{items.map((item) => <div key={item.label}><dt>{item.label}</dt><dd>{item.value}</dd></div>)}</dl>;
}
function CoverageBar({ value, expected }: { value: number | null; expected: number | null }) {
  const percent = value === null ? 0 : Math.min(Math.max(value * 100, 0), 100);
  const tone = value === null ? "unknown" : value === 1 ? "good" : value > 0 ? "warning" : (expected || 0) > 0 ? "error" : "unknown";
  return <div className="coverage-visual" aria-label={`向量覆盖率 ${percentage(value)}`}><div className="coverage-bar"><span className={`coverage-fill ${tone}`} style={{ width: `${percent}%` }} /></div><strong>{percentage(value)}</strong></div>;
}
function errorMessage(reason: unknown): string { return reason instanceof Error ? reason.message : String(reason); }
function latestTimestamp(values: Array<string | null | undefined>): string | null {
  const valid = values.filter((value): value is string => Boolean(value));
  if (!valid.length) return null;
  return valid.reduce((latest, value) => {
    const currentTime = new Date(value).getTime();
    const latestTime = new Date(latest).getTime();
    if (Number.isNaN(currentTime)) return latest;
    return Number.isNaN(latestTime) || currentTime > latestTime ? value : latest;
  });
}

export default function VectorCenterPage({ api, active }: PageProps) {
  const [memory, setMemory] = useState<MemoryStatus | null>(null);
  const [vector, setVector] = useState<VectorStatus | null>(null);
  const [coverage, setCoverage] = useState<VectorCoverage | null>(null);
  const [brain, setBrain] = useState<BrainStatusSummary | null>(null);
  const [memoryError, setMemoryError] = useState("");
  const [vectorError, setVectorError] = useState("");
  const [coverageError, setCoverageError] = useState("");
  const [brainError, setBrainError] = useState("");
  const [refreshing, setRefreshing] = useState(false);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [lastAttemptAt, setLastAttemptAt] = useState<string | null>(null);
  const [showAllMissing, setShowAllMissing] = useState(false);
  const inFlight = useRef(false);

  const load = useCallback(async () => {
    if (!active || inFlight.current) return;
    inFlight.current = true;
    setRefreshing(true);
    const [memoryResult, vectorResult, coverageResult, brainResult] = await Promise.allSettled([
      api.get<MemoryStatus>("/api/memory/status"), api.get<VectorStatus>("/api/vector/status"),
      api.get<VectorCoverage>("/api/vector/coverage"), api.get<BrainStatusSummary>("/api/brain/status"),
    ]);
    if (memoryResult.status === "fulfilled") { setMemory(memoryResult.value); setMemoryError(""); } else setMemoryError(errorMessage(memoryResult.reason));
    if (vectorResult.status === "fulfilled") { setVector(vectorResult.value); setVectorError(""); } else setVectorError(errorMessage(vectorResult.reason));
    if (coverageResult.status === "fulfilled") { setCoverage(coverageResult.value); setCoverageError(""); } else setCoverageError(errorMessage(coverageResult.reason));
    if (brainResult.status === "fulfilled") { setBrain(brainResult.value); setBrainError(""); } else setBrainError(errorMessage(brainResult.reason));
    setLastAttemptAt(new Date().toISOString());
    setRefreshing(false);
    inFlight.current = false;
  }, [active, api]);

  useEffect(() => { void load(); }, [load]);
  useEffect(() => {
    if (!active || !autoRefresh) return;
    const refreshWhenVisible = () => { if (document.visibilityState === "visible") void load(); };
    const intervalId = window.setInterval(refreshWhenVisible, REFRESH_INTERVAL_MS);
    document.addEventListener("visibilitychange", refreshWhenVisible);
    return () => { window.clearInterval(intervalId); document.removeEventListener("visibilitychange", refreshWhenVisible); };
  }, [active, autoRefresh, load]);

  const embedding: EmbeddingStatus | null = vector?.embedding ?? null;
  const configuredModel = embedding?.configured_model ?? embedding?.primary_model ?? null;
  const workspace = memory?.workspace ?? vector?.workspace ?? coverage?.workspace ?? brain?.workspace ?? null;
  const lastStatusAt = latestTimestamp([memory?.as_of, vector?.as_of, coverage?.as_of, brain?.status_as_of]);
  const stale = Boolean(memory?.stale || vector?.stale || coverage?.stale || brain?.status_stale);
  const warnings: RuntimeWarning[] = brain?.warnings ?? [];
  const missingIds = coverage?.missing_chunk_ids ?? [];
  const visibleMissingIds = showAllMissing ? missingIds : missingIds.slice(0, DEFAULT_MISSING_LIMIT);
  const allPrimaryFailed = !memory && !vector && !coverage && Boolean(memoryError && vectorError && coverageError);
  const topState = allPrimaryFailed ? "unavailable" : stale ? "stale" : vector?.state ?? memory?.state ?? coverage?.state ?? "unavailable";
  const endpointErrors = useMemo(() => [
    memoryError && `Memory Status: ${memoryError}`, vectorError && `Vector Status: ${vectorError}`,
    coverageError && `Vector Coverage: ${coverageError}`, brainError && `Brain Status: ${brainError}`,
  ].filter(Boolean) as string[], [brainError, coverageError, memoryError, vectorError]);

  if (!active && !memory && !vector && !coverage) return <Empty text="连接本机服务后显示向量中心。" />;

  return <div className="stack vector-center">
    {!active && <Notice kind="warning">本机服务已断开。页面保留上次成功数据，不会把连接失败伪装成本地状态。</Notice>}
    {allPrimaryFailed && <Notice kind="error">三个正式状态接口均读取失败。请检查 8766 控制服务、访问令牌和运行日志。</Notice>}
    {stale && <Notice kind="warning">当前状态快照已经超过有效时间。它表示数据可能不是最新，并不等于记忆系统已经损坏。</Notice>}

    <div className="toolbar vector-toolbar">
      <button className="button secondary" disabled={!active || refreshing} onClick={() => void load()} aria-label="刷新向量中心状态">{refreshing ? "正在刷新…" : "刷新状态"}</button>
      <label className="auto-refresh-toggle"><input type="checkbox" checked={autoRefresh} onChange={(event) => setAutoRefresh(event.target.checked)} aria-label="自动刷新向量中心" /><span>自动刷新（15 秒）</span></label>
      <span>状态时间：{time(lastStatusAt)}</span><span>本次尝试：{time(lastAttemptAt)}</span><span>Workspace：{text(workspace)}</span>
      <span>Memory 来源：{text(memory?.source)}</span><span>Vector 来源：{text(vector?.source)}</span><span>Coverage 来源：{text(coverage?.source)}</span><StatusBadge value={topState} />
    </div>

    <div className="vector-summary-grid">
      <Metric title="文档" value={count(memory?.documents)} detail={`Core Memory ${count(memory?.core_memories)}`} />
      <Metric title="Chunk" value={count(memory?.chunks)} detail={`Revision ${count(memory?.revision)}`} />
      <Metric title="向量" value={count(vector?.vectors)} detail={`已索引 ${count(coverage?.indexed)}`} tone={vector?.ready ? "good" : "warn"} />
      <Metric title="覆盖率" value={percentage(coverage?.coverage)} detail={`缺失 ${count(coverage?.missing)}`} tone={coverage?.coverage === 1 ? "good" : coverage?.coverage == null ? "neutral" : "warn"} />
    </div>
    <div className="vector-summary-grid">
      <Metric title="Embedding 实际模型" value={text(embedding?.active_model)} detail={`配置 ${text(configuredModel)}`} tone={embedding?.available ? "good" : "warn"} />
      <Metric title="实际向量维度" value={count(embedding?.dimension ?? vector?.dimension)} detail={`Collection ${count(vector?.dimension)}`} />
      <Metric title="Qdrant 模式" value={text(vector?.mode)} detail={vector?.ready ? "Ready" : "Not Ready"} tone={vector?.ready ? "good" : "warn"} />
      <Metric title="Collection" value={text(vector?.collection)} detail={vector?.collection_exists ? "已存在" : "不存在或未知"} />
    </div>

    <div className="vector-detail-grid">
      <Panel title="Memory Index">
        {memoryError && <Notice kind="error">上次数据已保留，本次刷新失败：{memoryError}</Notice>}
        <div className="panel-status-line"><StatusBadge value={memory?.state} /></div>
        <DetailList items={[
          { label: "数据库路径", value: <span className="path-value" title={memory?.database_path ?? undefined}>{text(memory?.database_path)}</span> },
          { label: "数据库大小", value: memory?.database_bytes == null ? "-" : bytes(memory.database_bytes) },
          { label: "文档数", value: count(memory?.documents) }, { label: "Chunk 数", value: count(memory?.chunks) },
          { label: "Core Memory 数", value: count(memory?.core_memories) }, { label: "Memory Revision", value: count(memory?.revision) },
          { label: "FTS tokenizer", value: text(memory?.fts_tokenizer) }, { label: "最近重建", value: time(memory?.last_rebuild_at) },
          { label: "Integrity", value: memory?.integrity?.healthy === undefined ? "-" : <BooleanBadge value={memory.integrity.healthy} trueLabel="健康" falseLabel="异常" /> },
          { label: "Integrity 错误", value: <span className="error-text">{text(memory?.integrity?.error)}</span> },
        ]} />
      </Panel>

      <Panel title="Embedding">
        {vectorError && <Notice kind="error">上次数据已保留，本次刷新失败：{vectorError}</Notice>}
        <div className="panel-status-line"><StatusBadge value={embedding?.state} /></div>
        <DetailList items={[
          { label: "Provider", value: text(embedding?.provider_id) }, { label: "配置模型", value: text(configuredModel) },
          { label: "实际模型", value: text(embedding?.active_model) }, { label: "备用模型", value: text(embedding?.fallback_model) },
          { label: "已验证", value: <BooleanBadge value={embedding?.verified} /> }, { label: "可用", value: <BooleanBadge value={embedding?.available} /> },
          { label: "向量维度", value: count(embedding?.dimension) }, { label: "请求次数", value: count(embedding?.request_count) },
          { label: "失败次数", value: count(embedding?.failure_count) },
          { label: "不可用模型", value: embedding?.unavailable_models?.length ? embedding.unavailable_models.join("、") : "-" },
          { label: "最近成功", value: time(embedding?.last_success_at) }, { label: "最近失败", value: time(embedding?.last_failure_at) },
          { label: "最近错误", value: <span className="error-text">{text(embedding?.last_error)}</span> },
        ]} />
      </Panel>

      <Panel title="Qdrant">
        <div className="panel-status-line"><StatusBadge value={vector?.state} /></div>
        {vector?.rebuild_required && <Notice kind="warning">当前 Embedding 维度或 Collection 合同发生变化，需要安全重建新的 Collection。</Notice>}
        <DetailList items={[
          { label: "状态", value: <StatusBadge value={vector?.state} /> }, { label: "模式", value: text(vector?.mode) },
          { label: "Collection", value: <span className="path-value" title={vector?.collection ?? undefined}>{text(vector?.collection)}</span> },
          { label: "Collection 存在", value: <BooleanBadge value={vector?.collection_exists} /> }, { label: "Ready", value: <BooleanBadge value={vector?.ready} /> },
          { label: "向量数量", value: count(vector?.vectors) }, { label: "向量维度", value: count(vector?.dimension) },
          { label: "距离算法", value: text(vector?.distance) }, { label: "需要重建", value: <BooleanBadge value={vector?.rebuild_required} trueLabel="需要" falseLabel="不需要" /> },
          { label: "最近错误", value: <span className="error-text">{text(vector?.last_error)}</span> },
        ]} />
      </Panel>

      <Panel title="向量覆盖率">
        {coverageError && <Notice kind="error">上次数据已保留，本次刷新失败：{coverageError}</Notice>}
        <div className="panel-status-line"><StatusBadge value={coverage?.state} /></div>
        <div className="metric-grid compact"><Metric title="Expected" value={count(coverage?.expected)} /><Metric title="Indexed" value={count(coverage?.indexed)} /><Metric title="Missing" value={count(coverage?.missing)} tone={(coverage?.missing ?? 0) > 0 ? "warn" : "good"} /><Metric title="Coverage" value={percentage(coverage?.coverage)} /></div>
        <CoverageBar value={coverage?.coverage ?? null} expected={coverage?.expected ?? null} />
        <div className="missing-chunks">
          <div className="panel-status-line"><strong>缺失 Chunk ID</strong>{missingIds.length > DEFAULT_MISSING_LIMIT && <button className="button secondary" onClick={() => setShowAllMissing((value) => !value)} aria-label={showAllMissing ? "收起缺失 Chunk ID" : "展开缺失 Chunk ID"}>{showAllMissing ? "收起" : `展开全部 ${missingIds.length} 个`}</button>}</div>
          {visibleMissingIds.length ? <div className="chunk-id-list">{visibleMissingIds.map((id) => <code key={id}>{id}</code>)}</div> : <p className="muted-text">没有返回缺失 Chunk ID。</p>}
          {coverage?.missing_chunk_ids_truncated && <Notice kind="warning">后端结果已截断，页面只展示状态接口返回的有限 ID。</Notice>}
          {coverage?.last_error && <p className="error-text">{coverage.last_error}</p>}
        </div>
      </Panel>
    </div>

    <Panel title="状态说明与错误诊断"><div className="status-diagnostics">
      <section><h3>最近错误</h3>{endpointErrors.length ? <ul>{endpointErrors.map((message) => <li key={message} className="error-text">{message}</li>)}</ul> : <p className="muted-text">接口未报告刷新错误。</p>}</section>
      <section><h3>Runtime warnings</h3>{warnings.length ? <ul>{warnings.map((warning, index) => <li key={`${warning.code || "warning"}-${index}`}><strong>{text(warning.code, "warning")}</strong><span>{text(warning.stage)} · {text(warning.message)}</span></li>)}</ul> : <p className="muted-text">没有 Runtime warning。</p>}</section>
      <section><h3>状态来源</h3><div className="source-explanations"><p><code>live</code> 当前拥有 MemoryGateway 的进程实时生成。</p><p><code>snapshot</code> 控制 API 从 memory_status.json 读取。</p><p><code>unavailable</code> 尚无可读取的运行状态。</p><p><code>stale</code> 快照超过有效时间，表示可能不新鲜，不等于系统损坏。</p></div></section>
    </div></Panel>
  </div>;
}
