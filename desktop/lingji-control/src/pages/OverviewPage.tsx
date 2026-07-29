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

const DAILY_FLOW: Array<{
  number: string;
  title: string;
  detail: string;
  label: string;
  page: PageId;
}> = [
  {
    number: "1",
    title: "连接与导入",
    detail: "扫描 Codex、Claude、WorkBuddy，导入已有 AI 历史。",
    label: "打开 AI 助手中心",
    page: "assistant_hub",
  },
  {
    number: "2",
    title: "查看处理",
    detail: "确认导入和采集任务正在运行、完成或失败。",
    label: "查看活动记录",
    page: "activity",
  },
  {
    number: "3",
    title: "审核记忆",
    detail: "决定哪些候选内容值得成为长期记忆。",
    label: "进入记忆审核",
    page: "memory_review",
  },
  {
    number: "4",
    title: "继续投喂",
    detail: "日常把新的文字、网页、文件或媒体交给灵机。",
    label: "打开投喂中心",
    page: "capture_center",
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

  return (
    <div className="stack overview-page observation-page">
      <section className={`overview-hero overview-hero-${stateTone(runtimeState) ?? "neutral"}`}>
        <div className="overview-hero-main">
          <span className="desktop-eyebrow">灵机开始中心</span>
          <div className="overview-title-line">
            <h2>{stateLabel(runtimeState)}</h2>
            <span className={`pill ${stateTone(runtimeState) === "good" ? "ok" : stateTone(runtimeState) === "bad" ? "error" : "warning"}`}>
              {display(runtimeState)}
            </span>
          </div>
          <p>
            第一次使用先看唯一推荐下一步，再连接 AI、导入已有资料并审核候选记忆。
            {memoryRuntime.as_of ? ` · 状态时间 ${display(memoryRuntime.as_of)}` : ""}
          </p>
        </div>
        <div className="observation-live-state">
          <span className={stateTone(runtimeState) === "good" ? "status-dot online" : "status-dot"} />
          <div>
            <strong>{Number(queue.running ?? 0) > 0 ? `${display(queue.running)} 个任务运行中` : "等待你的下一步"}</strong>
            <small>状态每 10 秒自动更新</small>
          </div>
        </div>
      </section>

      {stale && <Notice kind="warning">当前记忆和向量统计来自旧快照，系统正在自动刷新。</Notice>}

      <StartCenterPanel api={api} active={active} overview={data} onNavigate={onNavigate} />

      <section className="daily-flow" aria-label="灵机首次设置和日常使用流程">
        <div className="daily-flow-heading">
          <div>
            <span className="desktop-eyebrow">新用户按顺序完成</span>
            <h3>先把你的 AI 和已有记忆接进来</h3>
            <p>第一次按 1 → 2 → 3 完成设置；以后主要使用第 4 步继续投喂新资料。</p>
          </div>
          <button className="button" onClick={() => onNavigate("assistant_hub")}>开始连接 AI</button>
        </div>
        <div className="daily-flow-grid">
          {DAILY_FLOW.map((item) => (
            <button key={item.number} className="daily-flow-card" onClick={() => onNavigate(item.page)}>
              <span className="daily-flow-number">{item.number}</span>
              <span className="daily-flow-copy">
                <strong>{item.title}</strong>
                <small>{item.detail}</small>
                <em>{item.label}</em>
              </span>
            </button>
          ))}
        </div>
      </section>

      <CurrentWorkPanel api={api} active={active} />

      <section className={attentionCount ? "attention-summary attention-summary-warning" : "attention-summary"}>
        <div>
          <span className="desktop-eyebrow">需要主人决定</span>
          <h3>{attentionCount ? `${attentionCount} 类异常需要查看` : "暂时不需要你处理"}</h3>
          <p>{attentionCount ? "系统不能安全自行决定的事项已集中到待办页。" : "普通任务、重试和状态恢复由后台自动完成。"}</p>
        </div>
        <button className="button secondary" onClick={() => onNavigate("attention")}>查看待办</button>
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
            detail={embeddingReady ? "已激活" : "暂未激活，进入向量中心查看原因"}
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
