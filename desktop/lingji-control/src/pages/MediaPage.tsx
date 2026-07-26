import { useState } from "react";
import type { FormEvent } from "react";
import { Empty, Json, Notice, Panel } from "../components/ui";
import type { PageProps, Row } from "../types";

export default function MediaPage({ api, active }: PageProps) {
  const [path, setPath] = useState("");
  const [frames, setFrames] = useState("");
  const [asr, setAsr] = useState(true);
  const [ocr, setOcr] = useState(false);
  const [scenes, setScenes] = useState(true);
  const [result, setResult] = useState<Row | null>(null);

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!active) return;
    setResult(await api.post<Row>("/api/media/analyze", {
      media_path: path,
      keyframe_directory: frames || null,
      overrides: {
        auto_transcribe: asr,
        asr_provider: asr ? "faster_whisper" : "off",
        auto_ocr: ocr,
        ocr_provider: ocr ? "paddleocr" : "off",
        detect_scenes: scenes,
        scene_provider: scenes ? "pyscenedetect" : "off",
      },
    }));
  }

  return (
    <div className="two-column wide-left">
      <Panel title="本地媒体语义分析">
        <form className="form-grid" onSubmit={(event) => void submit(event)}>
          <label className="span-2">媒体文件<input required value={path} onChange={(event) => setPath(event.target.value)} /></label>
          <label className="span-2">关键帧目录<input value={frames} onChange={(event) => setFrames(event.target.value)} /></label>
          <div className="checkbox-stack">
            <label><input type="checkbox" checked={asr} onChange={(event) => setAsr(event.target.checked)} /> 自动转写</label>
            <label><input type="checkbox" checked={ocr} onChange={(event) => setOcr(event.target.checked)} /> 关键帧 OCR</label>
            <label><input type="checkbox" checked={scenes} onChange={(event) => setScenes(event.target.checked)} /> 镜头检测</label>
          </div>
          <button className="button primary">开始分析</button>
        </form>
        <Notice>首次使用需安装 <code>requirements-media.txt</code>，未安装 Provider 时不会损坏任务。</Notice>
      </Panel>
      <Panel title="结果">{result !== null ? <Json value={result} /> : <Empty text="分析结果写入 Derived 媒体目录。" />}</Panel>
    </div>
  );
}
