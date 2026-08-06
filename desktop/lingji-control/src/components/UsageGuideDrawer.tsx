import type { PageId } from "../types";

type Props = {
  open: boolean;
  onClose: () => void;
  onNavigate: (page: PageId) => void;
};

const AUTONOMY_STEPS: Array<{ title: string; detail: string; page: PageId }> = [
  { title: "1. 灵机自动发现", detail: "自动检测 AI 软件、已知目录元数据、模型和硬件状态，不读取正文。", page: "assistant_hub" },
  { title: "2. 灵机自动处理", detail: "已授权资料自动解析、去重、排队、重试并记录进度。", page: "activity" },
  { title: "3. 需要时请求授权", detail: "读取真实正文或修改外部客户端配置前才会询问主人。", page: "attention" },
  { title: "4. 主人最终定稿", detail: "只有你批准的候选才会成为永久记忆。", page: "memory_review" },
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
            <span className="desktop-eyebrow">运行说明</span>
            <h2>灵机会主动工作，你主要负责观察和授权</h2>
            <p>菜单用于查看状态、进度和手动干预。普通扫描、检测、处理、重试和恢复不需要逐项点击。</p>
          </div>
          <button className="usage-guide-close" onClick={onClose} aria-label="关闭使用说明">×</button>
        </header>

        <section className="usage-guide-section">
          <h3>自动运行与主人边界</h3>
          <div className="usage-guide-step-list">
            {AUTONOMY_STEPS.map((step) => (
              <button key={step.title} onClick={() => navigate(step.page)}>
                <strong>{step.title}</strong>
                <small>{step.detail}</small>
              </button>
            ))}
          </div>
        </section>

        <section className="usage-guide-section usage-guide-rules">
          <h3>哪些事情不会擅自做</h3>
          <ol>
            <li>自动扫描只读取允许目录的存在性、类型和数量元数据，不读取账号密码、Token、登录态或真实正文。</li>
            <li>读取 ChatGPT、Codex、剧本、Vault 等真实内容前必须获得主人授权。</li>
            <li>修改外部客户端配置、删除数据、重建 Production Qdrant 等高影响操作不会静默执行。</li>
            <li>导入内容先进入采集与候选链，不会直接成为 Core Memory。</li>
            <li>只有在“人工记忆审核”中确认的候选，才成为正式长期记忆。</li>
          </ol>
        </section>

        <section className="usage-guide-section usage-guide-advanced">
          <h3>常用观察与干预入口</h3>
          <div className="usage-guide-links">
            <button onClick={() => navigate("assistant_hub")}>查看 AI 发现与连接</button>
            <button onClick={() => navigate("activity")}>查看自动处理进度</button>
            <button onClick={() => navigate("attention")}>查看待授权与异常</button>
            <button onClick={() => navigate("memory_review")}>审核候选记忆</button>
            <button onClick={() => navigate("capture_center")}>授权新的资料来源</button>
            <button onClick={() => navigate("diagnostics")}>高级诊断与手动干预</button>
          </div>
        </section>
      </aside>
    </div>
  );
}
