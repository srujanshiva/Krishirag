"use client";

import React from "react";
import { X, ExternalLink, BookOpen, Hash, Copy, Check, ShieldCheck } from "lucide-react";
import { Citation } from "../types";

interface CitationInspectorProps {
  citation: Citation | null;
  onClose: () => void;
}

export const CitationInspector: React.FC<CitationInspectorProps> = ({ citation, onClose }) => {
  const [copied, setCopied] = React.useState(false);

  if (!citation) return null;

  const handleCopyChunkId = () => {
    navigator.clipboard.writeText(citation.chunk_id);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div id="citation-inspector-overlay" style={styles.overlay} onClick={onClose}>
      <aside
        id="citation-inspector-drawer"
        style={styles.drawer}
        onClick={(e) => e.stopPropagation()}
        aria-label="Citation Inspector"
      >
        <div style={styles.header}>
          <div style={styles.headerTitleRow}>
            <ShieldCheck size={20} color="#10b981" />
            <h2 style={styles.drawerTitle}>Grounded Evidence Inspector</h2>
          </div>
          <button
            id="btn-close-citation-inspector"
            onClick={onClose}
            style={styles.closeBtn}
            aria-label="Close Inspector"
          >
            <X size={18} />
          </button>
        </div>

        <div style={styles.body}>
          {/* Document Metadata Card */}
          <section style={styles.sectionCard}>
            <div style={styles.label}>Authoritative Publication</div>
            <h3 style={styles.docTitle}>{citation.document_title}</h3>
            <div style={styles.publisherBadge}>
              <BookOpen size={14} color="#0f614b" />
              <span>{citation.publisher}</span>
            </div>

            <div style={styles.metaGrid}>
              <div style={styles.metaItem}>
                <span style={styles.metaLabel}>Page Number</span>
                <span style={styles.metaValue}>{citation.page_number ?? "General / Manual"}</span>
              </div>
              <div style={styles.metaItem}>
                <span style={styles.metaLabel}>Section</span>
                <span style={styles.metaValue}>{citation.section ?? "Agronomic Practices"}</span>
              </div>
            </div>

            {citation.source_url && (
              <a
                id="citation-source-url-link"
                href={citation.source_url}
                target="_blank"
                rel="noopener noreferrer"
                style={styles.sourceLink}
              >
                <span>Access University / ICAR Publication</span>
                <ExternalLink size={14} />
              </a>
            )}
          </section>

          {/* Verbatim Excerpt */}
          <section style={styles.sectionCard}>
            <div style={styles.label}>Verbatim Extracted Excerpt</div>
            <div style={styles.quoteBox}>
              <p style={styles.excerptText}>&ldquo;{citation.excerpt}&rdquo;</p>
            </div>
          </section>

          {/* Cryptographic Trace */}
          <section style={styles.sectionCard}>
            <div style={styles.label}>Deterministic Vector Provenance</div>
            <div style={styles.chunkRow}>
              <div style={styles.chunkIdBox}>
                <Hash size={14} color="#819b8d" />
                <span style={styles.chunkId}>{citation.chunk_id}</span>
              </div>
              <button
                id="btn-copy-chunk-id"
                onClick={handleCopyChunkId}
                style={styles.copyBtn}
                title="Copy Vector Chunk ID"
              >
                {copied ? <Check size={14} color="#10b981" /> : <Copy size={14} />}
                <span>{copied ? "Copied" : "Copy ID"}</span>
              </button>
            </div>
            <p style={styles.footnote}>
              This chunk was retrieved from the Qdrant vector database using cosine similarity over
              FastEmbed BAAI/bge-small-en-v1.5 embeddings.
            </p>
          </section>
        </div>
      </aside>
    </div>
  );
};

