import {
  ChatApiResponse,
  FeedbackSubmission,
  HealthResponse,
  IngestionDocument,
  IngestionJob,
  ReadinessResponse,
} from "../types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

export class ApiError extends Error {
  status: number;
  errorCode?: string;

  constructor(message: string, status: number, errorCode?: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.errorCode = errorCode;
  }
}

async function request<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const url = `${API_BASE}${endpoint}`;
  try {
    const res = await fetch(url, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        ...options?.headers,
      },
    });

    if (!res.ok) {
      let errorMsg = `Server error (${res.status})`;
      let code = undefined;
      try {
        const errJson = await res.json();
        if (errJson.detail) {
          if (typeof errJson.detail === "object") {
            errorMsg = errJson.detail.message || JSON.stringify(errJson.detail);
            code = errJson.detail.error_code;
          } else {
            errorMsg = errJson.detail;
          }
        }
      } catch {
        // Response was not JSON
      }
      throw new ApiError(errorMsg, res.status, code);
    }

    return await res.json();
  } catch (err: unknown) {
    if (err instanceof ApiError) {
      throw err;
    }
    const msg = err instanceof Error ? err.message : "Network error. Backend unreachable.";
    throw new ApiError(msg, 0);
  }
}

export const api = {
  // Chat Advisory
  sendQuery: async (
    question: string,
    conversationId?: string | null,
    crop?: string | null,
    location?: string | null
  ): Promise<ChatApiResponse> => {
    return request<ChatApiResponse>("/chat", {
      method: "POST",
      body: JSON.stringify({
        question,
        conversation_id: conversationId || null,
        crop: crop || null,
        location: location || null,
      }),
    });
  },

  // Feedback
  submitFeedback: async (feedback: FeedbackSubmission): Promise<{ status: string }> => {
    return request<{ status: string }>("/feedback", {
      method: "POST",
      body: JSON.stringify(feedback),
    });
  },

  // Health & Readiness
  getHealth: async (): Promise<HealthResponse> => {
    return request<HealthResponse>("/health");
  },

  getReadiness: async (): Promise<ReadinessResponse> => {
    return request<ReadinessResponse>("/ready");
  },

  // Admin Ingestion
  listIngestionJobs: async (token: string): Promise<IngestionJob[]> => {
    return request<IngestionJob[]>("/admin/ingestion-jobs", {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });
  },

  listDocuments: async (token: string): Promise<IngestionDocument[]> => {
    return request<IngestionDocument[]>("/admin/documents", {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });
  },

  uploadDocument: async (
    file: File,
    title: string,
    publisher: string,
    sourceUrl: string,
    token: string
  ): Promise<IngestionJob> => {
    const formData = new FormData();
    formData.append("file", file);
    formData.append("title", title);
    formData.append("publisher", publisher);
    formData.append("source_url", sourceUrl);

    const res = await fetch(`${API_BASE}/admin/ingest-file`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
      },
      body: formData,
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Upload failed" }));
      throw new ApiError(err.detail || "Upload failed", res.status);
    }

    return await res.json();
  },
};
