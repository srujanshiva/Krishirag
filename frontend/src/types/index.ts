export interface Citation {
  chunk_id: string;
  document_title: string;
  publisher: string;
  source_url?: string | null;
  page_number?: number | null;
  section?: string | null;
  excerpt: string;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: string;
  crop?: string | null;
  location?: string | null;
  citations?: Citation[];
  uncertainty?: "none" | "low" | "high";
  retrieval_score?: number | null;
  evidence_count?: number;
  user_rating?: number | null;
}

export interface ChatApiResponse {
  request_id: string;
  answer: string;
  citations: Citation[];
  uncertainty: "none" | "low" | "high";
  conversation_id: string;
  message_id: string;
  retrieval_score?: number | null;
  evidence_count: number;
}

export interface ReadinessResponse {
  status: "ready" | "not_ready";
  database: "connected" | "disconnected" | "error";
  vector_store: "connected" | "disconnected" | "error";
  knowledge_base: "populated" | "empty";
  document_count: number;
  vector_count: number;
}

export interface HealthResponse {
  status: "ok" | "error";
  version: string;
  environment: string;
}

export interface IngestionJob {
  id: string;
  document_id?: string | null;
  status: "pending" | "processing" | "completed" | "failed" | "already_exists";
  chunks_created: number;
  error_message?: string | null;
  created_at: string;
  finished_at?: string | null;
}

export interface IngestionDocument {
  id: string;
  title: string;
  publisher: string;
  checksum_sha256: string;
  ingestion_status: string;
  source_url?: string | null;
  created_at: string;
}

export interface FeedbackSubmission {
  message_id: string;
  rating: number;
  user_notes?: string;
}
