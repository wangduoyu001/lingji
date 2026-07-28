import { useCallback, useEffect, useMemo, useState } from "react";
import { ApiError, isTauriDesktopRuntime } from "../api";
import { Empty, Metric, Notice, Panel } from "../components/ui";
import type { PageProps } from "../types";
import "./DramaPage.css";

type DramaSummary = {
  drama_id: string;
  title: string;
  source_format: string;
  status: string;
  character_count: number;
  episode_count: number;
  scene_count: number;
  chunk_count: number;
  updated_at: string;
};

type DramaStatus = {
  state: string;
  root: string;
  supported_extensions: string[];
  structured: {
    dramas: number;
    episodes: number;
    scenes: number;
    characters: number;
    chunks: number;
    fts_available: boolean;
  };
  semantic: {
    state: string;
    collection?: string | null;
    vectors?: number | null;
    last_error?: string | null;
    reason?: string | null;
  };
};

type SearchResult = {
  chunk_id: string;
  drama_id: string;
  drama_title: string;
  chunk_type: string;
  text: string;
  source_ref: string;
  episode_number?: number | null;
  scene_number?: number | null;
  characters?: string[];
  match_reasons?: string[];
  score: number;
};

type SearchResponse = {
  count: number;
  semantic_state: { state?: string; collection?: string | null };
  semantic_error?: string | null;
  results: SearchResult[];
};

type BatchImportResponse = {
  candidate_count: number;
  processed_count: number;
  imported_count: number;
  duplicate_count: number;
  failed_count: number;
  truncated: boolean;
  items: Array<{ relative_path: string; status: string; error?: string }>;
};

const errorText = (reason: unknown): string =>
  reason instanceof ApiError ? reason.message : reason instanceof Error ? reason.message : String(reason);

