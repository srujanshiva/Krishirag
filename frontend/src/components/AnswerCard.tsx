"use client";

import React, { useState } from "react";
import {
  ShieldCheck,
  AlertTriangle,
  FileText,
  MapPin,
  Star,
  CheckCircle,
  Clock,
  BookOpen,
} from "lucide-react";
import { ChatMessage, Citation } from "../types";
import { api } from "../lib/api";

interface AnswerCardProps {
  message: ChatMessage;
  onInspectCitation: (citation: Citation) => void;
}

export const AnswerCard: React.FC<AnswerCardProps> = ({ message, onInspectCitation }) => {
  const [rating, setRating] = useState<number | null>(message.user_rating || null);
  const [ratingSubmitted, setRatingSubmitted] = useState(false);
  const [submittingFeedback, setSubmittingFeedback] = useState(false);

  const isUser = message.role === "user";

  const handleRate = async (star: number) => {
    if (ratingSubmitted || submittingFeedback) return;
    setRating(star);
    setSubmittingFeedback(true);
    try {
      await api.submitFeedback({
        message_id: message.id,
        rating: star,
        user_notes: `Farmer rated ${star} stars from web interface`,
      });
      setRatingSubmitted(true);
    } catch (e) {
      console.error("Failed to submit feedback", e);
    } finally {
      setSubmittingFeedback(false);
    }
  };

  if (isUser) {
    return (
      <div id={`msg-user-${message.id}`} style={styles.userContainer}>
        <div style={styles.userBubble}>
          <p style={styles.userText}>{message.content}</p>
          <div style={styles.userMeta}>
            {message.crop && (
              <span style={styles.cropBadge}>
                <BookOpen size={11} /> {message.crop}
              </span>
            )}
            {message.location && (
              <span style={styles.locationBadge}>
                <MapPin size={11} /> {message.location}
              </span>
            )}
            <span style={styles.timeTag}>
              <Clock size={11} /> {message.timestamp}
            </span>
          </div>
        </div>
      </div>
    );
  }

  // Assistant Advisory
  const uncertainty = message.uncertainty || "high";
  const citations = message.citations || [];
  const retrievalScore = message.retrieval_score;

  return (
    <article id={`msg-assistant-${message.id}`} style={styles.assistantCard}>
      {/* Grounding & Evidence Header */}
      <div style={styles.groundingHeader}>
        {uncertainty === "none" || uncertainty === "low" ? (
          <div style={styles.groundedBadge}>
            <ShieldCheck size={16} color="#10b981" />
            <span>Grounded Agricultural Advisory</span>
            {retrievalScore && (
              <span style={styles.scoreTag}>Score: {(retrievalScore * 100).toFixed(1)}%</span>
            )}
          </div>
        ) : (
          <div style={styles.fallbackBadge}>
            <AlertTriangle size={16} color="#dc2626" />
            <span>High Uncertainty · Extension Advisory</span>
          </div>
        )}

        <div style={styles.evidenceCounter}>
          <span>{citations.length} Verified Evidence Chunks</span>
        </div>
      </div>

      {/* Advisory Text Content */}
      <div style={styles.answerBody}>
        {message.content.split("\n\n").map((para, i) => (
          <p key={i} style={styles.paragraph}>
            {para}
          </p>
        ))}
      </div>

      {/* High Uncertainty Warning Callout if applicable */}
      {uncertainty === "high" && (
        <div style={styles.warningCallout}>
          <AlertTriangle size={18} color="#dc2626" style={{ flexShrink: 0, marginTop: "2px" }} />
          <div>
            <strong>Krishi Bhavan & KVK Extension Advisory:</strong>
            <p style={{ marginTop: "0.2rem", fontSize: "0.82rem" }}>
              The verified agronomic references in our system did not yield sufficiently high-confidence
              evidence for this specific inquiry. Please verify dosages and treatment regimens with your
              local Krishi Bhavan or Krishi Vigyan Kendra (KVK) officer before field application.
            </p>
          </div>
        </div>
      )}

      {/* Verified Citations Shelf */}
      {citations.length > 0 && (
        <section style={styles.citationsSection}>
          <div style={styles.citationsTitle}>
            <FileText size={14} color="#0f614b" />
            <span>Verified Source Provenance (Click to Inspect Excerpt):</span>
          </div>
          <div style={styles.citationsGrid}>
            {citations.map((c, idx) => (
              <button
                key={idx}
                id={`btn-citation-${idx}`}
                onClick={() => onInspectCitation(c)}
                style={styles.citationPill}
                title={`Inspect citation: ${c.document_title}`}
              >
                <span style={styles.citationIndex}>[{idx + 1}]</span>
                <div style={styles.citationTextCol}>
                  <strong style={styles.citationDoc}>{c.document_title}</strong>
                  <span style={styles.citationPage}>
                    {c.page_number ? `Page ${c.page_number}` : "Manual"} · {c.publisher}
                  </span>
                </div>
              </button>
            ))}
          </div>
        </section>
      )}

      {/* Feedback Bar */}
      <div style={styles.feedbackBar}>
        <div style={styles.ratingPrompt}>Was this advisory helpful?</div>
        <div style={styles.starsGroup}>
          {[1, 2, 3, 4, 5].map((s) => (
            <button
              key={s}
              id={`star-${s}-${message.id}`}
              onClick={() => handleRate(s)}
              disabled={ratingSubmitted}
              style={{
                ...styles.starBtn,
                color: rating && rating >= s ? "#f59e0b" : "var(--border-strong)",
              }}
              aria-label={`Rate ${s} out of 5 stars`}
            >
              <Star size={16} fill={rating && rating >= s ? "#f59e0b" : "transparent"} />
            </button>
          ))}
        </div>
        {ratingSubmitted && (
          <div style={styles.ratingThanks}>
            <CheckCircle size={14} color="#10b981" />
            <span>Thank you for your feedback!</span>
          </div>
        )}
      </div>
    </article>
  );
};

