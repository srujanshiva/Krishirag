"use client";

import React, { useState, useEffect } from "react";
import {
  Sprout,
  ShieldCheck,
  BookOpen,
  AlertTriangle,
  RotateCcw,
  Sparkles,
  HelpCircle,
  FileText,
  Calculator,
  ArrowRight,
} from "lucide-react";
import { Header } from "../components/Header";
import { ChatInput } from "../components/ChatInput";
import { AnswerCard } from "../components/AnswerCard";
import { CitationInspector } from "../components/CitationInspector";
import { IngestionPortal } from "../components/IngestionPortal";
import { HealthDiagnostics } from "../components/HealthDiagnostics";
import { ErrorBanner } from "../components/ErrorBanner";
import { ChatMessage, Citation, ReadinessResponse } from "../types";
import { api, ApiError } from "../lib/api";

export default function Home() {
  const [activeTab, setActiveTab] = useState<"chat" | "ingestion" | "diagnostics">("chat");
  const [theme, setTheme] = useState<"light" | "dark">("light");
  const [readiness, setReadiness] = useState<ReadinessResponse | null>(null);

  // Advisory Dialogue State
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [activeCitation, setActiveCitation] = useState<Citation | null>(null);
  const [apiError, setApiError] = useState<Error | ApiError | null>(null);
  const [lastQuery, setLastQuery] = useState<{
    question: string;
    crop?: string;
    location?: string;
    imageData?: string;
  } | null>(null);

  // Sidebar Land Area Dosage Calculator State
  const [calcCrop, setCalcCrop] = useState("Rice");
  const [calcArea, setCalcArea] = useState("2");
  const [calcUnit, setCalcUnit] = useState("acre");


  // Poll readiness status once on load
  const checkReadiness = async () => {
    try {
      const r = await api.getReadiness();
      setReadiness(r);
    } catch (e) {
      console.warn("Backend readiness probe unreachable", e);
    }
  };

  useEffect(() => {
    checkReadiness();
  }, []);

  const toggleTheme = () => {
    const nextTheme = theme === "light" ? "dark" : "light";
    setTheme(nextTheme);
    document.documentElement.setAttribute("data-theme", nextTheme);
  };

  const getEstimatedBags = () => {
    const val = parseFloat(calcArea) || 0;
    if (val <= 0) return { urea: "0.0", dap: "0.0", mop: "0.0" };
    if (calcCrop === "Coconut") {
      return {
        urea: (val * 1.1 / 45).toFixed(1),
        dap: (val * 0.7 / 50).toFixed(1),
        mop: (val * 2.0 / 50).toFixed(1),
      };
    }
    let ha = val / 2.47105;
    if (calcUnit === "cent") ha = (val / 100) / 2.47105;
    else if (calcUnit === "guntha") ha = (val / 40) / 2.47105;
    else if (calcUnit === "hectare") ha = val;

    if (calcCrop === "Rice") {
      return {
        urea: (140 * ha / 45).toFixed(1),
        dap: (87 * ha / 50).toFixed(1),
        mop: (67 * ha / 50).toFixed(1),
      };
    }
    return {
      urea: (120 * ha / 45).toFixed(1),
      dap: (76 * ha / 50).toFixed(1),
      mop: (58 * ha / 50).toFixed(1),
    };
  };

  const handleSendQuery = async (
    question: string,
    crop?: string,
    location?: string,
    imageData?: string
  ) => {
    setApiError(null);
    setLastQuery({ question, crop, location, imageData });

    const userMessage: ChatMessage = {
      id: "temp-" + Date.now(),
      role: "user",
      content: question,
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      crop,
      location,
      image_data: imageData,
    };

    setMessages((prev) => [...prev, userMessage]);
    setIsLoading(true);

    try {
      const res = await api.sendQuery(question, conversationId, crop, location, imageData);

      if (!conversationId && res.conversation_id) {
        setConversationId(res.conversation_id);
      }

      const assistantMessage: ChatMessage = {
        id: res.message_id || "resp-" + Date.now(),
        role: "assistant",
        content: res.answer,
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        citations: res.citations,
        uncertainty: res.uncertainty,
        retrieval_score: res.retrieval_score,
        evidence_count: res.evidence_count,
        weather: res.weather,
        faithfulness: res.faithfulness,
        chemical_safety: res.chemical_safety,
        dosage_calculation: res.dosage_calculation,
        visual_diagnostic: res.visual_diagnostic,
      };

      setMessages((prev) => [...prev, assistantMessage]);
    } catch (err: unknown) {
      setApiError(err instanceof Error ? err : new Error("Unexpected error occurred"));
    } finally {
      setIsLoading(false);
    }
  };

  const handleResetSession = () => {
    setConversationId(null);
    setMessages([]);
    setApiError(null);
  };

  return (
    <div id="krishirag-app-root" style={styles.appContainer}>
      <Header
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        readiness={readiness}
        theme={theme}
        toggleTheme={toggleTheme}
      />

      <main style={styles.mainArea}>
        {/* TAB 1: FARMER ADVISORY CHAT */}
        {activeTab === "chat" && (
          <div style={styles.chatLayout}>
            {/* Left Sidebar */}
            <aside style={styles.sidebar}>
              <div style={styles.sidebarHeader}>
                <span style={styles.sidebarTitle}>Agronomic Workspace</span>
                <button
                  id="btn-new-advisory-session"
                  onClick={handleResetSession}
                  style={styles.newChatBtn}
                  title="Start fresh conversation"
                >
                  <RotateCcw size={13} />
                  <span>New Query Session</span>
                </button>
              </div>

              {/* Quick Land Area Fertilizer Calculator Tool */}
              <div style={styles.calculatorCard}>
                <div style={styles.calcTitleRow}>
                  <Calculator size={15} color="#15803d" />
                  <span style={styles.calcTitleText}>Land Area Fertilizer Tool</span>
                </div>
                <p style={styles.calcDesc}>
                  Convert farmer acreage to commercial fertilizer bags (Urea, DAP, MOP):
                </p>

                <div style={styles.calcInputRow}>
                  <select
                    id="select-calc-crop"
                    value={calcCrop}
                    onChange={(e) => {
                      setCalcCrop(e.target.value);
                      if (e.target.value === "Coconut") setCalcUnit("palms");
                      else if (calcUnit === "palms") setCalcUnit("acre");
                    }}
                    style={styles.calcSelect}
                  >
                    <option value="Rice">Rice (Paddy)</option>
                    <option value="Coconut">Coconut</option>
                    <option value="Black Pepper">Black Pepper</option>
                    <option value="Maize">Maize (Corn)</option>
                  </select>

                  <div style={styles.calcAreaInputWrap}>
                    <input
                      id="input-calc-area"
                      type="number"
                      min="0.1"
                      step="0.5"
                      value={calcArea}
                      onChange={(e) => setCalcArea(e.target.value)}
                      style={styles.calcNumberInput}
                    />
                    <select
                      id="select-calc-unit"
                      value={calcUnit}
                      onChange={(e) => setCalcUnit(e.target.value)}
                      style={styles.calcUnitSelect}
                    >
                      {calcCrop === "Coconut" ? (
                        <option value="palms">Palms</option>
                      ) : calcCrop === "Black Pepper" ? (
                        <>
                          <option value="vines">Vines</option>
                          <option value="acre">Acres</option>
                        </>
                      ) : (
                        <>
                          <option value="acre">Acres</option>
                          <option value="cent">Cents</option>
                          <option value="guntha">Gunthas</option>
                          <option value="hectare">Hectares</option>
                        </>
                      )}
                    </select>
                  </div>
                </div>

                {/* Instant Estimation Chips */}
                {(() => {
                  const est = getEstimatedBags();
                  return (
                    <div style={styles.calcResultsGrid}>
                      <div style={styles.calcResultPill}>
                        <span style={styles.calcPillLabel}>Urea (45kg):</span>
                        <strong style={styles.calcPillVal}>{est.urea} Bags</strong>
                      </div>
                      <div style={styles.calcResultPill}>
                        <span style={styles.calcPillLabel}>DAP (50kg):</span>
                        <strong style={styles.calcPillVal}>{est.dap} Bags</strong>
                      </div>
                      <div style={styles.calcResultPill}>
                        <span style={styles.calcPillLabel}>MOP (50kg):</span>
                        <strong style={styles.calcPillVal}>{est.mop} Bags</strong>
                      </div>
                    </div>
                  );
                })()}

                <button
                  type="button"
                  id="btn-apply-calculator-query"
                  onClick={() => {
                    const prompt = `How many bags of fertilizer do I need for ${calcArea} ${calcUnit} of ${calcCrop}?`;
                    handleSendQuery(prompt, calcCrop, "Palakkad");
                  }}
                  style={styles.calcAskBtn}
                  title="Query KrishiRAG for detailed application splits and chemical safety"
                >
                  <span>Get Official POP Schedule</span>
                  <ArrowRight size={13} />
                </button>
              </div>

              {/* Verified Sources Badge */}
              <div style={styles.sourceGuideCard}>
                <div style={styles.sourceGuideTitle}>
                  <BookOpen size={15} color="#10b981" />
                  <span>Knowledge Repositories</span>
                </div>
                <p style={styles.sourceGuideDesc}>
                  Advisories are synthesized strictly from vetted Indian agronomic manuals:
                </p>
                <ul style={styles.sourceList}>
                  <li style={styles.sourceItem}>TNAU Crop Production Guide (Rice)</li>
                  <li style={styles.sourceItem}>NFSM Ready Reckoner for Field Crops</li>
                  <li style={styles.sourceItem}>ICAR Rice Production Package</li>
                  <li style={styles.sourceItem}>Kerala Agricultural University (KAU)</li>
                </ul>
              </div>

              {/* Grounding Principles Callout */}
              <div style={styles.guardrailCard}>
                <div style={styles.guardrailTitle}>
                  <ShieldCheck size={15} color="#0f614b" />
                  <span>Safety & Honesty Standards</span>
                </div>
                <p style={styles.guardrailText}>
                  • Unretrieved citations are stripped automatically.
                  <br />
                  • If evidence is insufficient, system defers to your local <strong>Krishi Bhavan</strong>.
                  <br />
                  • Prompt injection attempts are quarantined.
                </p>
              </div>
            </aside>

            {/* Chat Content Panel */}
            <div style={styles.chatCenter}>
              <ErrorBanner
                error={apiError}
                onRetry={() => {
                  if (lastQuery) handleSendQuery(lastQuery.question, lastQuery.crop, lastQuery.location);
                }}
                onDismiss={() => setApiError(null)}
              />

              {/* Messages Scroll Area */}
              <div id="messages-scroll-feed" style={styles.messagesFeed}>
                {messages.length === 0 ? (
                  <div style={styles.welcomeHero}>
                    <div style={styles.heroBadge}>
                      <Sprout size={32} color="#10b981" />
                    </div>
                    <h2 style={styles.heroTitle}>Farmer Query Support & Advisory</h2>
                    <p style={styles.heroSubtitle}>
                      Ask questions regarding crop protection, nutrient schedules, nursery management,
                      and disease treatment with verifiable citations from agricultural university guides.
                    </p>

                    <div style={styles.featureGrid}>
                      <div style={styles.featureItem}>
                        <ShieldCheck size={20} color="#10b981" />
                        <div>
                          <strong>Zero Hallucinated Rates</strong>
                          <p>Fertilizer and pesticide rates must match verified university manuals.</p>
                        </div>
                      </div>
                      <div style={styles.featureItem}>
                        <FileText size={20} color="#0f614b" />
                        <div>
                          <strong>Inspectable Evidence</strong>
                          <p>Click any citation badge to view the original excerpt and page number.</p>
                        </div>
                      </div>
                      <div style={styles.featureItem}>
                        <AlertTriangle size={20} color="#d97706" />
                        <div>
                          <strong>Honest Uncertainty</strong>
                          <p>When verified data is absent, the system advises extension contact.</p>
                        </div>
                      </div>
                    </div>
                  </div>
                ) : (
                  messages.map((msg) => (
                    <AnswerCard
                      key={msg.id}
                      message={msg}
                      onInspectCitation={(c) => setActiveCitation(c)}
                    />
                  ))
                )}
              </div>

              {/* Bottom Input Area */}
              <ChatInput onSend={handleSendQuery} isLoading={isLoading} />
            </div>
          </div>
        )}

        {/* TAB 2: INGESTION PORTAL */}
        {activeTab === "ingestion" && <IngestionPortal />}

        {/* TAB 3: DIAGNOSTICS */}
        {activeTab === "diagnostics" && <HealthDiagnostics />}
      </main>

      {/* Citation Inspector Side Drawer */}
      <CitationInspector
        citation={activeCitation}
        onClose={() => setActiveCitation(null)}
      />
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  appContainer: {
    minHeight: "100vh",
    display: "flex",
    flexDirection: "column",
    backgroundColor: "var(--bg-main)",
  },
  mainArea: {
    flex: 1,
    maxWidth: "1400px",
    width: "100%",
    margin: "0 auto",
    padding: "1rem 1.5rem",
    display: "flex",
    flexDirection: "column",
  },
  chatLayout: {
    display: "grid",
    gridTemplateColumns: "300px 1fr",
    gap: "1.5rem",
    height: "calc(100vh - 105px)",
  },
  sidebar: {
    display: "flex",
    flexDirection: "column",
    gap: "1rem",
    backgroundColor: "var(--bg-surface)",
    border: "1px solid var(--border-subtle)",
    borderRadius: "14px",
    padding: "1.1rem",
    boxShadow: "var(--shadow-sm)",
    height: "100%",
    overflowY: "auto",
  },
  sidebarHeader: {
    display: "flex",
    flexDirection: "column",
    gap: "0.5rem",
    borderBottom: "1px solid var(--border-subtle)",
    paddingBottom: "0.75rem",
  },
  sidebarTitle: {
    fontSize: "0.82rem",
    fontWeight: 700,
    textTransform: "uppercase",
    letterSpacing: "0.05em",
    color: "var(--text-faint)",
  },
  newChatBtn: {
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    gap: "0.4rem",
    backgroundColor: "var(--bg-elevated)",
    border: "1px solid var(--border-subtle)",
    color: "var(--emerald-700)",
    padding: "0.45rem",
    borderRadius: "8px",
    fontSize: "0.8rem",
    fontWeight: 600,
    cursor: "pointer",
    transition: "all 0.15s ease",
  },
  sourceGuideCard: {
    backgroundColor: "var(--bg-elevated)",
    borderRadius: "10px",
    padding: "0.85rem",
    border: "1px solid var(--border-subtle)",
    display: "flex",
    flexDirection: "column",
    gap: "0.4rem",
  },
  sourceGuideTitle: {
    display: "flex",
    alignItems: "center",
    gap: "0.4rem",
    fontSize: "0.82rem",
    fontWeight: 700,
    color: "var(--text-main)",
  },
  sourceGuideDesc: {
    fontSize: "0.74rem",
    color: "var(--text-muted)",
    lineHeight: 1.4,
  },
  sourceList: {
    paddingLeft: "1.1rem",
    fontSize: "0.74rem",
    color: "var(--text-muted)",
    lineHeight: 1.5,
  },
  sourceItem: {
    marginBottom: "0.15rem",
  },
  guardrailCard: {
    backgroundColor: "var(--emerald-50)",
    borderRadius: "10px",
    padding: "0.85rem",
    border: "1px solid var(--emerald-400)",
    display: "flex",
    flexDirection: "column",
    gap: "0.4rem",
  },
  guardrailTitle: {
    display: "flex",
    alignItems: "center",
    gap: "0.4rem",
    fontSize: "0.82rem",
    fontWeight: 700,
    color: "var(--emerald-800)",
  },
  guardrailText: {
    fontSize: "0.73rem",
    color: "var(--emerald-900)",
    lineHeight: 1.45,
  },
  chatCenter: {
    display: "flex",
    flexDirection: "column",
    height: "100%",
    overflow: "hidden",
  },
  messagesFeed: {
    flex: 1,
    overflowY: "auto",
    paddingRight: "0.5rem",
    display: "flex",
    flexDirection: "column",
  },
  welcomeHero: {
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    textAlign: "center",
    margin: "auto",
    maxWidth: "680px",
    padding: "2rem 1rem",
  },
  heroBadge: {
    width: "64px",
    height: "64px",
    borderRadius: "16px",
    background: "var(--emerald-50)",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    marginBottom: "1rem",
    border: "1px solid var(--emerald-400)",
  },
  heroTitle: {
    fontSize: "1.65rem",
    fontWeight: 800,
    fontFamily: "var(--font-display)",
    color: "var(--text-main)",
    letterSpacing: "-0.02em",
    marginBottom: "0.5rem",
  },
  heroSubtitle: {
    fontSize: "0.92rem",
    color: "var(--text-muted)",
    lineHeight: 1.55,
    marginBottom: "1.75rem",
  },
  featureGrid: {
    display: "grid",
    gridTemplateColumns: "1fr",
    gap: "0.85rem",
    textAlign: "left",
    width: "100%",
  },
  featureItem: {
    display: "flex",
    alignItems: "flex-start",
    gap: "0.75rem",
    backgroundColor: "var(--bg-surface)",
    border: "1px solid var(--border-subtle)",
    borderRadius: "12px",
    padding: "0.85rem 1rem",
    boxShadow: "var(--shadow-sm)",
  },
  calculatorCard: {
    backgroundColor: "var(--bg-surface)",
    borderRadius: "10px",
    padding: "0.85rem",
    border: "1px solid var(--border-subtle)",
    display: "flex",
    flexDirection: "column",
    gap: "0.5rem",
    boxShadow: "var(--shadow-sm)",
  },
  calcTitleRow: {
    display: "flex",
    alignItems: "center",
    gap: "0.4rem",
  },
  calcTitleText: {
    fontSize: "0.82rem",
    fontWeight: 700,
    color: "var(--foreground)",
  },
  calcDesc: {
    fontSize: "0.72rem",
    color: "var(--foreground-muted)",
    lineHeight: 1.35,
    margin: 0,
  },
  calcInputRow: {
    display: "flex",
    flexDirection: "column",
    gap: "0.4rem",
  },
  calcSelect: {
    width: "100%",
    padding: "0.35rem 0.5rem",
    fontSize: "0.76rem",
    borderRadius: "6px",
    border: "1px solid var(--border-strong)",
    backgroundColor: "var(--bg-elevated)",
    color: "var(--foreground)",
  },
  calcAreaInputWrap: {
    display: "flex",
    gap: "0.35rem",
  },
  calcNumberInput: {
    width: "60px",
    padding: "0.35rem 0.45rem",
    fontSize: "0.76rem",
    borderRadius: "6px",
    border: "1px solid var(--border-strong)",
    backgroundColor: "var(--bg-elevated)",
    color: "var(--foreground)",
  },
  calcUnitSelect: {
    flex: 1,
    padding: "0.35rem 0.45rem",
    fontSize: "0.76rem",
    borderRadius: "6px",
    border: "1px solid var(--border-strong)",
    backgroundColor: "var(--bg-elevated)",
    color: "var(--foreground)",
  },
  calcResultsGrid: {
    display: "flex",
    flexDirection: "column",
    gap: "0.25rem",
    backgroundColor: "rgba(16, 185, 129, 0.06)",
    padding: "0.45rem 0.6rem",
    borderRadius: "6px",
    border: "1px solid rgba(16, 185, 129, 0.2)",
  },
  calcResultPill: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    fontSize: "0.72rem",
  },
  calcPillLabel: {
    color: "var(--foreground-muted)",
  },
  calcPillVal: {
    color: "#059669",
    fontWeight: 700,
  },
  calcAskBtn: {
    marginTop: "0.2rem",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    gap: "0.35rem",
    padding: "0.45rem 0.65rem",
    borderRadius: "6px",
    backgroundColor: "var(--emerald-600)",
    color: "#ffffff",
    border: "none",
    fontSize: "0.75rem",
    fontWeight: 600,
    cursor: "pointer",
    transition: "all 0.2s ease",
  },
};

