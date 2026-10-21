export interface Citation {
  chunk_id: string;
  document_title: string;
  publisher: string;
  source_url?: string | null;
  page_number?: number | null;
  section?: string | null;
  excerpt: string;
}

export interface WeatherData {
  location: string;
  temperature_c?: number | null;
  humidity_percent?: number | null;
  precipitation_mm?: number | null;
  precipitation_prob_percent?: number | null;
  wind_speed_kmh?: number | null;
  condition?: string | null;
  spraying_advisory?: string | null;
  fieldwork_advisory?: string | null;
}

export interface ClaimVerification {
  claim_text: string;
  is_grounded: boolean;
  confidence_score: number;
  supporting_chunk_id?: string | null;
  supporting_doc?: string | null;
  supporting_page?: number | null;
}

export interface FaithfulnessData {
  score: number;
  faithfulness_percent: number;
  total_claims: number;
  grounded_claims: number;
  unverified_claims: number;
  claims?: ClaimVerification[];
}

export interface ChemicalSafetyData {
  chemical: string;
  crop?: string | null;
  is_safe: boolean;
  warning_level: "safe" | "caution" | "critical" | "banned";
  phi_days: number;
  toxicity_class: string;
  mrl_ppm: number;
  explanation: string;
  alternative_recommended?: string | null;
}

export interface DosageCalculationData {
  crop: string;
  input_display: string;
  area_hectares: number;
  recommended_npk_ratio: string;
  urea_kg: number;
  dap_kg: number;
  mop_kg: number;
  application_splits: string[];
  notes: string;
}

export interface VisualDiagnosticData {
  crop: string;
  symptoms_detected: string[];
  suspected_diseases: string[];
  confidence_score: number;
  visual_features?: Record<string, any>;
  immediate_action: string;
  search_keywords: string[];
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: string;
  crop?: string | null;
  location?: string | null;
  image_data?: string | null;
  citations?: Citation[];
  uncertainty?: "none" | "low" | "high";
  retrieval_score?: number | null;
  evidence_count?: number;
  user_rating?: number | null;
  weather?: WeatherData | null;
  faithfulness?: FaithfulnessData | null;
  chemical_safety?: ChemicalSafetyData | null;
  dosage_calculation?: DosageCalculationData | null;
  visual_diagnostic?: VisualDiagnosticData | null;
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
  weather?: WeatherData | null;
  faithfulness?: FaithfulnessData | null;
  chemical_safety?: ChemicalSafetyData | null;
  dosage_calculation?: DosageCalculationData | null;
  visual_diagnostic?: VisualDiagnosticData | null;
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
