import { ADVANCED_NAVIGATION } from "../navigation";
import NavIcon from "../components/NavIcon";
import type { PageId } from "../types";

const GROUPS: Array<{ title: string; description: string; pages: PageId[] }> = [
  {
    title: "系统与运行",
    description: "查看核心、算力、模型和向量状态。",
    pages: ["brain_status", "system_compute", "models", "vector_center"],
  },
  {
    title: "记忆与项目",
    description: "检查项目、记忆来源、审核和 Obsidian。",
    pages: ["codex_workspace", "memory_inspector", "memory_review", "auto_review", "obsidian"],
  },
  {
    title: "采集与任务",
    description: "处理手动投喂、媒体分析和任务明细。",
    pages: ["capture_center", "media", "jobs"],
  },
  {
    title: "存储与运维",
    description: "查看存储、备份、验收、设置和日志。",
    pages: ["storage", "backups", "acceptance", "settings", "logs"],
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
                  <button className="diagnostics-card" key={item.id} onClick={() => onNavigate(item.id)}>
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