const styles: Record<string, React.CSSProperties> = {
  userContainer: {
    display: "flex",
    justifyContent: "flex-end",
    marginBottom: "1rem",
  },
  userBubble: {
    maxWidth: "80%",
    backgroundColor: "var(--emerald-700)",
    color: "#ffffff",
    padding: "0.85rem 1.25rem",
    borderRadius: "16px 16px 4px 16px",
    boxShadow: "var(--shadow-sm)",
  },
  userText: {
    fontSize: "0.94rem",
    lineHeight: 1.45,
    fontWeight: 500,
  },
  userMeta: {
    display: "flex",
    alignItems: "center",
    gap: "0.6rem",
    marginTop: "0.5rem",
    paddingTop: "0.4rem",
    borderTop: "1px solid rgba(255, 255, 255, 0.2)",
    fontSize: "0.72rem",
    opacity: 0.9,
  },
  cropBadge: {
    display: "flex",
    alignItems: "center",
    gap: "0.25rem",
    backgroundColor: "rgba(255, 255, 255, 0.2)",
    padding: "0.15rem 0.45rem",
    borderRadius: "4px",
    fontWeight: 600,
  },
  locationBadge: {
    display: "flex",
    alignItems: "center",
    gap: "0.25rem",
    backgroundColor: "rgba(255, 255, 255, 0.2)",
    padding: "0.15rem 0.45rem",
    borderRadius: "4px",
  },
  timeTag: {
    display: "flex",
    alignItems: "center",
    gap: "0.25rem",
    marginLeft: "auto",
  },
  assistantCard: {
    backgroundColor: "var(--bg-surface)",
    border: "1px solid var(--border-subtle)",
    borderRadius: "16px",
    padding: "1.25rem 1.5rem",
    boxShadow: "var(--shadow-md)",
    marginBottom: "1.5rem",
    display: "flex",
    flexDirection: "column",
    gap: "0.9rem",
  },
  groundingHeader: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    borderBottom: "1px solid var(--border-subtle)",
    paddingBottom: "0.65rem",
  },
  groundedBadge: {
    display: "flex",
    alignItems: "center",
    gap: "0.45rem",
    color: "var(--emerald-600)",
    fontSize: "0.82rem",
    fontWeight: 700,
  },
  fallbackBadge: {
    display: "flex",
    alignItems: "center",
    gap: "0.45rem",
    color: "var(--danger-600)",
    fontSize: "0.82rem",
    fontWeight: 700,
  },
  scoreTag: {
    backgroundColor: "var(--emerald-50)",
    color: "var(--emerald-700)",
    padding: "0.15rem 0.45rem",
    borderRadius: "4px",
    fontSize: "0.72rem",
    fontFamily: "var(--font-mono)",
    fontWeight: 600,
  },
  evidenceCounter: {
    fontSize: "0.74rem",
    color: "var(--text-faint)",
    fontWeight: 500,
  },
  answerBody: {
    display: "flex",
    flexDirection: "column",
    gap: "0.65rem",
  },
  paragraph: {
    fontSize: "0.93rem",
    color: "var(--text-main)",
    lineHeight: 1.6,
  },
  warningCallout: {
    display: "flex",
    gap: "0.75rem",
    backgroundColor: "var(--danger-50)",
    border: "1px solid var(--danger-100)",
    color: "var(--danger-600)",
    padding: "0.85rem 1rem",
    borderRadius: "10px",
  },
  citationsSection: {
    marginTop: "0.4rem",
    borderTop: "1px dashed var(--border-subtle)",
    paddingTop: "0.75rem",
  },
  citationsTitle: {
    display: "flex",
    alignItems: "center",
    gap: "0.4rem",
    fontSize: "0.76rem",
    fontWeight: 700,
    color: "var(--emerald-700)",
    textTransform: "uppercase",
    letterSpacing: "0.04em",
    marginBottom: "0.55rem",
  },
  citationsGrid: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fill, minmax(240px, 1fr))",
    gap: "0.6rem",
  },
  citationPill: {
    display: "flex",
    alignItems: "flex-start",
    gap: "0.5rem",
    padding: "0.55rem 0.75rem",
    borderRadius: "8px",
    border: "1px solid var(--border-strong)",
    backgroundColor: "var(--bg-elevated)",
    cursor: "pointer",
    textAlign: "left",
    transition: "all 0.2s ease",
  },
  citationIndex: {
    backgroundColor: "var(--emerald-600)",
    color: "#ffffff",
    fontWeight: 700,
    fontSize: "0.72rem",
    padding: "0.1rem 0.35rem",
    borderRadius: "4px",
  },
  citationTextCol: {
    display: "flex",
    flexDirection: "column",
    overflow: "hidden",
  },
  citationDoc: {
    fontSize: "0.8rem",
    color: "var(--text-main)",
    whiteSpace: "nowrap",
    overflow: "hidden",
    textOverflow: "ellipsis",
  },
  citationPage: {
    fontSize: "0.7rem",
    color: "var(--text-muted)",
    marginTop: "0.15rem",
  },
  feedbackBar: {
    display: "flex",
    alignItems: "center",
    gap: "0.75rem",
    borderTop: "1px solid var(--border-subtle)",
    paddingTop: "0.6rem",
    marginTop: "0.2rem",
  },
  ratingPrompt: {
    fontSize: "0.78rem",
    color: "var(--text-muted)",
    fontWeight: 500,
  },
  starsGroup: {
    display: "flex",
    gap: "0.2rem",
  },
  starBtn: {
    border: "none",
    background: "transparent",
    cursor: "pointer",
    padding: "0.15rem",
  },
  ratingThanks: {
    display: "flex",
    alignItems: "center",
    gap: "0.35rem",
    fontSize: "0.76rem",
    color: "var(--emerald-600)",
    fontWeight: 600,
    marginLeft: "0.5rem",
  },
};
