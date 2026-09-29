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
