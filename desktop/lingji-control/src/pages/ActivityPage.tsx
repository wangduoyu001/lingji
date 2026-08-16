import { useCallback, useMemo, useState } from "react";
import { Empty, Notice } from "../components/ui";
import { usePollingResource } from "../hooks/usePollingResource";
import type { LingJiApi } from "../api";
import type { PageId, Row } from "../types";
import type { CodexCurrent } from "./codexWorkspaceTypes";

const ACTIVE_STATES = new Set(["queued", "leased", "running", "retrying"]);

function statusLabel(value: unknown): string {
  const state = String(value ?? "unknown").toLowerCase();
  const labels: Record<string, string> = {
    queued: "等待自动处理",
    leased: "准备处理中",
    running: "正在处理",
    retrying: "正在自动重试",
    completed: "已经完成",
    failed: "自动处理未完成",
    cancelled: "已停止",
  };
  return labels[state] ?? "状态待确认";
}

function sourceLabel(value: unknown): string {
  const key = String(value ?? "").toLowerCase();
  const labels: Record<string, string> = {
    chatgpt_export: "ChatGPT 历史",
    codex_report: "Codex 工作记录",
    web: "网页/文字资料",
    media: "媒体资料",
    file: "本地文件",
  };
  return labels[key] ?? (key || "资料");
}

function safeFilename(value: unknown): string {
  const raw = String(value ?? "").replaceAll("\\", "/").trim();
  return raw ? (raw.split("/").at(-1) ?? "").slice(0, 160) : "";
}

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" && !Array.isArray(value) ? value as Record<string, unknown> : {};
}

function titleFor(job: Row): string {
  const payload = asRecord(job.payload);
  return String(payload.title ?? job.title ?? safeFilename(job.input_path) ?? sourceLabel(job.source_type)).trim() || sourceLabel(job.source_type);
}

function workNarrative(job: Row): { done: string; result: string; next: string } {
  const state = String(job.status ?? "").toLowerCase();
  const result = asRecord(job.result);
  const summary = String(job.result_summary ?? job.progress_message ?? "").trim();
  if (state === "queued") return { done: "已接收并排入自动处理队列。", result: "还没有产生处理结果。", next: "灵机会自动开始，不需要你守着。" };
  if (state === "leased" || state === "running") return { done: summary || "正在读取、解析和整理这份资料。", result: "任务仍在进行。", next: "灵机会继续完成剩余步骤。" };
  if (state === "retrying") return { done: "上一次执行没有完成，系统已经进入自动重试。", result: String(job.last_error ?? job.error_message ?? "失败原因已保留。"), next: "先由灵机继续重试；只有跨过主人边界时才会找你。" };
  if (state === "failed") return { done: "自动处理和既定重试已经结束。", result: String(job.last_error ?? job.error_message ?? "失败原因已保留在任务记录中。"), next: "这不是自动生成的主人待办。需要排查时可进入高级任务队列。" };
  if (state === "cancelled") return { done: "这项工作已经停止。", result: "原始资料和历史记录没有因此被删除。", next: "除非重新提交，否则不会继续处理。" };
  if (state === "completed") {
    const created = Array.isArray(result.created) ? result.created.length : 0;
    const updated = Array.isArray(result.updated) ? result.updated.length : 0;
    const skipped = Array.isArray(result.skipped) ? result.skipped.length : 0;
    const parts = [created ? `新增 ${created} 条` : "", updated ? `更新 ${updated} 条` : "", skipped ? `去重跳过 ${skipped} 条` : ""].filter(Boolean);
    return {
      done: summary || "资料已经完成自动收纳和整理。",
      result: parts.length ? parts.join("，") : result.indexed === true ? "结果已写入并完成索引。" : "任务已完成，具体结果已保留。",
      next: result.indexed === true ? "已经可以在记忆中查看和取回。" : "灵机会继续同步可重建索引状态。",
    };
  }
  return { done: "任务已经被系统记录。", result: "当前状态还没有足够信息解释。", next: "灵机会继续刷新真实状态。" };
}

function dateTime(value: unknown): string {
  if (!value) return "时间未知";
  const date = new Date(String(value));
  return Number.isNaN(date.getTime()) ? "时间未知" : date.toLocaleString();
}

type ActivitySnapshot = { current: CodexCurrent; jobs: Row };

