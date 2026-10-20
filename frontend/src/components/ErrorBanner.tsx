"use client";

import React from "react";
import { AlertCircle, RefreshCw, Key, ShieldAlert } from "lucide-react";
import { ApiError } from "../lib/api";

interface ErrorBannerProps {
  error: Error | ApiError | null;
  onRetry?: () => void;
  onDismiss?: () => void;
}

export const ErrorBanner: React.FC<ErrorBannerProps> = ({ error, onRetry, onDismiss }) => {
  if (!error) return null;

  const isApiError = error instanceof ApiError;
  const status = isApiError ? error.status : 0;
  const code = isApiError ? error.errorCode : undefined;

  let title = "Advisory Service Error";
  let description = error.message;

  if (code === "LLM_NOT_CONFIGURED" || status === 503) {
    title = "LLM Gateway Not Configured (HTTP 503)";
    description =
      "Neither GROQ_API_KEY nor GOOGLE_API_KEY is configured in the backend environment. Please verify your .env settings.";
  } else if (code === "LLM_QUOTA_EXCEEDED" || status === 429) {
    title = "API Rate Limit Exceeded (HTTP 429)";
    description =
      "The LLM provider quota has been temporarily exhausted. Please wait a moment before resubmitting your query.";
  } else if (code === "LLM_TIMEOUT" || status === 504) {
    title = "Gateway Timeout (HTTP 504)";
    description =
      "The model inference exceeded the maximum bounded deadline. Click retry to query the fallback model.";
  }

  return (
    <div id="error-banner-callout" style={styles.banner}>
      <div style={styles.contentRow}>
        <div style={styles.iconCol}>
          {code === "LLM_NOT_CONFIGURED" ? (
            <Key size={20} color="#dc2626" />
          ) : (
            <AlertCircle size={20} color="#dc2626" />
          )}
        </div>
        <div style={styles.textCol}>
          <strong style={styles.title}>{title}</strong>
          <p style={styles.desc}>{description}</p>
        </div>
        <div style={styles.actions}>
          {onRetry && (
            <button id="btn-error-retry" onClick={onRetry} style={styles.retryBtn}>
              <RefreshCw size={14} />
              <span>Retry Query</span>
            </button>
          )}
          {onDismiss && (
            <button id="btn-error-dismiss" onClick={onDismiss} style={styles.dismissBtn}>
              Dismiss
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

const styles: Record<string, React.CSSProperties> = {
  banner: {
    backgroundColor: "var(--danger-50)",
    border: "1px solid var(--danger-100)",
    borderRadius: "12px",
    padding: "0.9rem 1.25rem",
    boxShadow: "var(--shadow-sm)",
    marginBottom: "1rem",
    animation: "fadeIn 0.25s ease-out",
  },
  contentRow: {
    display: "flex",
    alignItems: "center",
    gap: "0.85rem",
  },
  iconCol: {
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
  },
  textCol: {
    flex: 1,
    display: "flex",
    flexDirection: "column",
    gap: "0.2rem",
  },
  title: {
    fontSize: "0.88rem",
    color: "var(--danger-600)",
    fontWeight: 700,
  },
  desc: {
    fontSize: "0.8rem",
    color: "var(--text-main)",
    lineHeight: 1.4,
  },
  actions: {
    display: "flex",
    alignItems: "center",
    gap: "0.5rem",
  },
  retryBtn: {
    display: "flex",
    alignItems: "center",
    gap: "0.35rem",
    backgroundColor: "var(--danger-600)",
    color: "#ffffff",
    border: "none",
    borderRadius: "6px",
    padding: "0.35rem 0.75rem",
    fontSize: "0.78rem",
    fontWeight: 600,
    cursor: "pointer",
  },
  dismissBtn: {
    border: "none",
    background: "transparent",
    color: "var(--text-muted)",
    fontSize: "0.78rem",
    cursor: "pointer",
  },
};
