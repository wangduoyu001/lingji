import { useCallback, useState } from "react";
import DataTable from "../components/DataTable";
import { Notice, Panel } from "../components/ui";
import { usePollingResource } from "../hooks/usePollingResource";
import type { PageProps } from "../types";
import type { CaptureJob, CaptureJobsResponse } from "./captureCenterTypes";

export default function JobsPage({ api, active }: PageProps) {
  const [status, setStatus] = useState("");
  const load = useCallback(
    (signal: AbortSignal) => api.get<CaptureJobsResponse>(`/api/capture/jobs?limit=200&offset=0${status ? `&status=${status}` : ""}`, { signal }),
    [api, status],
  );
  const resource = usePollingResource({
    fetcher: load,
    enabled: active,
    intervalMs: 3_000,
    staleAfterMs: 10_000,
    pauseWhenHidden: true,
  });
  const data = resource.data ?? { items: [], pagination: { limit: 200, offset: 0, total: 0, has_more: false }, stats: {} };

  return (
    <div className="stack">
      <div className="toolbar">
        <select value={status} onChange={(event) => setStatus(event.target.value)}>
          <option value="">全部状态</option>
          {["queued", "running", "retrying", "failed", "completed"].map((item) => <option key={item}>{item}</option>)}
        </select>
        <button className="button secondary" disabled={!active || resource.refreshing} onClick={() => void resource.refresh()}>
          {resource.refreshing ? "刷新中..." : "刷新"}
        </button>
        {resource.stale && <span>数据已过期</span>}
      </div>
      {resource.error && <Notice kind="error">刷新失败：{resource.error.message}。已保留最近一次成功数据。</Notice>}
      <Panel title="任务队列">
        <DataTable
          headers={["任务 ID", "来源", "状态", "进度", "尝试", "错误", "更新时间"]}
          rows={(data.items ?? []).map((job: CaptureJob) => [
            job.work_item_id || job.job_id,
            String(job.source_type ?? ""),
            String(job.status ?? "unknown"),
            String(job.progress_message ?? "-"),
            `${Number(job.attempts ?? 0)}/${Number(job.max_attempts ?? 0)}`,
            String(job.error_message ?? "-"),
            String(job.updated_at ?? ""),
          ] as React.ReactNode[])}
        />
      </Panel>
    </div>
  );
}