const styles: Record<string, React.CSSProperties> = {
  overlay: {
    position: "fixed",
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: "rgba(0, 0, 0, 0.45)",
    backdropFilter: "blur(4px)",
    zIndex: 100,
    display: "flex",
    justifyContent: "flex-end",
    animation: "fadeIn 0.2s ease-out",
  },
  drawer: {
    width: "480px",
    maxWidth: "92vw",
    height: "100%",
    backgroundColor: "var(--bg-surface)",
    boxShadow: "var(--shadow-lg)",
    display: "flex",
    flexDirection: "column",
    overflowY: "auto",
    animation: "slideDown 0.3s ease-out",
    borderLeft: "1px solid var(--border-subtle)",
  },
  header: {
    padding: "1.25rem 1.5rem",
    borderBottom: "1px solid var(--border-subtle)",
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    backgroundColor: "var(--bg-elevated)",
  },
  headerTitleRow: {
    display: "flex",
    alignItems: "center",
    gap: "0.6rem",
  },
  drawerTitle: {
    fontSize: "1.05rem",
    fontWeight: 700,
    fontFamily: "var(--font-display)",
    color: "var(--text-main)",
  },
  closeBtn: {
    border: "none",
    backgroundColor: "transparent",
    color: "var(--text-muted)",
    cursor: "pointer",
    padding: "0.3rem",
    borderRadius: "6px",
    display: "flex",
    alignItems: "center",
  },
  body: {
    padding: "1.5rem",
    display: "flex",
    flexDirection: "column",
    gap: "1.25rem",
  },
  sectionCard: {
    backgroundColor: "var(--bg-card)",
    border: "1px solid var(--border-subtle)",
    borderRadius: "12px",
    padding: "1.1rem",
    boxShadow: "var(--shadow-sm)",
  },
  label: {
    fontSize: "0.72rem",
    fontWeight: 700,
    textTransform: "uppercase",
    letterSpacing: "0.06em",
    color: "var(--emerald-600)",
    marginBottom: "0.5rem",
  },
  docTitle: {
    fontSize: "1rem",
    fontWeight: 700,
    color: "var(--text-main)",
    lineHeight: 1.35,
    marginBottom: "0.6rem",
  },
  publisherBadge: {
    display: "inline-flex",
    alignItems: "center",
    gap: "0.4rem",
    backgroundColor: "var(--emerald-50)",
    color: "var(--emerald-700)",
    padding: "0.25rem 0.65rem",
    borderRadius: "6px",
    fontSize: "0.78rem",
    fontWeight: 600,
    marginBottom: "0.85rem",
  },
  metaGrid: {
    display: "grid",
    gridTemplateColumns: "1fr 1fr",
    gap: "0.75rem",
    paddingTop: "0.6rem",
    borderTop: "1px dashed var(--border-subtle)",
  },
  metaItem: {
    display: "flex",
    flexDirection: "column",
  },
  metaLabel: {
    fontSize: "0.72rem",
    color: "var(--text-faint)",
    fontWeight: 500,
  },
  metaValue: {
    fontSize: "0.85rem",
    color: "var(--text-main)",
    fontWeight: 600,
    marginTop: "0.1rem",
  },
  sourceLink: {
    display: "inline-flex",
    alignItems: "center",
    gap: "0.4rem",
    marginTop: "0.85rem",
    fontSize: "0.8rem",
    fontWeight: 600,
    color: "var(--emerald-600)",
    textDecoration: "underline",
  },
  quoteBox: {
    backgroundColor: "var(--bg-elevated)",
    borderLeft: "3px solid var(--emerald-500)",
    padding: "0.85rem 1rem",
    borderRadius: "0 8px 8px 0",
  },
  excerptText: {
    fontSize: "0.88rem",
    color: "var(--text-main)",
    lineHeight: 1.55,
    fontStyle: "italic",
  },
  chunkRow: {
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    gap: "0.5rem",
    backgroundColor: "var(--bg-elevated)",
    padding: "0.5rem 0.75rem",
    borderRadius: "8px",
    border: "1px solid var(--border-subtle)",
  },
  chunkIdBox: {
    display: "flex",
    alignItems: "center",
    gap: "0.4rem",
    overflow: "hidden",
  },
  chunkId: {
    fontFamily: "var(--font-mono)",
    fontSize: "0.72rem",
    color: "var(--text-muted)",
    textOverflow: "ellipsis",
    overflow: "hidden",
    whiteSpace: "nowrap",
  },
  copyBtn: {
    display: "inline-flex",
    alignItems: "center",
    gap: "0.3rem",
    padding: "0.25rem 0.5rem",
    borderRadius: "6px",
    border: "1px solid var(--border-subtle)",
    backgroundColor: "var(--bg-surface)",
    color: "var(--text-muted)",
    fontSize: "0.72rem",
    fontWeight: 600,
    cursor: "pointer",
  },
  footnote: {
    fontSize: "0.72rem",
    color: "var(--text-faint)",
    marginTop: "0.6rem",
    lineHeight: 1.4,
  },
};
