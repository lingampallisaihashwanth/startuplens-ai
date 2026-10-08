"use client";

import React, { useState, useCallback, useRef, useEffect, useMemo } from "react";
import { Sidebar } from "@/components/Sidebar";
import { AgentStatus, AgentStep } from "@/components/AgentStatus";
import { Composer } from "@/components/Composer";
import { ResearchReport } from "@/components/ResearchReport";
import { SuggestedPrompts } from "@/components/SuggestedPrompts";
import { ThemeToggle } from "@/components/ThemeToggle";
import { SettingsModal } from "@/components/SettingsModal";
import { SavedIdeasView } from "@/components/SavedIdeasView";
import { HistoryView } from "@/components/HistoryView";
import { ResearchTrackerView } from "@/components/ResearchTrackerView";
import { IntelligenceRail } from "@/components/IntelligenceRail";
import { IntelligenceNetworkVisual } from "@/components/IntelligenceNetworkVisual";
import {
  analyzeTopic,
  getResearchById,
  getModels,
  createTracker,
  saveIdea,
  getSavedIdeas,
  deleteSavedIdea,
  AnalyzeResponse,
  Opportunity,
  MultiModelEntry,
  ApiError,
} from "@/lib/api";

// ─── Types ────────────────────────────────────────────────────────────────────

interface Message {
  id: string;
  role: "user" | "assistant";
  topic?: string;
  data?: AnalyzeResponse;
  error?: string;
  errorCode?: string;
  failedModel?: string;
}

function uniqueId() {
  return `msg_${Date.now()}_${Math.random().toString(36).slice(2, 7)}`;
}

function stepForProgress(step: number): AgentStep {
  const map: AgentStep[] = ["searching", "extracting", "analyzing", "generating", "validating", "done"];
  return map[Math.min(step, map.length - 1)];
}

// ─── Main Page Component ──────────────────────────────────────────────────────

