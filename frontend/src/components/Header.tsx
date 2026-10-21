"use client";

import React from "react";
import { Sprout, Database, Activity, Moon, Sun, ShieldCheck, AlertCircle } from "lucide-react";
import { ReadinessResponse } from "../types";

interface HeaderProps {
  activeTab: "chat" | "ingestion" | "diagnostics";
  setActiveTab: (tab: "chat" | "ingestion" | "diagnostics") => void;
  readiness: ReadinessResponse | null;
  theme: "light" | "dark";
  toggleTheme: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  activeTab,
  setActiveTab,
  readiness,
  theme,
  toggleTheme,
}) => {
  const isReady = readiness?.status === "ready";
  const vectorCount = readiness?.vector_count || 0;

  return (
    <header id="app-header" style={styles.header}>
      <div style={styles.branding}>
        <div style={styles.logoBadge}>
          <Sprout size={24} color="#ffffff" />
        </div>
        <div>
          <div style={styles.titleRow}>
            <h1 style={styles.title}>KrishiRAG</h1>
            <span style={styles.badgeSih}>SIH25076</span>
            <span style={styles.badgeGov}>Govt. of Kerala</span>
          </div>
          <p style={styles.subtitle}>
            AI-Based Farmer Query Support & Advisory System · Grounded in ICAR / TNAU Guides
          </p>
        </div>
      </div>

      <nav style={styles.navRow}>
        <div style={styles.tabGroup}>
          <button
            id="tab-chat"
            onClick={() => setActiveTab("chat")}
            style={{
              ...styles.tabButton,
              ...(activeTab === "chat" ? styles.tabButtonActive : {}),
            }}
          >
            <Sprout size={16} />
            <span>Farmer Advisory</span>
          </button>
          <button
            id="tab-ingestion"
            onClick={() => setActiveTab("ingestion")}
            style={{
              ...styles.tabButton,
              ...(activeTab === "ingestion" ? styles.tabButtonActive : {}),
            }}
          >
            <Database size={16} />
            <span>Knowledge Ingestion</span>
          </button>
          <button
            id="tab-diagnostics"
            onClick={() => setActiveTab("diagnostics")}
            style={{
              ...styles.tabButton,
              ...(activeTab === "diagnostics" ? styles.tabButtonActive : {}),
            }}
          >
            <Activity size={16} />
            <span>Diagnostics</span>
          </button>
        </div>

        <div style={styles.statusPill}>
          {isReady ? (
            <>
              <ShieldCheck size={16} color="#10b981" />
              <span style={styles.statusText}>
                Active · <strong>{vectorCount}</strong> Chunks
              </span>
            </>
          ) : (
            <>
              <AlertCircle size={16} color="#f59e0b" />
              <span style={styles.statusText}>Checking KB...</span>
            </>
          )}
        </div>

        <button
          id="btn-toggle-theme"
          onClick={toggleTheme}
          style={styles.themeToggle}
          title={theme === "light" ? "Switch to Dark Mode" : "Switch to Light Mode"}
          aria-label="Toggle visual theme"
        >
          {theme === "light" ? <Moon size={18} /> : <Sun size={18} />}
        </button>
      </nav>
    </header>
  );
};

const styles: Record<string, React.CSSProperties> = {
  header: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    padding: "0.85rem 2rem",
    backgroundColor: "var(--bg-surface)",
    borderBottom: "1px solid var(--border-subtle)",
    boxShadow: "var(--shadow-sm)",
    position: "sticky",
    top: 0,
    zIndex: 50,
    backdropFilter: "blur(12px)",
  },
  branding: {
    display: "flex",
    alignItems: "center",
    gap: "0.9rem",
  },
  logoBadge: {
    width: "42px",
    height: "42px",
    borderRadius: "10px",
    background: "linear-gradient(135deg, var(--emerald-700), var(--emerald-500))",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    boxShadow: "0 4px 12px rgba(16, 185, 129, 0.3)",
  },
  titleRow: {
    display: "flex",
    alignItems: "center",
    gap: "0.6rem",
  },
  title: {
    fontSize: "1.35rem",
    fontWeight: 700,
    fontFamily: "var(--font-display)",
    color: "var(--text-main)",
    letterSpacing: "-0.02em",
  },
  badgeSih: {
    backgroundColor: "var(--emerald-50)",
    color: "var(--emerald-700)",
    border: "1px solid var(--emerald-400)",
    padding: "0.15rem 0.5rem",
    borderRadius: "6px",
    fontSize: "0.72rem",
    fontWeight: 700,
    letterSpacing: "0.03em",
  },
  badgeGov: {
    backgroundColor: "var(--gold-100)",
    color: "var(--gold-600)",
    border: "1px solid var(--gold-500)",
    padding: "0.15rem 0.5rem",
    borderRadius: "6px",
    fontSize: "0.72rem",
    fontWeight: 600,
  },
  subtitle: {
    fontSize: "0.78rem",
    color: "var(--text-muted)",
    marginTop: "0.15rem",
  },
  navRow: {
    display: "flex",
    alignItems: "center",
    gap: "1rem",
  },
  tabGroup: {
    display: "flex",
    backgroundColor: "var(--bg-elevated)",
    borderRadius: "10px",
    padding: "0.25rem",
    border: "1px solid var(--border-subtle)",
  },
  tabButton: {
    display: "flex",
    alignItems: "center",
    gap: "0.45rem",
    padding: "0.45rem 0.9rem",
    borderRadius: "8px",
    border: "none",
    backgroundColor: "transparent",
    color: "var(--text-muted)",
    fontSize: "0.85rem",
    fontWeight: 600,
    cursor: "pointer",
    transition: "all 0.2s ease",
  },
  tabButtonActive: {
    backgroundColor: "var(--bg-surface)",
    color: "var(--emerald-700)",
    boxShadow: "var(--shadow-sm)",
  },
  statusPill: {
    display: "flex",
    alignItems: "center",
    gap: "0.45rem",
    padding: "0.4rem 0.8rem",
    borderRadius: "9999px",
    backgroundColor: "var(--bg-elevated)",
    border: "1px solid var(--border-subtle)",
    fontSize: "0.78rem",
  },
  statusText: {
    color: "var(--text-muted)",
  },
  themeToggle: {
    width: "36px",
    height: "36px",
    borderRadius: "9px",
    border: "1px solid var(--border-subtle)",
    backgroundColor: "var(--bg-surface)",
    color: "var(--text-main)",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    cursor: "pointer",
    transition: "all 0.2s ease",
  },
};
