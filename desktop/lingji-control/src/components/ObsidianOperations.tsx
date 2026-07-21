import { useRef, useState } from "react";
import { ApiError } from "../api";
import type { LingJiApi } from "../api";
import { isAllowedObsidianDirectory, OBSIDIAN_ALLOWED_DIRECTORIES } from "../pages/codexWorkspaceContract";
import { MemoryReviewApi } from "../pages/memoryReviewApi";
import type { ObsidianNote, ObsidianScan } from "../pages/memoryReviewTypes";
import { Notice, Panel } from "./ui";

export default function ObsidianOperations({ api, active }: { api: LingJiApi; active: boolean }) {
  const client = new MemoryReviewApi(api);
  const [relativePath, setRelativePath] = useState("");
  const [note, setNote] = useState<ObsidianNote | null>(null);
  const [directory, setDirectory] = useState<(typeof OBSIDIAN_ALLOWED_DIRECTORIES)[number]>(OBSIDIAN_ALLOWED_DIRECTORIES[0]);
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [project, setProject] = useState("");
  const [tags, setTags] = useState("");
  const [privacy, setPrivacy] = useState<"private" | "restricted">("private");
  const [scan, setScan] = useState<ObsidianScan | null>(null);
  const [busy, setBusy] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const controller = useRef<AbortController | null>(null);
  const requestId = useRef(0);

  const fail = (reason: unknown) => {
    if (!(reason instanceof ApiError)) return setError("操作失败");
    if (reason.status === 404) setError("文件不存在");
    else if (reason.status === 422 && reason.code.includes("PRIVATE")) setError("08-Private 默认不可读取");
    else if (reason.status === 422) setError("路径不允许");
    else if (reason.status === 401) setError("需要本地授权");
    else if (reason.status === 503) setError("Obsidian 服务暂不可用");
    else setError(reason.message || "操作失败");
  };

  const read = async () => {
    if (!relativePath.trim()) return;
    controller.current?.abort(); const abort = new AbortController(); const id = ++requestId.current; controller.current = abort;
    setBusy("read"); setError("");
    try { const response = await client.readNote(relativePath.trim(), abort.signal); if (id === requestId.current) setNote(response); }
    catch (reason) { if (id === requestId.current && !(reason instanceof ApiError && reason.code === "REQUEST_CANCELLED")) fail(reason); }
    finally { if (id === requestId.current) setBusy(""); }
  };

  const create = async () => {
    if (!isAllowedObsidianDirectory(directory) || !title.trim() || !content.trim()) return;
    setBusy("create"); setError(""); setMessage("");
    try {
      const response = await client.createNote({ directory, title: title.trim(), content, project_ids: project.split(",").map((x) => x.trim()).filter(Boolean), tags: tags.split(",").map((x) => x.trim()).filter(Boolean), privacy });
      setMessage(`已创建 ${response.relative_path}`); setTitle(""); setContent("");
    } catch (reason) { fail(reason); } finally { setBusy(""); }
  };

  const scanNow = async () => {
    setBusy("scan"); setError("");
    try { setScan(await client.scan()); } catch (reason) { fail(reason); } finally { setBusy(""); }
  };

  return <div className="loop-grid">
    {error && <Notice kind="error">{error}</Notice>}{message && <Notice>{message}</Notice>}
    <Panel title="测试读取"><div className="settings-list"><label>Vault 相对路径<input value={relativePath} onChange={(e) => setRelativePath(e.target.value)} placeholder="03-Knowledge/Notes/example.md" /></label><button className="button secondary" disabled={!active || busy === "read" || !relativePath.trim()} onClick={() => void read()}>{busy === "read" ? "读取中…" : "读取笔记"}</button>{note && <dl className="detail-list"><div><dt>标题</dt><dd>{note.title ?? "未知"}</dd></div><div><dt>相对路径</dt><dd>{note.relative_path}</dd></div><div><dt>Hash</dt><dd>{note.content_hash ?? "未知"}</dd></div><div><dt>Metadata</dt><dd><pre>{JSON.stringify(note.metadata ?? {}, null, 2)}</pre></dd></div><div><dt>内容</dt><dd><pre>{note.content ?? ""}</pre></dd></div></dl>}</div></Panel>
    <Panel title="手动新建笔记"><div className="settings-list"><label>目录<select value={directory} onChange={(e) => setDirectory(e.target.value as typeof directory)}>{OBSIDIAN_ALLOWED_DIRECTORIES.map((item) => <option key={item}>{item}</option>)}</select></label><label>标题<input value={title} onChange={(e) => setTitle(e.target.value)} /></label><label>正文<textarea value={content} onChange={(e) => setContent(e.target.value)} /></label><label>项目<input value={project} onChange={(e) => setProject(e.target.value)} placeholder="逗号分隔" /></label><label>Tags<input value={tags} onChange={(e) => setTags(e.target.value)} placeholder="逗号分隔" /></label><label>隐私<select value={privacy} onChange={(e) => setPrivacy(e.target.value as typeof privacy)}><option>private</option><option>restricted</option></select></label><button className="button primary" disabled={!active || busy === "create" || !title.trim() || !content.trim()} onClick={() => void create()}>{busy === "create" ? "创建中…" : "创建笔记"}</button></div></Panel>
    <Panel title="扫描变化"><button className="button secondary" disabled={!active || busy === "scan"} onClick={() => void scanNow()}>{busy === "scan" ? "扫描中…" : "扫描 Obsidian 变化"}</button>{scan && <dl className="detail-list"><div><dt>changed</dt><dd>{scan.changed ?? "未知"}</dd></div><div><dt>new</dt><dd>{scan.new ?? "未知"}</dd></div><div><dt>missing</dt><dd>{scan.missing ?? "未知"}</dd></div><div><dt>external_modified_core</dt><dd>{scan.external_modified_core ?? "未知"}</dd></div><div><dt>indexed</dt><dd>{scan.indexed ?? "未知"}</dd></div><div><dt>failed</dt><dd>{scan.failed ?? "未知"}</dd></div><div><dt>last_scan_at</dt><dd>{scan.last_scan_at ?? "未知"}</dd></div></dl>}</Panel>
  </div>;
}
