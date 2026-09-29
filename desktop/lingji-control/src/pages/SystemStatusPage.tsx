import { useCallback } from "react";
import { Empty, Metric, Notice, Panel, bytes as formatBytes } from "../components/ui";
import { usePollingResource } from "../hooks/usePollingResource";
import type { LingJiApi } from "../api";
import {
  normalizeBrainStatus,
  type BrainStatusSummary,
  type PipelineHealthSnapshot,
} from "../contracts/brainStatus";

// 主人 2026-09-29 指示：UI 必须详细显示所有功能的状态，问题不能等主人自己发现。
// 本页是全系统状态的总观察面：只读、无任何待办按钮，异常直接亮出来。

function nullableText(value: unknown, fallback = "未知"): string {
  return value === null || value === undefined || value === "" ? fallback : String(value);
}

function shortTime(value: unknown): string {
  const text = nullableText(value, "");
  if (!text) return "无记录";
  return text.replace("T", " ").slice(0, 19);
}

const EVENT_LABELS: Record<string, string> = {
  memory_searched: "记忆检索",
  memory_fetched: "读取记忆详情",
  memory_proposed: "提交记忆提案",
  memory_candidate_created: "生成记忆候选",
  memory_index_rebuilt: "记忆索引重建",
  memory_index_synced: "记忆索引同步",
  automatic_memory_reconciliation: "自动扫描核对",
  context_pack_built: "构建上下文包",
  memory_gateway: "记忆服务",
  work_failed_items_merged: "失败台账归并",
  work_failure_recorded: "记录失败台账",
};

function eventLabel(value: unknown): string {
  const raw = String(value ?? "");
  return EVENT_LABELS[raw] ?? raw ?? "未知事件";
}

function pipelineState(pipeline: PipelineHealthSnapshot): { label: string; kind: "ok" | "warning" | "error" } {
  if (pipeline.degraded) return { label: "降级（连续失败，自动重试中）", kind: "error" };
  if ((pipeline.consecutive_failures ?? 0) > 0) return { label: "有失败（自动重试中）", kind: "warning" };
  if (pipeline.last_success_at) return { label: "正常", kind: "ok" };
  return { label: "尚未运行", kind: "warning" };
}

