import type { PageId } from "../types";

type Props = {
  open: boolean;
  onClose: () => void;
  onNavigate: (page: PageId) => void;
};

const DAILY_STEPS: Array<{ title: string; detail: string; page: PageId }> = [
  { title: "1. 投喂资料", detail: "把文字、网页、文件或媒体交给灵机。", page: "capture_center" },
  { title: "2. 查看处理", detail: "在活动记录确认任务是否完成。", page: "activity" },
  { title: "3. 审核记忆", detail: "决定哪些候选内容值得长期保留。", page: "memory_review" },
  { title: "4. 处理异常", detail: "只处理灵机无法安全替你决定的事项。", page: "attention" },
];

export default function UsageGuideDrawer({ open, onClose, onNavigate }: Props) {
  if (!open) return null;

  const navigate = (page: PageId) => {
    onNavigate(page);
    onClose();
  };

  return (
    <div className="usage-guide-backdrop" role="presentation" onMouseDown={onClose}>
      <aside
        className="usage-guide-drawer"
        role="dialog"
        aria-modal="true"
        aria-label="灵机使用说明"
        onMouseDown={(event) => event.stopPropagation()}
      >
        <header className="usage-guide-header">
          <div>
            <span className="desktop-eyebrow">使用说明</span>
            <h2>灵机到底怎么用</h2>
            <p>日常使用只走四步。高级诊断只在出现警告或故障时进入。</p>
          </div>
          <button className="usage-guide-close" onClick={onClose} aria-label="关闭使用说明">×</button>
        </header>

        <section className="usage-guide-section">
          <h3>日常流程</h3>
          <div className="usage-guide-step-list">
            {DAILY_STEPS.map((step) => (
              <button key={step.title} onClick={() => navigate(step.page)}>
                <strong>{step.title}</strong>
                <small>{step.detail}</small>
              </button>
            ))}
          </div>
        </section>

        <section className="usage-guide-section usage-guide-rules">
          <h3>只记住三条</h3>
          <ol>
            <li>打开后先看“运行状态”，右上角显示“运行中”即可。</li>
            <li>提交资料后去“活动记录”，不要在技术页面里找进度。</li>
            <li>看到降级或错误时先看“需要我处理”，再进入高级诊断。</li>
          </ol>
        </section>

        <section className="usage-guide-section usage-guide-advanced">
          <h3>高级诊断什么时候用</h3>
          <div className="usage-guide-links">
            <button onClick={() => navigate("models")}>模型不可用</button>
            <button onClick={() => navigate("vector_center")}>向量异常</button>
            <button onClick={() => navigate("system_compute")}>GPU / 算力问题</button>
            <button onClick={() => navigate("storage")}>磁盘或路径问题</button>
            <button onClick={() => navigate("logs")}>查看错误日志</button>
            <button onClick={() => navigate("acceptance")}>版本验收</button>
          </div>
        </section>
      </aside>
    </div>
  );
}
