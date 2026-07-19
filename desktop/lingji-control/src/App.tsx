import { useCallback, useEffect, useMemo, useState } from "react";
import type { FormEvent, ReactNode } from "react";
import { LingJiApi } from "./api";

type Row = Record<string, any>;
type Page = "overview" | "jobs" | "capture" | "media" | "storage" | "backups" | "settings" | "logs";
type SettingDefinition = {
  group: string;
  label: string;
  description: string;
  type: "integer" | "number" | "boolean" | "string" | "choice";
  default: unknown;
  minimum?: number;
  maximum?: number;
  choices?: string[];
};
type SettingsSnapshot = {
  values: Record<string, any>;
  overrides: Record<string, any>;
  definitions: Record<string, SettingDefinition>;
};

const NAV: Array<{ id: Page; label: string; hint: string }> = [
  { id: "overview", label: "总览", hint: "状态与预警" },
  { id: "jobs", label: "任务", hint: "采集与处理队列" },
  { id: "capture", label: "主动投喂", hint: "网页、文字和本地文件" },
  { id: "media", label: "媒体分析", hint: "转写、OCR 与镜头" },
  { id: "storage", label: "存储", hint: "容量、冷存储与恢复" },
  { id: "backups", label: "备份", hint: "校验与隔离恢复" },
  { id: "settings", label: "设置", hint: "全部运行参数" },
  { id: "logs", label: "日志", hint: "错误与运行记录" },
];

function bytes(value: unknown): string {
  let size = Number(value || 0);
  if (size < 1024) return `${size} B`;
  const units = ["KB", "MB", "GB", "TB", "PB"];
  let index = -1;
  while (size >= 1024 && index < units.length - 1) {
    size /= 1024;
    index += 1;
  }
  return `${size.toFixed(size >= 100 ? 0 : size >= 10 ? 1 : 2)} ${units[index]}`;
}

export default function App() {
  const api = useMemo(() => new LingJiApi(), []);
  const [page, setPage] = useState<Page>("overview");
  const [baseUrl, setBaseUrl] = useState(api.baseUrl);
  const [token, setToken] = useState(api.token);
  const [connected, setConnected] = useState(false);
  const [overview, setOverview] = useState<Row | null>(null);
  const [error, setError] = useState("");

  const connect = useCallback(async () => {
    api.configure(baseUrl, token);
    try {
      const next = await api.get<Row>("/api/overview");
      setOverview(next);
      setConnected(true);
      setError("");
    } catch (reason) {
      setConnected(false);
      setError(reason instanceof Error ? reason.message : String(reason));
    }
  }, [api, baseUrl, token]);

  useEffect(() => {
    void (async () => {
      await api.tryTauriToken();
      setBaseUrl(api.baseUrl);
      setToken(api.token);
      try {
        setOverview(await api.get<Row>("/api/overview"));
        setConnected(true);
      } catch {
        setConnected(false);
      }
    })();
  }, [api]);

  useEffect(() => {
    if (!connected) return;
    const timer = window.setInterval(() => {
      void api.get<Row>("/api/overview").then(setOverview).catch(() => setConnected(false));
    }, 10000);
    return () => window.clearInterval(timer);
  }, [api, connected]);

  const current = NAV.find((item) => item.id === page) ?? NAV[0];
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand"><div className="brand-mark">灵</div><div><strong>灵机</strong><span>本地控制中心</span></div></div>
        <nav>{NAV.map((item) => <button key={item.id} className={page === item.id ? "nav-item active" : "nav-item"} onClick={() => setPage(item.id)}><span>{item.label}</span><small>{item.hint}</small></button>)}</nav>
        <div className="sidebar-footer"><span className={connected ? "status-dot online" : "status-dot"} />{connected ? "本机服务已连接" : "本机服务未连接"}</div>
      </aside>
      <main className="main-area">
        <header className="topbar">
          <div><h1>{current.label}</h1><p>{current.hint}</p></div>
          <div className="connection-controls">
            <input value={baseUrl} onChange={(event) => setBaseUrl(event.target.value)} aria-label="API 地址" />
            <input value={token} onChange={(event) => setToken(event.target.value)} type="password" placeholder="控制令牌" aria-label="控制令牌" />
            <button className="button secondary" onClick={() => void connect()}>连接</button>
          </div>
        </header>
        {error && <Notice kind="error">{error}</Notice>}
        {!connected && <Notice kind="warning">先启动 <code>python run_control_api.py</code>。浏览器开发模式需填写 <code>storage/control_api_token</code>。</Notice>}
        <section className="page-content">
          {page === "overview" && <Overview data={overview} refresh={connect} />}
          {page === "jobs" && <Jobs api={api} active={connected} />}
          {page === "capture" && <Capture api={api} active={connected} />}
          {page === "media" && <Media api={api} active={connected} />}
          {page === "storage" && <Storage api={api} active={connected} />}
          {page === "backups" && <Backups api={api} active={connected} />}
          {page === "settings" && <Settings api={api} active={connected} />}
          {page === "logs" && <Logs api={api} active={connected} />}
        </section>
      </main>
    </div>
  );
}

