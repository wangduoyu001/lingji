import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import { LingJiApi } from "./api";

type AnyRecord = Record<string, any>;
type Page = "overview" | "jobs" | "capture" | "media" | "storage" | "backups" | "settings" | "logs";

type SettingDefinition = {
  group: string;
  label: string;
  description: string;
  type: "integer" | "number" | "boolean" | "string" | "choice";
  default: any;
  minimum?: number;
  maximum?: number;
  max_length?: number;
  choices?: string[];
  restart_required?: boolean;
};

type SettingsSnapshot = {
  schema_version: number;
  values: Record<string, any>;
  overrides: Record<string, any>;
  definitions: Record<string, SettingDefinition>;
};

const NAV: Array<{ id: Page; label: string; hint: string }> = [
  { id: "overview", label: "总览", hint: "状态与预警" },
  { id: "jobs", label: "任务", hint: "采集与处理队列" },
  { id: "capture", label: "主动投喂", hint: "网页、文字和本地文件" },
  { id: "media", label: "媒体分析", hint: "转写、OCR、镜头" },
  { id: "storage", label: "存储", hint: "容量、冷存储与恢复" },
  { id: "backups", label: "备份", hint: "校验与隔离恢复" },
  { id: "settings", label: "设置", hint: "全部运行参数" },
  { id: "logs", label: "日志", hint: "错误与运行记录" },
];

function formatBytes(value: number | undefined): string {
  const bytes = Number(value || 0);
  if (bytes < 1024) return `${bytes} B`;
  const units = ["KB", "MB", "GB", "TB", "PB"];
  let size = bytes;
  let index = -1;
  do {
    size /= 1024;
    index += 1;
  } while (size >= 1024 && index < units.length - 1);
  return `${size.toFixed(size >= 100 ? 0 : size >= 10 ? 1 : 2)} ${units[index]}`;
}

function JsonPanel({ value }: { value: unknown }) {
  return <pre className="json-panel">{JSON.stringify(value, null, 2)}</pre>;
}

function Notice({ kind = "info", children }: { kind?: "info" | "error" | "success" | "warning"; children: React.ReactNode }) {
  return <div className={`notice notice-${kind}`}>{children}</div>;
}

