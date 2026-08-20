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
  evidence: OwnerSummaryEvidence;
};

export type OwnerWorkbenchSummary = {
  completed: OwnerSummaryItem[];
  running: OwnerSummaryItem[];
  decisions: OwnerSummaryItem[];
  nextSteps: OwnerSummaryItem[];
};

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
    nextActor?: OwnerNextActor;
  }>;
}): OwnerWorkbenchSummary {
  const completed: OwnerSummaryItem[] = [];
  const running: OwnerSummaryItem[] = [];

  for (const item of workItems) {
    const summary: OwnerSummaryItem = {
      title: item.title || "未命名工作",
      detail: item.outcome || "已有真实 WorkItem，但暂无可展示结果。",
      nextActor: item.nextActor || "无需操作",
      evidence: {
        workItemId: item.workItemId,
        captureId: item.captureId,
        jobId: item.jobId,
      },
    };

    if (item.status === "completed") completed.push(summary);
    else running.push(summary);
  }

  const decisions = attentionItems.map((item) => ({
    title: item.title,
    detail: item.detail,
    nextActor: "你" as const,
    evidence: { workItemId: item.objectId },
  }));

  return {
    completed,
    running,
    decisions,
    nextSteps: [
      ...running.map((item) => ({
        ...item,
        nextActor: item.nextActor || "灵机",
      })),
      ...decisions,
    ],
  };
}
