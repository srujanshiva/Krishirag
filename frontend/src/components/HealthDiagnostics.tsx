"use client";

import React, { useState, useEffect } from "react";
import {
  Activity,
  CheckCircle,
  XCircle,
  Database,
  Cpu,
  Layers,
  RefreshCw,
  Clock,
  Shield,
} from "lucide-react";
import { HealthResponse, ReadinessResponse } from "../types";
import { api } from "../lib/api";

export const HealthDiagnostics: React.FC = () => {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [readiness, setReadiness] = useState<ReadinessResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [latencyMs, setLatencyMs] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  const probe = async () => {
    setLoading(true);
    setError(null);
    const start = performance.now();
    try {
      const [h, r] = await Promise.all([api.getHealth(), api.getReadiness()]);
      const elapsed = Math.round(performance.now() - start);
      setHealth(h);
      setReadiness(r);
      setLatencyMs(elapsed);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Diagnostics probe failed");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    probe();
  }, []);

  return (
    <div id="diagnostics-panel" style={styles.container}>
      <div style={styles.topBar}>
        <div>
          <h2 style={styles.title}>System Health & Operational Diagnostics</h2>
          <p style={styles.subtitle}>
            Live verification probes for PostgreSQL, Qdrant vector database, and FastAPI service
          </p>
        </div>
        <button id="btn-reprobe-diagnostics" onClick={probe} disabled={loading} style={styles.probeBtn}>
          <RefreshCw size={14} style={{ animation: loading ? "spin 1s linear infinite" : "none" }} />
          <span>Run Probe</span>
        </button>
      </div>

      {error && <div style={styles.errorBox}>{error}</div>}

      <div style={styles.cardsGrid}>
        {/* Core Liveness */}
        <section style={styles.diagCard}>
          <div style={styles.cardHeader}>
            <Activity size={18} color="#10b981" />
            <h3 style={styles.cardLabel}>FastAPI Liveness Probe</h3>
          </div>
          <div style={styles.metricRow}>
            <span style={styles.metricKey}>Status</span>
            <span style={styles.metricValGreen}>
              <CheckCircle size={14} /> {health?.status?.toUpperCase() || "UNKNOWN"}
            </span>
          </div>
          <div style={styles.metricRow}>
            <span style={styles.metricKey}>Environment</span>
            <span style={styles.metricVal}>{health?.environment || "development"}</span>
          </div>
          <div style={styles.metricRow}>
            <span style={styles.metricKey}>Probe Latency</span>
            <span style={styles.metricVal}>{latencyMs !== null ? `${latencyMs} ms` : "..."}</span>
          </div>
        </section>

        {/* PostgreSQL Database */}
        <section style={styles.diagCard}>
          <div style={styles.cardHeader}>
            <Database size={18} color="#0f614b" />
            <h3 style={styles.cardLabel}>PostgreSQL 17 Alpine</h3>
          </div>
          <div style={styles.metricRow}>
            <span style={styles.metricKey}>Connection</span>
            <span
              style={
                readiness?.database === "connected" || (readiness as any)?.db === "ok"
                  ? styles.metricValGreen
                  : styles.metricValRed
              }
            >
              {readiness?.database === "connected" || (readiness as any)?.db === "ok" ? (
                <CheckCircle size={14} />
              ) : (
                <XCircle size={14} />
              )}
              {readiness?.database === "connected" || (readiness as any)?.db === "ok"
                ? "CONNECTED"
                : readiness?.database?.toUpperCase() || "CHECKING"}
            </span>
          </div>
          <div style={styles.metricRow}>
            <span style={styles.metricKey}>Connection Pool</span>
            <span style={styles.metricVal}>Asyncpg / SQLAlchemy 2.0</span>
          </div>
          <div style={styles.metricRow}>
            <span style={styles.metricKey}>Documents Ingested</span>
            <span style={styles.metricVal}>
              <strong>{readiness?.document_count ?? 0}</strong> Publications
            </span>
          </div>
        </section>

        {/* Qdrant Vector Store */}
        <section style={styles.diagCard}>
          <div style={styles.cardHeader}>
            <Layers size={18} color="#d97706" />
            <h3 style={styles.cardLabel}>Qdrant Vector Database</h3>
          </div>
          <div style={styles.metricRow}>
            <span style={styles.metricKey}>Collection Status</span>
            <span
              style={
                readiness?.vector_store === "connected"
                  ? styles.metricValGreen
                  : styles.metricValRed
              }
            >
              {readiness?.vector_store === "connected" ? (
                <CheckCircle size={14} />
              ) : (
                <XCircle size={14} />
              )}
              {readiness?.vector_store === "connected"
                ? "CONNECTED"
                : readiness?.vector_store?.toUpperCase() || "CHECKING"}
            </span>
          </div>
          <div style={styles.metricRow}>
            <span style={styles.metricKey}>Vectors Indexed</span>
            <span style={styles.metricVal}>
              <strong>{readiness?.vector_count ?? 0}</strong> Chunks
            </span>
          </div>
          <div style={styles.metricRow}>
            <span style={styles.metricKey}>Embedding Dimension</span>
            <span style={styles.metricVal}>384 (FastEmbed BGE-Small)</span>
          </div>
        </section>

        {/* Agentic Guardrails & LLM Gateway */}
        <section style={styles.diagCard}>
          <div style={styles.cardHeader}>
            <Shield size={18} color="#10b981" />
            <h3 style={styles.cardLabel}>Agentic Guardrails & Gateway</h3>
          </div>
          <div style={styles.metricRow}>
            <span style={styles.metricKey}>Primary Model</span>
            <span style={styles.metricVal}>Groq · qwen/qwen3.8-27b</span>
          </div>
          <div style={styles.metricRow}>
            <span style={styles.metricKey}>Fallback Gateway</span>
            <span style={styles.metricVal}>Google Gemini · gemini-3.8-flash</span>
          </div>
          <div style={styles.metricRow}>
            <span style={styles.metricKey}>Hard Iteration Bound</span>
            <span style={styles.metricVal}>Max 10 Steps / 45s Timeout</span>
          </div>
        </section>
      </div>
    </div>
  );
};