export default function App() {
  const api = useMemo(() => new LingJiApi(), []);
  const [page, setPage] = useState<Page>("overview");
  const [baseUrl, setBaseUrl] = useState(api.baseUrl);
  const [token, setToken] = useState(api.token);
  const [connected, setConnected] = useState(false);
  const [connectionError, setConnectionError] = useState("");
  const [overview, setOverview] = useState<AnyRecord | null>(null);
  const [refreshing, setRefreshing] = useState(false);

  const connect = useCallback(async () => {
    api.configure(baseUrl, token);
    setRefreshing(true);
    setConnectionError("");
    try {
      const data = await api.get<AnyRecord>("/api/overview");
      setOverview(data);
      setConnected(true);
    } catch (error) {
      setConnected(false);
      setConnectionError(error instanceof Error ? error.message : String(error));
    } finally {
      setRefreshing(false);
    }
  }, [api, baseUrl, token]);

  useEffect(() => {
    void (async () => {
      await api.tryTauriToken();
      setBaseUrl(api.baseUrl);
      setToken(api.token);
      try {
        const data = await api.get<AnyRecord>("/api/overview");
        setOverview(data);
        setConnected(true);
      } catch {
        setConnected(false);
      }
    })();
  }, [api]);

  useEffect(() => {
    if (!connected) return;
    const timer = window.setInterval(() => {
      void api.get<AnyRecord>("/api/overview").then(setOverview).catch(() => setConnected(false));
    }, 10000);
    return () => window.clearInterval(timer);
  }, [api, connected]);

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark">灵</div>
          <div>
            <strong>灵机</strong>
            <span>本地控制中心</span>
          </div>
        </div>
        <nav>
          {NAV.map((item) => (
            <button key={item.id} className={page === item.id ? "nav-item active" : "nav-item"} onClick={() => setPage(item.id)}>
              <span>{item.label}</span>
              <small>{item.hint}</small>
            </button>
          ))}
        </nav>
        <div className="sidebar-footer">
          <span className={connected ? "status-dot online" : "status-dot"} />
          {connected ? "本机服务已连接" : "本机服务未连接"}
        </div>
      </aside>

      <main className="main-area">
        <header className="topbar">
          <div>
            <h1>{NAV.find((item) => item.id === page)?.label}</h1>
            <p>{NAV.find((item) => item.id === page)?.hint}</p>
          </div>
          <div className="connection-controls">
            <input aria-label="API 地址" value={baseUrl} onChange={(event) => setBaseUrl(event.target.value)} placeholder="http://127.0.0.1:8766" />
            <input aria-label="控制令牌" type="password" value={token} onChange={(event) => setToken(event.target.value)} placeholder="控制令牌" />
            <button className="button secondary" onClick={() => void connect()} disabled={refreshing}>
              {refreshing ? "连接中" : "连接"}
            </button>
          </div>
        </header>

        {connectionError && <Notice kind="error">{connectionError}</Notice>}
        {!connected && (
          <Notice kind="warning">
            先启动 <code>python run_control_api.py</code>。桌面版会尝试自动读取令牌；浏览器开发模式需要粘贴 storage/control_api_token。
          </Notice>
        )}

        <section className="page-content">
          {page === "overview" && <OverviewPage data={overview} onRefresh={connect} />}
          {page === "jobs" && <JobsPage api={api} active={connected} />}
          {page === "capture" && <CapturePage api={api} active={connected} />}
          {page === "media" && <MediaPage api={api} active={connected} />}
          {page === "storage" && <StoragePage api={api} active={connected} />}
          {page === "backups" && <BackupsPage api={api} active={connected} />}
          {page === "settings" && <SettingsPage api={api} active={connected} />}
          {page === "logs" && <LogsPage api={api} active={connected} />}
        </section>
      </main>
    </div>
  );
}

function OverviewPage({ data, onRefresh }: { data: AnyRecord | null; onRefresh: () => Promise<void> }) {
  if (!data) return <EmptyState text="连接本机服务后显示总览。" />;
  const health = data.health || {};
  const queue = data.queue?.stats || {};
  const storage = data.storage?.totals || {};
  const alerts = data.storage?.alerts || {};
  const checks: AnyRecord[] = health.checks || [];
  return (
    <div className="stack">
      <div className="toolbar"><button className="button secondary" onClick={() => void onRefresh()}>立即刷新</button></div>
      <div className="metric-grid">
        <Metric title="系统状态" value={health.healthy ? "正常" : "需处理"} detail={`${checks.filter((item) => item.status === "error").length} 个错误`} tone={health.healthy ? "good" : "bad"} />
        <Metric title="待处理任务" value={String(queue.pending || 0)} detail={`运行中 ${queue.running || 0}`} tone={queue.failed ? "warn" : "neutral"} />
        <Metric title="灵机数据" value={formatBytes(storage.bytes)} detail={`${storage.files || 0} 个文件`} />
        <Metric title="磁盘剩余" value={formatBytes(storage.disk_free_bytes)} detail={`${storage.disk_free_percent || 0}%`} tone={alerts.below_minimum_free ? "bad" : "good"} />
      </div>
      {(alerts.over_configured_limit || alerts.below_minimum_free) && (
        <Notice kind="warning">存储已触发配置预警。先进入“存储”生成预览计划，禁止直接删除原始资料。</Notice>
      )}
      <div className="two-column">
        <Panel title="健康检查">
          <div className="list">
            {checks.map((check) => (
              <div className="list-row" key={check.name || check.label}>
                <span className={`pill ${check.status || "unknown"}`}>{check.status || "unknown"}</span>
                <div><strong>{check.label || check.name}</strong><small>{check.message || ""}</small></div>
              </div>
            ))}
          </div>
        </Panel>
        <Panel title="本地 Provider">
          <div className="list">
            {Object.entries(data.providers || {}).map(([name, provider]: [string, any]) => (
              <div className="list-row" key={name}>
                <span className={`status-dot ${provider.available ? "online" : ""}`} />
                <div><strong>{name}</strong><small>{provider.available ? `可用 · ${provider.capability}` : `未安装 · ${provider.optional_requirements}`}</small></div>
              </div>
            ))}
          </div>
        </Panel>
      </div>
      <Panel title="定时任务">
        <Table headers={["任务", "状态", "下次运行", "上次错误"]} rows={(data.scheduler || []).map((job: AnyRecord) => [job.name, job.status, job.next_run_at, job.last_error || "-"])} />
      </Panel>
    </div>
  );
}

