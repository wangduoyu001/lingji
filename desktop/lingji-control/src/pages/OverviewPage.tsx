import CurrentWorkPanel from "../components/CurrentWorkPanel";
import { Empty, Metric, Notice, bytes } from "../components/ui";
import type { LingJiApi } from "../api";
import type { PageId, Row } from "../types";

const display = (value: unknown, suffix = "") =>
  value === null || value === undefined || value === "" ? "未知" : `${String(value)}${suffix}`;

const stateTone = (value: unknown): "good" | "warn" | "bad" | undefined => {
  const state = String(value ?? "").toLowerCase();
  if (["healthy", "ready", "available", "ok"].includes(state)) return "good";
  if (["degraded", "warning", "busy", "configuration_required", "stale"].includes(state)) return "warn";
  if (["failed", "error", "unavailable", "blocked"].includes(state)) return "bad";
  return undefined;
};

function stateLabel(value: unknown): string {
  const state = String(value ?? "unknown").toLowerCase();
  const labels: Record<string, string> = {
    healthy: "运行正常",
    ready: "已就绪",
    available: "可用",
    degraded: "降级运行",
    warning: "需要关注",
    stale: "数据过期",
    failed: "运行失败",
    error: "存在错误",
    unavailable: "当前不可用",
    blocked: "已阻止",
  };
  return labels[state] ?? display(value);
}

export default function OverviewPage({
  data,
  api,
  active,
  onNavigate,
}: {
  data: Row | null;
  api: LingJiApi;
  active: boolean;
  onNavigate: (page: PageId) => void;
}) {
  if (!data) return <Empty text="灵机核心连接后会自动显示运行状态。" />;
  const d = data as Record<string, unknown>;
  const health = (d.health ?? {}) as Record<string, unknown>;
  const queue = ((d.queue as Record<string, unknown> | undefined)?.stats ?? {}) as Record<string, unknown>;
  const storageRoot = (d.storage ?? {}) as Record<string, unknown>;
  const storage = (storageRoot.totals ?? {}) as Record<string, unknown>;
  const storageAlerts = (storageRoot.alerts ?? {}) as Record<string, unknown>;
  const memoryRuntime = (d.memory_runtime ?? {}) as Record<string, unknown>;
  const memory = (memoryRuntime.memory ?? d.memory_stats ?? {}) as Record<string, unknown>;
  const vector = (memoryRuntime.vector ?? d.vector_status ?? {}) as Record<string, unknown>;
  const embedding = (memoryRuntime.embedding ?? d.embedding_status ?? {}) as Record<string, unknown>;
  const hardware = (d.hardware ?? {}) as Record<string, unknown>;
  const computePolicy = (hardware.compute_policy ?? {}) as Record<string, unknown>;
  const runtimeState = memoryRuntime.state ?? health.status;
  const stale = Boolean(memoryRuntime.stale);

  return (
    <div className="stack overview-page observation-page">
      <section className={`overview-hero overview-hero-${stateTone(runtimeState) ?? "neutral"}`}>
        <div className="overview-hero-main">
          <span className="desktop-eyebrow">SYSTEM POSTURE</span>
          <div className="overview-title-line">
            <h2>{stateLabel(runtimeState)}</h2>
            <span className={`pill ${stateTone(runtimeState) === "good" ? "ok" : stateTone(runtimeState) === "bad" ? "error" : "warning"}`}>
              {display(runtimeState)}
            </span>
          </div>
          <p>
            灵机会自动检查服务、处理队列、更新索引和恢复连接。
            {memoryRuntime.as_of ? ` · 状态时间 ${display(memoryRuntime.as_of)}` : ""}
          </p>
        </div>
        <div className="observation-live-state">
          <span className={stateTone(runtimeState) === "good" ? "status-dot online" : "status-dot"} />
          <div>
            <strong>{Number(queue.running ?? 0) > 0 ? `${display(queue.running)} 个任务运行中` : "后台自动运行"}</strong>
            <small>状态每 10 秒自动更新</small>
          </div>
        </div>
      </section>

      {stale && <Notice kind="warning">当前记忆和向量统计来自旧快照，系统正在自动刷新。</Notice>}

      <CurrentWorkPanel api={api} active={active} />

      <section className="attention-summary">
        <div>
          <span className="desktop-eyebrow">OWNER ATTENTION</span>
          <h3>需要你决定的事项以真实待办为准</h3>
          <p>只有持久化 Work Fact 中存在 PendingAction 时，灵机才会把事情交给你。</p>
        </div>
        <button className="button secondary" onClick={() => onNavigate("attention")}>查看待办</button>
      </section>

      <section className="overview-section">
        <div className="overview-section-heading">
          <div><span className="desktop-eyebrow">SYSTEM SIGNALS</span><h3>关键状态</h3></div>
          <small>详细技术信息已移到高级诊断</small>
        </div>
        <div className="metric-grid observation-metric-grid">
          <Metric
            title="任务队列"
            value={Number(queue.running ?? 0) > 0 ? `${display(queue.running)} 运行中` : `${display(queue.pending)} 等待`}
            detail={`自动重试 ${display(queue.retrying)} · 失败 ${display(queue.failed)}`}
            tone={Number(queue.failed ?? 0) > 0 ? "bad" : Number(queue.retrying ?? 0) > 0 ? "warn" : "good"}
          />
          <Metric
            title="记忆处理"
            value={display(memory.documents)}
            detail={`文档 · ${display(memory.chunks)} 个分块`}
            tone={stateTone(memory.state)}
          />
          <Metric
            title="向量索引"
            value={display(vector.vectors)}
            detail={`${stateLabel(vector.state)} · 维度 ${display(vector.dimension)}`}
            tone={vector.rebuild_required ? "bad" : stateTone(vector.state)}
          />
          <Metric
            title="本地模型"
            value={display(embedding.active_model ?? embedding.configured_model)}
            detail={stateLabel(embedding.state)}
            tone={stateTone(embedding.state)}
          />
          <Metric
            title="算力模式"
            value={display(computePolicy.requested_mode ?? computePolicy.mode)}
            detail={`设备 ${display(computePolicy.selected_device ?? computePolicy.device)}`}
            tone={stateTone(computePolicy.state)}
          />
          <Metric
            title="磁盘剩余"
            value={storage.disk_free_bytes == null ? "未知" : bytes(Number(storage.disk_free_bytes))}
            detail={`${display(storage.disk_free_percent, "%")} · 灵机占用 ${storage.bytes == null ? "未知" : bytes(Number(storage.bytes))}`}
            tone={storageAlerts.below_minimum_free ? "bad" : "good"}
          />
        </div>
      </section>

      <div className="overview-footer-actions">
        <button className="button secondary" onClick={() => onNavigate("activity")}>查看活动记录</button>
        <button className="button secondary" onClick={() => onNavigate("diagnostics")}>打开高级诊断</button>
      </div>
    </div>
  );
}
