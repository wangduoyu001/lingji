import { ADVANCED_NAVIGATION } from "../navigation";
import NavIcon from "../components/NavIcon";
import type { PageId } from "../types";

const GROUPS: Array<{ title: string; description: string; pages: PageId[] }> = [
  {
    title: "运行与错误",
    description: "查看最近完成的工作、任务明细、自动审查和运行日志。",
    pages: ["activity", "jobs", "auto_review", "logs", "permanent_memory"],
  },
  {
    title: "数据与索引",
    description: "检查项目、记忆、来源、向量、投喂和 Obsidian 数据。",
    pages: ["codex_workspace", "memory_inspector", "memory_review", "vector_center", "capture_center", "media", "obsidian"],
  },
  {
    title: "模型与算力",
    description: "查看脑状态、系统算力和 AI 模型配置。",
    pages: ["brain_status", "system_compute", "models"],
  },
  {
    title: "存储与备份",
    description: "查看存储、备份、环境验收和设置。",
    pages: ["storage", "backups", "acceptance", "settings"],
  },
];

export default function DiagnosticsPage({ onNavigate }: { onNavigate: (page: PageId) => void }) {
  return (
    <div className="stack observation-page diagnostics-page">
      <section className="observation-hero diagnostics-hero">
        <div>
          <span className="desktop-eyebrow">高级诊断入口</span>
          <h2>高级诊断</h2>
          <p>日常不需要进入这里。只有状态异常、需要核查或调整配置时再打开详细页面。</p>
        </div>
      </section>

      <div className="diagnostics-groups">
        {GROUPS.map((group, index) => (
          <details className="diagnostics-group" key={group.title} open={index === 0}>
            <summary>
              <div>
                <strong>{group.title}</strong>
                <small>{group.description}</small>
              </div>
              <span>{group.pages.length}</span>
            </summary>
            <div className="diagnostics-grid">
              {group.pages.map((pageId) => {
                const item = ADVANCED_NAVIGATION.find((candidate) => candidate.id === pageId);
                if (!item) return null;
                return (
                  <button aria-label={item.label} className="diagnostics-card" key={item.id} onClick={() => onNavigate(item.id)}>
                    <span className="desktop-nav-icon"><NavIcon name={item.icon} /></span>
                    <span>
                      <strong>{item.label}</strong>
                      <small>{item.hint}</small>
                    </span>
                  </button>
                );
              })}
            </div>
          </details>
        ))}
      </div>
    </div>
  );
}
