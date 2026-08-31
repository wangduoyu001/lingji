import type { WorkFact } from "../contracts/workFact";

const EMPTY_SCAN_SUMMARIES = [
  /^扫描完成，已检查\s*0\s*个来源文件（新增\s*0，复用\s*0）$/,
  /^扫描完成，已检查\s*0\s*个来源文件\s*\(新增\s*0，复用\s*0\)$/,
];

const GENERIC_SUCCESS = new Set(["成功", "已完成", "completed", "success"]);

const automaticMemoryTitles: Record<string, string> = {
  codex_rollout: "检查 Codex聊天记录",
  codex_transcript: "检查 Codex聊天记录",
  codex_history: "检查 Codex聊天记录",
  codex: "检查 Codex聊天记录",
  chatgpt_export: "检查 ChatGPT 导出记录",
  chatgpt_history: "检查 ChatGPT 导出记录",
  obsidian: "检查 Obsidian 长期记忆区",
  generic: "检查其他聊天来源",
  generic_ai_history: "检查其他聊天来源",
};

/** Keep internal automatic-memory work names out of ordinary owner surfaces. */
export function formatWorkFactTitle(value: unknown): string {
  const title = String(value ?? "").trim();
  const match = title.match(/^扫描\s+([^\s]+)$/i);
  if (match) return automaticMemoryTitles[match[1].toLowerCase()] ?? "检查其他聊天来源";
  return title;
}

function finiteEvidenceNumber(evidence: Record<string, unknown> | undefined, key: string): number | undefined {
  const value = evidence?.[key];
  return typeof value === "number" && Number.isFinite(value) ? value : undefined;
}

/**
 * WorkProjector keeps a generic summary.result and puts the useful automatic
 * scan explanation in outcome.summary/evidence. Keep this interpretation in
 * one controlled presentation boundary so a generic success cannot mask an
 * empty or changed scan.
 */
export function formatWorkFactResult(fact: WorkFact): string {
  const status = String(fact.outcome?.status ?? fact.work?.status ?? "").toLowerCase();
  const outcomeSummary = String(fact.outcome?.summary ?? "").trim();
  const evidence = fact.outcome?.evidence;
  const jobs = finiteEvidenceNumber(evidence, "jobs");
  const queued = finiteEvidenceNumber(evidence, "queued");
  const summaryIsEmpty = EMPTY_SCAN_SUMMARIES.some((pattern) => pattern.test(outcomeSummary));

  if (/^unsupported automatic-memory source kind:\s*[^\s]+$/i.test(outcomeSummary)) {
    return "这个来源暂不支持自动接入，其他记忆不受影响";
  }

  if ((status === "completed" || status === "success") && ((jobs === 0 && queued === 0) || summaryIsEmpty)) {
    return "检查完成，未发现新内容";
  }
  if ((status === "completed" || status === "success") && queued !== undefined && queued > 0 && (!outcomeSummary || GENERIC_SUCCESS.has(outcomeSummary))) {
    return `检查完成，新增 ${queued} 条内容`;
  }
  if (outcomeSummary && !GENERIC_SUCCESS.has(outcomeSummary)) return outcomeSummary;
  if (status === "failed") return "这次检查没有完成";
  if (status === "completed" || status === "success") return "检查已完成，结果尚未获得";
  return "检查结果尚未获得";
}