function JobsPage({ api, active }: { api: LingJiApi; active: boolean }) {
  const [status, setStatus] = useState("");
  const [data, setData] = useState<AnyRecord>({ stats: {}, jobs: [] });
  const [error, setError] = useState("");
  const load = useCallback(async () => {
    if (!active) return;
    try {
      setData(await api.get(`/api/jobs?limit=300${status ? `&status=${encodeURIComponent(status)}` : ""}`));
      setError("");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : String(reason));
    }
  }, [active, api, status]);
  useEffect(() => { void load(); }, [load]);
  return (
    <div className="stack">
      <div className="toolbar">
        <select value={status} onChange={(event) => setStatus(event.target.value)}>
          <option value="">全部状态</option><option value="queued">排队</option><option value="running">运行中</option><option value="retrying">重试</option><option value="failed">失败</option><option value="completed">完成</option>
        </select>
        <button className="button secondary" onClick={() => void load()}>刷新</button>
      </div>
      {error && <Notice kind="error">{error}</Notice>}
      <div className="metric-grid compact">
        {Object.entries(data.stats || {}).filter(([key]) => key !== "pending").map(([key, value]) => <Metric key={key} title={key} value={String(value)} />)}
      </div>
      <Panel title="提取任务">
        <Table headers={["任务 ID", "来源", "状态", "进度", "尝试", "错误", "更新时间"]} rows={(data.jobs || []).map((job: AnyRecord) => [job.job_id, job.source_type, job.status, job.progress_message || "-", `${job.attempts || 0}/${job.max_attempts || 0}`, job.last_error || "-", job.updated_at])} />
      </Panel>
    </div>
  );
}

function CapturePage({ api, active }: { api: LingJiApi; active: boolean }) {
  const [form, setForm] = useState({ platform: "web", title: "", url: "", text: "", input_path: "" });
  const [result, setResult] = useState<unknown>(null);
  const [error, setError] = useState("");
  const submit = async (event: FormEvent) => {
    event.preventDefault();
    if (!active) return;
    try {
      const sourceType = form.input_path ? "media" : form.platform || "web";
      setResult(await api.post("/api/share", { source_type: sourceType, ...form }));
      setError("");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : String(reason));
    }
  };
  return (
    <div className="two-column wide-left">
      <Panel title="主动投喂">
        <form className="form-grid" onSubmit={(event) => void submit(event)}>
          <label>平台<select value={form.platform} onChange={(event) => setForm({ ...form, platform: event.target.value })}><option value="web">普通网页</option><option value="wechat_article">公众号</option><option value="video_channel">视频号</option><option value="douyin">抖音</option><option value="xiaohongshu">小红书</option><option value="bilibili">Bilibili</option><option value="youtube">YouTube</option></select></label>
          <label>标题<input value={form.title} onChange={(event) => setForm({ ...form, title: event.target.value })} /></label>
          <label className="span-2">链接<input value={form.url} onChange={(event) => setForm({ ...form, url: event.target.value })} placeholder="https://..." /></label>
          <label className="span-2">本地文件路径<input value={form.input_path} onChange={(event) => setForm({ ...form, input_path: event.target.value })} placeholder="D:\media\example.mp4" /></label>
          <label className="span-2">正文或选中文字<textarea rows={12} value={form.text} onChange={(event) => setForm({ ...form, text: event.target.value })} /></label>
          <button className="button primary" type="submit">提交到灵机</button>
        </form>
        {error && <Notice kind="error">{error}</Notice>}
      </Panel>
      <Panel title="提交结果">{result ? <JsonPanel value={result} /> : <EmptyState text="提交后显示保存路径或任务 ID。" />}</Panel>
    </div>
  );
}

