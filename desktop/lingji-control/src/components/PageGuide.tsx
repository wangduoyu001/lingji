import { NAVIGATION } from "../navigation";
import type { PageId } from "../types";

type GuideAction = {
  label: string;
  page: PageId;
};

type Guide = {
  purpose: string;
  when: string;
  steps: string[];
  primary?: GuideAction;
  secondary?: GuideAction;
};

const GUIDES: Partial<Record<PageId, Guide>> = {
  overview: {
    purpose: "先确认灵机是否正常，再从投喂、查看进度或处理待办开始日常使用。",
    when: "每次打开灵机先看这里。状态正常时，不需要进入技术页面。",
    steps: ["确认右上角显示“运行中”", "查看“需要我处理”是否有待办", "选择投喂内容或查看最近活动"],
    primary: { label: "开始投喂内容", page: "capture_center" },
    secondary: { label: "查看活动记录", page: "activity" },
  },
  activity: {
    purpose: "查看灵机正在处理什么、哪些任务已经完成、哪些任务失败。",
    when: "提交内容后想确认处理进度，或者怀疑某项工作没有完成时。",
    steps: ["先看当前任务", "再看最近结果", "失败任务转到“需要我处理”判断是否重试"],
    primary: { label: "查看需要我处理", page: "attention" },
  },
  attention: {
    purpose: "这里只放灵机无法安全替你决定的事项。",
    when: "首页提示有异常、记忆需要审核、任务需要人工决定时。",
    steps: ["先看风险说明", "确认影响范围", "只处理你理解并认可的操作"],
    primary: { label: "审核候选记忆", page: "memory_review" },
  },
  diagnostics: {
    purpose: "高级诊断是维修入口，不是日常工作台。",
    when: "系统出现警告、模型不可用、向量异常、存储不足或需要查看日志时。",
    steps: ["根据问题选择对应模块", "先看状态和解释", "没有明确原因时不要执行重建或删除操作"],
    primary: { label: "查看系统与算力", page: "system_compute" },
    secondary: { label: "查看日志", page: "logs" },
  },
  capture_center: {
    purpose: "把文字、网页、文件或媒体正式交给灵机处理。",
    when: "你希望灵机记住、整理、分析或后续检索某项资料时。",
    steps: ["选择来源类型", "确认内容和隐私范围", "提交后去活动记录看处理结果"],
    primary: { label: "提交后查看进度", page: "activity" },
  },
  capture: {
    purpose: "快速提交单条文字、网页或本地文件。",
    when: "只需要一次简单投喂，不需要查看完整采集队列时。",
    steps: ["选择输入方式", "确认来源信息", "提交后检查任务状态"],
    primary: { label: "查看任务队列", page: "jobs" },
  },
  media: {
    purpose: "查看音频、视频和图片的转写、OCR、镜头与摘要结果。",
    when: "已提交媒体文件，需要确认分析结果或失败原因时。",
    steps: ["选择媒体任务", "查看处理阶段", "需要长期保留时再进入记忆审核"],
    primary: { label: "查看活动记录", page: "activity" },
  },
  memory_review: {
    purpose: "批准、编辑或拒绝灵机提出的候选记忆。",
    when: "有新候选记忆、冲突提示或旧记忆需要更新时。",
    steps: ["先读来源和候选内容", "确认是否值得长期保留", "批准前修正错误、隐私和适用范围"],
    primary: { label: "检查记忆详情", page: "memory_inspector" },
  },
  memory_inspector: {
    purpose: "检查一条记忆从来源、分块、版本到向量索引的完整关系。",
    when: "怀疑记忆错误、来源不清、检索不到或需要追溯版本时。",
    steps: ["先定位记忆或来源", "查看引用和状态", "发现问题后回到记忆审核处理"],
    primary: { label: "返回记忆审核", page: "memory_review" },
  },
  codex_workspace: {
    purpose: "查看项目、对话、当前工作和处理进度。",
    when: "需要知道某个项目最近做了什么，或追踪 Codex 任务来源时。",
    steps: ["选择项目", "进入相关会话", "需要追溯记忆时打开检查器"],
    primary: { label: "查看记忆检查器", page: "memory_inspector" },
  },
  obsidian: {
    purpose: "确认 Obsidian Vault 连接、路径和安全操作状态。",
    when: "正式知识没有同步、Vault 路径变化或需要执行只读检查时。",
    steps: ["确认 Vault 和 CLI 状态", "先执行只读检查", "写入前确认目标文件和影响"],
    primary: { label: "查看存储状态", page: "storage" },
  },
  brain_status: {
    purpose: "查看记忆、模型、向量、算力和任务的综合技术状态。",
    when: "首页显示降级，但你需要判断到底是哪项能力不可用时。",
    steps: ["先区分错误与警告", "定位到具体能力", "再进入对应诊断页"],
    primary: { label: "查看向量中心", page: "vector_center" },
  },
  vector_center: {
    purpose: "查看 Qdrant、向量数量、维度、覆盖率和重建需求。",
    when: "语义检索不可用、向量数量异常或模型切换后需要核对索引时。",
    steps: ["确认 collection 和 workspace", "核对模型与维度", "仅在明确提示时执行重建"],
    primary: { label: "查看 AI 与模型", page: "models" },
  },
  models: {
    purpose: "查看模型是否安装、实际激活、适用任务和失败原因。",
    when: "Embedding、OCR、转写或本地 AI 显示不可用时。",
    steps: ["确认配置模型", "确认实际激活模型", "再检查模型文件、Provider 和算力"],
    primary: { label: "查看系统与算力", page: "system_compute" },
  },
  system_compute: {
    purpose: "查看 CPU、GPU、显存、运行模式和硬件探测结果。",
    when: "模型运行慢、GPU 没有启用、硬件状态异常或验收环境时。",
    steps: ["先看当前选择的设备", "核对可用显存和运行模式", "模型问题再转到 AI 与模型"],
    primary: { label: "查看 AI 与模型", page: "models" },
  },
  jobs: {
    purpose: "查看提取、索引、重试和失败任务的明细。",
    when: "活动记录只能看到结果，但你需要更详细的任务阶段和错误时。",
    steps: ["按状态筛选任务", "查看失败阶段和重试次数", "确认原因后再重试或取消"],
    primary: { label: "返回活动记录", page: "activity" },
  },
  auto_review: {
    purpose: "查看自动审查建议、风险和解释；这里不会自动执行变更。",
    when: "需要审计系统建议或判断规则是否可靠时。",
    steps: ["查看建议依据", "核对风险", "需要修改记忆时转到人工审核"],
    primary: { label: "进入人工记忆审核", page: "memory_review" },
  },
  storage: {
    purpose: "查看灵机占用空间、磁盘余量、冷存储和路径状态。",
    when: "磁盘空间不足、数据目录异常或准备迁移数据时。",
    steps: ["确认当前 workspace", "核对 DataRoot 和剩余空间", "迁移前先做备份"],
    primary: { label: "查看备份", page: "backups" },
  },
  backups: {
    purpose: "查看备份、校验结果和隔离恢复入口。",
    when: "升级、迁移、重建索引或处理重大故障之前。",
    steps: ["确认备份范围", "执行校验", "恢复时优先使用隔离目录验证"],
    primary: { label: "查看存储", page: "storage" },
  },
  acceptance: {
    purpose: "对真实资料执行只读诊断，确认系统不会误写生产数据。",
    when: "新版本安装、路径迁移、重大模块调整或合并前验收时。",
    steps: ["确认当前是 acceptance workspace", "执行只读检查", "保存报告后再决定是否进入生产"],
    primary: { label: "查看运行状态", page: "overview" },
  },
  settings: {
    purpose: "查看默认值、推荐值和主人覆盖项。",
    when: "路径、模型、任务策略或启动行为确实需要调整时。",
    steps: ["先读推荐值和影响", "一次只修改一组相关设置", "保存后按提示重启或执行任务"],
    primary: { label: "查看运行状态", page: "overview" },
  },
  logs: {
    purpose: "查看错误和运行记录，用于定位具体故障。",
    when: "页面给出的错误说明不足，或需要向开发者提供证据时。",
    steps: ["先按时间和错误级别定位", "只复制相关片段", "不要公开 Token、私人正文或完整数据库内容"],
    primary: { label: "复制诊断后返回首页", page: "overview" },
  },
};