function Overview({ data, refresh }: { data: Row | null; refresh: () => Promise<void> }) {
  if (!data) return <Empty text="连接服务后显示总览。" />;
  const health = data.health ?? {};
  const queue = data.queue?.stats ?? {};
  const storage = data.storage?.totals ?? {};
  const checks: Row[] = health.checks ?? [];
  const healthy = health.status === "healthy";
  return <div className="stack">
    <div className="toolbar"><button className="button secondary" onClick={() => void refresh()}>立即刷新</button></div>
    <div className="metric-grid">
      <Metric title="系统状态" value={healthy ? "正常" : health.status || "未知"} detail={`${health.error_count || 0} 错误 / ${health.warning_count || 0} 警告`} tone={healthy ? "good" : "warn"} />
      <Metric title="待处理任务" value={String(queue.pending || 0)} detail={`运行中 ${queue.running || 0}`} />
      <Metric title="灵机占用" value={bytes(storage.bytes)} detail={`${storage.files || 0} 个文件`} />
      <Metric title="磁盘剩余" value={bytes(storage.disk_free_bytes)} detail={`${storage.disk_free_percent || 0}%`} tone={data.storage?.alerts?.below_minimum_free ? "bad" : "good"} />
    </div>
    <div className="two-column">
      <Panel title="健康检查"><div className="list">{checks.map((check) => <div className="list-row" key={check.name}><span className={`pill ${check.status}`}>{check.status}</span><div><strong>{check.name}</strong><small>{check.message}</small></div></div>)}</div></Panel>
      <Panel title="本地 Provider"><div className="list">{Object.entries(data.providers ?? {}).map(([name, value]) => { const provider = value as Row; return <div className="list-row" key={name}><span className={provider.available ? "status-dot online" : "status-dot"} /><div><strong>{name}</strong><small>{provider.available ? `可用 · ${provider.capability}` : `未安装 · ${provider.optional_requirements}`}</small></div></div>; })}</div></Panel>
    </div>
    <Panel title="定时任务"><DataTable headers={["任务", "状态", "下次运行", "错误"]} rows={(data.scheduler ?? []).map((job: Row) => [job.name, job.status, job.next_run_at, job.last_error || "-"])} /></Panel>
  </div>;
}

function Jobs({ api, active }: { api: LingJiApi; active: boolean }) {
  const [data, setData] = useState<Row>({ stats: {}, jobs: [] });
  const [status, setStatus] = useState("");
  const load = useCallback(async () => { if (active) setData(await api.get<Row>(`/api/jobs?limit=300${status ? `&status=${status}` : ""}`)); }, [active, api, status]);
  useEffect(() => { void load(); }, [load]);
  return <div className="stack"><div className="toolbar"><select value={status} onChange={(event) => setStatus(event.target.value)}><option value="">全部状态</option>{["queued", "running", "retrying", "failed", "completed"].map((item) => <option key={item}>{item}</option>)}</select><button className="button secondary" onClick={() => void load()}>刷新</button></div><Panel title="任务队列"><DataTable headers={["任务 ID", "来源", "状态", "进度", "尝试", "错误", "更新时间"]} rows={(data.jobs ?? []).map((job: Row) => [job.job_id, job.source_type, job.status, job.progress_message || "-", `${job.attempts || 0}/${job.max_attempts || 0}`, job.last_error || "-", job.updated_at])} /></Panel></div>;
}

