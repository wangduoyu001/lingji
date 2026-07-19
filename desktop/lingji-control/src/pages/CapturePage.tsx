import { useState } from "react";
import type { FormEvent } from "react";
import { Empty, Json, Notice, Panel } from "../components/ui";
import type { PageProps, Row } from "../types";

export default function CapturePage({ api, active }: PageProps) {
  const [form, setForm] = useState({ platform: "web", title: "", url: "", input_path: "", text: "" });
  const [result, setResult] = useState<Row | null>(null);
  const [error, setError] = useState("");

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!active) return;
    try {
      setResult(await api.post<Row>("/api/share", { source_type: form.input_path ? "media" : form.platform, ...form }));
      setError("");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : String(reason));
    }
  }

  return (
    <div className="two-column wide-left">
      <Panel title="主动投喂">
        <form className="form-grid" onSubmit={(event) => void submit(event)}>
          <label>平台<select value={form.platform} onChange={(event) => setForm({ ...form, platform: event.target.value })}>{["web", "wechat_article", "video_channel", "douyin", "xiaohongshu", "bilibili", "youtube"].map((item) => <option key={item}>{item}</option>)}</select></label>
          <label>标题<input value={form.title} onChange={(event) => setForm({ ...form, title: event.target.value })} /></label>
          <label className="span-2">链接<input value={form.url} onChange={(event) => setForm({ ...form, url: event.target.value })} /></label>
          <label className="span-2">本地文件<input value={form.input_path} onChange={(event) => setForm({ ...form, input_path: event.target.value })} placeholder="D:\media\example.mp4" /></label>
          <label className="span-2">正文或选中文字<textarea rows={12} value={form.text} onChange={(event) => setForm({ ...form, text: event.target.value })} /></label>
          <button className="button primary">提交到灵机</button>
        </form>
        {error && <Notice kind="error">{error}</Notice>}
      </Panel>
      <Panel title="结果">{result !== null ? <Json value={result} /> : <Empty text="提交后显示保存路径或任务 ID。" />}</Panel>
    </div>
  );
}
