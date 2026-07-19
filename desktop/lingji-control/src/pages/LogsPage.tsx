import { useCallback, useEffect, useState } from "react";
import { bytes } from "../components/ui";
import type { PageProps, Row } from "../types";

export default function LogsPage({ api, active }: PageProps) {
  const [data, setData] = useState<Row>({ lines: [] });
  const load = useCallback(async () => {
    if (active) setData(await api.get<Row>("/api/logs?lines=1000"));
  }, [active, api]);
  useEffect(() => { void load(); }, [load]);
  return (
    <div className="stack">
      <div className="toolbar"><button className="button secondary" onClick={() => void load()}>刷新</button><span>{data.path}</span><span>{bytes(data.size)}</span></div>
      <pre className="log-view">{(data.lines ?? []).join("\n") || "暂无日志"}</pre>
    </div>
  );
}