function Capture({ api, active }: { api: LingJiApi; active: boolean }) {
  const [form, setForm] = useState({ platform: "web", title: "", url: "", input_path: "", text: "" });
  const [result, setResult] = useState<Row | null>(null);
  const [error, setError] = useState("");
  async function submit(event: FormEvent) { event.preventDefault(); if (!active) return; try { setResult(await api.post<Row>("/api/share", { source_type: form.input_path ? "media" : form.platform, ...form })); setError(""); } catch (reason) { setError(reason instanceof Error ? reason.message : String(reason)); } }
  return <div className="two-column wide-left"><Panel title="主动投喂"><form className="form-grid" onSubmit={(event) => void submit(event)}><label>平台<select value={form.platform} onChange={(event) => setForm({ ...form, platform: event.target.value })}>{["web", "wechat_article", "video_channel", "douyin", "xiaohongshu", "bilibili", "youtube"].map((item) => <option key={item}>{item}</option>)}</select></label><label>标题<input value={form.title} onChange={(event) => setForm({ ...form, title: event.target.value })} /></label><label className="span-2">链接<input value={form.url} onChange={(event) => setForm({ ...form, url: event.target.value })} /></label><label className="span-2">本地文件<input value={form.input_path} onChange={(event) => setForm({ ...form, input_path: event.target.value })} placeholder="D:\media\example.mp4" /></label><label className="span-2">正文或选中文字<textarea rows={12} value={form.text} onChange={(event) => setForm({ ...form, text: event.target.value })} /></label><button className="button primary">提交到灵机</button></form>{error && <Notice kind="error">{error}</Notice>}</Panel><Panel title="结果">{result !== null ? <Json value={result} /> : <Empty text="提交后显示保存路径或任务 ID。" />}</Panel></div>;
}

function Media({ api, active }: { api: LingJiApi; active: boolean }) {
  const [path, setPath] = useState("");
  const [frames, setFrames] = useState("");
  const [asr, setAsr] = useState(true);
  const [ocr, setOcr] = useState(false);
  const [scenes, setScenes] = useState(true);
  const [result, setResult] = useState<Row | null>(null);
  async function submit(event: FormEvent) { event.preventDefault(); if (!active) return; setResult(await api.post<Row>("/api/media/analyze", { media_path: path, keyframe_directory: frames || null, overrides: { auto_transcribe: asr, asr_provider: asr ? "faster_whisper" : "off", auto_ocr: ocr, ocr_provider: ocr ? "paddleocr" : "off", detect_scenes: scenes, scene_provider: scenes ? "pyscenedetect" : "off" } })); }
  return <div className="two-column wide-left"><Panel title="本地媒体语义分析"><form className="form-grid" onSubmit={(event) => void submit(event)}><label className="span-2">媒体文件<input required value={path} onChange={(event) => setPath(event.target.value)} /></label><label className="span-2">关键帧目录<input value={frames} onChange={(event) => setFrames(event.target.value)} /></label><div className="checkbox-stack"><label><input type="checkbox" checked={asr} onChange={(event) => setAsr(event.target.checked)} /> 自动转写</label><label><input type="checkbox" checked={ocr} onChange={(event) => setOcr(event.target.checked)} /> 关键帧 OCR</label><label><input type="checkbox" checked={scenes} onChange={(event) => setScenes(event.target.checked)} /> 镜头检测</label></div><button className="button primary">开始分析</button></form><Notice>首次使用需安装 <code>requirements-media.txt</code>，未安装 Provider 时不会损坏任务。</Notice></Panel><Panel title="结果">{result !== null ? <Json value={result} /> : <Empty text="分析结果写入 Derived 媒体目录。" />}</Panel></div>;
}

