export type Citation = {
  chunk_id: string;
  relative_path?: string | null;
  start_line?: number | null;
  end_line?: number | null;
};

export type Pagination = {
  limit: number;
  offset: number;
  total: number | null;
  has_more: boolean;
};

export type PageResponse<T> = {
  items: T[];
  pagination: Pagination;
};

export type SourceItem = {
  source_id: string;
  source_type?: string | null;
  display_name?: string | null;
  privacy?: string | null;
  projects?: unknown[] | null;
  status?: string | null;
  conversation_count?: number | null;
  message_count?: number | null;
  updated_at?: string | null;
};

export type ConversationItem = {
  conversation_id: string;
  source_id?: string | null;
  title?: string | null;
  participants?: unknown[] | null;
  projects?: unknown[] | null;
  privacy?: string | null;
  started_at?: string | null;
  ended_at?: string | null;
  message_count?: number | null;
};

export type MessageItem = {
  message_id: string;
  conversation_id?: string | null;
  source_id?: string | null;
  role?: string | null;
  author?: string | null;
  occurred_at?: string | null;
  content_preview?: string | null;
  content?: string | null;
  privacy?: string | null;
  metadata?: {
    model?: string | null;
    is_branch?: boolean | null;
    [key: string]: unknown;
  } | null;
};

export type MemoryLink = {
  memory_id: string;
  relation_type?: string | null;
  confidence?: number | null;
};

export type MessageDetailResponse = {
  item: MessageItem;
  memory_links: MemoryLink[];
};

export type MemoryItem = {
  memory_id: string;
  title?: string | null;
  memory_type?: string | null;
  status?: string | null;
  chunks?: unknown[] | null;
  chunk_count?: number | null;
};

export type MemoryDetailResponse = { item: MemoryItem };

export type MemorySourceResponse = {
  memory_id?: string;
  canonical?: {
    relative_path?: string | null;
    citations?: Citation[] | null;
    [key: string]: unknown;
  } | null;
  links?: Array<{
    message_id?: string | null;
    relation_type?: string | null;
    citation?: string | null;
    [key: string]: unknown;
  }>;
};

export type MemoryVectorResponse = {
  memory_id?: string;
  vector?: {
    state?: string | null;
    rebuild_required?: boolean | null;
    chunks?: unknown[];
  } | null;
};

export type InspectorStatusResponse = {
  workspace?: string | null;
  as_of?: string | null;
  sources?: {
    state?: string | null;
    sources?: number | null;
    conversations?: number | null;
    messages?: number | null;
  } | null;
  memory?: {
    state?: string | null;
    documents?: number | null;
    chunks?: number | null;
  } | null;
  vector?: {
    state?: string | null;
    coverage?: number | null;
    rebuild_required?: boolean | null;
  } | null;
};

export type InspectorSummary = {
  sources: number | null;
  conversations: number | null;
  messages: number | null;
  memories: number | null;
  chunks: number | null;
  vectorCoverage: number | null;
  vectorState: string | null;
  rebuildRequired: boolean | null;
  asOf: string | null;
};

export type InspectorFilters = {
  sourceType: string;
  project: string;
  privacy: string;
  status: string;
  role: string;
  q: string;
  fromTime: string;
  toTime: string;
};