export default function ActivityPage({ api, active, onNavigate }: { api: LingJiApi; active: boolean; onNavigate: (page: PageId) => void }) {
  const [selectedId, setSelectedId] = useState("");
  const load = useCallback(async (signal: AbortSignal): Promise<ActivitySnapshot> => {
    const [current, jobs] = await Promise.all([
      api.get<CodexCurrent>("/api/codex/current", { signal }),
      api.get<Row>("/api/jobs?limit=80", { signal }),
    ]);
    return { current, jobs };
  }, [api]);

  const resource = usePollingResource({ fetcher: load, enabled: active, intervalMs: 5_000, staleAfterMs: 18_000, pauseWhenHidden: true });
  const jobs = useMemo(() => ((resource.data?.jobs as { jobs?: Row[] } | undefined)?.jobs ?? []), [resource.data]);
  const activeJobs = jobs.filter((job) => ACTIVE_STATES.has(String(job.status ?? "").toLowerCase()));
  const historyJobs = jobs.filter((job) => !ACTIVE_STATES.has(String(job.status ?? "").toLowerCase())).slice(0, 30);
  const allVisible = [...activeJobs, ...historyJobs];
  const selected = allVisible.find((job) => String(job.job_id ?? "") === selectedId) ?? allVisible[0] ?? null;
  const selectedNarrative = selected ? workNarrative(selected) : null;
  const codexActivity = resource.data?.current.activity;

  if (!active) return <Empty text="灵机核心连接后，这里会显示它真实做过的工作。" />;
  if (resource.loading && !resource.data) return <Empty text="正在整理灵机工作履历…" />;
  if (resource.error && !resource.data) return <Notice kind="error">工作履历暂时不可用，已有任务不会因此被改写。</Notice>;

  return (
    <div className="workbench-v4 work-history-v4">
      <section className="v4-page-intro">
        <div><span className="v4-kicker">工作履历</span><h2>灵机做过什么，不看原始日志也能看懂</h2><p>每项工作都尽量说明发生了什么、系统做了什么、结果是什么，以及下一步由谁继续。</p></div>
        <div className="v4-intro-actions"><button className="v4-button" onClick={() => onNavigate("memory")}>查看记忆结果</button><button className="v4-button" onClick={() => onNavigate("capture_center")}>添加资料</button></div>
      </section>

      {resource.error && resource.data && <Notice kind="warning">状态刷新暂时失败，正在显示最近一次可验证工作记录。</Notice>}

      <section className="work-history-summary">
        <div className="work-history-live">
          <span className={`v4-state-orb ${activeJobs.length || codexActivity ? "ok" : "idle"}`} />
          <div><span className="v4-kicker">现在</span><strong>{codexActivity?.summary || (activeJobs.length ? `${activeJobs.length} 项自动工作进行中` : "当前没有运行中的工作")}</strong><small>{codexActivity?.stage ? `Codex 阶段：${codexActivity.stage}` : activeJobs.length ? "任务状态每 5 秒自动更新" : "系统继续观察已授权来源"}</small></div>
        </div>
        <div className="work-history-counts"><span><strong>{activeJobs.length}</strong><small>进行中</small></span><span><strong>{historyJobs.filter((job) => String(job.status) === "completed").length}</strong><small>最近完成</small></span><span><strong>{historyJobs.filter((job) => String(job.status) === "failed").length}</strong><small>未完成</small></span></div>
      </section>

      <section className="work-history-layout">
        <div className="work-history-list-pane">
          <div className="v4-section-heading compact"><div><span className="v4-kicker">真实工作对象</span><h3>{allVisible.length ? `${allVisible.length} 项最近工作` : "暂无工作记录"}</h3></div></div>
          {allVisible.length ? <div className="work-history-list">
            {allVisible.map((job) => {
              const narrative = workNarrative(job);
              const id = String(job.job_id ?? `${job.source_type}-${job.updated_at}`);
              return <button className={`work-history-row ${selected === job ? "active" : ""}`} key={id} onClick={() => setSelectedId(String(job.job_id ?? ""))}>
                <span className={`work-status-dot ${String(job.status ?? "unknown").toLowerCase()}`} />
                <div><div><strong>{titleFor(job)}</strong><span>{statusLabel(job.status)}</span></div><p>{narrative.done}</p><small>{sourceLabel(job.source_type)} · {dateTime(job.updated_at ?? job.completed_at ?? job.created_at)}</small></div>
              </button>;
            })}
          </div> : <div className="v4-empty-state"><strong>还没有工作记录</strong><p>新资料或新的自动化动作出现后，这里才会增加记录。</p></div>}
        </div>

        <aside className="work-history-detail-pane">
          {selected && selectedNarrative ? <>
            <div className="work-detail-head"><span className="v4-kicker">工作详情</span><h3>{titleFor(selected)}</h3><div><span>{sourceLabel(selected.source_type)}</span><span>{statusLabel(selected.status)}</span></div></div>
            <div className="work-story-step"><span>发生了什么</span><p>灵机收到或发现了一项 {sourceLabel(selected.source_type)} 工作，并把它作为可追踪任务处理。</p></div>
            <div className="work-story-step"><span>灵机做了什么</span><p>{selectedNarrative.done}</p></div>
            <div className="work-story-step"><span>结果</span><p>{selectedNarrative.result}</p></div>
            <div className="work-story-step next"><span>下一步</span><p>{selectedNarrative.next}</p></div>
            <div className="work-detail-actions">
              {String(selected.status ?? "").toLowerCase() === "completed" && <button className="v4-button primary" onClick={() => onNavigate("memory")}>看记忆结果</button>}
              {String(selected.status ?? "").toLowerCase() === "failed" && <button className="v4-button" onClick={() => onNavigate("jobs")}>查看高级原因</button>}
            </div>
            <details className="v4-technical-details"><summary>技术记录</summary><div><span>任务 ID：{String(selected.job_id ?? "未知")}</span><span>尝试：{Number(selected.attempts ?? 0)} / {Number(selected.max_attempts ?? 0)}</span><span>更新时间：{dateTime(selected.updated_at)}</span></div></details>
          </> : <div className="memory-detail-empty"><span className="v4-kicker">工作详情</span><h3>选择左侧一项工作</h3><p>右侧会把队列状态翻译成可以理解的动作、结果和下一步。</p></div>}
        </aside>
      </section>
    </div>
  );
}
