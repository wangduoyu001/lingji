export type OwnerMemoryLayer = { state?: string | null; label?: string | null; reason?: string | null };
export type OwnerMemoryCard = {
  memory_id: string;
  kind?: string;
  state?: string | null;
  topic?: string | null;
  developments?: string[] | null;
  evidence_lines?: string[] | null;
  conclusion?: string | null;
  freshness?: { state?: string | null; label?: string | null; reason?: string | null; latest_evidence_at?: string | null; replacement_id?: string | null } | null;
  source?: { label?: string | null; status?: string | null; message_count?: number | null; latest_evidence_at?: string | null; source_id?: string | null; conversation_id?: string | null; type?: string | null } | null;
  layers?: Record<string, OwnerMemoryLayer> | null;
  trust?: { state?: string | null; confidence?: number | null; conflict?: string | null; provenance?: string | null } | null;
  action?: { type?: string | null; label?: string | null; reason?: string | null } | null;
  permanent_memory?: string | null;
  evidence_count?: number;
  evidence?: Array<{ message_id?: string | null; preview?: string | null; occurred_at?: string | null; role?: string | null; conversation_id?: string | null; source_id?: string | null; sequence?: number | null }>;
  current_hash?: string | null;
  as_of?: string | null;
  content_hash?: string | null;
};

export type CanonicalChunk = {
  chunk_id?: string | null;
  text?: string | null;
  content_hash?: string | null;
  start_line?: number | null;
  end_line?: number | null;
  truncated?: boolean;
};

export type CanonicalBody = {
  asOf: string | null;
  contentHash: string | null;
  chunks: CanonicalChunk[];
  truncated: boolean;
  nextCursor: string | null;
};

export type EvidenceItem = {
  source_id?: string | null;
  conversation_id?: string | null;
  message_id?: string | null;
  role?: string | null;
  sequence?: number | null;
  occurred_at?: string | null;
  excerpt?: string | null;
  content?: string | null;
  content_hash?: string | null;
  raw_reference?: string | null;
  truncated?: boolean;
};

export type EvidencePage = {
  asOf: string | null;
  memoryId: string;
  items: EvidenceItem[];
  limit: number;
  offset: number;
  total: number | null;
  hasMore: boolean;
  nextCursor: string | null;
};

export type ConversationMessage = {
  message_id?: string | null;
  role?: string | null;
  occurred_at?: string | null;
  content?: string | null;
  content_preview?: string | null;
};

export type LayerState = OwnerMemoryLayer & { state: string | null };
export type DetailLoadState = {
  status: "idle" | "loading" | "ready" | "error" | "unknown";
  error?: string | null;
};

export type OwnerMemoryDetail = {
  memoryId: string;
  asOf: string | null;
  contentHash: string | null;
  card: OwnerMemoryCard;
  canonical: CanonicalBody | null;
  vector: Record<string, unknown> | null;
  source: Record<string, unknown> | null;
  evidence: EvidencePage | null;
  conversationMessages?: ConversationMessage[];
  loads: { card: DetailLoadState; canonical: DetailLoadState; vector: DetailLoadState; source: DetailLoadState; evidence: DetailLoadState };
};

export type OwnerFacingConclusion = {
  label: "最新结论" | "当前可确认" | "当前状态" | "当前结论";
  text: string;
};

/**
 * Build the one conclusion surface shown in both the card and its detail.
 * Every sentence is derived from an existing lifecycle/trust/evidence field;
 * this helper must never infer a new fact from a topic or an internal id.
 */
export function ownerFacingConclusion(card: OwnerMemoryCard): OwnerFacingConclusion {
  const conclusion = typeof card.conclusion === "string" ? card.conclusion.trim() : "";
  if (conclusion) return { label: "最新结论", text: conclusion };

  const freshness = String(card.freshness?.state ?? card.state ?? "").trim().toLowerCase();
  const cardState = String(card.state ?? "").trim().toLowerCase();
  const trust = String(card.trust?.state ?? "").trim().toLowerCase();
  const sourceState = String(card.source?.status ?? "").trim().toLowerCase();
  if (trust === "conflict" || card.trust?.conflict === "conflict") {
    return { label: "当前状态", text: "来源之间存在冲突，当前内容需要核对。" };
  }
  if (freshness === "superseded" || cardState === "superseded") {
    return { label: "当前状态", text: "这条内容已被更新版本替代，请以当前版本为准。" };
  }
  if (freshness === "archived" || cardState === "archived") {
    return { label: "当前状态", text: "这条内容已移出当前记忆，历史记录仍保留。" };
  }
  if (["invalidated", "stale", "overdue"].includes(freshness) || ["invalidated", "stale"].includes(cardState)) {
    return { label: "当前状态", text: "这条内容可能已经过时，请根据最近证据核对。" };
  }
  if (freshness === "source_revoked" || sourceState === "revoked") {
    return { label: "当前状态", text: "来源已停止，这条内容需要重新核对。" };
  }

  const evidenceLines = [
    ...(Array.isArray(card.developments) ? card.developments : []),
    ...(Array.isArray(card.evidence_lines) ? card.evidence_lines : []),
    ...(Array.isArray(card.evidence) ? card.evidence.map((item) => item.preview ?? "") : []),
  ];
  const firstEvidence = evidenceLines.find((line) => typeof line === "string" && line.trim());
  if (firstEvidence) return { label: "当前可确认", text: firstEvidence.trim() };
  return { label: "当前结论", text: "尚未获得" };
}

export type OwnerMemoryCardsResponse = {
  items?: OwnerMemoryCard[];
  pagination?: { limit?: number; offset?: number; total?: number | null; has_more?: boolean } | null;
};

export const OWNER_MEMORY_CARD_LIMIT = 20;