function MediaPage({ api, active }: { api: LingJiApi; active: boolean }) {
  const [mediaPath, setMediaPath] = useState("");
  const [keyframes, setKeyframes] = useState("");
  const [transcribe, setTranscribe] = useState(true);
  const [ocr, setOcr] = useState(false);
  const [scenes, setScenes] = useState(true);
  const [model, setModel] = useState("small");
  const [result, setResult] = useState<unknown>(null);
  const [error, setError] = useState("");
  const submit = async (event: FormEvent) => {
    event.preventDefault();
    if (!active) return;
    try {
      setResult(await api.post("/api/media/analyze", {
        media_path: mediaPath,
        keyframe_directory: keyframes || null,
        overrides: {
          auto_transcribe: transcribe,
          asr_provider: transcribe ? "faster_whisper" : "off",
          asr_model: model,
          auto_ocr: ocr,
          ocr_provider: ocr ? "paddleocr" : "off",
          detect_scenes: scenes,
          scene_provider: scenes ? "pyscenedetect" : "off",
        },
      }));
      setError("");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : String(reason));
    }
  };
  return (
    <div className="two-column wide-left">
      <Panel title="本地媒体语义分析">
        <form className="form-grid" onSubmit={(event) => void submit(event)}>
          <label className="span-2">媒体文件<input required value={mediaPath} onChange={(event) => setMediaPath(event.target.value)} placeholder="D:\media\example.mp4" /></label>
          <label className="span-2">关键帧目录（OCR 可选）<input value={keyframes} onChange={(event) => setKeyframes(event.target.value)} /></label>
          <label>ASR 模型<input value={model} onChange={(event) => setModel(event.target.value)} /></label>
          <div className="checkbox-stack">
            <label><input type="checkbox" checked={transcribe} onChange={(event) => setTranscribe(event.target.checked)} /> 自动转写</label>
            <label><input type="checkbox" checked={ocr} onChange={(event) => setOcr(event.target.checked)} /> 关键帧 OCR</label>
            <label><input type="checkbox" checked={scenes} onChange={(event) => setScenes(event.target.checked)} /> 镜头检测</label>
          </div>
          <button className="button primary" type="submit">开始分析</button>
        </form>
        <Notice>首次使用需安装 <code>requirements-media.txt</code>。Provider 未安装时只返回警告，原媒体不会受影响。</Notice>
        {error && <Notice kind="error">{error}</Notice>}
      </Panel>
      <Panel title="分析结果">{result ? <JsonPanel value={result} /> : <EmptyState text="结果保存在 storage/derived/media/&lt;sha256&gt;/semantic。" />}</Panel>
    </div>
  );
}