const styles: Record<string, React.CSSProperties> = {
  container: {
    display: "flex",
    flexDirection: "column",
    gap: "1.25rem",
    padding: "1rem 0",
  },
  topBar: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
  },
  title: {
    fontSize: "1.15rem",
    fontWeight: 700,
    fontFamily: "var(--font-display)",
    color: "var(--text-main)",
  },
  subtitle: {
    fontSize: "0.8rem",
    color: "var(--text-muted)",
    marginTop: "0.15rem",
  },
  probeBtn: {
    display: "flex",
    alignItems: "center",
    gap: "0.45rem",
    padding: "0.45rem 0.95rem",
    borderRadius: "8px",
    border: "1px solid var(--border-subtle)",
    backgroundColor: "var(--emerald-600)",
    color: "#ffffff",
    fontSize: "0.82rem",
    fontWeight: 600,
    cursor: "pointer",
  },
  errorBox: {
    backgroundColor: "var(--danger-50)",
    color: "var(--danger-600)",
    padding: "0.75rem 1rem",
    borderRadius: "8px",
    fontSize: "0.85rem",
  },
  cardsGrid: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))",
    gap: "1.25rem",
  },
  diagCard: {
    backgroundColor: "var(--bg-surface)",
    border: "1px solid var(--border-subtle)",
    borderRadius: "14px",
    padding: "1.25rem",
    boxShadow: "var(--shadow-md)",
    display: "flex",
    flexDirection: "column",
    gap: "0.75rem",
  },
  cardHeader: {
    display: "flex",
    alignItems: "center",
    gap: "0.5rem",
    borderBottom: "1px solid var(--border-subtle)",
    paddingBottom: "0.6rem",
  },
  cardLabel: {
    fontSize: "0.95rem",
    fontWeight: 700,
    color: "var(--text-main)",
  },
  metricRow: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    fontSize: "0.82rem",
  },
  metricKey: {
    color: "var(--text-muted)",
  },
  metricVal: {
    color: "var(--text-main)",
    fontWeight: 600,
  },
  metricValGreen: {
    display: "flex",
    alignItems: "center",
    gap: "0.3rem",
    color: "var(--emerald-600)",
    fontWeight: 700,
  },
  metricValRed: {
    display: "flex",
    alignItems: "center",
    gap: "0.3rem",
    color: "var(--danger-600)",
    fontWeight: 700,
  },
};
