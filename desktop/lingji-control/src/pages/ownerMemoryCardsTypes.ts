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
  source?: { label?: string | null; status?: string | null; message_count?: number | null; latest_evidence_at?: string | null; source_id?: string | null } | null;
  layers?: Record<string, OwnerMemoryLayer> | null;
  trust?: { state?: string | null; confidence?: number | null; conflict?: string | null; provenance?: string | null } | null;
  action?: { type?: string | null; label?: string | null; reason?: string | null } | null;
  permanent_memory?: string | null;
  evidence_count?: number;
  evidence?: Array<{ message_id?: string | null; preview?: string | null; occurred_at?: string | null; role?: string | null }>;
  current_hash?: string | null;
};

export type OwnerMemoryCardsResponse = {
  items?: OwnerMemoryCard[];
  pagination?: { limit?: number; offset?: number; total?: number | null; has_more?: boolean } | null;
};

export const OWNER_MEMORY_CARD_LIMIT = 20;