function StoragePage({ api, active }: { api: LingJiApi; active: boolean }) {
  const [inventory, setInventory] = useState<AnyRecord | null>(null);
  const [plans, setPlans] = useState<AnyRecord[]>([]);
  const [selected, setSelected] = useState<AnyRecord | null>(null);
  const [confirmation, setConfirmation] = useState("");
  const [error, setError] = useState("");
  const load = useCallback(async () => {
    if (!active) return;
    try {
      const [nextInventory, nextPlans] = await Promise.all([api.get<AnyRecord>("/api/storage"), api.get<AnyRecord[]>("/api/storage/plans")]);
      setInventory(nextInventory); setPlans(nextPlans); setError("");
    } catch (reason) { setError(reason instanceof Error ? reason.message : String(reason)); }
  }, [active, api]);
  useEffect(() => { void load(); }, [load]);
  const createPlan = async () => {
    try { const plan = await api.post<AnyRecord>("/api/storage/plans", {}); setSelected(plan); setConfirmation(""); await load(); } catch (reason) { setError(reason instanceof Error ? reason.message : String(reason)); }
  };
  const execute = async () => {
    if (!selected) return;
    try { setSelected(await api.post(`/api/storage/plans/${selected.plan_id}/execute`, { confirmation })); await load(); } catch (reason) { setError(reason instanceof Error ? reason.message : String(reason)); }
  };
  const restore = async () => {
    if (!selected) return;
    try { setSelected(await api.post(`/api/storage/plans/${selected.plan_id}/restore`, { confirmation })); await load(); } catch (reason) { setError(reason instanceof Error ? reason.message : String(reason)); }
  };
  return (
    <div className="stack">
      <div className="toolbar"><button className="button secondary" onClick={() => void load()}>刷新统计</button><button className="button primary" onClick={() => void createPlan()}>按当前设置生成预览计划</button></div>
      {error && <Notice kind="error">{error}</Notice>}
      {inventory && <div className="metric-grid"><Metric title="灵机总占用" value={formatBytes(inventory.totals?.bytes)} /><Metric title="文件数" value={String(inventory.totals?.files || 0)} /><Metric title="磁盘剩余" value={formatBytes(inventory.totals?.disk_free_bytes)} /><Metric title="剩余比例" value={`${inventory.totals?.disk_free_percent || 0}%`} /></div>}
      <Panel title="分类占用">
        <Table headers={["类别", "路径", "文件", "占用", "保护", "可清理", "可冷存储"]} rows={Object.entries(inventory?.categories || {}).map(([name, row]: [string, any]) => [name, row.path, row.files, formatBytes(row.bytes), row.protected ? "是" : "否", row.cleanup_allowed ? "是" : "否", row.cold_archive_allowed ? "是" : "否"])} />
      </Panel>
      <div className="two-column">
        <Panel title="历史计划"><div className="list">{plans.map((plan) => <button className="list-button" key={plan.plan_id} onClick={async () => setSelected(await api.get(`/api/storage/plans/${plan.plan_id}`))}><strong>{plan.plan_id}</strong><small>{plan.status} · {formatBytes(plan.summary?.bytes)} · {plan.summary?.files || 0} 文件</small></button>)}</div></Panel>
        <Panel title="计划详情">
          {selected ? <><JsonPanel value={selected} /><label>确认文字<input value={confirmation} onChange={(event) => setConfirmation(event.target.value)} placeholder={selected.status === "preview" || selected.status === "partial" ? `EXECUTE_STORAGE_PLAN:${selected.plan_id}` : `RESTORE_STORAGE_PLAN:${selected.plan_id}`} /></label><div className="toolbar"><button className="button danger" onClick={() => void execute()}>执行可恢复清理/迁移</button><button className="button secondary" onClick={() => void restore()}>从恢复区还原</button></div></> : <EmptyState text="生成或选择一个计划。原始资料和 Vault 不会进入自动清理计划。" />}
        </Panel>
      </div>
    </div>
  );
}