function Storage({ api, active }: { api: LingJiApi; active: boolean }) {
  const [inventory, setInventory] = useState<Row | null>(null);
  const [plans, setPlans] = useState<Row[]>([]);
  const [selected, setSelected] = useState<Row | null>(null);
  const [confirmation, setConfirmation] = useState("");
  const load = useCallback(async () => { if (!active) return; const [i, p] = await Promise.all([api.get<Row>("/api/storage"), api.get<Row[]>("/api/storage/plans")]); setInventory(i); setPlans(p); }, [active, api]);
  useEffect(() => { void load(); }, [load]);
  async function createPlan() { const plan = await api.post<Row>("/api/storage/plans", {}); setSelected(plan); setConfirmation(""); await load(); }
  async function execute() { if (!selected) return; setSelected(await api.post<Row>(`/api/storage/plans/${selected.plan_id}/execute`, { confirmation })); await load(); }
  async function restore() { if (!selected) return; setSelected(await api.post<Row>(`/api/storage/plans/${selected.plan_id}/restore`, { confirmation })); await load(); }
  return <div className="stack"><div className="toolbar"><button className="button secondary" onClick={() => void load()}>刷新</button><button className="button primary" onClick={() => void createPlan()}>生成预览计划</button></div>{inventory && <div className="metric-grid"><Metric title="总占用" value={bytes(inventory.totals?.bytes)} /><Metric title="文件" value={String(inventory.totals?.files || 0)} /><Metric title="磁盘剩余" value={bytes(inventory.totals?.disk_free_bytes)} /><Metric title="剩余比例" value={`${inventory.totals?.disk_free_percent || 0}%`} /></div>}<Panel title="分类占用"><DataTable headers={["类别", "路径", "文件", "占用", "保护", "可清理"]} rows={Object.entries(inventory?.categories ?? {}).map(([name, value]) => { const row = value as Row; return [name, row.path, row.files, bytes(row.bytes), row.protected ? "是" : "否", row.cleanup_allowed ? "是" : "否"]; })} /></Panel><div className="two-column"><Panel title="计划"><div className="list">{plans.map((plan) => <button className="list-button" key={plan.plan_id} onClick={async () => setSelected(await api.get<Row>(`/api/storage/plans/${plan.plan_id}`))}><strong>{plan.plan_id}</strong><small>{plan.status} · {bytes(plan.summary?.bytes)}</small></button>)}</div></Panel><Panel title="计划详情">{selected ? <><Json value={selected} /><label>确认文字<input value={confirmation} onChange={(event) => setConfirmation(event.target.value)} /></label><div className="toolbar"><button className="button danger" onClick={() => void execute()}>执行</button><button className="button secondary" onClick={() => void restore()}>恢复</button></div></> : <Empty text="原始资料和 Vault 永远不会进入自动清理计划。" />}</Panel></div></div>;
}

function Backups({ api, active }: { api: LingJiApi; active: boolean }) {
  const [items, setItems] = useState<Row[]>([]);
  const [selected, setSelected] = useState<Row | null>(null);
  const [result, setResult] = useState<Row | null>(null);
  const [confirmation, setConfirmation] = useState("");
  const load = useCallback(async () => { if (active) setItems(await api.get<Row[]>("/api/backups")); }, [active, api]);
  useEffect(() => { void load(); }, [load]);
  async function create(profile: string) { setResult(await api.post<Row>("/api/backups", { profile })); await load(); }
  async function verify() { if (selected) setResult(await api.post<Row>("/api/backups/verify", { backup: selected.path })); }
  async function stage() { if (selected) setResult(await api.post<Row>("/api/backups/stage-restore", { backup: selected.path, confirmation })); }
  return <div className="two-column"><Panel title="备份"><div className="toolbar"><button className="button primary" onClick={() => void create("metadata")}>创建 metadata</button><button className="button secondary" onClick={() => void create("full")}>创建 full</button></div><div className="list">{items.map((item) => <button className="list-button" key={item.backup_id} onClick={() => { setSelected(item); setConfirmation(""); }}><strong>{item.backup_id}</strong><small>{item.profile} · {bytes(item.archive_bytes)}</small></button>)}</div></Panel><Panel title="校验与隔离恢复">{selected ? <><Json value={selected} /><button className="button secondary" onClick={() => void verify()}>验证完整性</button><label>确认文字<input value={confirmation} onChange={(event) => setConfirmation(event.target.value)} placeholder={`STAGE_RESTORE:${selected.backup_id}`} /></label><button className="button warning" onClick={() => void stage()}>恢复到隔离目录</button></> : <Empty text="选择一个备份。" />}{result !== null && <Json value={result} />}</Panel></div>;
}

