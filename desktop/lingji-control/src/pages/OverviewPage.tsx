import AssistantDiscoveryPanel from "../components/AssistantDiscoveryPanel";
import CurrentWorkPanel from "../components/CurrentWorkPanel";
import { Empty, Metric, Notice, bytes } from "../components/ui";
import type { LingJiApi } from "../api";
import type { PageId, Row } from "../types";
import "../AssistantAutopilot.css";

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
    degraded: "部分能力待配置",
    configuration_required: "正在完成首次配置",
    warning: "需要关注",
    stale: "状态待更新",
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
  if (!data) return <Empty text="灵机核心连接后会自动开始检查本机环境。" />;
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

  const attentionCount = [
    Number(health.error_count ?? 0) > 0,
    Number(queue.failed ?? 0) > 0,
    vector.rebuild_required === true,
    storageAlerts.below_minimum_free === true,
  ].filter(Boolean).length;

  return (
    <div className="stack overview-page observation-page">
      <section className={`overview-hero overview-hero-${stateTone(runtimeState) ?? "neutral"}`}>
        <div className="overview-hero-main">
          <span className="desktop-eyebrow">灵机自动驾驶</span>
          <div className="overview-title-line">
            <h2>{stateLabel(runtimeState)}</h2>
            <span className={`pill ${stateTone(runtimeState) === "good" ? "ok" : stateTone(runtimeState) === "bad" ? "error" : "warning"}`}>
              {attentionCount ? `${attentionCount} 项需要关注` : "后台自动运行"}
            </span>
          </div>
          <p>
            灵机会自己发现本机 AI 工具、检查运行状态、处理已经授权的资料并自动重试。
            只有读取真实内容、写入永久记忆或执行不可逆操作时才需要你决定。
          </p>
        </div>
        <div className="observation-live-state">
          <span className={stateTone(runtimeState) === "good" ? "status-dot online" : "status-dot"} />
          <div>
            <strong>{Number(queue.running ?? 0) > 0 ? `${display(queue.running)} 个任务正在处理` : "系统自己工作中"}</strong>
            <small>状态自动更新</small>
          </div>
        </div>
      </section>

      {stale && <Notice kind="warning">部分状态来自旧快照，灵机正在后台重新确认。</Notice>}

      <AssistantDiscoveryPanel
        api={api}
        active={active}
        onOpenCodex={() => onNavigate("codex_workspace")}
        onOpenActivity={() => onNavigate("activity")}
      />

      <CurrentWorkPanel api={api} active={active} />

      <section className={attentionCount ? "attention-summary attention-summary-warning" : "attention-summary"}>
        <div>
          <span className="desktop-eyebrow">需要你决定</span>
          <h3>{attentionCount ? `${attentionCount} 类事项无法安全自动决定` : "现在没有必须由你处理的事项"}</h3>
          <p>
            {attentionCount
              ? "灵机能自动处理的事情已经先处理，剩下的集中放在这里。"
              : "普通扫描、状态检查、重试和恢复由后台自己完成。"}
          </p>
        </div>
        <button className="button secondary" onClick={() => onNavigate("attention")}>
          {attentionCount ? "查看需要我决定的事项" : "查看决策记录"}
        </button>
      </section>

      <details className="overview-technical-summary">
        <summary>
          <span>系统健康细节</span>
          <span>模型、向量、算力、存储等技术信息</span>
        </summary>
        <div>
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
          <div className="overview-footer-actions">
            <button className="button secondary" onClick={() => onNavigate("diagnostics")}>打开高级工具</button>
          </div>
        </div>
      </details>
    </div>
  );
}
