import CurrentWorkPanel from "../components/CurrentWorkPanel";
import StartCenterPanel from "../components/StartCenterPanel";
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
    degraded: "部分能力待处理",
    warning: "需要关注",
    stale: "数据过期",
    failed: "运行失败",
    error: "存在错误",
    unavailable: "当前不可用",
    blocked: "已阻止",
  };
  return labels[state] ?? display(value);
}

const AUTONOMY_FLOW: Array<{
  number: string;
  title: string;
  detail: string;
  label: string;
  page: PageId;
  ownerDecision?: boolean;
}> = [
  {
    number: "1",
    title: "自动发现",
    detail: "灵机主动扫描 AI 软件、允许目录元数据、模型和硬件状态。",
    label: "查看发现结果",
    page: "assistant_hub",
  },
  {
    number: "2",
    title: "自动处理",
    detail: "已授权资料会自动解析、去重、排队、重试并记录进度。",
    label: "查看处理进度",
    page: "activity",
  },
  {
    number: "3",
    title: "需要时才询问",
    detail: "读取真实正文或修改外部客户端配置前，灵机才会请求授权。",
    label: "查看待授权事项",
    page: "attention",
    ownerDecision: true,
  },
  {
    number: "4",
    title: "主人只做最终决定",
    detail: "永久记忆的批准、拒绝和高风险操作必须由你定稿。",
    label: "查看候选记忆",
    page: "memory_review",
    ownerDecision: true,
  },
];

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
  const embeddingReady = ["healthy", "ready", "available"].includes(
    String(embedding.state ?? "").toLowerCase(),
  );

  const attentionCount = [
    Number(health.error_count ?? 0) > 0,
    Number(queue.failed ?? 0) > 0,
    vector.rebuild_required === true,
    storageAlerts.below_minimum_free === true,
  ].filter(Boolean).length;
  const activeJobs = Number(queue.running ?? 0) + Number(queue.pending ?? 0) + Number(queue.retrying ?? 0);

  return (
    <div className="stack overview-page observation-page">
      <section className={`overview-hero overview-hero-${stateTone(runtimeState) ?? "neutral"}`}>
        <div className="overview-hero-main">
          <span className="desktop-eyebrow">灵机运行观察台</span>
          <div className="overview-title-line">
            <h2>{stateLabel(runtimeState)}</h2>
            <span className={`pill ${stateTone(runtimeState) === "good" ? "ok" : stateTone(runtimeState) === "bad" ? "error" : "warning"}`}>
              {display(runtimeState)}
            </span>
          </div>
          <p>
            灵机会主动启动、发现、处理、重试和恢复。你主要通过这里了解它在做什么；
            只有读取真实内容、修改外部配置或写入永久记忆时才需要决定。
            {memoryRuntime.as_of ? ` · 状态时间 ${display(memoryRuntime.as_of)}` : ""}
          </p>
        </div>
        <div className="observation-live-state">
          <span className={stateTone(runtimeState) === "good" ? "status-dot online" : "status-dot"} />
          <div>
            <strong>{activeJobs > 0 ? `${activeJobs} 个任务正在自动推进` : "当前空闲，不需要操作"}</strong>
            <small>状态每 10 秒自动更新</small>
          </div>
        </div>
      </section>

      {stale && <Notice kind="warning">当前记忆和向量统计来自旧快照，系统正在自动刷新。</Notice>}

      <StartCenterPanel api={api} active={active} overview={data} onNavigate={onNavigate} />

      <section className="daily-flow" aria-label="灵机自动运行与主人授权边界">
        <div className="daily-flow-heading">
          <div>
            <span className="desktop-eyebrow">灵机如何主动工作</span>
            <h3>自动干活，必要时才打扰主人</h3>
            <p>下面是运行机制，不是要求你逐项点击的操作流程。所有入口都用于查看、授权或手动干预。</p>
          </div>
          <button className="button secondary" onClick={() => onNavigate("activity")}>查看灵机正在做什么</button>
        </div>
        <div className="daily-flow-grid">
          {AUTONOMY_FLOW.map((item) => (
            <button key={item.number} className="daily-flow-card" onClick={() => onNavigate(item.page)}>
              <span className="daily-flow-number">{item.number}</span>
              <span className="daily-flow-copy">
                <strong>{item.title}</strong>
                <small>{item.detail}</small>
                <em>{item.ownerDecision ? `需要你时：${item.label}` : item.label}</em>
              </span>
            </button>
          ))}
        </div>
      </section>

      <CurrentWorkPanel api={api} active={active} />

      <section className={attentionCount ? "attention-summary attention-summary-warning" : "attention-summary"}>
        <div>
          <span className="desktop-eyebrow">需要主人决定</span>
          <h3>{attentionCount ? `${attentionCount} 类事项等待查看` : "暂时不需要你处理"}</h3>
          <p>{attentionCount ? "系统不能安全自行决定的事项已集中到待办页。" : "普通任务、重试和状态恢复由后台自动完成。"}</p>
        </div>
        <button className="button secondary" onClick={() => onNavigate("attention")}>查看待办与授权</button>
      </section>

      <section className="overview-section">
        <div className="overview-section-heading">
          <div><span className="desktop-eyebrow">关键状态</span><h3>系统现在怎么样</h3></div>
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
            title="Embedding"
            value={display(embedding.active_model ?? embedding.configured_model)}
            detail={embeddingReady ? "已激活" : "后台正在诊断模型、Provider 与索引状态"}
            tone={embeddingReady ? "good" : "warn"}
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