function BackupsPage({ api, active }: { api: LingJiApi; active: boolean }) {
  const [backups, setBackups] = useState<AnyRecord[]>([]);
  const [profile, setProfile] = useState("metadata");
  const [selected, setSelected] = useState<AnyRecord | null>(null);
  const [confirmation, setConfirmation] = useState("");
  const [result, setResult] = useState<unknown>(null);
  const [error, setError] = useState("");
  const load = useCallback(async () => { if (!active) return; try { setBackups(await api.get("/api/backups")); setError(""); } catch (reason) { setError(reason instanceof Error ? reason.message : String(reason)); } }, [active, api]);
  useEffect(() => { void load(); }, [load]);
  const create = async () => { try { setResult(await api.post("/api/backups", { profile })); await load(); } catch (reason) { setError(reason instanceof Error ? reason.message : String(reason)); } };
  const verify = async () => { if (!selected) return; try { setResult(await api.post("/api/backups/verify", { backup: selected.path })); } catch (reason) { setError(reason instanceof Error ? reason.message : String(reason)); } };
  const stage = async () => { if (!selected) return; try { setResult(await api.post("/api/backups/stage-restore", { backup: selected.path, confirmation })); } catch (reason) { setError(reason instanceof Error ? reason.message : String(reason)); } };
  return (
    <div className="two-column">
      <Panel title="创建与选择备份">
        <div className="toolbar"><select value={profile} onChange={(event) => setProfile(event.target.value)}><option value="metadata">metadata：Vault、配置、数据库与版本</option><option value="full">full：再包含 Raw 与 Derived</option></select><button className="button primary" onClick={() => void create()}>创建并校验</button></div>
        {error && <Notice kind="error">{error}</Notice>}
        <div className="list">{backups.map((backup) => <button key={backup.backup_id} className={selected?.backup_id === backup.backup_id ? "list-button selected" : "list-button"} onClick={() => { setSelected(backup); setConfirmation(""); }}><strong>{backup.backup_id}</strong><small>{backup.profile || "unknown"} · {formatBytes(backup.archive_bytes)} · {backup.created_at || ""}</small></button>)}</div>
      </Panel>
      <Panel title="校验与隔离恢复">
        {selected ? <><JsonPanel value={selected} /><div className="toolbar"><button className="button secondary" onClick={() => void verify()}>验证完整性</button></div><label>隔离恢复确认<input value={confirmation} onChange={(event) => setConfirmation(event.target.value)} placeholder={`STAGE_RESTORE:${selected.backup_id}`} /></label><button className="button warning" onClick={() => void stage()}>解压到隔离目录</button><Notice>不会覆盖当前 Vault。恢复内容先进入 storage/restore-staging，验收后才能人工切换。</Notice></> : <EmptyState text="选择一个备份。" />}
        {result && <JsonPanel value={result} />}
      </Panel>
    </div>
  );
}

function SettingsPage({ api, active }: { api: LingJiApi; active: boolean }) {
  const [snapshot, setSnapshot] = useState<SettingsSnapshot | null>(null);
  const [draft, setDraft] = useState<Record<string, any>>({});
  const [group, setGroup] = useState("media_processing");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const load = useCallback(async () => { if (!active) return; try { const data = await api.get<SettingsSnapshot>("/api/settings"); setSnapshot(data); setDraft(data.values); setError(""); } catch (reason) { setError(reason instanceof Error ? reason.message : String(reason)); } }, [active, api]);
  useEffect(() => { void load(); }, [load]);
  if (!snapshot) return <EmptyState text={error || "连接后加载设置。"} />;
  const groups = Array.from(new Set(Object.values(snapshot.definitions).map((definition) => definition.group)));
  const rows = Object.entries(snapshot.definitions).filter(([, definition]) => definition.group === group);
  const save = async () => { try { const data = await api.patch<SettingsSnapshot>("/api/settings", { values: draft }); setSnapshot(data); setDraft(data.values); setMessage("设置已保存"); setError(""); } catch (reason) { setError(reason instanceof Error ? reason.message : String(reason)); } };
  const resetGroup = async () => { try { const keys = rows.map(([key]) => key); const data = await api.post<SettingsSnapshot>("/api/settings/reset", { keys }); setSnapshot(data); setDraft(data.values); setMessage("当前分组已恢复默认值"); } catch (reason) { setError(reason instanceof Error ? reason.message : String(reason)); } };
  return (
    <div className="settings-layout">
      <div className="settings-groups">{groups.map((item) => <button key={item} className={group === item ? "active" : ""} onClick={() => setGroup(item)}>{item}</button>)}</div>
      <Panel title={`设置 · ${group}`}>
        {message && <Notice kind="success">{message}</Notice>}{error && <Notice kind="error">{error}</Notice>}
        <div className="settings-list">{rows.map(([key, definition]) => <SettingField key={key} name={key} definition={definition} value={draft[key]} overridden={Object.prototype.hasOwnProperty.call(snapshot.overrides, key)} onChange={(value) => setDraft({ ...draft, [key]: value })} />)}</div>
        <div className="toolbar sticky-actions"><button className="button primary" onClick={() => void save()}>保存全部修改</button><button className="button secondary" onClick={() => void resetGroup()}>当前分组恢复默认</button></div>
      </Panel>
    </div>
  );
}

