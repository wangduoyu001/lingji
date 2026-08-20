import type { OwnerAttentionItem } from "./ownerWorkbenchModel";

export type OwnerNextActor = "灵机" | "你" | "外部" | "无需操作";

export type OwnerSummaryEvidence = {
  workItemId?: string;
  captureId?: string;
  jobId?: string;
  resultId?: string;
};

export type OwnerSummaryItem = {
  title: string;
  detail: string;
  nextActor: OwnerNextActor;
  nextStep: string;
  evidence: OwnerSummaryEvidence;
};

export type OwnerWorkbenchSummary = {
  completed: OwnerSummaryItem[];
  running: OwnerSummaryItem[];
  decisions: OwnerSummaryItem[];
  nextSteps: OwnerSummaryItem[];
};

function actor(value: string | undefined): OwnerNextActor {
  if (value === "system") return "灵机";
  if (value === "owner") return "你";
  if (value === "external") return "外部";
  return "无需操作";
}

export function buildOwnerWorkbenchSummary({
  attentionItems,
  workItems,
}: {
  attentionItems: OwnerAttentionItem[];
  workItems: Array<{
    workItemId?: string;
    captureId?: string;
    jobId?: string;
    title?: string;
    outcome?: string;
    status?: string;
    nextActor?: string;
    nextStep?: string;
    resultId?: string;
  }>;
}): OwnerWorkbenchSummary {
  const completed: OwnerSummaryItem[] = [];
  const running: OwnerSummaryItem[] = [];

  for (const item of workItems) {
    const summary: OwnerSummaryItem = {
      title: item.title || "未命名工作",
      detail: item.outcome || "已有真实 WorkItem，但暂无可展示结果。",
      nextActor: actor(item.nextActor),
      nextStep: item.nextStep || "查看工作结果",
      evidence: {
        workItemId: item.workItemId,
        captureId: item.captureId,
        jobId: item.jobId,
        resultId: item.resultId,
      },
    };

    if (item.status === "completed") completed.push(summary);
    else running.push(summary);
  }

  const decisions = attentionItems.map((item) => ({
    title: item.title,
    detail: item.detail,
    nextActor: "你" as const,
    nextStep: "等待你的确认",
    evidence: { workItemId: item.objectId },
  }));

  return {
    completed,
    running,
    decisions,
    nextSteps: [
      ...running,
      ...decisions,
    ],
  };
}
