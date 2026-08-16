import type { PageId } from "./types";

export type ReviewCandidate = {
  memory_id: string;
  title?: string | null;
  content_preview?: string | null;
  proposal_reason?: string | null;
  confidence?: number | null;
  created_at?: string | null;
};

export type ReviewResponse = {
  items?: ReviewCandidate[];
  pagination?: { total?: number | null; has_more?: boolean };
};

export type ImportCandidate = {
  candidate_id: string;
  display_name?: string | null;
  size_bytes?: number | null;
};

export type ImportSource = {
  id: string;
  label: string;
  candidates?: ImportCandidate[];
};

export type AssistantRecord = {
  id: string;
  label: string;
  detection_state: string;
  candidate_count?: number;
  latest_activity_at?: string | null;
  message?: string;
};

export type AssistantHub = {
  assistants?: AssistantRecord[];
  import_plan?: { sources?: ImportSource[] };
};

export type MemoryAttentionItem = {
  kind: "memory";
  id: string;
  objectId: string;
  title: string;
  detail: string;
  target: PageId;
  memoryId: string;
  candidate: ReviewCandidate;
};

export type ImportAttentionItem = {
  kind: "import";
  id: string;
  objectId: string;
  title: string;
  detail: string;
  target: PageId;
  candidateId: string;
  source: ImportSource;
  candidate: ImportCandidate;
};

export type VectorAttentionItem = {
  kind: "vector";
  id: string;
  objectId: string;
  title: string;
  detail: string;
  target: PageId;
};

export type OwnerAttentionItem = MemoryAttentionItem | ImportAttentionItem | VectorAttentionItem;

export function formatFileSize(value: unknown): string {
  const bytes = Number(value ?? 0);
  if (!Number.isFinite(bytes) || bytes <= 0) return "大小未知";
  if (bytes >= 1024 * 1024) return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
  return `${Math.max(1, Math.round(bytes / 1024))} KB`;
}

export function buildOwnerAttentionItems({
  reviewItems,
  importSources,
  vectorRebuildRequired,
}: {
  reviewItems: ReviewCandidate[];
  importSources: ImportSource[];
  vectorRebuildRequired: boolean;
}): OwnerAttentionItem[] {
  const result: OwnerAttentionItem[] = [];

  for (const candidate of reviewItems) {
    if (!candidate.memory_id) continue;
    result.push({
      kind: "memory",
      id: `memory:${candidate.memory_id}`,
      objectId: candidate.memory_id,
      title: candidate.title || "候选记忆等待确认",
      detail: candidate.proposal_reason || candidate.content_preview || "只有你确认后，它才会进入永久记忆。",
      target: "memory_review",
      memoryId: candidate.memory_id,
      candidate,
    });
  }

  for (const source of importSources) {
    for (const candidate of source.candidates ?? []) {
      if (!candidate.candidate_id) continue;
      result.push({
        kind: "import",
        id: `import:${candidate.candidate_id}`,
        objectId: candidate.candidate_id,
        title: `允许读取 ${source.label} · ${candidate.display_name || "新资料"}`,
        detail: `已发现文件元数据 · ${formatFileSize(candidate.size_bytes)}。读取正文会跨过隐私边界，所以停下来等你。`,
        target: "attention",
        candidateId: candidate.candidate_id,
        source,
        candidate,
      });
    }
  }

  if (vectorRebuildRequired) {
    result.push({
      kind: "vector",
      id: "vector-rebuild",
      objectId: "vector-rebuild",
      title: "确认是否重建向量索引",
      detail: "索引重建属于不可逆维护，灵机不会自动删除并重建 Collection。",
      target: "vector_center",
    });
  }

  return result;
}

export function hasReviewConsistencyIssue({
  pendingReviewCount,
  reviewsLoaded,
  reviewItems,
}: {
  pendingReviewCount: number;
  reviewsLoaded: boolean;
  reviewItems: ReviewCandidate[];
}): boolean {
  return pendingReviewCount > 0 && reviewsLoaded && reviewItems.length === 0;
}

export function ownerSourcesUnknown({ reviewsLoaded, assistantsLoaded }: { reviewsLoaded: boolean; assistantsLoaded: boolean }): boolean {
  return !reviewsLoaded || !assistantsLoaded;
}

export function ownerAttentionSummary({
  items,
  sourceUnknown,
  activeWorkCount,
}: {
  items: OwnerAttentionItem[];
  sourceUnknown: boolean;
  activeWorkCount: number;
}): { title: string; detail: string; state: "owner" | "unknown" | "auto" } {
  if (items.length > 0) {
    return {
      title: `有 ${items.length} 件事真的需要你`,
      detail: "这些事项都有真实对象和明确原因。其余扫描、整理、重试和索引由灵机自己继续。",
      state: "owner",
    };
  }
  if (sourceUnknown) {
    return {
      title: "正在确认有没有事情需要你",
      detail: "部分主人边界状态暂时没读到，灵机正在自动重试；未知不会被显示成“没有待办”。",
      state: "unknown",
    };
  }
  if (activeWorkCount > 0) {
    return {
      title: "现在不用你做任何事",
      detail: `灵机正在自动处理 ${activeWorkCount} 项工作，你不用守着它。`,
      state: "auto",
    };
  }
  return {
    title: "现在不用你做任何事",
    detail: "没有权限、冲突或不可逆事项等你处理。灵机会继续观察已授权来源。",
    state: "auto",
  };
}