export default function Home() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [agentStep, setAgentStep] = useState<AgentStep>("idle");
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [composerInitialValue, setComposerInitialValue] = useState("");
  const [currentNav, setCurrentNav] = useState<"chat" | "history" | "saved" | "tracker">("chat");
  const [showSettings, setShowSettings] = useState(false);
  const [showModeDropdown, setShowModeDropdown] = useState(false);
  const [showMoreMenu, setShowMoreMenu] = useState(false);
  const [showRightRail, setShowRightRail] = useState(false);
  const [fallbackStatus, setFallbackStatus] = useState<{
    step: "unavailable" | "switching" | "active";
    text: string;
  } | null>(null);

  // Models state (Phase 2 Multi-Model)
  const [models, setModels] = useState<MultiModelEntry[]>([]);
  const [selectedModel, setSelectedModel] = useState<string>("auto");

  const groupedModels = useMemo(() => {
    const groups: { title: string; items: MultiModelEntry[] }[] = [];
    const autoItems = models.filter((m) => m.id === "auto");
    if (autoItems.length > 0) {
      groups.push({ title: "AI MODELS", items: autoItems });
    }
    const geminiItems = models.filter(
      (m) =>
        m.id !== "auto" &&
        (m.provider?.toLowerCase().includes("gemini") ||
          m.provider?.toLowerCase().includes("google") ||
          m.id.toLowerCase().includes("gemini"))
    );
    if (geminiItems.length > 0) {
      groups.push({ title: "GOOGLE GEMINI", items: geminiItems });
    }
    const groqItems = models.filter(
      (m) =>
        m.id !== "auto" &&
        (m.provider?.toLowerCase().includes("groq") || m.id.toLowerCase().includes("groq"))
    );
    if (groqItems.length > 0) {
      groups.push({ title: "GROQ", items: groqItems });
    }
    const mistralItems = models.filter(
      (m) =>
        m.id !== "auto" &&
        (m.provider?.toLowerCase().includes("mistral") || m.id.toLowerCase().includes("mistral"))
    );
    if (mistralItems.length > 0) {
      groups.push({ title: "MISTRAL", items: mistralItems });
    }
    const otherItems = models.filter(
      (m) =>
        m.id !== "auto" &&
        !geminiItems.includes(m) &&
        !groqItems.includes(m) &&
        !mistralItems.includes(m)
    );
    if (otherItems.length > 0) {
      groups.push({ title: "OTHER PROVIDERS", items: otherItems });
    }
    return groups;
  }, [models]);

  // Saved ideas backed by SQLite with local fallback
  const [savedIdeas, setSavedIdeas] = useState<Opportunity[]>([]);

  const abortRef = useRef<AbortController | null>(null);
  const workspaceEndRef = useRef<HTMLDivElement>(null);
  const isLoadingRef = useRef(false);

  useEffect(() => {
    isLoadingRef.current = isLoading;
  }, [isLoading]);

  // Load models from backend
  useEffect(() => {
    getModels()
      .then((res) => {
        if (res.models && res.models.length > 0) {
          setModels(res.models);
          setSelectedModel(res.default || "auto");
        }
      })
      .catch(() => {
        // Fallback default model list if offline
        setModels([
          { id: "auto", display_name: "Auto", provider: "router", speed: "auto", reasoning_level: "auto" },
          { id: "gemini-balanced", display_name: "Gemini Balanced", provider: "Google Gemini", model: "gemini-3.5-flash", speed: "balanced", reasoning_level: "standard" },
          { id: "groq-fast", display_name: "Groq Fast", provider: "Groq", model: "openai/gpt-oss-20b", speed: "fast", reasoning_level: "standard" },
          { id: "groq-reasoning", display_name: "Groq Reasoning", provider: "Groq", model: "openai/gpt-oss-120b", speed: "balanced", reasoning_level: "high" },
          { id: "mistral-small", display_name: "Mistral Small", provider: "Mistral", model: "mistral-small-latest", speed: "fast", reasoning_level: "standard" },
        ]);
        setSelectedModel("auto");
      });
  }, []);

  // Load saved ideas from backend SQLite
  const loadSavedIdeas = useCallback(async () => {
    try {
      const list = await getSavedIdeas();
      const oppList: Opportunity[] = list.map((item) => ({
        id: item.id,
        title: item.title,
        problem: item.problem,
        customer: item.customer,
        solution: item.solution,
        why_now: item.why_now,
        competitors: item.competitors,
        mvp_features: item.mvp_features,
        risks: item.risks,
        evidence: item.evidence,
        score: item.score,
      }));
      setSavedIdeas(oppList);
    } catch {
      // Local fallback
      try {
        const stored = localStorage.getItem("startuplens_saved_ideas");
        if (stored) setSavedIdeas(JSON.parse(stored));
      } catch {
        // ignore
      }
    }
  }, []);

  useEffect(() => {
    let active = true;
    getSavedIdeas().then((list) => {
      if (!active) return;
      const oppList: Opportunity[] = list.map((item) => ({
        id: item.id,
        title: item.title,
        problem: item.problem,
        customer: item.customer,
        solution: item.solution,
        why_now: item.why_now,
        competitors: item.competitors,
        mvp_features: item.mvp_features,
        risks: item.risks,
        evidence: item.evidence,
        score: item.score,
      }));
      setSavedIdeas(oppList);
    }).catch(() => {
      if (!active) return;
      try {
        const stored = localStorage.getItem("startuplens_saved_ideas");
        if (stored) setSavedIdeas(JSON.parse(stored));
      } catch {
        // ignore
      }
    });

    return () => {
      active = false;
    };
  }, []);

  // New Research
  const handleNewResearch = useCallback(() => {
    if (abortRef.current) abortRef.current.abort();
    setMessages([]);
    setActiveSessionId(null);
    setIsLoading(false);
    isLoadingRef.current = false;
    setAgentStep("idle");
    setComposerInitialValue("");
    setCurrentNav("chat");
  }, []);

  // Global shortcut: Cmd+K / Ctrl+K
  useEffect(() => {
    const handleKeyDown = (e: globalThis.KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        handleNewResearch();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [handleNewResearch]);

  const scrollToBottom = useCallback(() => {
    setTimeout(() => {
      workspaceEndRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
    }, 80);
  }, []);

  // Save / Unsave idea handler
  const handleToggleSaveOpportunity = useCallback(
    async (opp: Opportunity) => {
      const exists = savedIdeas.some((o) => o.title === opp.title);
      if (exists) {
        // Find idea ID if known, otherwise delete by title
        const existingItem = savedIdeas.find((o) => o.title === opp.title);
        const delKey = existingItem?.id || opp.title;
        setSavedIdeas((prev) => prev.filter((o) => o.title !== opp.title));
        try {
          await deleteSavedIdea(delKey);
        } catch {
          // ignore
        }
      } else {
        setSavedIdeas((prev) => [opp, ...prev]);
        try {
          await saveIdea({
            session_id: activeSessionId || undefined,
            topic: messages.find((m) => m.topic)?.topic || "General",
            title: opp.title,
            problem: opp.problem,
            customer: opp.customer,
            solution: opp.solution,
            why_now: opp.why_now,
            competitors: opp.competitors,
            mvp_features: opp.mvp_features,
            risks: opp.risks,
            evidence: opp.evidence,
            score: opp.score,
          });
          loadSavedIdeas();
        } catch {
          // ignore
        }
      }
    },
    [savedIdeas, activeSessionId, messages, loadSavedIdeas]
  );

  const savedOpportunityTitles = new Set(savedIdeas.map((o) => o.title));

  // Track research handler
  const handleTrackTopic = useCallback(
    async (topic: string) => {
      try {
        await createTracker(topic, activeSessionId || undefined);
      } catch {
        // ignore
      }
    },
    [activeSessionId]
  );

  // Core request executor
  const executeAnalysis = useCallback(
    async (
      topic: string,
      asstMsgId: string,
      controller: AbortController,
      documentIds: string[] = []
    ) => {
      setIsLoading(true);
      isLoadingRef.current = true;
      setAgentStep("searching");

      const stepTimers: ReturnType<typeof setTimeout>[] = [];
      const advance = (step: number, delay: number) => {
        stepTimers.push(
          setTimeout(() => {
            if (!controller.signal.aborted) setAgentStep(stepForProgress(step));
          }, delay)
        );
      };
      advance(1, 3500);  // extracting: Analyzing market signals
      advance(2, 8500);  // analyzing: Identifying customer problems
      advance(3, 15000); // generating: Generating opportunities
      advance(4, 22000); // validating: Validating evidence

      try {
        const result = await analyzeTopic(topic, {
          documentIds,
          model: selectedModel,
          signal: controller.signal,
        });

        stepTimers.forEach(clearTimeout);
        setAgentStep("done");
        setActiveSessionId(result.session_id);

        setMessages((prev) =>
          prev.map((m) =>
            m.id === asstMsgId
              ? { ...m, topic, data: result, error: undefined, errorCode: undefined }
              : m
          )
        );

        // Brief 800ms transition for subtle success state before resting
        setTimeout(() => {
          setAgentStep("idle");
        }, 800);
      } catch (err: unknown) {
        stepTimers.forEach(clearTimeout);
        setAgentStep("idle");

        if (err instanceof Error && err.name === "AbortError") return;

        let errorMsg = "Something went wrong. Please try again.";
        let errorCode: string | undefined;

        if (err instanceof ApiError) {
          errorCode = err.code;
          if (err.code === "AI_QUOTA_EXHAUSTED") {
            errorMsg = "AI service quota has been exhausted. Please try again after quota resets or switch models.";
          } else if (err.code === "AI_SERVICE_UNAVAILABLE" || err.status === 503) {
            errorMsg = "AI analysis is temporarily unavailable. Please try again later.";
          } else if (err.code === "AI_RATE_LIMITED" || err.status === 429) {
            errorMsg = err.message || "AI service rate limit reached. Please try again shortly or switch model.";
          } else if (err.code === "AI_AUTH_ERROR" || err.status === 401) {
            errorMsg = err.message || "AI authentication failed. Please verify provider API keys.";
          } else if (err.code === "WEB_RESEARCH_FAILED") {
            errorMsg = "Current web research could not be completed. Try again when web research is available.";
          } else if (err.code === "NETWORK_ERROR" || err.status === 0) {
            errorMsg = "Cannot connect to backend server. Ensure FastAPI is running on port 8003.";
          } else if (err.code === "TIMEOUT") {
            errorMsg = "The research pipeline timed out. Please try again.";
          } else if (err.status === 400 || err.code === "INVALID_TOPIC" || err.code === "AI_INVALID_REQUEST") {
            errorMsg = "Please provide a valid research topic (minimum 2 characters).";
          } else {
            errorMsg = err.message || errorMsg;
          }
        }

        setMessages((prev) =>
          prev.map((m) =>
            m.id === asstMsgId
              ? {
                  ...m,
                  error: errorMsg,
                  errorCode,
                  failedModel: selectedModel,
                  topic,
                  data: undefined,
                }
              : m
          )
        );
      } finally {
        setIsLoading(false);
        isLoadingRef.current = false;
        scrollToBottom();
      }
    },
    [selectedModel, scrollToBottom]
  );

  // Auto Fallback Motion Trigger: Gemini unavailable -> Switching to Groq Fast -> Using Groq Fast
  const handleAutoFallback = useCallback(
    async (topic: string, failedMsgId: string) => {
      setFallbackStatus({ step: "unavailable", text: "Gemini unavailable" });
      setTimeout(() => {
        setFallbackStatus({ step: "switching", text: "Switching to Groq Fast" });
        setTimeout(() => {
          setFallbackStatus({ step: "active", text: "Using Groq Fast" });
          setSelectedModel("groq-fast");
          setTimeout(() => {
            setFallbackStatus(null);
            if (abortRef.current) abortRef.current.abort();
            const controller = new AbortController();
            abortRef.current = controller;
            executeAnalysis(topic, failedMsgId, controller, []);
          }, 600);
        }, 900);
      }, 900);
    },
    [executeAnalysis]
  );

  // Submit topic + attachments
  const handleSubmit = useCallback(
    async (topic: string, documentIds: string[] = []) => {
      if (isLoadingRef.current) return;
      setCurrentNav("chat");

      if (abortRef.current) abortRef.current.abort();
      const controller = new AbortController();
      abortRef.current = controller;

      const userMsgId = uniqueId();
      const asstMsgId = uniqueId();

      setMessages((prev) => [
        ...prev,
        { id: userMsgId, role: "user", topic },
        { id: asstMsgId, role: "assistant" },
      ]);
      setActiveSessionId(null);
      scrollToBottom();

      await executeAnalysis(topic, asstMsgId, controller, documentIds);
    },
    [executeAnalysis, scrollToBottom]
  );

  // Retry failed query
  const handleRetry = useCallback(
    async (asstMsgId: string, topic: string) => {
      if (isLoadingRef.current) return;

      setMessages((prev) =>
        prev.map((m) =>
          m.id === asstMsgId
            ? { ...m, error: undefined, errorCode: undefined, data: undefined }
            : m
        )
      );

      if (abortRef.current) abortRef.current.abort();
      const controller = new AbortController();
      abortRef.current = controller;

      scrollToBottom();
      await executeAnalysis(topic, asstMsgId, controller);
    },
    [executeAnalysis, scrollToBottom]
  );

  // Select historical session
  const handleSelectSession = useCallback(
    async (sessionId: string) => {
      setCurrentNav("chat");
      if (sessionId === activeSessionId) return;

      const asstMsgId = uniqueId();
      setActiveSessionId(sessionId);
      setMessages([{ id: asstMsgId, role: "assistant" }]);
      setIsLoading(true);
      isLoadingRef.current = true;
      setAgentStep("idle");
      scrollToBottom();

      try {
        const data = await getResearchById(sessionId);
        setMessages([{ id: asstMsgId, role: "assistant", topic: data.topic, data }]);
      } catch (err: unknown) {
        const msg =
          err instanceof ApiError ? err.message : "Failed to load research session.";
        setMessages([{ id: asstMsgId, role: "assistant", error: msg }]);
      } finally {
        setIsLoading(false);
        isLoadingRef.current = false;
        scrollToBottom();
      }
    },
    [activeSessionId, scrollToBottom]
  );

  const handleSessionDeleted = useCallback(
    (sessionId: string) => {
      if (sessionId === activeSessionId) {
        setMessages([]);
        setActiveSessionId(null);
      }
    },
    [activeSessionId]
  );

  const currentTopic =
    messages.find((m) => m.topic)?.topic ||
    (activeSessionId ? "Research Session" : "New Research");

  const latestAssistantData = [...messages].reverse().find((m) => m.data)?.data || null;
  const currentModelEntry = models.find((m) => m.id === selectedModel);

  const showEmptyState = messages.length === 0 && !isLoading && currentNav === "chat";

  return (
    <div className="flex min-h-[100dvh] h-[100dvh] overflow-hidden bg-[var(--background)] text-[var(--foreground)]">
      {/* ── 1. SIDEBAR ──────────────────────────────────────────────────────── */}
      <Sidebar
        activeSessionId={activeSessionId}
        onSelectSession={handleSelectSession}
        onNewResearch={handleNewResearch}
        isOpenMobile={sidebarOpen}
        onCloseMobile={() => setSidebarOpen(false)}
        onSessionDeleted={handleSessionDeleted}
        currentNav={currentNav}
        onNavigate={setCurrentNav}
        onOpenSettings={() => setShowSettings(true)}
        savedIdeasCount={savedIdeas.length}
      />

      {/* ── 2. MAIN CHAT / WORKSPACE AREA ───────────────────────────────────── */}
      <div className="flex flex-1 min-w-0 flex-col overflow-hidden">
        {/* Top Header */}
        <header className="flex h-14 shrink-0 items-center justify-between border-b border-[var(--border)] bg-[var(--background)] px-4 sm:px-6 z-20">
          <div className="flex items-center gap-3 min-w-0">
            {/* Mobile Hamburger */}
            <button
              type="button"
              onClick={() => setSidebarOpen(true)}
              className="flex h-8 w-8 items-center justify-center rounded-lg text-[var(--muted)] hover:bg-[var(--surface)] hover:text-[var(--foreground)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-[var(--focus)] md:hidden"
              aria-label="Open sidebar"
            >
              <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                <path strokeLinecap="round" strokeLinejoin="round" d="M4 6h16M4 12h16M4 18h16" />
              </svg>
            </button>

            {/* Current Research / Topic Indicator */}
            <div className="flex items-center gap-2 min-w-0">
              <span className="truncate text-sm font-semibold text-[var(--foreground)]">
                {currentTopic}
              </span>
            </div>

            {/* AI Model Selector Dropdown — Aligned with Topic/New Research */}
            <div className="relative hidden sm:block">
              <button
                type="button"
                onClick={() => setShowModeDropdown((v) => !v)}
                aria-expanded={showModeDropdown}
                aria-label="Select AI model"
                className="h-8 flex items-center gap-2 rounded-lg border border-[var(--border)] bg-[var(--surface-raised)]/70 hover:bg-[var(--surface-raised)] px-2.5 text-xs font-medium text-[var(--muted)] transition-all duration-180 ease-out hover:border-[var(--accent)]/40 hover:text-[var(--foreground)] shadow-2xs focus-visible:outline focus-visible:outline-2 focus-visible:outline-[var(--focus)]"
              >
                <span className="relative flex h-2 w-2 items-center justify-center">
                  <span
                    className={`absolute inline-flex h-full w-full rounded-full opacity-60 animate-ping ${
                      selectedModel.startsWith("groq")
                        ? "bg-emerald-400"
                        : selectedModel.startsWith("gemini")
                        ? "bg-blue-400"
                        : selectedModel.startsWith("mistral")
                        ? "bg-amber-400"
                        : "bg-[var(--accent)]"
                    }`}
                  />
                  <span
                    className={`relative inline-flex h-1.5 w-1.5 rounded-full ${
                      selectedModel.startsWith("groq")
                        ? "bg-emerald-400"
                        : selectedModel.startsWith("gemini")
                        ? "bg-blue-400"
                        : selectedModel.startsWith("mistral")
                        ? "bg-amber-400"
                        : "bg-[var(--accent)]"
                    }`}
                  />
                </span>
                <span className="text-[11px] font-medium text-[var(--muted)]">AI Model</span>
                <span className="text-[var(--border)]">·</span>
                <span
                  key={selectedModel}
                  className="font-semibold text-[var(--foreground)] transition-all duration-200 animate-[motionFadeSlideInRight_160ms_ease-out]"
                >
                  {currentModelEntry?.display_name || (selectedModel === "auto" ? "Auto" : selectedModel)}
                </span>
                <span className={`text-[10px] text-[var(--muted)] transition-transform duration-180 ${showModeDropdown ? "rotate-180" : ""}`}>▾</span>
              </button>

              <div
                className={`absolute top-full left-0 mt-1.5 w-80 rounded-xl border border-[var(--border)] bg-[var(--surface)] p-2 shadow-2xl z-30 transition-all ${
                  showModeDropdown
                    ? "opacity-100 translate-y-0 visible duration-160 ease-out pointer-events-auto"
                    : "opacity-0 -translate-y-1 invisible duration-120 ease-in pointer-events-none"
                }`}
              >
                <div className="max-h-96 overflow-y-auto space-y-2 pr-1">
                  {groupedModels.map((group: { title: string; items: MultiModelEntry[] }) => (
                    <div key={group.title} className="space-y-1">
                      <div className="flex items-center justify-between px-2 pt-1.5 pb-0.5">
                        <p className="text-[10px] font-mono font-bold uppercase tracking-wider text-[var(--muted)]">
                          {group.title}
                        </p>
                        {group.title === "AI MODELS" && (
                          <span className="text-[10px] text-[var(--muted)] font-mono">{models.length} configured</span>
                        )}
                      </div>
                      {group.items.map((m: MultiModelEntry) => (
                        <button
                          key={m.id}
                          type="button"
                          onClick={() => {
                            setSelectedModel(m.id);
                            setShowModeDropdown(false);
                          }}
                          className={`flex w-full flex-col items-start rounded-lg p-2 text-left text-xs transition-colors duration-140 ${
                            selectedModel === m.id
                              ? "bg-[var(--accent-subtle)] text-[var(--accent)] font-semibold"
                              : "hover:bg-[var(--surface-raised)] text-[var(--foreground)]"
                          }`}
                        >
                          <div className="flex w-full items-center justify-between">
                            <div className="flex items-center gap-1.5">
                              <span className="font-medium">{m.display_name}</span>
                              {m.id === "auto" && (
                                <span className="rounded bg-[var(--accent)]/15 text-[var(--accent)] px-1.5 py-0.2 text-[9px] font-mono font-semibold">
                                  Best available
                                </span>
                              )}
                            </div>
                            {selectedModel === m.id && (
                              <span className="animate-[motionFadeSlideInRight_140ms_ease-out] text-[var(--accent)]">✓</span>
                            )}
                          </div>
                          <span className="text-[10px] text-[var(--muted)] font-normal mt-0.5 font-mono">
                            {m.id === "auto"
                              ? "Dynamic routing: fast research, deep analysis"
                              : m.model || (m.speed ? `${m.speed} speed · ${m.reasoning_level || "standard"} reasoning` : "")}
                          </span>
                        </button>
                      ))}
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>

          {/* Right Header Actions — Equal h-8 Heights & Consistent Alignment */}
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={handleNewResearch}
              className="h-8 inline-flex items-center gap-1.5 rounded-lg border border-[var(--border)] bg-[var(--surface-raised)]/70 px-3 text-xs font-medium text-[var(--foreground)] hover:border-[var(--accent)]/40 hover:bg-[var(--surface-raised)] transition-all duration-180 shadow-2xs"
            >
              <span className="text-[var(--accent)] text-xs font-bold leading-none">+</span>
              <span>New</span>
            </button>

            {/* Toggle Intelligence Rail button (only available during active or completed research) */}
            {!showEmptyState && (
              <button
                type="button"
                onClick={() => setShowRightRail((v) => !v)}
                title={showRightRail ? "Collapse Intelligence Rail" : "Expand Intelligence Rail"}
                aria-label={showRightRail ? "Collapse Intelligence Rail" : "Expand Intelligence Rail"}
                className={`h-8 px-2.5 rounded-lg border text-xs font-medium inline-flex items-center gap-1.5 transition-colors duration-140 ${
                  showRightRail
                    ? "border-[var(--accent)]/40 bg-[var(--accent-subtle)] text-[var(--accent)]"
                    : "border-[var(--border)] bg-[var(--surface)] text-[var(--muted)] hover:text-[var(--foreground)]"
                }`}
              >
                <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M9 17V7m0 10a2 2 0 01-2 2H5a2 2 0 01-2-2V7a2 2 0 012-2h2a2 2 0 012 2m0 10a2 2 0 002 2h2a2 2 0 002-2M9 7a2 2 0 012-2h2a2 2 0 012 2m0 10V7m0 10a2 2 0 002 2h2a2 2 0 002-2V7a2 2 0 00-2-2h-2a2 2 0 00-2 2" />
                </svg>
                <span className="hidden sm:inline">Intelligence</span>
              </button>
            )}

            <ThemeToggle />

            <div className="relative">
              <button
                type="button"
                onClick={() => setShowMoreMenu((v) => !v)}
                title="More actions"
                aria-label="More actions"
                className="flex h-8 w-8 items-center justify-center rounded-lg border border-[var(--border)] bg-[var(--surface)] text-[var(--muted)] transition-colors duration-140 hover:border-[var(--accent)]/40 hover:text-[var(--foreground)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-[var(--focus)]"
              >
                <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                  <circle cx="12" cy="12" r="1" />
                  <circle cx="19" cy="12" r="1" />
                  <circle cx="5" cy="12" r="1" />
                </svg>
              </button>

              <div
                className={`absolute top-full right-0 mt-1.5 w-48 rounded-xl border border-[var(--border)] bg-[var(--surface)] p-1.5 shadow-2xl z-30 transition-all ${
                  showMoreMenu
                    ? "opacity-100 translate-y-0 visible duration-160 ease-out pointer-events-auto"
                    : "opacity-0 -translate-y-1 invisible duration-120 ease-in pointer-events-none"
                }`}
              >
                <button
                  type="button"
                  onClick={() => {
                    setShowMoreMenu(false);
                    handleNewResearch();
                  }}
                  className="flex w-full items-center gap-2 rounded-lg px-2.5 py-1.5 text-xs text-[var(--text-secondary)] hover:bg-[var(--surface-raised)] hover:text-[var(--foreground)]"
                >
                  <span>+ New Research</span>
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setShowMoreMenu(false);
                    setShowSettings(true);
                  }}
                  className="flex w-full items-center gap-2 rounded-lg px-2.5 py-1.5 text-xs text-[var(--text-secondary)] hover:bg-[var(--surface-raised)] hover:text-[var(--foreground)]"
                >
                  <span>⚙ Settings</span>
                </button>
                {activeSessionId && (
                  <button
                    type="button"
                    onClick={() => {
                      setShowMoreMenu(false);
                      handleSessionDeleted(activeSessionId);
                    }}
                    className="flex w-full items-center gap-2 rounded-lg px-2.5 py-1.5 text-xs text-red-400 hover:bg-red-950/20"
                  >
                    <span>🗑 Clear Dossier</span>
                  </button>
                )}
              </div>
            </div>
          </div>
        </header>

        {/* ── 3-Zone Desktop Workspace Container ───────────────────────── */}
        <div className="flex flex-1 min-w-0 overflow-hidden">
          {/* Center Research Workspace (Main + Composer) */}
          <div className="flex flex-1 min-w-0 flex-col overflow-hidden">
            {/* ── Main Scrollable Body ────────────────────────────────────────── */}
            <main
              id="main-workspace"
              className="flex-1 overflow-y-auto"
              aria-label="Research workspace"
            >
              {/* View: Saved Ideas */}
              {currentNav === "saved" && (
                <SavedIdeasView
                  savedIdeas={savedIdeas}
                  onToggleSave={handleToggleSaveOpportunity}
                  onBackToChat={() => setCurrentNav("chat")}
                />
              )}

              {/* View: Research History */}
              {currentNav === "history" && (
                <HistoryView
                  onSelectSession={handleSelectSession}
                  onBackToChat={() => setCurrentNav("chat")}
                  onSessionDeleted={handleSessionDeleted}
                />
              )}

              {/* View: Research Tracker & Market Change Signals */}
              {currentNav === "tracker" && (
                <ResearchTrackerView
                  onBackToChat={() => setCurrentNav("chat")}
                  onSelectTopic={(topic) => {
                    setCurrentNav("chat");
                    handleSubmit(topic);
                  }}
                  onSelectSession={(sessionId) => {
                    handleSelectSession(sessionId);
                  }}
                />
              )}

              {/* View: Landing / New Research Screen */}
              {showEmptyState && (
                <div className="relative flex min-h-[calc(100dvh-3.5rem)] flex-col items-center justify-center px-4 py-8 sm:py-10 text-center overflow-hidden">
                  {/* Subtle ambient lighting & network pattern behind hero */}
                  <div className="pointer-events-none absolute inset-0 flex items-center justify-center" aria-hidden="true">
                    <div className="h-[420px] w-[600px] rounded-full bg-[radial-gradient(ellipse_at_center,rgba(94,158,240,0.05)_0%,transparent_70%)] blur-2xl" />
                  </div>
                  <IntelligenceNetworkVisual />

                  <div className="relative z-10 mx-auto flex w-full max-w-4xl flex-col items-center justify-center">
                    {/* Small StartupLens mark */}
                    <div className="animate-landing-logo flex h-8 w-8 items-center justify-center rounded-xl border border-[var(--border)] bg-[var(--surface-raised)] text-[var(--accent)] shadow-2xs">
                      <svg
                        className="h-4 w-4"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="2.2"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        aria-hidden="true"
                      >
                        <circle cx="12" cy="12" r="9" />
                        <circle cx="12" cy="12" r="3" />
                        <line x1="12" y1="3" x2="12" y2="6" />
                        <line x1="12" y1="18" x2="12" y2="21" />
                        <line x1="3" y1="12" x2="6" y2="12" />
                        <line x1="18" y1="12" x2="21" y2="12" />
                      </svg>
                    </div>

                    {/* Eyebrow */}
                    <div className="animate-landing-eyebrow mt-2.5 mb-2 inline-flex items-center gap-1.5 rounded-full border border-[var(--border-subtle)] bg-[var(--surface-raised)]/70 px-3 py-0.5 text-[10px] font-mono font-bold uppercase tracking-widest text-[var(--muted)]">
                      <span className="h-1.5 w-1.5 rounded-full bg-[var(--accent)] animate-pulse" />
                      <span>AI STARTUP INTELLIGENCE ENGINE</span>
                    </div>

                    {/* Main Headline — Refined Scale */}
                    <h1 className="animate-landing-headline text-2xl font-bold tracking-tight text-[var(--foreground)] sm:text-3xl md:text-[40px] lg:text-[44px] max-w-[780px] leading-[1.18] text-balance">
                      Discover &amp; Validate High-Conviction<br className="hidden sm:inline" /> Startup Opportunities
                    </h1>

                    {/* Supporting Text */}
                    <p className="animate-landing-subtitle mt-2.5 max-w-[620px] text-xs sm:text-sm text-[var(--muted)] leading-relaxed">
                      Research markets, discover customer problems, analyze competitors, and generate evidence-informed startup opportunities.
                    </p>

                    {/* Capability Pills */}
                    <div className="animate-landing-pills flex flex-wrap justify-center items-center gap-2 pt-3 text-xs">
                      <span className="h-7 sm:h-8 inline-flex items-center rounded-full border border-[var(--border)] bg-[var(--surface-raised)]/60 px-3 text-[11px] font-medium text-[var(--text-secondary)] hover:border-[var(--accent)]/50 hover:text-[var(--foreground)] hover:bg-[var(--surface-raised)] transition-colors duration-160 shadow-2xs">
                        Live Web Research
                      </span>
                      <span className="h-7 sm:h-8 inline-flex items-center rounded-full border border-[var(--border)] bg-[var(--surface-raised)]/60 px-3 text-[11px] font-medium text-[var(--text-secondary)] hover:border-[var(--accent)]/50 hover:text-[var(--foreground)] hover:bg-[var(--surface-raised)] transition-colors duration-160 shadow-2xs">
                        Market Signals
                      </span>
                      <span className="h-7 sm:h-8 inline-flex items-center rounded-full border border-[var(--border)] bg-[var(--surface-raised)]/60 px-3 text-[11px] font-medium text-[var(--text-secondary)] hover:border-[var(--accent)]/50 hover:text-[var(--foreground)] hover:bg-[var(--surface-raised)] transition-colors duration-160 shadow-2xs">
                        Multi-Model Engine
                      </span>
                      <span className="h-7 sm:h-8 inline-flex items-center rounded-full border border-[var(--border)] bg-[var(--surface-raised)]/60 px-3 text-[11px] font-medium text-[var(--text-secondary)] hover:border-[var(--accent)]/50 hover:text-[var(--foreground)] hover:bg-[var(--surface-raised)] transition-colors duration-160 shadow-2xs">
                        Evidence Validation
                      </span>
                    </div>

                    {/* Connected Composer — Closer to Hero */}
                    <div className="animate-landing-composer w-full max-w-[860px] mx-auto mt-7 sm:mt-9">
                      <Composer
                        onSubmit={handleSubmit}
                        isLoading={isLoading}
                        initialValue={composerInitialValue}
                        modelDisplay={currentModelEntry?.display_name || (selectedModel === "auto" ? "Auto" : selectedModel)}
                        onOpenModelSelector={() => setShowModeDropdown(true)}
                      />
                    </div>

                    {/* Quick Actions Under Composer */}
                    <div className="animate-landing-actions w-full flex justify-center mt-3">
                      <SuggestedPrompts
                        onSelectPrompt={(prompt) => {
                          setComposerInitialValue(prompt);
                          handleSubmit(prompt);
                        }}
                        disabled={isLoading}
                      />
                    </div>
                  </div>
                </div>
              )}

              {/* View: Chat Messages Stream */}
              {currentNav === "chat" && messages.length > 0 && (
                <div className="mx-auto max-w-[1240px] w-full px-4 sm:px-6 lg:px-8 py-5">
              {messages.map((msg) => (
                <div key={msg.id} className="mb-8">
                  {msg.role === "user" && msg.topic && (
                    <div className="mb-6 flex justify-end">
                      <div className="max-w-lg rounded-2xl rounded-tr-sm bg-[var(--surface-raised)] border border-[var(--border)] px-4 py-2.5 shadow-xs">
                        <p className="text-sm font-medium text-[var(--foreground)]">{msg.topic}</p>
                      </div>
                    </div>
                  )}

                  {msg.role === "assistant" && (
                    <div className="space-y-4">
                      <div className="flex items-center gap-2">
                        <div className="flex h-6 w-6 items-center justify-center rounded-lg bg-[var(--accent)] text-[var(--background)] font-bold text-xs shadow-xs">
                          SL
                        </div>
                        <span className="text-xs font-semibold text-[var(--foreground)]">
                          StartupLens AI
                        </span>
                        <span className="rounded-full bg-[var(--surface)] border border-[var(--border)] px-2 py-0.2 text-[10px] text-[var(--muted)]">
                          Intelligence Agent
                        </span>
                      </div>

                      {fallbackStatus && (
                        <div
                          role="status"
                          aria-live="polite"
                          className="my-3 inline-flex items-center gap-2 rounded-xl border border-[var(--border)] bg-[var(--surface-raised)] px-3 py-1.5 text-xs shadow-sm transition-all duration-180 animate-[motionFadeSlideInRight_160ms_ease-out]"
                        >
                          <span
                            className={`h-2 w-2 rounded-full transition-colors duration-200 ${
                              fallbackStatus.step === "unavailable"
                                ? "bg-amber-400"
                                : fallbackStatus.step === "switching"
                                ? "bg-[var(--accent)] animate-pulse"
                                : "bg-[var(--success)]"
                            }`}
                          />
                          <span
                            key={fallbackStatus.text}
                            className="font-medium text-[var(--foreground)] animate-[motionFadeSlideInRight_160ms_ease-out]"
                          >
                            {fallbackStatus.text}
                          </span>
                        </div>
                      )}

                      {!msg.data && !msg.error && (isLoading || agentStep === "done") && (
                        <AgentStatus
                          currentStep={agentStep}
                          topic={msg.topic || (currentTopic !== "New Research" ? currentTopic : "Startup Intelligence")}
                        />
                      )}

                      {msg.error && (
                        <div
                          role="alert"
                          className="rounded-xl border border-red-900/40 bg-red-950/20 p-4 animate-[motionFadeSlideDown_200ms_cubic-bezier(0.16,1,0.3,1)_both]"
                        >
                          <div className="flex items-start gap-3">
                            <span className="mt-0.5 text-red-400 text-sm animate-[motionPulseSubtle_2s_ease-in-out_infinite]" aria-hidden="true">
                              ⚠
                            </span>
                            <div className="flex-1">
                              <p className="text-xs font-semibold text-red-300">
                                {msg.errorCode === "AI_QUOTA_EXHAUSTED"
                                  ? "AI service quota exhausted."
                                  : msg.errorCode === "AI_SERVICE_UNAVAILABLE"
                                  ? "AI service temporarily unavailable."
                                  : msg.errorCode === "AI_RATE_LIMITED"
                                  ? "Rate limit exceeded"
                                  : "Research Pipeline Notice"}
                              </p>
                              <p className="mt-1 text-xs text-red-400/90">{msg.error}</p>
                              
                              <div className="mt-3 flex flex-wrap items-center gap-2">
                                {msg.topic && (
                                  <button
                                    id={`retry-btn-${msg.id}`}
                                    type="button"
                                    disabled={isLoading}
                                    onClick={() => handleRetry(msg.id, msg.topic!)}
                                    className="rounded-lg border border-red-800/50 bg-red-950/40 px-3 py-1.5 text-xs font-medium text-red-300 transition-all duration-140 hover:bg-red-900/40 active:scale-95 focus-visible:outline focus-visible:outline-2 focus-visible:outline-[var(--focus)] disabled:cursor-not-allowed disabled:opacity-50"
                                  >
                                    {isLoading ? "Retrying…" : "Retry Analysis"}
                                  </button>
                                )}

                                {msg.topic && (msg.failedModel?.includes("gemini") || msg.failedModel === "auto" || msg.errorCode === "AI_QUOTA_EXHAUSTED" || msg.errorCode === "AI_RATE_LIMITED") && (
                                  <button
                                    type="button"
                                    disabled={isLoading}
                                    onClick={() => handleAutoFallback(msg.topic!, msg.id)}
                                    className="rounded-lg border border-[var(--accent)]/40 bg-[var(--accent-subtle)] px-3 py-1.5 text-xs font-medium text-[var(--accent)] transition-all duration-140 hover:bg-[var(--accent)]/20 active:scale-95 focus-visible:outline focus-visible:outline-2 focus-visible:outline-[var(--focus)]"
                                  >
                                    ⚡ Switch to Groq Fast
                                  </button>
                                )}
                              </div>
                            </div>
                          </div>
                        </div>
                      )}

                      {msg.data && (
                        <ResearchReport
                          data={msg.data}
                          topic={msg.topic || msg.data.topic}
                          savedOpportunityTitles={savedOpportunityTitles}
                          onToggleSaveOpportunity={handleToggleSaveOpportunity}
                          onTrackTopic={handleTrackTopic}
                        />
                      )}
                    </div>
                  )}
                </div>
              ))}
              <div ref={workspaceEndRef} aria-hidden="true" />
            </div>
          )}
        </main>

            {/* ── 4. FLOATING COMPOSER (WHEN IN CHAT / ACTIVE RESEARCH / REPORT) ─── */}
            {currentNav === "chat" && !showEmptyState && (
              <div className="shrink-0 border-t border-[var(--border)] bg-[var(--background)] px-4 py-3 sm:px-6">
                <div className="mx-auto max-w-[860px]">
                  <Composer
                    onSubmit={handleSubmit}
                    isLoading={isLoading}
                    initialValue={composerInitialValue}
                    modelDisplay={currentModelEntry?.display_name || (selectedModel === "auto" ? "Auto" : selectedModel)}
                    onOpenModelSelector={() => setShowModeDropdown(true)}
                  />
                </div>
              </div>
            )}
          </div>

          {/* ── 5. RIGHT INTELLIGENCE CONTEXT RAIL (3-ZONE DESKTOP) ────────── */}
          {currentNav === "chat" && !showEmptyState && (
            <IntelligenceRail
              isOpen={showRightRail}
              onToggle={() => setShowRightRail((v) => !v)}
              data={latestAssistantData}
              selectedModel={selectedModel}
              modelEntry={currentModelEntry}
              isLoading={isLoading}
              agentStep={agentStep}
              fallbackStatus={fallbackStatus}
            />
          )}
        </div>
      </div>

      <SettingsModal
        isOpen={showSettings}
        onClose={() => setShowSettings(false)}
      />
    </div>
  );
}