export default function SystemStatusPage({ api, active }: { api: LingJiApi; active: boolean }) {
  const load = useCallback(
    (signal: AbortSignal) => api.get<unknown>("/api/brain/status", { signal }).then(normalizeBrainStatus),
    [api],
  );
  const resource = usePollingResource({ fetcher: load, enabled: active, intervalMs: 15_000, staleAfterMs: 45_000, pauseWhenHidden: true });

  if (!active) return <Empty text="连接灵机后显示全部功能状态。" />;
  if (resource.loading && !resource.data) return <Empty text="正在读取系统状态…" />;
  if (resource.error && !resource.data) return <Notice kind="error">系统状态暂时无法读取，正在自动重试：{resource.error.message}</Notice>;
  const data = resource.data as BrainStatusSummary | null;
  if (!data) return <Empty text="正在等待状态数据…" />;
  const pipelines = Object.entries(data.pipelines ?? {});
  const degradedPipelines = pipelines.filter(([, item]) => item.degraded);
  const queue = data.extraction_queue ?? {};
  const failureRecords = data.failure_ledger?.failures ?? [];
  const failureTotal = data.failure_ledger?.total ?? failureRecords.length;
  const queueFailed = typeof queue.failed === "number" ? queue.failed : 0;
  const overallBad = degradedPipelines.length > 0 || failureTotal > 0 || queueFailed > 0 || data.status_stale || (data.warnings?.length ?? 0) > 0;

  return (
    <div className="stack observation-page system-status-page">
      <section className="workspace-hero">
        <div>
          <span className="section-kicker">全部功能实时状态 · 无需你操作</span>
          <h2>状态</h2>
          <p>
            {overallBad
              ? `检测到需要留意的异常：${degradedPipelines.length} 个管线降级、失败台账 ${failureTotal} 条、失败任务 ${queueFailed} 个。系统在自动重试与保守处理，这里保证它们对你可见。`
              : "所有子系统正常。灵机自动工作，问题会第一时间出现在这一页。"}
          </p>
        </div>
        <span className="auto-refresh-note">每 15 秒自动刷新</span>
      </section>

      {resource.stale && <Notice kind="warning">状态数据暂时过期，正在自动重试。</Notice>}
      {resource.error && data && <Notice kind="error">状态刷新失败：{resource.error.message}</Notice>}

      <Panel title="记忆与索引">
        <div className="metric-grid">
          <Metric title="记忆条数" value={nullableText(data.memory_count)} detail={`分块 ${nullableText(data.memory_chunk_count)}`} />
          <Metric title="向量条数" value={nullableText(data.vector_count)} detail={`${nullableText(data.vector_collection)} · ${nullableText(data.vector_dimension)} 维`} />
          <Metric title="记忆库大小" value={data.memory_bytes === null || data.memory_bytes === undefined ? "未知" : formatBytes(data.memory_bytes)} detail={`版本 ${nullableText(data.memory_revision)}`} />
          <Metric title="嵌入模型" value={nullableText(data.embed_model)} detail={`状态 ${nullableText(data.embedding_state)}`} />
        </div>
        <div className="list">
          <div className="list-row"><div><strong>记忆索引</strong><small>状态 {nullableText(data.memory_state)}</small></div></div>
          <div className="list-row"><div><strong>语义索引</strong><small>状态 {nullableText(data.vector_state)}{data.vector_rebuild_required ? " · 需要重建（自动进行中）" : ""}</small></div></div>
        </div>
      </Panel>

      <Panel title="自动记忆管线（提炼 / 晋升 / 回填）">
        {pipelines.length ? (
          <div className="list">
            {pipelines.map(([name, pipeline]) => {
              const state = pipelineState(pipeline);
              return (
                <div className="list-row" key={name}>
                  <div>
                    <strong>{pipeline.name || name} — {state.label}</strong>
                    <small>
                      连续失败 {nullableText(pipeline.consecutive_failures, "0")} · 累计失败 {nullableText(pipeline.total_failures, "0")} · 最近成功 {shortTime(pipeline.last_success_at)} · 最近失败 {shortTime(pipeline.last_failure_at)}
                    </small>
                    {pipeline.last_error ? <small>最近错误：{String(pipeline.last_error).slice(0, 200)}</small> : null}
                  </div>
                </div>
              );
            })}
          </div>
        ) : (
          <Empty text="管线状态暂无记录（自动记忆运行时未上报）。" />
        )}
      </Panel>

      <Panel title="采集队列">
        <div className="metric-grid">
          <Metric title="排队中" value={String(queue.queued ?? 0)} detail={`重试 ${queue.retrying ?? 0} · 运行 ${queue.running ?? 0}`} />
          <Metric title="已完成" value={String(queue.completed ?? 0)} detail={`已取消 ${queue.cancelled ?? 0}`} />
          <Metric title="失败任务" value={String(queueFailed)} detail={queueFailed > 0 ? "自动重试中" : "无"} />
        </div>
      </Panel>

      <Panel title={`失败台账（${failureTotal} 条 · 系统自动重试与保守处理，无需你操作）`}>
        {failureRecords.length ? (
          <div className="list">
            {failureRecords.map((record) => (
              <div className="list-row" key={String(record.failure_key ?? record.reason)}>
                <div>
                  <strong>{nullableText(record.stage)} × {nullableText(record.occurrence_count, "1")}{record.requires_owner ? " · 需留意" : ""}</strong>
                  <small>{String(record.reason ?? "").slice(0, 260)}</small>
                  <small>来源 {nullableText(record.source_id, "未知")} · 最近出现 {shortTime(record.last_seen_at)} · {record.retryable ? "可自动重试" : "不可重试（保守跳过）"}</small>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <Empty text="没有失败记录。" />
        )}
      </Panel>

      <Panel title="存储与占用（上限由你的设置决定）">
        {(() => {
          const totals = data.storage_summary?.totals ?? null;
          const alerts = data.storage_summary?.alerts ?? null;
          const categories = Object.entries(data.storage_summary?.categories ?? {})
            .map(([name, row]) => ({ name, bytes: typeof row?.bytes === "number" ? row.bytes : 0, files: row?.files }))
            .sort((a, b) => b.bytes - a.bytes)
            .slice(0, 6);
          return (
            <>
              {alerts?.over_configured_limit && (
                <Notice kind="error">已超过你配置的存储上限。灵机会按最旧优先自动淘汰可清理数据，正式记忆不受影响。</Notice>
              )}
              {alerts?.below_minimum_free && (
                <Notice kind="warning">磁盘剩余空间低于下限，灵机会保守处理写入。</Notice>
              )}
              <div className="metric-grid">
                <Metric title="灵机总占用" value={totals?.bytes === null || totals?.bytes === undefined ? "未知" : formatBytes(totals.bytes)} detail={`文件 ${nullableText(totals?.files, "未知")} 个`} />
                <Metric title="磁盘剩余" value={totals?.disk_free_bytes === null || totals?.disk_free_bytes === undefined ? "未知" : formatBytes(totals.disk_free_bytes)} detail="低于下限会自动保守写入" />
              </div>
              {categories.length ? (
                <div className="list">
                  {categories.map((row) => (
                    <div className="list-row" key={row.name}>
                      <div>
                        <strong>{row.name}</strong>
                        <small>{formatBytes(row.bytes)} · {nullableText(row.files, "未知")} 个文件</small>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <Empty text="存储分类暂无数据。" />
              )}
            </>
          );
        })()}
      </Panel>

      <Panel title="采集与调度（自动盯盘，无需你操作）">
        {(() => {
          const watcher = data.watcher_status;
          const jobs = data.scheduler_jobs ?? [];
          const mode = String(watcher?.automation_mode ?? "");
          const modeLabel = mode === "event_watcher" ? "事件监听（文件一变就处理）" : mode ? mode : "未知";
          const nextSeconds = watcher?.next_reconciliation_seconds;
          return (
            <div className="list">
              <div className="list-row"><div><strong>运行方式 — {modeLabel}</strong><small>已授权来源 {nullableText(watcher?.authorized_watcher_count, "未知")} 个 · 事件监听{watcher?.event_watcher_enabled ? "已启用" : "未启用"}</small></div></div>
              <div className="list-row"><div><strong>下次全面核对</strong><small>{typeof nextSeconds === "number" ? `约 ${Math.round(nextSeconds / 60)} 分钟后` : "等待调度"}</small></div></div>
              {watcher?.last_global_error ? <div className="list-row"><div><strong style={{ color: "inherit" }}>最近全局错误</strong><small>{String(watcher.last_global_error).slice(0, 260)}</small></div></div> : null}
              {jobs.length ? jobs.map((job) => (
                <div className="list-row" key={String(job.name)}>
                  <div>
                    <strong>{nullableText(job.name)} — {job.enabled ? "已启用" : "已暂停"}</strong>
                    <small>{job.run_count === null || job.run_count === undefined ? "" : `已运行 ${job.run_count} 次 · `}{job.last_run_at ? `上次 ${shortTime(job.last_run_at)} · ` : ""}{job.next_run_at ? `下次 ${shortTime(job.next_run_at)}` : ""}{job.paused_reason ? ` · ${String(job.paused_reason)}` : ""}</small>
                  </div>
                </div>
              )) : <Empty text="调度任务暂无记录。" />}
            </div>
          );
        })()}
      </Panel>

      <Panel title="服务依赖（本地服务健康）">
        {(() => {
          const providers = data.providers ?? {};
          const optional = (["faster_whisper", "paddleocr", "pyscenedetect"] as const).map((name) => {
            const row = providers[name] as { available?: boolean; capability?: string } | undefined;
            const labels: Record<string, string> = { faster_whisper: "语音转写", paddleocr: "图片文字识别", pyscenedetect: "镜头切分" };
            return { name: labels[name] ?? name, available: Boolean(row?.available) };
          });
          const qdrant = providers.qdrant as { state?: string } | undefined;
          const embedding = providers.embedding as { state?: string; active_model?: string } | undefined;
          return (
            <div className="list">
              <div className="list-row"><div><strong>向量数据库 Qdrant — {nullableText(qdrant?.state)}</strong><small>语义检索的本地依赖</small></div></div>
              <div className="list-row"><div><strong>嵌入服务 — {nullableText(embedding?.state)}</strong><small>当前模型 {nullableText(embedding?.active_model)}</small></div></div>
              {optional.map((item) => (
                <div className="list-row" key={item.name}>
                  <div>
                    <strong>{item.name} — {item.available ? "可用" : "未安装"}</strong>
                    <small>可选的媒体分析能力，未安装不影响记忆与检索</small>
                  </div>
                </div>
              ))}
            </div>
          );
        })()}
      </Panel>

      <Panel title="语义覆盖（未向量化存量，自动追平）">
        {data.vector_coverage && Object.keys(data.vector_coverage).length ? (
          <div className="list">
            {Object.entries(data.vector_coverage).filter(([, value]) => typeof value !== "object").map(([key, value]) => (
              <div className="list-row" key={key}>
                <div>
                  <strong>{key.includes("missing") ? `待补齐（${key}）` : key}</strong>
                  <small>{typeof value === "number" ? `${value} 条` : String(value)}{key.includes("missing") && typeof value === "number" && value > 0 ? " · 回填线程自动追平" : ""}</small>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <Empty text="暂无覆盖率数据。" />
        )}
      </Panel>

      <Panel title="最近动态（灵机刚刚做了什么）">
        {data.recent_events?.length ? (
          <div className="list">
            {data.recent_events.map((event, index) => (
              <div className="list-row" key={`${event.event_type ?? "event"}-${index}`}>
                <div>
                  <strong>{eventLabel(event.event_type)}</strong>
                  <small>{shortTime(event.created_at)}</small>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <Empty text="暂无动态记录。" />
        )}
      </Panel>

      <Panel title="模型与算力">
        <div className="metric-grid">
          <Metric title="对话模型" value={nullableText(data.chat_model)} detail={`已安装模型 ${nullableText(data.installed_models)}`} />
          <Metric title="运行模式" value={nullableText(data.compute_mode)} detail={data.cuda_version ? `CUDA ${data.cuda_version}` : "CUDA 未知"} />
        </div>
        {data.gpus?.length ? (
          <div className="list">
            {data.gpus.map((gpu, index) => (
              <div className="list-row" key={String(gpu.gpu_id ?? index)}>
                <div>
                  <strong>{nullableText(gpu.name)}</strong>
                  <small>状态 {nullableText(gpu.status)} · 利用率 {gpu.utilization_percent === null || gpu.utilization_percent === undefined ? "未知" : `${gpu.utilization_percent}%`}{gpu.stale ? " · 遥测已过期" : ""}</small>
                  {gpu.errors?.length ? <small>{(gpu.errors as unknown[]).map(String).join("；").slice(0, 200)}</small> : null}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <Empty text="未发现 GPU 遥测（纯 CPU 模式正常）。" />
        )}
      </Panel>

      <Panel title={`运行警告（${data.warnings?.length ?? 0}）`}>
        {data.warnings?.length ? (
          <div className="list">
            {data.warnings.map((warning, index) => (
              <div className="list-row" key={`${warning.code ?? "warning"}-${index}`}>
                <div>
                  <strong>{nullableText(warning.code)} · {nullableText(warning.stage)}</strong>
                  <small>{nullableText(warning.message)}</small>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <Empty text="没有运行警告。" />
        )}
      </Panel>
    </div>
  );
}
