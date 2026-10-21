"use client";

import React, { useState, useEffect, useRef } from "react";
import { Send, MapPin, Sparkles, Loader2, Mic, MicOff, Globe, AlertCircle, Camera, X, ImageIcon } from "lucide-react";

interface ChatInputProps {
  onSend: (question: string, crop?: string, location?: string, imageData?: string) => void;
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

const SPEECH_LANGUAGES = [
  { code: "en-IN", label: "English (India)" },
  { code: "ml-IN", label: "മലയാളം (Malayalam)" },
  { code: "ta-IN", label: "தமிழ் (Tamil)" },
  { code: "te-IN", label: "తెలుగు (Telugu)" },
  { code: "hi-IN", label: "हिन्दी (Hindi)" },
];

const SUGGESTED_PROMPTS = [
  { text: "How many bags of fertilizer for 2 acres of rice?", crop: "Rice (Paddy)" },
  { text: "How to identify and control blast disease (Magnaporthe oryzae) in paddy?", crop: "Rice (Paddy)" },
  { text: "What is the recommended fertilizer dosage for 50 coconut palms?", crop: "Coconut" },
  { text: "Can I spray Tricyclazole on paddy 8 days before harvest?", crop: "Rice (Paddy)" },
  { text: "What are the soil application rates for zinc sulphate in deficient soils?", crop: "Rice (Paddy)" },
];

export const ChatInput: React.FC<ChatInputProps> = ({ onSend, isLoading }) => {
  const [question, setQuestion] = useState("");
  const [selectedCrop, setSelectedCrop] = useState<string>("Rice (Paddy)");
  const [selectedLocation, setSelectedLocation] = useState<string>("Palakkad");
  const [isListening, setIsListening] = useState(false);
  const [speechLanguage, setSpeechLanguage] = useState("en-IN");
  const [speechSupported, setSpeechSupported] = useState(false);
  const [speechError, setSpeechError] = useState<string | null>(null);
  const [selectedImage, setSelectedImage] = useState<string | null>(null);
  const recognitionRef = useRef<any>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  useEffect(() => {
    if (typeof window !== "undefined") {
      const SpeechRecognition =
        (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
      if (SpeechRecognition) {
        setSpeechSupported(true);
      }
    }
  }, []);

  const toggleListening = () => {
    if (isListening) {
      if (recognitionRef.current) {
        try {
          recognitionRef.current.stop();
        } catch {
          // ignore
        }
      }
      setIsListening(false);
      return;
    }

    setSpeechError(null);
    if (typeof window === "undefined") return;

    const SpeechRecognition =
      (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SpeechRecognition) {
      setSpeechError("Speech recognition is not supported in this browser. Please use Chrome/Edge or type your question.");
      return;
    }

    try {
      const recognition = new SpeechRecognition();
      recognition.lang = speechLanguage;
      recognition.continuous = false;
      recognition.interimResults = true;

      recognition.onstart = () => {
        setIsListening(true);
      };

      recognition.onresult = (event: any) => {
        let currentTranscript = "";
        for (let i = event.resultIndex; i < event.results.length; i++) {
          currentTranscript += event.results[i][0].transcript;
        }
        if (currentTranscript) {
          setQuestion(currentTranscript);
        }
      };

      recognition.onerror = (event: any) => {
        console.warn("Speech recognition error:", event.error);
        if (event.error === "not-allowed") {
          setSpeechError("Microphone permission denied. Please allow microphone access in your browser settings.");
        } else if (event.error !== "no-speech") {
          setSpeechError(`Voice input error: ${event.error}`);
        }
        setIsListening(false);
      };

      recognition.onend = () => {
        setIsListening(false);
      };

      recognitionRef.current = recognition;
      recognition.start();
    } catch (err: any) {
      setSpeechError(err?.message || "Could not start voice recognition.");
      setIsListening(false);
    }
  };

  const handleImageSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    if (!file.type.startsWith("image/")) {
      alert("Please select a valid image file (JPEG, PNG, WebP).");
      return;
    }
    const reader = new FileReader();
    reader.onload = (uploadEvent) => {
      const b64 = uploadEvent.target?.result as string;
      setSelectedImage(b64);
    };
    reader.readAsDataURL(file);
  };

  const handleRemoveImage = () => {
    setSelectedImage(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  const handleSubmit = (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    const effectiveQ = question.trim() || (selectedImage ? "Please diagnose this crop leaf image for pests, lesions, or diseases." : "");
    if (!effectiveQ || isLoading) return;
    onSend(effectiveQ, selectedCrop, selectedLocation, selectedImage || undefined);
    setQuestion("");
    setSelectedImage(null);
    if (fileInputRef.current) fileInputRef.current.value = "";
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

          <div style={styles.contextItem}>
            <label htmlFor="select-speech-lang" style={styles.contextLabel}>
              <Globe size={13} style={{ display: "inline", marginRight: "3px" }} />
              Voice Input Lang:
            </label>
            <select
              id="select-speech-lang"
              value={speechLanguage}
              onChange={(e) => setSpeechLanguage(e.target.value)}
              style={styles.select}
              disabled={isListening}
              title="Select speech recognition language"
            >
              {SPEECH_LANGUAGES.map((l) => (
                <option key={l.code} value={l.code}>
                  {l.label}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Hidden File Input for Leaf Photo */}
        <input
          type="file"
          id="input-leaf-file"
          ref={fileInputRef}
          accept="image/*"
          onChange={handleImageSelect}
          style={{ display: "none" }}
        />

        {/* Selected Leaf Image Preview Bar */}
        {selectedImage && (
          <div style={styles.imagePreviewRow}>
            <div style={styles.thumbnailWrapper}>
              <img src={selectedImage} alt="Leaf preview" style={styles.thumbnailImg} />
              <button
                type="button"
                id="btn-remove-leaf-image"
                onClick={handleRemoveImage}
                style={styles.removeImageBtn}
                title="Remove attached photo"
                aria-label="Remove image"
              >
                <X size={12} color="#ffffff" />
              </button>
            </div>
            <div style={styles.imagePreviewTextWrap}>
              <span style={styles.imagePreviewTitle}>Leaf Diagnostic Image Attached</span>
              <span style={styles.imagePreviewSubtitle}>KrishiRAG will perform lesion recognition & grounded POP retrieval</span>
            </div>
          </div>
        )}

        {/* Input Textarea, Voice Mic, Camera & Send Button */}
        <div style={styles.inputRow}>
          <textarea
            id="input-farmer-question"
            rows={2}
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={
              isListening
                ? "🎙️ Listening... Speak your agricultural question now..."
                : selectedImage
                ? "Describe visible symptoms or click 'Advise' to run diagnostic screening..."
                : "Ask your agronomic question (type, voice, or attach leaf photo)..."
            }
            style={{
              ...styles.textarea,
              ...(isListening ? styles.textareaListening : {}),
            }}
            disabled={isLoading}
          />

          {/* Leaf Photo Upload Button */}
          <button
            id="btn-upload-leaf-image"
            type="button"
            onClick={() => fileInputRef.current?.click()}
            disabled={isLoading}
            style={{
              ...styles.cameraButton,
              ...(selectedImage ? styles.cameraButtonActive : {}),
            }}
            title={selectedImage ? "Change attached leaf image" : "Upload or capture leaf photo for visual pest/disease diagnosis"}
            aria-label="Upload leaf image"
          >
            <Camera size={18} color={selectedImage ? "#10b981" : "var(--emerald-600)"} />
          </button>

          {/* Voice Input Microphone Button */}
          <button
            id="btn-voice-input"
            type="button"
            onClick={toggleListening}
            disabled={isLoading}
            style={{
              ...styles.micButton,
              ...(isListening ? styles.micButtonListening : {}),
            }}
            title={
              isListening
                ? "Listening... Click to finish speaking"
                : "Click to speak your inquiry via microphone (Web Speech API)"
            }
            aria-label="Voice input microphone"
          >
            {isListening ? (
              <>
                <MicOff size={18} color="#dc2626" />
                <span style={styles.micListeningText}>Listening...</span>
              </>
            ) : (
              <Mic size={18} color="var(--emerald-600)" />
            )}
          </button>

          <button
            id="btn-submit-question"
            type="submit"
            disabled={(!question.trim() && !selectedImage) || isLoading}
            style={{
              ...styles.sendButton,
              ...((!question.trim() && !selectedImage) || isLoading ? styles.sendButtonDisabled : {}),
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

        {speechError && (
          <div id="speech-error-banner" style={styles.speechErrorRow}>
            <AlertCircle size={13} color="#dc2626" style={{ flexShrink: 0 }} />
            <span>{speechError}</span>
          </div>
        )}
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
  textareaListening: {
    backgroundColor: "rgba(239, 68, 68, 0.05)",
    borderRadius: "8px",
    padding: "0.25rem",
  },
  micButton: {
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    gap: "0.35rem",
    backgroundColor: "var(--bg-elevated)",
    border: "1px solid var(--border-strong)",
    borderRadius: "10px",
    padding: "0.65rem 0.85rem",
    color: "var(--emerald-600)",
    cursor: "pointer",
    transition: "all 0.2s ease",
  },
  micButtonListening: {
    backgroundColor: "rgba(220, 38, 38, 0.12)",
    borderColor: "#dc2626",
    color: "#dc2626",
    boxShadow: "0 0 10px rgba(220, 38, 38, 0.35)",
  },
  micListeningText: {
    fontSize: "0.78rem",
    fontWeight: 600,
    color: "#dc2626",
  },
  speechErrorRow: {
    display: "flex",
    alignItems: "center",
    gap: "0.4rem",
    fontSize: "0.74rem",
    color: "#dc2626",
    backgroundColor: "var(--danger-50)",
    border: "1px solid var(--danger-100)",
    padding: "0.35rem 0.65rem",
    borderRadius: "6px",
    marginTop: "0.2rem",
  },
  cameraButton: {
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: "var(--bg-elevated)",
    border: "1px solid var(--border-strong)",
    borderRadius: "10px",
    padding: "0.65rem 0.75rem",
    color: "var(--emerald-600)",
    cursor: "pointer",
    transition: "all 0.2s ease",
  },
  cameraButtonActive: {
    backgroundColor: "rgba(16, 185, 129, 0.12)",
    borderColor: "#10b981",
    color: "#10b981",
  },
  imagePreviewRow: {
    display: "flex",
    alignItems: "center",
    gap: "0.65rem",
    padding: "0.45rem 0.75rem",
    backgroundColor: "rgba(16, 185, 129, 0.08)",
    border: "1px solid rgba(16, 185, 129, 0.25)",
    borderRadius: "8px",
    marginBottom: "0.45rem",
  },
  thumbnailWrapper: {
    position: "relative",
    width: "44px",
    height: "44px",
    flexShrink: 0,
  },
  thumbnailImg: {
    width: "100%",
    height: "100%",
    objectFit: "cover",
    borderRadius: "6px",
    border: "1px solid var(--border-strong)",
  },
  removeImageBtn: {
    position: "absolute",
    top: "-5px",
    right: "-5px",
    width: "18px",
    height: "18px",
    borderRadius: "50%",
    backgroundColor: "#dc2626",
    border: "none",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    cursor: "pointer",
    boxShadow: "0 1px 3px rgba(0,0,0,0.3)",
  },
  imagePreviewTextWrap: {
    display: "flex",
    flexDirection: "column",
    gap: "0.1rem",
  },
  imagePreviewTitle: {
    fontSize: "0.78rem",
    fontWeight: 700,
    color: "#065f46",
  },
  imagePreviewSubtitle: {
    fontSize: "0.7rem",
    color: "var(--foreground-muted)",
  },
};

