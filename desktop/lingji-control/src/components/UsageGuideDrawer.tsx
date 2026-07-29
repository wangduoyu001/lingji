import type { PageId } from "../types";

type Props = {
  open: boolean;
  onClose: () => void;
  onNavigate: (page: PageId) => void;
};

const FIRST_USE_STEPS: Array<{ title: string; detail: string; page: PageId }> = [
  { title: "1. 扫描 AI 软件", detail: "检测 Codex、Claude Code、WorkBuddy 的安全本机痕迹。", page: "assistant_hub" },
  { title: "2. 导入已有资料", detail: "选择 ChatGPT Export 或 Codex Report，提交到统一采集队列。", page: "assistant_hub" },
  { title: "3. 查看处理", detail: "在活动记录确认导入是否完成或失败。", page: "activity" },
  { title: "4. 审核永久记忆", detail: "只批准真正值得长期保留的候选内容。", page: "memory_review" },
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
            <h2>第一次打开灵机怎么做</h2>
            <p>先连接 AI 和导入资料，再查看处理并审核永久记忆。高级诊断只在故障时进入。</p>
          </div>
          <button className="usage-guide-close" onClick={onClose} aria-label="关闭使用说明">×</button>
        </header>

        <section className="usage-guide-section">
          <h3>首次设置流程</h3>
          <div className="usage-guide-step-list">
            {FIRST_USE_STEPS.map((step) => (
              <button key={step.title} onClick={() => navigate(step.page)}>
                <strong>{step.title}</strong>
                <small>{step.detail}</small>
              </button>
            ))}
          </div>
        </section>

        <section className="usage-guide-section usage-guide-rules">
          <h3>永久记忆不会自动乱写</h3>
          <ol>
            <li>扫描只读取允许目录和文件元数据，不读取账号密码、Token 或浏览器登录态。</li>
            <li>导入内容先进入采集队列，不会直接成为 Core Memory。</li>
            <li>只有在“人工记忆审核”中确认的候选，才成为正式长期记忆。</li>
          </ol>
        </section>

        <section className="usage-guide-section usage-guide-advanced">
          <h3>接下来常用入口</h3>
          <div className="usage-guide-links">
            <button onClick={() => navigate("assistant_hub")}>连接 AI / 导入历史</button>
            <button onClick={() => navigate("capture_center")}>继续投喂新资料</button>
            <button onClick={() => navigate("activity")}>查看处理进度</button>
            <button onClick={() => navigate("memory_review")}>审核候选记忆</button>
            <button onClick={() => navigate("attention")}>处理异常</button>
            <button onClick={() => navigate("diagnostics")}>高级诊断</button>
          </div>
        </section>
      </aside>
    </div>
  );
}
