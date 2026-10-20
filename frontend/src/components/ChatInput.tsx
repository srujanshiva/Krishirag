"use client";

import React, { useState } from "react";
import { Send, MapPin, Sparkles, Loader2 } from "lucide-react";

interface ChatInputProps {
  onSend: (question: string, crop?: string, location?: string) => void;
  isLoading: boolean;
}

const KERALA_DISTRICTS = [
  "Palakkad",
  "Thrissur",
  "Alappuzha",
  "Wayanad",
  "Idukki",
  "Kottayam",
  "Ernakulam",
  "Malappuram",
  "Kozhikode",
  "Kannur",
  "Kasaragod",
  "Kollam",
  "Pathanamthitta",
  "Thiruvananthapuram",
];

const CROPS = [
  "Rice (Paddy)",
  "Coconut",
  "Black Pepper",
  "Banana",
  "Rubber",
  "Cardamom",
  "Tapioca",
  "Vegetables",
];

const SUGGESTED_PROMPTS = [
  { text: "What is the recommended nitrogen fertilizer schedule for transplanted rice?", crop: "Rice (Paddy)" },
  { text: "How to identify and control blast disease (Magnaporthe oryzae) in paddy?", crop: "Rice (Paddy)" },
  { text: "What is the optimum seedling age for SRI vs conventional paddy transplanting?", crop: "Rice (Paddy)" },
  { text: "What are the soil application rates for zinc sulphate in deficient soils?", crop: "Rice (Paddy)" },
];