function Settings({ api, active }: { api: LingJiApi; active: boolean }) {
  const [snapshot, setSnapshot] = useState<SettingsSnapshot | null>(null);
  const [draft, setDraft] = useState<Record<string, any>>({});
  const [group, setGroup] = useState("media_processing");
  const load = useCallback(async () => { if (!active) return; const next = await api.get<SettingsSnapshot>("/api/settings"); setSnapshot(next); setDraft(next.values); }, [active, api]);
  useEffect(() => { void load(); }, [load]);
  if (!snapshot) return <Empty text="连接后加载设置。" />;
  const groups = Array.from(new Set(Object.values(snapshot.definitions).map((item) => item.group)));
  const rows = Object.entries(snapshot.definitions).filter(([, definition]) => definition.group === group);
  async function save() { const next = await api.patch<SettingsSnapshot>("/api/settings", { values: draft }); setSnapshot(next); setDraft(next.values); }
  async function reset() { const next = await api.post<SettingsSnapshot>("/api/settings/reset", { keys: rows.map(([key]) => key) }); setSnapshot(next); setDraft(next.values); }
  return <div className="settings-layout"><div className="settings-groups">{groups.map((item) => <button className={item === group ? "active" : ""} key={item} onClick={() => setGroup(item)}>{item}</button>)}</div><Panel title={`设置 · ${group}`}><div className="settings-list">{rows.map(([key, definition]) => <Setting key={key} name={key} definition={definition} value={draft[key]} overridden={Object.prototype.hasOwnProperty.call(snapshot.overrides, key)} change={(value) => setDraft({ ...draft, [key]: value })} />)}</div><div className="toolbar sticky-actions"><button className="button primary" onClick={() => void save()}>保存</button><button className="button secondary" onClick={() => void reset()}>恢复默认</button></div></Panel></div>;
}

function Setting({ name, definition, value, overridden, change }: { name: string; definition: SettingDefinition; value: any; overridden: boolean; change: (value: any) => void }) {
  let input: ReactNode;
  if (definition.type === "boolean") input = <input type="checkbox" checked={Boolean(value)} onChange={(event) => change(event.target.checked)} />;
  else if (definition.type === "choice") input = <select value={String(value ?? "")} onChange={(event) => change(event.target.value)}>{(definition.choices ?? []).map((choice) => <option key={choice}>{choice}</option>)}</select>;
  else input = <input type={definition.type === "string" ? "text" : "number"} min={definition.minimum} max={definition.maximum} step={definition.type === "integer" ? 1 : "any"} value={String(value ?? "")} onChange={(event) => change(definition.type === "integer" ? Number.parseInt(event.target.value || "0", 10) : definition.type === "number" ? Number(event.target.value || 0) : event.target.value)} />;
  return <div className="setting-row"><div><strong>{definition.label}</strong><code>{name}</code><p>{definition.description}</p><small>默认：{String(definition.default)}{overridden ? " · 已覆盖" : ""}</small></div><div className="setting-control">{input}</div></div>;
}

function Logs({ api, active }: { api: LingJiApi; active: boolean }) {
  const [data, setData] = useState<Row>({ lines: [] });
  const load = useCallback(async () => { if (active) setData(await api.get<Row>("/api/logs?lines=1000")); }, [active, api]);
  useEffect(() => { void load(); }, [load]);
  return <div className="stack"><div className="toolbar"><button className="button secondary" onClick={() => void load()}>刷新</button><span>{data.path}</span><span>{bytes(data.size)}</span></div><pre className="log-view">{(data.lines ?? []).join("\n") || "暂无日志"}</pre></div>;
}

function Panel({ title, children }: { title: string; children: ReactNode }) { return <section className="panel"><h2>{title}</h2><div className="panel-body">{children}</div></section>; }
function Notice({ kind = "info", children }: { kind?: "info" | "error" | "warning"; children: ReactNode }) { return <div className={`notice notice-${kind}`}>{children}</div>; }
function Metric({ title, value, detail = "", tone = "neutral" }: { title: string; value: string; detail?: string; tone?: string }) { return <div className={`metric metric-${tone}`}><span>{title}</span><strong>{value}</strong><small>{detail}</small></div>; }
function Empty({ text }: { text: string }) { return <div className="empty-state">{text}</div>; }
function Json({ value }: { value: unknown }) { return <pre className="json-panel">{JSON.stringify(value, null, 2)}</pre>; }
function DataTable({ headers, rows }: { headers: string[]; rows: ReactNode[][] }) { return <div className="table-scroll"><table><thead><tr>{headers.map((header) => <th key={header}>{header}</th>)}</tr></thead><tbody>{rows.length ? rows.map((row, index) => <tr key={index}>{row.map((cell, cellIndex) => <td key={cellIndex}>{cell}</td>)}</tr>) : <tr><td colSpan={headers.length}><Empty text="暂无数据" /></td></tr>}</tbody></table></div>; }
