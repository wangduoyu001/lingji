import { useCallback, useEffect, useState } from "react";
import { Empty, Json, Panel, bytes } from "../components/ui";
import type { PageProps, Row } from "../types";

export default function BackupsPage({ api, active }: PageProps) {
  const [items, setItems] = useState<Row[]>([]);
  const [selected, setSelected] = useState<Row | null>(null);
  const [result, setResult] = useState<Row | null>(null);
  const [confirmation, setConfirmation] = useState("");

  const load = useCallback(async () => {
    if (active) setItems(await api.get<Row[]>("/api/backups"));
  }, [active, api]);
  useEffect(() => { void load(); }, [load]);

  async function create(profile: string) {
    setResult(await api.post<Row>("/api/backups", { profile }));
    await load();
  }
  async function verify() {
    if (selected) setResult(await api.post<Row>("/api/backups/verify", { backup: selected.path }));
  }
  async function stage() {
    if (selected) setResult(await api.post<Row>("/api/backups/stage-restore", { backup: selected.path, confirmation }));
  }

  return (
    <div className="two-column">
      <Panel title="备份">
        <div className="toolbar"><button className="button primary" onClick={() => void create("metadata")}>创建 metadata</button><button className="button secondary" onClick={() => void create("full")}>创建 full</button></div>
        <div className="list">{items.map((item) => <button className="list-button" key={item.backup_id as React.Key} onClick={() => { setSelected(item); setConfirmation(""); }}><strong>{String(item.backup_id ?? "")}</strong><small>{String(item.profile ?? "")} · {bytes(item.archive_bytes as number ?? 0)}</small></button>)}</div>
      </Panel>
      <Panel title="校验与隔离恢复">
        {selected ? <><Json value={selected} /><button className="button secondary" onClick={() => void verify()}>验证完整性</button><label>确认文字<input value={confirmation} onChange={(event) => setConfirmation(event.target.value)} placeholder={`STAGE_RESTORE:${selected.backup_id}`} /></label><button className="button warning" onClick={() => void stage()}>恢复到隔离目录</button></> : <Empty text="选择一个备份。" />}
        {result !== null && <Json value={result} />}
      </Panel>
    </div>
  );
}