export default function DramaPage({ api, active }: PageProps) {
  const [status, setStatus] = useState<DramaStatus | null>(null);
  const [library, setLibrary] = useState<DramaSummary[]>([]);
  const [selectedDrama, setSelectedDrama] = useState("");
  const [sourcePath, setSourcePath] = useState("");
  const [batchDirectory, setBatchDirectory] = useState("");
  const [title, setTitle] = useState("");
  const [query, setQuery] = useState("");
  const [chunkType, setChunkType] = useState("");
  const [results, setResults] = useState<SearchResult[]>([]);
  const [batchResult, setBatchResult] = useState<BatchImportResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [importing, setImporting] = useState(false);
  const [batchImporting, setBatchImporting] = useState(false);
  const [searching, setSearching] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const selectedTitle = useMemo(
    () => library.find((item) => item.drama_id === selectedDrama)?.title ?? "全部短剧",
    [library, selectedDrama],
  );

  const load = useCallback(async () => {
    if (!active) return;
    setLoading(true);
    setError("");
    try {
      const [statusResult, libraryResult] = await Promise.all([
        api.get<DramaStatus>("/api/drama/status"),
        api.get<{ items: DramaSummary[] }>("/api/drama/library?limit=200&offset=0"),
      ]);
      setStatus(statusResult);
      setLibrary(libraryResult.items ?? []);
    } catch (reason) {
      setError(errorText(reason));
    } finally {
      setLoading(false);
    }
  }, [active, api]);

  useEffect(() => { void load(); }, [load]);

  const choosePath = async (directory: boolean) => {
    if (!isTauriDesktopRuntime()) {
      setMessage("文件选择只在真实桌面安装版中可用");
      return;
    }
    try {
      const { open } = await import("@tauri-apps/plugin-dialog");
      const selected = await open({
        multiple: false,
        directory,
        filters: directory ? undefined : [{ name: "短剧剧本", extensions: ["txt", "md", "docx", "pdf", "srt", "vtt", "ass"] }],
      });
      if (typeof selected !== "string") return;
      if (directory) setBatchDirectory(selected);
      else setSourcePath(selected);
    } catch (reason) {
      setMessage(errorText(reason));
    }
  };

  const importDrama = async () => {
    if (!sourcePath.trim() || importing || batchImporting) return;
    setImporting(true);
    setError("");
    setMessage("");
    try {
      const response = await api.post<{
        duplicate: boolean;
        drama: DramaSummary;
        semantic: { state?: string; indexed?: number; collection?: string };
        warnings?: string[];
      }>(
        "/api/drama/import",
        { source_path: sourcePath.trim(), title: title.trim() || undefined, force: false },
        { timeoutMs: 15 * 60 * 1000 },
      );
      setMessage(
        response.duplicate
          ? `已存在：${response.drama.title}，未重复入库`
          : `导入完成：${response.drama.title}；语义索引 ${response.semantic.state ?? "未知"}`,
      );
      setSelectedDrama(response.drama.drama_id);
      await load();
    } catch (reason) {
      setError(errorText(reason));
    } finally {
      setImporting(false);
    }
  };

  const importBatch = async () => {
    if (!batchDirectory.trim() || batchImporting || importing) return;
    setBatchImporting(true);
    setBatchResult(null);
    setError("");
    setMessage("");
    try {
      const response = await api.post<BatchImportResponse>(
        "/api/drama/import-directory",
        { directory_path: batchDirectory.trim(), recursive: false, limit: 100, force: false },
        { timeoutMs: 30 * 60 * 1000 },
      );
      setBatchResult(response);
      setMessage(`批量处理 ${response.processed_count} 部：新增 ${response.imported_count}，重复 ${response.duplicate_count}，失败 ${response.failed_count}`);
      await load();
    } catch (reason) {
      setError(errorText(reason));
    } finally {
      setBatchImporting(false);
    }
  };

  const search = async () => {
    if (!query.trim() || searching) return;
    setSearching(true);
    setError("");
    try {
      const response = await api.post<SearchResponse>(
        "/api/drama/search",
        {
          query: query.trim(),
          limit: 12,
          drama_id: selectedDrama || undefined,
          chunk_type: chunkType || undefined,
        },
        { timeoutMs: 2 * 60 * 1000 },
      );
      setResults(response.results ?? []);
      if (response.semantic_error) setMessage(`语义检索降级，当前仅使用原文检索：${response.semantic_error}`);
      else setMessage(`找到 ${response.count} 条参考，范围：${selectedTitle}`);
    } catch (reason) {
      setError(errorText(reason));
    } finally {
      setSearching(false);
    }
  };

  if (!active) return <Notice kind="warning">连接本机核心后才能使用短剧编剧工作台。</Notice>;

  return (
    <div className="drama-page">
      <Panel title="Drama Memory 状态">
        <div className="metric-grid">
          <Metric title="短剧" value={String(status?.structured?.dramas ?? 0)} />
          <Metric title="分集" value={String(status?.structured?.episodes ?? 0)} />
          <Metric title="场景" value={String(status?.structured?.scenes ?? 0)} />
          <Metric title="检索片段" value={String(status?.structured?.chunks ?? 0)} />
          <Metric title="原文索引" value={status?.structured?.fts_available ? "可用" : "降级"} />
          <Metric title="语义索引" value={status?.semantic?.state ?? "未知"} />
        </div>
        <small>领域数据根：{status?.root ?? "读取中"}</small>
        <small>Drama Collection：{status?.semantic?.collection ?? "尚未创建"}</small>
        {status?.semantic?.last_error && <Notice kind="warning">{status.semantic.last_error}</Notice>}
      </Panel>

      <div className="drama-two-column">
        <Panel title="导入剧本">
          <div className="drama-form">
            <label>单部剧本<div className="drama-path-row"><input value={sourcePath} onChange={(event) => setSourcePath(event.target.value)} placeholder="选择 txt / md / docx / pdf / srt / vtt / ass" /><button className="button secondary" onClick={() => void choosePath(false)}>选择文件</button></div></label>
            <label>剧名（可选）<input value={title} onChange={(event) => setTitle(event.target.value)} placeholder="默认使用文件名" /></label>
            <button className="button primary" disabled={!sourcePath.trim() || importing || batchImporting} onClick={() => void importDrama()}>{importing ? "正在解析并建立索引…" : "导入单部剧本"}</button>
            <div className="drama-divider" />
            <label>批量剧本目录<div className="drama-path-row"><input value={batchDirectory} onChange={(event) => setBatchDirectory(event.target.value)} placeholder="选择包含10部剧本的目录" /><button className="button secondary" onClick={() => void choosePath(true)}>选择目录</button></div></label>
            <button className="button primary" disabled={!batchDirectory.trim() || batchImporting || importing} onClick={() => void importBatch()}>{batchImporting ? "正在批量导入并建立索引…" : "批量导入目录"}</button>
            <small>单个失败不会中断整批；扫描版 PDF 会明确标记需要 OCR。</small>
          </div>
        </Panel>

        <Panel title="精准参考检索">
          <div className="drama-form">
            <label>要找的桥段或结构<textarea value={query} onChange={(event) => setQuery(event.target.value)} placeholder="例如：女主被公开羞辱后真实身份曝光，情绪从压抑转为爽感释放" /></label>
            <div className="drama-filter-row">
              <label>检索范围<select value={selectedDrama} onChange={(event) => setSelectedDrama(event.target.value)}><option value="">全部短剧</option>{library.map((item) => <option key={item.drama_id} value={item.drama_id}>{item.title}</option>)}</select></label>
              <label>片段类型<select value={chunkType} onChange={(event) => setChunkType(event.target.value)}><option value="">全部</option><option value="episode">分集</option><option value="scene">场景</option></select></label>
            </div>
            <button className="button primary" disabled={!query.trim() || searching} onClick={() => void search()}>{searching ? "正在混合检索…" : "搜索剧本记忆"}</button>
          </div>
        </Panel>
      </div>

      {error && <Notice kind="error">{error}</Notice>}
      {message && <Notice>{message}</Notice>}
      {batchResult?.failed_count ? <Notice kind="warning">失败文件：{batchResult.items.filter((item) => item.status === "failed").map((item) => `${item.relative_path}：${item.error ?? "未知错误"}`).join("；")}</Notice> : null}

      <Panel title={`短剧库 · ${library.length}`}>
        <div className="drama-library">
          {library.length === 0 ? <Empty text="尚未导入剧本。先用一部结构清晰的短剧测试，不要一上来扔十部乱码 PDF。" /> : library.map((item) => (
            <button key={item.drama_id} className={selectedDrama === item.drama_id ? "drama-library-card selected" : "drama-library-card"} onClick={() => setSelectedDrama(item.drama_id)}>
              <strong>{item.title}</strong><span>{item.episode_count} 集 · {item.scene_count} 场 · {item.character_count} 人物</span><small>{item.source_format.toUpperCase()} · {item.chunk_count} 个检索片段</small>
            </button>
          ))}
        </div>
        <button className="button secondary" disabled={loading} onClick={() => void load()}>{loading ? "刷新中…" : "刷新短剧库"}</button>
      </Panel>

      <Panel title="检索结果">
        {results.length === 0 ? <Empty text="检索后会显示剧名、集数、场次、原文位置、命中原因和正文片段。" /> : (
          <div className="drama-results">
            {results.map((item) => (
              <article key={item.chunk_id} className="drama-result-card">
                <header><div><strong>{item.drama_title}</strong><span>{item.source_ref}</span></div><small>{(item.match_reasons ?? []).join(" + ") || "结构召回"}</small></header>
                <p>{item.text}</p>
                <footer><span>第 {item.episode_number ?? "?"} 集{item.scene_number ? ` · 第 ${item.scene_number} 场` : ""}</span><span>{item.characters?.length ? `人物：${item.characters.join("、")}` : "人物未识别"}</span></footer>
              </article>
            ))}
          </div>
        )}
      </Panel>

      <Panel title="编剧 Agent">
        <Notice kind="warning">第二阶段开放。先让剧本库能稳定找回原文、结构和来源，再给模型写剧权限。互联网已经有足够多的垃圾生成按钮。</Notice>
        <button className="button secondary" disabled>等待检索验收通过</button>
      </Panel>
    </div>
  );
}