export default function PageGuide({
  page,
  onNavigate,
}: {
  page: PageId;
  onNavigate: (page: PageId) => void;
}) {
  const navigation = NAVIGATION.find((item) => item.id === page);
  const guide = GUIDES[page] ?? {
    purpose: navigation?.hint ?? "查看当前模块状态和可用操作。",
    when: "只有在日常流程或异常处理需要时进入。",
    steps: ["先阅读页面说明", "确认当前状态", "理解影响后再执行操作"],
  };

  return (
    <section className="page-guide" aria-label={`${navigation?.label ?? "当前页面"}使用说明`}>
      <div className="page-guide-copy">
        <span className="desktop-eyebrow">这页怎么用</span>
        <h2>{navigation?.label ?? "当前页面"}</h2>
        <p>{guide.purpose}</p>
        <small><strong>什么时候来：</strong>{guide.when}</small>
      </div>
      <ol className="page-guide-steps">
        {guide.steps.map((step) => <li key={step}>{step}</li>)}
      </ol>
      {(guide.primary || guide.secondary) && (
        <div className="page-guide-actions">
          {guide.primary && (
            <button className="button" onClick={() => onNavigate(guide.primary!.page)}>
              {guide.primary.label}
            </button>
          )}
          {guide.secondary && (
            <button className="button secondary" onClick={() => onNavigate(guide.secondary!.page)}>
              {guide.secondary.label}
            </button>
          )}
        </div>
      )}
    </section>
  );
}
