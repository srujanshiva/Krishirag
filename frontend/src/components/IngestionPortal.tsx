"use client";

import React, { useState, useEffect } from "react";
import {
  Upload,
  FileCheck,
  RefreshCw,
  AlertCircle,
  Database,
  ExternalLink,
  Shield,
  Layers,
  Key,
  CheckCircle2,
} from "lucide-react";
import { IngestionDocument, IngestionJob } from "../types";
import { api } from "../lib/api";

export const IngestionPortal: React.FC = () => {
  const [token, setToken] = useState<string>(() => {
    if (typeof window !== "undefined") {
      return localStorage.getItem("krishirag_admin_token") || "local-dev-admin-token";
    }
    return "local-dev-admin-token";
  });
  const [documents, setDocuments] = useState<IngestionDocument[]>([]);
  const [jobs, setJobs] = useState<IngestionJob[]>([]);
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // Form inputs for upload
  const [file, setFile] = useState<File | null>(null);
  const [title, setTitle] = useState("");
  const [publisher, setPublisher] = useState("ICAR / State Agricultural University");
  const [sourceUrl, setSourceUrl] = useState("https://agritech.tnau.ac.in/");

  const loadData = async () => {
    if (!token) return;
    setLoading(true);
    setError(null);
    try {
      const [docsData, jobsData] = await Promise.all([
        api.listDocuments(token),
        api.listIngestionJobs(token),
      ]);
      setDocuments(docsData);
      setJobs(jobsData);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to load admin data");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [token]);

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file || !title) return;
    setUploading(true);
    setError(null);
    setSuccessMsg(null);
    try {
      const job = await api.uploadDocument(file, title, publisher, sourceUrl, token);
      setSuccessMsg(
        `Document submitted successfully! Job status: ${job.status} (${job.chunks_created} chunks indexed).`
      );
      setFile(null);
      setTitle("");
      await loadData();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Ingestion upload failed");
    } finally {
      setUploading(false);
    }
  };

  return (
    <div id="ingestion-portal-view" style={styles.container}>
      {/* Top Banner / Token settings */}
      <section style={styles.topCard}>
        <div style={styles.tokenRow}>
          <div style={styles.tokenLabelGroup}>
            <Key size={16} color="#0f614b" />
            <span style={styles.tokenLabel}>Admin Authentication Token:</span>
          </div>
          <input
            id="input-admin-token"
            type="password"
            value={token || ""}
            onChange={(e) => {
              setToken(e.target.value);
              if (typeof window !== "undefined") {
                localStorage.setItem("krishirag_admin_token", e.target.value);
              }
            }}
            style={styles.tokenInput}
            placeholder="Enter ADMIN_TOKEN"
          />
          <button
            id="btn-refresh-ingestion"
            onClick={loadData}
            disabled={loading}
            style={styles.refreshBtn}
            title="Refresh documents and jobs"
          >
            <RefreshCw size={14} style={{ animation: loading ? "spin 1s linear infinite" : "none" }} />
            <span>Refresh</span>
          </button>
        </div>
      </section>

      {error && (
        <div style={styles.errorAlert}>
          <AlertCircle size={16} color="#dc2626" />
          <span>{error}</span>
        </div>
      )}

      {successMsg && (
        <div style={styles.successAlert}>
          <CheckCircle2 size={16} color="#10b981" />
          <span>{successMsg}</span>
        </div>
      )}

      <div style={styles.grid}>
        {/* Document Ingestion Form */}
        <section style={styles.card}>
          <div style={styles.cardHeader}>
            <Upload size={18} color="#10b981" />
            <h2 style={styles.cardTitle}>Ingest Authoritative Publication</h2>
          </div>
          <form id="form-upload-document" onSubmit={handleUpload} style={styles.form}>
            <div style={styles.formGroup}>
              <label htmlFor="input-pdf-file" style={styles.label}>
                Agricultural PDF Guide / Package of Practices:
              </label>
              <input
                id="input-pdf-file"
                type="file"
                accept=".pdf"
                onChange={(e) => {
                  const f = e.target.files?.[0];
                  if (f) {
                    setFile(f);
                    if (!title) setTitle(f.name.replace(".pdf", ""));
                  }
                }}
                required
                style={styles.fileInput}
              />
            </div>

            <div style={styles.formGroup}>
              <label htmlFor="input-doc-title" style={styles.label}>
                Document Title:
              </label>
              <input
                id="input-doc-title"
                type="text"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="e.g. TNAU Crop Production Guide - Rice"
                required
                style={styles.textInput}
              />
            </div>

            <div style={styles.formGroup}>
              <label htmlFor="input-doc-publisher" style={styles.label}>
                Publisher / Authority:
              </label>
              <input
                id="input-doc-publisher"
                type="text"
                value={publisher}
                onChange={(e) => setPublisher(e.target.value)}
                required
                style={styles.textInput}
              />
            </div>

            <div style={styles.formGroup}>
              <label htmlFor="input-source-url" style={styles.label}>
                Source URL:
              </label>
              <input
                id="input-source-url"
                type="url"
                value={sourceUrl}
                onChange={(e) => setSourceUrl(e.target.value)}
                style={styles.textInput}
              />
            </div>

            <button
              id="btn-submit-ingestion"
              type="submit"
              disabled={uploading || !file || !title}
              style={{
                ...styles.uploadBtn,
                ...(uploading || !file || !title ? styles.uploadBtnDisabled : {}),
              }}
            >
              {uploading ? "Extracting & Chunking..." : "Process & Index Knowledge"}
            </button>
          </form>
        </section>

        {/* Indexed Publications Registry */}
        <section style={styles.card}>
          <div style={styles.cardHeader}>
            <Database size={18} color="#0f614b" />
            <h2 style={styles.cardTitle}>Verified Agricultural Knowledge Base ({documents.length})</h2>
          </div>

          <div style={styles.docList}>
            {documents.length === 0 ? (
              <div style={styles.emptyState}>No documents currently ingested in knowledge base.</div>
            ) : (
              documents.map((doc) => (
                <div key={doc.id} style={styles.docCard}>
                  <div style={styles.docCardTop}>
                    <FileCheck size={16} color="#10b981" />
                    <strong style={styles.docName}>{doc.title}</strong>
                    <span style={styles.statusPill}>{doc.ingestion_status}</span>
                  </div>
                  <div style={styles.docMeta}>
                    <span>{doc.publisher}</span>
                    <span style={styles.checksumTag}>SHA-256: {doc.checksum_sha256.slice(0, 12)}...</span>
                  </div>
                  {doc.source_url && (
                    <a
                      href={doc.source_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      style={styles.docUrl}
                    >
                      <span>Public Source Repository</span>
                      <ExternalLink size={12} />
                    </a>
                  )}
                </div>
              ))
            )}
          </div>
        </section>
      </div>

      {/* Ingestion Jobs Audit Table */}
      <section style={styles.jobsCard}>
        <div style={styles.cardHeader}>
          <Layers size={18} color="#d97706" />
          <h2 style={styles.cardTitle}>Asynchronous Ingestion Jobs Trace ({jobs.length})</h2>
        </div>
        <div style={styles.tableWrapper}>
          <table style={styles.table}>
            <thead>
              <tr style={styles.tableHeadRow}>
                <th style={styles.th}>Job ID</th>
                <th style={styles.th}>Status</th>
                <th style={styles.th}>Chunks Indexed</th>
                <th style={styles.th}>Created At</th>
                <th style={styles.th}>Finished At</th>
              </tr>
            </thead>
            <tbody>
              {jobs.map((job) => (
                <tr key={job.id} style={styles.tableRow}>
                  <td style={styles.tdMono}>{job.id.slice(0, 8)}...</td>
                  <td style={styles.td}>
                    <span
                      style={{
                        ...styles.jobStatusPill,
                        backgroundColor:
                          job.status === "completed"
                            ? "var(--emerald-50)"
                            : job.status === "already_exists"
                            ? "var(--gold-100)"
                            : "var(--danger-50)",
                        color:
                          job.status === "completed"
                            ? "var(--emerald-700)"
                            : job.status === "already_exists"
                            ? "var(--gold-600)"
                            : "var(--danger-600)",
                      }}
                    >
                      {job.status}
                    </span>
                  </td>
                  <td style={styles.td}>
                    <strong>{job.chunks_created}</strong> passages
                  </td>
                  <td style={styles.tdTime}>{new Date(job.created_at).toLocaleTimeString()}</td>
                  <td style={styles.tdTime}>
                    {job.finished_at ? new Date(job.finished_at).toLocaleTimeString() : "Pending"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
};

const styles: Record<string, React.CSSProperties> = {
  container: {
    display: "flex",
    flexDirection: "column",
    gap: "1.5rem",
    padding: "1rem 0",
  },
  topCard: {
    backgroundColor: "var(--bg-surface)",
    border: "1px solid var(--border-subtle)",
    borderRadius: "12px",
    padding: "0.85rem 1.25rem",
    boxShadow: "var(--shadow-sm)",
  },
  tokenRow: {
    display: "flex",
    alignItems: "center",
    gap: "0.85rem",
  },
  tokenLabelGroup: {
    display: "flex",
    alignItems: "center",
    gap: "0.4rem",
  },
  tokenLabel: {
    fontSize: "0.82rem",
    fontWeight: 600,
    color: "var(--text-main)",
  },
  tokenInput: {
    flex: 1,
    maxWidth: "360px",
    backgroundColor: "var(--bg-elevated)",
    border: "1px solid var(--border-subtle)",
    borderRadius: "6px",
    padding: "0.35rem 0.65rem",
    fontSize: "0.82rem",
    fontFamily: "var(--font-mono)",
    color: "var(--text-main)",
  },
  refreshBtn: {
    display: "flex",
    alignItems: "center",
    gap: "0.4rem",
    padding: "0.4rem 0.85rem",
    borderRadius: "6px",
    border: "1px solid var(--border-subtle)",
    backgroundColor: "var(--bg-elevated)",
    color: "var(--text-main)",
    fontSize: "0.8rem",
    fontWeight: 600,
    cursor: "pointer",
  },
  errorAlert: {
    display: "flex",
    alignItems: "center",
    gap: "0.6rem",
    backgroundColor: "var(--danger-50)",
    color: "var(--danger-600)",
    padding: "0.75rem 1rem",
    borderRadius: "8px",
    fontSize: "0.85rem",
  },
  successAlert: {
    display: "flex",
    alignItems: "center",
    gap: "0.6rem",
    backgroundColor: "var(--emerald-50)",
    color: "var(--emerald-600)",
    padding: "0.75rem 1rem",
    borderRadius: "8px",
    fontSize: "0.85rem",
  },
  grid: {
    display: "grid",
    gridTemplateColumns: "1fr 1fr",
    gap: "1.5rem",
  },
  card: {
    backgroundColor: "var(--bg-surface)",
    border: "1px solid var(--border-subtle)",
    borderRadius: "14px",
    padding: "1.25rem",
    boxShadow: "var(--shadow-md)",
  },
  cardHeader: {
    display: "flex",
    alignItems: "center",
    gap: "0.5rem",
    borderBottom: "1px solid var(--border-subtle)",
    paddingBottom: "0.75rem",
    marginBottom: "1rem",
  },
  cardTitle: {
    fontSize: "1.05rem",
    fontWeight: 700,
    fontFamily: "var(--font-display)",
    color: "var(--text-main)",
  },
  form: {
    display: "flex",
    flexDirection: "column",
    gap: "0.85rem",
  },
  formGroup: {
    display: "flex",
    flexDirection: "column",
    gap: "0.3rem",
  },
  label: {
    fontSize: "0.78rem",
    fontWeight: 600,
    color: "var(--text-muted)",
  },
  fileInput: {
    backgroundColor: "var(--bg-elevated)",
    border: "1px dashed var(--border-strong)",
    borderRadius: "8px",
    padding: "0.6rem",
    fontSize: "0.82rem",
    color: "var(--text-main)",
  },
  textInput: {
    backgroundColor: "var(--bg-elevated)",
    border: "1px solid var(--border-subtle)",
    borderRadius: "8px",
    padding: "0.45rem 0.75rem",
    fontSize: "0.85rem",
    color: "var(--text-main)",
    outline: "none",
  },
  uploadBtn: {
    marginTop: "0.5rem",
    backgroundColor: "var(--emerald-600)",
    color: "#ffffff",
    border: "none",
    borderRadius: "8px",
    padding: "0.65rem",
    fontSize: "0.88rem",
    fontWeight: 600,
    cursor: "pointer",
    boxShadow: "var(--shadow-sm)",
  },
  uploadBtnDisabled: {
    backgroundColor: "var(--border-strong)",
    color: "var(--text-faint)",
    cursor: "not-allowed",
  },
  docList: {
    display: "flex",
    flexDirection: "column",
    gap: "0.75rem",
    maxHeight: "360px",
    overflowY: "auto",
  },
  emptyState: {
    fontSize: "0.85rem",
    color: "var(--text-faint)",
    padding: "1rem",
    textAlign: "center",
  },
  docCard: {
    backgroundColor: "var(--bg-elevated)",
    border: "1px solid var(--border-subtle)",
    borderRadius: "10px",
    padding: "0.85rem",
    display: "flex",
    flexDirection: "column",
    gap: "0.35rem",
  },
  docCardTop: {
    display: "flex",
    alignItems: "center",
    gap: "0.45rem",
  },
  docName: {
    fontSize: "0.9rem",
    color: "var(--text-main)",
    flex: 1,
  },
  statusPill: {
    fontSize: "0.72rem",
    fontWeight: 600,
    backgroundColor: "var(--emerald-50)",
    color: "var(--emerald-700)",
    padding: "0.15rem 0.45rem",
    borderRadius: "4px",
    textTransform: "uppercase",
  },
  docMeta: {
    display: "flex",
    justifyContent: "space-between",
    fontSize: "0.74rem",
    color: "var(--text-muted)",
  },
  checksumTag: {
    fontFamily: "var(--font-mono)",
  },
  docUrl: {
    display: "inline-flex",
    alignItems: "center",
    gap: "0.3rem",
    fontSize: "0.75rem",
    color: "var(--emerald-600)",
    textDecoration: "underline",
    marginTop: "0.2rem",
  },
  jobsCard: {
    backgroundColor: "var(--bg-surface)",
    border: "1px solid var(--border-subtle)",
    borderRadius: "14px",
    padding: "1.25rem",
    boxShadow: "var(--shadow-md)",
  },
  tableWrapper: {
    overflowX: "auto",
  },
  table: {
    width: "100%",
    borderCollapse: "collapse",
    fontSize: "0.82rem",
  },
  tableHeadRow: {
    backgroundColor: "var(--bg-elevated)",
    textAlign: "left",
  },
  th: {
    padding: "0.6rem 0.85rem",
    color: "var(--text-muted)",
    fontWeight: 600,
    borderBottom: "1px solid var(--border-subtle)",
  },
  tableRow: {
    borderBottom: "1px solid var(--border-subtle)",
  },
  td: {
    padding: "0.6rem 0.85rem",
    color: "var(--text-main)",
  },
  tdMono: {
    padding: "0.6rem 0.85rem",
    fontFamily: "var(--font-mono)",
    color: "var(--text-muted)",
  },
  tdTime: {
    padding: "0.6rem 0.85rem",
    color: "var(--text-muted)",
    fontSize: "0.76rem",
  },
  jobStatusPill: {
    padding: "0.15rem 0.45rem",
    borderRadius: "4px",
    fontSize: "0.72rem",
    fontWeight: 600,
    textTransform: "uppercase",
  },
};