export const ChatInput: React.FC<ChatInputProps> = ({ onSend, isLoading }) => {
  const [question, setQuestion] = useState("");
  const [selectedCrop, setSelectedCrop] = useState<string>("Rice (Paddy)");
  const [selectedLocation, setSelectedLocation] = useState<string>("Palakkad");

  const handleSubmit = (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!question.trim() || isLoading) return;
    onSend(question.trim(), selectedCrop, selectedLocation);
    setQuestion("");
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const handleApplySuggestion = (promptText: string, cropName: string) => {
    setQuestion(promptText);
    setSelectedCrop(cropName);
  };

  return (
    <div style={styles.container}>
      {/* Suggestions Chips */}
      <div style={styles.suggestionsRow}>
        <div style={styles.suggestionHeader}>
          <Sparkles size={13} color="#10b981" />
          <span style={styles.suggestionTitle}>Verified Agronomic Inquiries:</span>
        </div>
        <div style={styles.chipScroller}>
          {SUGGESTED_PROMPTS.map((item, idx) => (
            <button
              key={idx}
              id={`btn-suggestion-${idx}`}
              type="button"
              onClick={() => handleApplySuggestion(item.text, item.crop)}
              style={styles.suggestionChip}
            >
              {item.text}
            </button>
          ))}
        </div>
      </div>

      <form id="chat-input-form" onSubmit={handleSubmit} style={styles.formCard}>
        {/* Context Controls: Crop & District */}
        <div style={styles.contextRow}>
          <div style={styles.contextItem}>
            <label htmlFor="select-crop" style={styles.contextLabel}>
              Target Crop:
            </label>
            <select
              id="select-crop"
              value={selectedCrop}
              onChange={(e) => setSelectedCrop(e.target.value)}
              style={styles.select}
            >
              <option value="">All Crops</option>
              {CROPS.map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </select>
          </div>

          <div style={styles.contextItem}>
            <label htmlFor="select-location" style={styles.contextLabel}>
              <MapPin size={13} style={{ display: "inline", marginRight: "3px" }} />
              Kerala District:
            </label>
            <select
              id="select-location"
              value={selectedLocation}
              onChange={(e) => setSelectedLocation(e.target.value)}
              style={styles.select}
            >
              <option value="">All Regions</option>
              {KERALA_DISTRICTS.map((d) => (
                <option key={d} value={d}>
                  {d}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Input Textarea & Send Button */}
        <div style={styles.inputRow}>
          <textarea
            id="input-farmer-question"
            rows={2}
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask your agronomic question (e.g. fertilizer dose, disease identification, nursery management)..."
            style={styles.textarea}
            disabled={isLoading}
          />
          <button
            id="btn-submit-question"
            type="submit"
            disabled={!question.trim() || isLoading}
            style={{
              ...styles.sendButton,
              ...(!question.trim() || isLoading ? styles.sendButtonDisabled : {}),
            }}
            aria-label="Send query"
          >
            {isLoading ? (
              <Loader2 size={18} style={{ animation: "spin 1s linear infinite" }} />
            ) : (
              <Send size={18} />
            )}
            <span style={styles.sendButtonText}>{isLoading ? "Grounded Reasoning..." : "Advise"}</span>
          </button>
        </div>
      </form>
    </div>
  );
};

const styles: Record<string, React.CSSProperties> = {
  container: {
    display: "flex",
    flexDirection: "column",
    gap: "0.6rem",
    padding: "0.5rem 0",
  },
  suggestionsRow: {
    display: "flex",
    flexDirection: "column",
    gap: "0.4rem",
  },
  suggestionHeader: {
    display: "flex",
    alignItems: "center",
    gap: "0.4rem",
  },
  suggestionTitle: {
    fontSize: "0.74rem",
    fontWeight: 600,
    color: "var(--text-faint)",
    textTransform: "uppercase",
    letterSpacing: "0.05em",
  },
  chipScroller: {
    display: "flex",
    gap: "0.5rem",
    overflowX: "auto",
    paddingBottom: "0.2rem",
  },
  suggestionChip: {
    whiteSpace: "nowrap",
    backgroundColor: "var(--bg-card)",
    border: "1px solid var(--border-subtle)",
    color: "var(--text-muted)",
    padding: "0.35rem 0.75rem",
    borderRadius: "9999px",
    fontSize: "0.76rem",
    cursor: "pointer",
    transition: "all 0.15s ease",
  },
  formCard: {
    backgroundColor: "var(--bg-surface)",
    border: "1px solid var(--border-strong)",
    borderRadius: "14px",
    padding: "0.85rem",
    boxShadow: "var(--shadow-md)",
    display: "flex",
    flexDirection: "column",
    gap: "0.65rem",
  },
  contextRow: {
    display: "flex",
    alignItems: "center",
    gap: "1.25rem",
    borderBottom: "1px solid var(--border-subtle)",
    paddingBottom: "0.55rem",
  },
  contextItem: {
    display: "flex",
    alignItems: "center",
    gap: "0.4rem",
  },
  contextLabel: {
    fontSize: "0.76rem",
    fontWeight: 600,
    color: "var(--text-muted)",
  },
  select: {
    backgroundColor: "var(--bg-elevated)",
    border: "1px solid var(--border-subtle)",
    borderRadius: "6px",
    padding: "0.25rem 0.55rem",
    fontSize: "0.78rem",
    color: "var(--text-main)",
    fontWeight: 500,
    cursor: "pointer",
    outline: "none",
  },
  inputRow: {
    display: "flex",
    alignItems: "flex-end",
    gap: "0.75rem",
  },
  textarea: {
    flex: 1,
    border: "none",
    outline: "none",
    resize: "none",
    backgroundColor: "transparent",
    color: "var(--text-main)",
    fontFamily: "var(--font-sans)",
    fontSize: "0.92rem",
    lineHeight: 1.45,
  },
  sendButton: {
    display: "flex",
    alignItems: "center",
    gap: "0.45rem",
    backgroundColor: "var(--emerald-600)",
    color: "#ffffff",
    border: "none",
    borderRadius: "10px",
    padding: "0.65rem 1.15rem",
    fontSize: "0.88rem",
    fontWeight: 600,
    cursor: "pointer",
    boxShadow: "0 2px 8px rgba(16, 185, 129, 0.3)",
    transition: "all 0.2s ease",
  },
  sendButtonDisabled: {
    backgroundColor: "var(--border-strong)",
    color: "var(--text-faint)",
    boxShadow: "none",
    cursor: "not-allowed",
  },
  sendButtonText: {
    fontWeight: 600,
  },
};
