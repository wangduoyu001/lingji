import { useCallback, useMemo, useState } from "react";
import { Empty, Notice } from "../components/ui";
import { usePollingResource } from "../hooks/usePollingResource";
import type { LingJiApi } from "../api";
import { buildOwnerWorkFeed } from "../ownerWorkFeed";
import type { PageId } from "../types";
import type { CaptureJobsResponse } from "./captureCenterTypes";

const ACTIVE_STATES = new Set(["queued", "leased", "running", "retrying"]);

function dateTime(value: unknown): string {
  if (!value) return "时间未知";
  const date = new Date(String(value));
  return Number.isNaN(date.getTime()) ? "时间未知" : date.toLocaleString();
}

function nextActorLabel(value: string): string {
  if (value === "system") return "灵机";
  if (value === "owner") return "你";
  if (value === "external") return "外部系统";
  return "无待执行者";
}

export default function ActivityPage({ api, active, onNavigate }: { api: LingJiApi; active: boolean; onNavigate: (page: PageId) => void }) {
  const [selectedId, setSelectedId] = useState("");
  const load = useCallback(
    (signal: AbortSignal) => api.get<CaptureJobsResponse>("/api/capture/jobs?limit=80&offset=0", { signal }),
    [api],
  );
  const resource = usePollingResource({ fetcher: load, enabled: active, intervalMs: 5_000, staleAfterMs: 18_000, pauseWhenHidden: true });
  const feed = useMemo(
    () => buildOwnerWorkFeed({ jobsResponse: resource.data ?? null, expectedDocuments: null, limit: 50 }),
    [resource.data],
  );
  const activeItems = feed.items.filter((item) => ACTIVE_STATES.has(item.status));
  const historyItems = feed.items.filter((item) => !ACTIVE_STATES.has(item.status)).slice(0, 30);
  const allVisible = [...activeItems, ...historyItems];
  const selected = allVisible.find((item) => item.workItemId === selectedId) ?? allVisible[0] ?? null;

  if (!active) return <Empty text="灵机核心连接后，这里会显示真实 WorkItem。" />;
  if (resource.loading && !resource.data) return <Empty text="正在读取真实工作对象…" />;
  if (resource.error && !resource.data) return <Notice kind="error">真实 WorkItem 暂时不可用。工作页不会拿日志或记忆数量冒充工作履历。</Notice>;

  return (
    <div className="workbench-v4 work-history-v4">
      <section className="v4-page-intro">
        <div>
          <span className="v4-kicker">工作履历</span>
          <h2>每一项都必须有真实 WorkItem</h2>
          <p>这里与首页读取同一个 Capture/Extraction 工作投影。没有 WorkItem，就不会宣称灵机做过这件事。</p>
        </div>
        <div className="v4-intro-actions">
          <button className="v4-button" onClick={() => onNavigate("memory")}>查看记忆</button>
          <button className="v4-button" onClick={() => onNavigate("capture_center")}>添加资料</button>
        </div>
      </section>

      {resource.error && resource.data && <Notice kind="warning">刷新暂时失败，正在显示最近一次成功读取的 WorkItem。</Notice>}
      {feed.detailsState === "unavailable" && <Notice kind="warning">{feed.detailsMessage}</Notice>}

      <section className="work-history-summary">
        <div className="work-history-live">
          <span className={`v4-state-orb ${activeItems.length ? "ok" : "idle"}`} />
          <div>
            <span className="v4-kicker">现在</span>
            <strong>{activeItems.length ? `${activeItems.length} 项真实工作进行中` : "当前没有运行中的 WorkItem"}</strong>
            <small>{activeItems.length ? "状态每 5 秒从同一工作接口更新" : "空闲不会被包装成正在工作"}</small>
          </div>
        </div>
        <div className="work-history-counts">
          <span><strong>{activeItems.length}</strong><small>进行中</small></span>
          <span><strong>{historyItems.filter((item) => item.status === "completed").length}</strong><small>最近完成</small></span>
          <span><strong>{historyItems.filter((item) => item.status === "failed").length}</strong><small>未完成</small></span>
        </div>
      </section>

      <section className="work-history-layout">
        <div className="work-history-list-pane">
          <div className="v4-section-heading compact">
            <div><span className="v4-kicker">真实工作对象</span><h3>{allVisible.length ? `${allVisible.length} 项最近工作` : "暂无工作记录"}</h3></div>
          </div>
          {allVisible.length ? <div className="work-history-list">
            {allVisible.map((item) => (
              <button className={`work-history-row ${selected === item ? "active" : ""}`} key={item.workItemId} onClick={() => setSelectedId(item.workItemId)}>
                <span className={`work-status-dot ${item.status}`} />
                <div>
                  <div><strong>{item.title}</strong><span>{item.stageLabel}</span></div>
                  <p>{item.done}</p>
                  <small>{item.source} · {dateTime(item.occurredAt)}</small>
                </div>
              </button>
            ))}
          </div> : <div className="v4-empty-state"><strong>还没有真实 WorkItem</strong><p>只有 Capture 或后续正式自动化真正创建工作对象后，这里才会增加记录。</p></div>}
        </div>

        <aside className="work-history-detail-pane">
          {selected ? <>
            <div className="work-detail-head">
              <span className="v4-kicker">工作详情</span>
              <h3>{selected.title}</h3>
              <div><span>{selected.source}</span><span>{selected.stageLabel}</span></div>
            </div>
            <div className="work-story-step"><span>工作对象</span><p>{selected.captureId ? `资料 ${selected.captureId} 已绑定到工作 ${selected.workItemId}。` : `工作 ${selected.workItemId} 没有 Capture 来源，界面不会猜测来源。`}</p></div>
            <div className="work-story-step"><span>真实结果</span><p>{selected.done}</p></div>
            <div className="work-story-step next"><span>下一步</span><p>{selected.nextStep}</p><small>下一执行者：{nextActorLabel(selected.nextActor)}</small></div>
            <div className="work-detail-actions">
              {selected.memoryId && <button className="v4-button primary" onClick={() => onNavigate("memory")}>查看记忆结果</button>}
              {selected.status === "failed" && <button className="v4-button" onClick={() => onNavigate("jobs")}>查看高级任务记录</button>}
            </div>
            <details className="v4-technical-details">
              <summary>技术记录</summary>
              <div>
                <span>WorkItem：{selected.workItemId}</span>
                <span>Capture：{selected.captureId || "无"}</span>
                <span>结果对象：{selected.resultObjectIds.length ? selected.resultObjectIds.join(", ") : "无明确对象"}</span>
                <span>更新时间：{dateTime(selected.occurredAt)}</span>
              </div>
            </details>
          </> : <div className="memory-detail-empty"><span className="v4-kicker">工作详情</span><h3>选择左侧一项工作</h3><p>右侧只解释后端已经持久化的 WorkItem、结果和下一执行者。</p></div>}
        </aside>
      </section>
    </div>
  );
}
