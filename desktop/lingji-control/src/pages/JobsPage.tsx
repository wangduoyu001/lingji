import { useCallback, useEffect, useState } from "react";
import DataTable from "../components/DataTable";
import { Panel } from "../components/ui";
import type { PageProps, Row } from "../types";

export default function JobsPage({ api, active }: PageProps) {
  const [data, setData] = useState<Row>({ stats: {}, jobs: [] });
  const [status, setStatus] = useState("");
  const load = useCallback(async () => {
    if (active) setData(await api.get<Row>(`/api/jobs?limit=300${status ? `&status=${status}` : ""}`));
  }, [active, api, status]);
  useEffect(() => { void load(); }, [load]);
  return (
    <div className="stack">
      <div className="toolbar">
        <select value={status} onChange={(event) => setStatus(event.target.value)}>
          <option value="">全部状态</option>
          {["queued", "running", "retrying", "failed", "completed"].map((item) => <option key={item}>{item}</option>)}
        </select>
        <button className="button secondary" onClick={() => void load()}>刷新</button>
      </div>
      <Panel title="任务队列"><DataTable headers={["任务 ID", "来源", "状态", "进度", "尝试", "错误", "更新时间"]} rows={(data.jobs ?? []).map((job: Row) => [job.job_id, job.source_type, job.status, job.progress_message || "-", `${job.attempts || 0}/${job.max_attempts || 0}`, job.last_error || "-", job.updated_at])} /></Panel>
    </div>
  );
}