function SettingField({ name, definition, value, overridden, onChange }: { name: string; definition: SettingDefinition; value: any; overridden: boolean; onChange: (value: any) => void }) {
  let control: React.ReactNode;
  if (definition.type === "boolean") {
    control = <input type="checkbox" checked={Boolean(value)} onChange={(event) => onChange(event.target.checked)} />;
  } else if (definition.type === "choice") {
    control = <select value={String(value ?? "")} onChange={(event) => onChange(event.target.value)}>{(definition.choices || []).map((choice) => <option key={choice} value={choice}>{choice}</option>)}</select>;
  } else {
    control = <input type={definition.type === "integer" || definition.type === "number" ? "number" : "text"} step={definition.type === "integer" ? 1 : "any"} min={definition.minimum} max={definition.maximum} value={value ?? ""} onChange={(event) => onChange(definition.type === "integer" ? Number.parseInt(event.target.value || "0", 10) : definition.type === "number" ? Number(event.target.value || 0) : event.target.value)} />;
  }
  return <div className="setting-row"><div><strong>{definition.label}</strong><code>{name}</code><p>{definition.description}</p><small>默认：{String(definition.default)}{overridden ? " · 已覆盖" : ""}</small></div><div className="setting-control">{control}</div></div>;
}

function LogsPage({ api, active }: { api: LingJiApi; active: boolean }) {
  const [data, setData] = useState<AnyRecord>({ lines: [] });
  const [error, setError] = useState("");
  const load = useCallback(async () => { if (!active) return; try { setData(await api.get("/api/logs?lines=1000")); setError(""); } catch (reason) { setError(reason instanceof Error ? reason.message : String(reason)); } }, [active, api]);
  useEffect(() => { void load(); }, [load]);
  return <div className="stack"><div className="toolbar"><button className="button secondary" onClick={() => void load()}>刷新</button><span>{data.path}</span><span>{formatBytes(data.size)}</span></div>{error && <Notice kind="error">{error}</Notice>}<pre className="log-view">{(data.lines || []).join("\n") || "暂无日志"}</pre></div>;
}

function Panel({ title, children }: { title: string; children: React.ReactNode }) { return <section className="panel"><h2>{title}</h2><div className="panel-body">{children}</div></section>; }
function Metric({ title, value, detail = "", tone = "neutral" }: { title: string; value: string; detail?: string; tone?: string }) { return <div className={`metric metric-${tone}`}><span>{title}</span><strong>{value}</strong><small>{detail}</small></div>; }
function EmptyState({ text }: { text: string }) { return <div className="empty-state">{text}</div>; }
function Table({ headers, rows }: { headers: string[]; rows: Array<Array<React.ReactNode>> }) { return <div className="table-scroll"><table><thead><tr>{headers.map((header) => <th key={header}>{header}</th>)}</tr></thead><tbody>{rows.length ? rows.map((row, index) => <tr key={index}>{row.map((cell, cellIndex) => <td key={cellIndex}>{cell}</td>)}</tr>) : <tr><td colSpan={headers.length}><EmptyState text="暂无数据" /></td></tr>}</tbody></table></div>; }
