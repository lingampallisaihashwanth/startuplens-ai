"use client";

import React from "react";
import { AnalyzeResponse, MultiModelEntry } from "@/lib/api";
import { AgentStep } from "./AgentStatus";

interface IntelligenceRailProps {
  isOpen: boolean;
  onToggle: () => void;
  data?: AnalyzeResponse | null;
  selectedModel: string;
  modelEntry?: MultiModelEntry;
  isLoading: boolean;
  agentStep: AgentStep;
  fallbackStatus?: {
    step: "unavailable" | "switching" | "active";
    text: string;
  } | null;
}

export function IntelligenceRail({
  isOpen,
  onToggle,
  data,
  selectedModel,
  modelEntry,
  isLoading,
  agentStep,
  fallbackStatus,
}: IntelligenceRailProps) {
  if (!isOpen) {
    return null;
  }

  const sources = data?.sources || [];
  const opportunities = data?.opportunities || [];
  const research = data?.research;

  const recentCount = sources.filter((s) => !s.is_historical && s.freshness_label?.toLowerCase().includes("recent")).length ||
    sources.filter((s) => !s.is_historical).length;
  const historicalCount = sources.length - recentCount;

  const currentProvider = data?.provider_used || modelEntry?.provider || (selectedModel === "auto" ? "Dynamic Router" : "AI Provider");
  const currentModelName = data?.model_used || modelEntry?.display_name || selectedModel;
  const currentModelIdentifier = modelEntry?.model || (selectedModel === "auto" ? "Dynamic multi-model" : selectedModel);

  const sessionCreated = data?.created_at
    ? new Date(data.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
    : null;
  const sessionUpdated = data?.retrieved_at
    ? new Date(data.retrieved_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
    : null;

  // Real backend pipeline state calculation
  const isSearching = isLoading && agentStep === "searching";
  const isAnalyzing = isLoading && (agentStep === "extracting" || agentStep === "analyzing");
  const isGenerating = isLoading && agentStep === "generating";
  const isValidating = isLoading && agentStep === "validating";

  const sourcesDone = sources.length > 0 || (isLoading && ["extracting", "analyzing", "generating", "validating", "done"].includes(agentStep));
  const signalsDone = (research && (research.market_signals?.length || 0) > 0) || (isLoading && ["generating", "validating", "done"].includes(agentStep));
  const oppsDone = opportunities.length > 0 || (isLoading && ["validating", "done"].includes(agentStep));
  const evidenceDone = Boolean(data && data.sources?.length);

  return (
    <aside
      aria-label="Intelligence context rail"
      className="hidden xl:flex w-72 shrink-0 flex-col border-l border-[var(--border)] bg-[var(--background)] text-[var(--foreground)] overflow-y-auto transition-all duration-200 ease-out"
    >
      {/* Rail Header */}
      <div className="flex h-14 shrink-0 items-center justify-between border-b border-[var(--border)] px-4">
        <div className="flex items-center gap-2">
          <span className="flex h-2 w-2 rounded-full bg-[var(--accent)] animate-[motionPulseSubtle_2s_ease-in-out_infinite]" />
          <span className="text-xs font-bold uppercase tracking-wider text-[var(--foreground)] font-mono">
            INTELLIGENCE CONTEXT
          </span>
        </div>
        <button
          type="button"
          onClick={onToggle}
          title="Collapse rail"
          aria-label="Collapse rail"
          className="flex h-7 w-7 items-center justify-center rounded-lg text-[var(--muted)] hover:bg-[var(--surface-hover)] hover:text-[var(--foreground)] transition-colors duration-140 focus-visible:outline focus-visible:outline-2 focus-visible:outline-[var(--focus)]"
        >
          <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
            <path strokeLinecap="round" strokeLinejoin="round" d="M11 19l-7-7 7-7m8 14l-7-7 7-7" />
          </svg>
        </button>
      </div>

      <div className="p-3.5 space-y-4 text-xs">
        {/* 1. RESEARCH ACTIVITY */}
        <section aria-labelledby="rail-activity-title" className="space-y-2">
          <div className="flex items-center justify-between">
            <h4 id="rail-activity-title" className="text-[10px] font-mono font-bold uppercase tracking-wider text-[var(--muted)]">
              RESEARCH ACTIVITY
            </h4>
            <span className="rounded bg-[var(--surface-raised)] border border-[var(--border-subtle)] px-1.5 py-0.2 text-[9px] font-mono text-[var(--accent)] font-semibold">
              {isLoading ? "ACTIVE" : data ? "VERIFIED" : "STANDBY"}
            </span>
          </div>

          <div className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-3 space-y-2 text-xs">
            {/* Step 1: Web sources */}
            <div className="flex items-center justify-between">
              <span className="text-[var(--text-secondary)]">Web sources</span>
              <span className="font-mono text-[11px]">
                {sourcesDone ? (
                  <span className="text-[var(--success)] font-semibold">✓ Retrieved {sources.length > 0 ? `(${sources.length})` : ""}</span>
                ) : isSearching ? (
                  <span className="text-[var(--accent)] font-semibold animate-pulse">● Querying...</span>
                ) : (
                  <span className="text-[var(--muted)]">○ Standby</span>
                )}
              </span>
            </div>

            {/* Step 2: Market signals */}
            <div className="flex items-center justify-between">
              <span className="text-[var(--text-secondary)]">Market signals</span>
              <span className="font-mono text-[11px]">
                {signalsDone ? (
                  <span className="text-[var(--success)] font-semibold">✓ Analyzed</span>
                ) : isAnalyzing ? (
                  <span className="text-[var(--accent)] font-semibold animate-pulse">● Analyzing...</span>
                ) : (
                  <span className="text-[var(--muted)]">○ Standby</span>
                )}
              </span>
            </div>

            {/* Step 3: Opportunities */}
            <div className="flex items-center justify-between">
              <span className="text-[var(--text-secondary)]">Opportunities</span>
              <span className="font-mono text-[11px]">
                {oppsDone ? (
                  <span className="text-[var(--success)] font-semibold">✓ Generated {opportunities.length > 0 ? `(${opportunities.length})` : ""}</span>
                ) : isGenerating ? (
                  <span className="text-[var(--accent)] font-semibold animate-pulse">● Formulating...</span>
                ) : (
                  <span className="text-[var(--muted)]">○ Standby</span>
                )}
              </span>
            </div>

            {/* Step 4: Evidence */}
            <div className="flex items-center justify-between">
              <span className="text-[var(--text-secondary)]">Evidence</span>
              <span className="font-mono text-[11px]">
                {evidenceDone ? (
                  <span className="text-[var(--success)] font-semibold">✓ Audited</span>
                ) : isValidating ? (
                  <span className="text-[var(--accent)] font-semibold animate-pulse">● Auditing...</span>
                ) : (
                  <span className="text-[var(--muted)]">○ Standby</span>
                )}
              </span>
            </div>
          </div>
        </section>

        {/* 2. CURRENT AI MODEL */}
        <section aria-labelledby="rail-model-title" className="space-y-2">
          <h4 id="rail-model-title" className="text-[10px] font-mono font-bold uppercase tracking-wider text-[var(--muted)]">
            CURRENT AI MODEL
          </h4>

          <div className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-3 space-y-1.5">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-1.5">
                <span
                  className={`h-2 w-2 rounded-full ${
                    selectedModel.startsWith("groq")
                      ? "bg-emerald-400"
                      : selectedModel.startsWith("gemini")
                      ? "bg-blue-400"
                      : selectedModel.startsWith("mistral")
                      ? "bg-amber-400"
                      : "bg-[var(--accent)]"
                  }`}
                />
                <span className="font-semibold text-[var(--foreground)]">
                  {currentModelName}
                </span>
              </div>
              <span className="rounded bg-[var(--surface-raised)] border border-[var(--border-subtle)] px-1.5 py-0.2 text-[9px] text-[var(--muted)] font-mono">
                {currentProvider}
              </span>
            </div>

            <p className="text-[11px] text-[var(--text-secondary)] font-mono truncate" title={currentModelIdentifier}>
              {currentModelIdentifier}
            </p>

            {fallbackStatus && (
              <div className="rounded-lg border border-amber-500/30 bg-amber-500/10 p-2 text-[10px] text-amber-400">
                <span className="font-semibold">Fallback: </span>
                <span>{fallbackStatus.text}</span>
              </div>
            )}
          </div>
        </section>

        {/* 3. EVIDENCE */}
        <section aria-labelledby="rail-evidence-title" className="space-y-2">
          <h4 id="rail-evidence-title" className="text-[10px] font-mono font-bold uppercase tracking-wider text-[var(--muted)]">
            EVIDENCE
          </h4>

          <div className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-3 space-y-2">
            <div className="flex items-center justify-between text-xs">
              <span className="text-[var(--text-secondary)]">Verified sources</span>
              <span className="font-mono font-semibold text-[var(--foreground)]">{sources.length}</span>
            </div>

            <div className="flex items-center justify-between text-xs">
              <span className="text-[var(--text-secondary)]">Recent sources</span>
              <span className="font-mono text-[var(--success)]">{recentCount}</span>
            </div>

            <div className="flex items-center justify-between text-xs">
              <span className="text-[var(--text-secondary)]">Historical sources</span>
              <span className="font-mono text-[var(--muted)]">{historicalCount}</span>
            </div>
          </div>
        </section>

        {/* 4. SESSION */}
        <section aria-labelledby="rail-session-title" className="space-y-2">
          <h4 id="rail-session-title" className="text-[10px] font-mono font-bold uppercase tracking-wider text-[var(--muted)]">
            SESSION
          </h4>

          <div className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-3 space-y-1.5 text-[11px]">
            <div className="flex items-center justify-between">
              <span className="text-[var(--muted)]">Research ID</span>
              <span className="font-mono text-[var(--foreground)] truncate max-w-[120px]" title={data?.session_id || "Active session"}>
                {data?.session_id ? `${data.session_id.slice(0, 10)}...` : "LIVE_SESSION"}
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-[var(--muted)]">Created</span>
              <span className="font-mono text-[var(--foreground)]">{sessionCreated || "Just now"}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-[var(--muted)]">Updated</span>
              <span className="font-mono text-[var(--foreground)]">{sessionUpdated || "Realtime"}</span>
            </div>
          </div>
        </section>
      </div>
    </aside>
  );
}
