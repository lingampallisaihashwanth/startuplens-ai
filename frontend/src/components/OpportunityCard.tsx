"use client";

import React, { useState } from "react";
import { Opportunity } from "@/lib/api";

interface OpportunityCardProps {
  opportunity: Opportunity;
  index: number;
  isTopSignal?: boolean;
  isSaved?: boolean;
  onToggleSave?: (opp: Opportunity) => void;
  isSelectedForCompare?: boolean;
  onToggleCompare?: (opp: Opportunity) => void;
}

export function OpportunityCard({
  opportunity,
  index,
  isTopSignal = false,
  isSaved = false,
  onToggleSave,
  isSelectedForCompare = false,
  onToggleCompare,
}: OpportunityCardProps) {
  const [expanded, setExpanded] = useState(false);
  const score = opportunity.score;

  // Normalized score out of 10
  const normalizedScore = score?.overall_score
    ? (score.overall_score <= 10 ? score.overall_score : score.overall_score / 5).toFixed(1)
    : "8.5";

  const scorePercent = score?.overall_score
    ? Math.min(100, Math.round(score.overall_score <= 10 ? (score.overall_score / 10) * 100 : (score.overall_score / 50) * 100))
    : 85;

  const rankingNumber = String(index + 1).padStart(2, "0");

  const evidenceStrength = score?.confidence_label || "Strong";

  return (
    <article
      style={{ animationDelay: `${Math.min(index * 40, 200)}ms` }}
      className={`group motion-card-enter relative rounded-2xl border bg-[var(--surface)] p-6 sm:p-7 transition-all duration-200 ease-out shadow-xs hover:shadow-md ${
        isSelectedForCompare
          ? "border-[var(--accent)] ring-1 ring-[var(--accent)]/50"
          : isTopSignal
          ? "border-[var(--border)] hover:border-[var(--accent)]/40"
          : "border-[var(--border)] hover:border-[var(--border)]/80"
      }`}
      aria-labelledby={`opp-title-${index}`}
    >
      {/* Editorial Number */}
      <div className="flex items-center justify-between">
        <span className="font-mono text-2xl font-bold tracking-tight text-[var(--accent)]">
          {rankingNumber}
        </span>
        {isTopSignal && (
          <span className="inline-flex items-center gap-1 rounded bg-[var(--accent-subtle)] border border-[var(--accent)]/30 px-2 py-0.5 text-[9px] font-mono font-bold uppercase tracking-wider text-[var(--accent)]">
            ★ TOP SIGNAL
          </span>
        )}
      </div>

      {/* Title */}
      <h3
        id={`opp-title-${index}`}
        className="mt-3 text-xl font-bold tracking-tight text-[var(--foreground)] sm:text-2xl leading-snug"
      >
        {opportunity.title}
      </h3>

      {/* One-line Description / Why Now */}
      <p className="mt-2 text-xs sm:text-sm text-[var(--muted)] leading-relaxed">
        {opportunity.why_now || opportunity.solution}
      </p>

      {/* Editorial Sections: Customer, Problem, Solution */}
      <div className="mt-5 space-y-4 border-t border-[var(--border-subtle)] pt-4 text-xs">
        <div>
          <span className="block font-mono text-[10px] font-bold uppercase tracking-wider text-[var(--muted)]">
            CUSTOMER
          </span>
          <p className="mt-1 text-[var(--foreground)] font-medium leading-relaxed">
            {opportunity.customer}
          </p>
        </div>

        <div>
          <span className="block font-mono text-[10px] font-bold uppercase tracking-wider text-[var(--muted)]">
            PROBLEM
          </span>
          <p className="mt-1 text-[var(--text-secondary)] leading-relaxed">
            {opportunity.problem}
          </p>
        </div>

        <div>
          <span className="block font-mono text-[10px] font-bold uppercase tracking-wider text-[var(--muted)]">
            SOLUTION
          </span>
          <p className="mt-1 text-[var(--text-secondary)] leading-relaxed">
            {opportunity.solution}
          </p>
        </div>
      </div>

      {/* Opportunity Score & Evidence Strength */}
      <div className="mt-5 rounded-xl border border-[var(--border-subtle)] bg-[var(--surface-raised)]/70 p-3.5 space-y-2">
        <div className="flex items-center justify-between text-xs">
          <div className="flex items-center gap-2">
            <span className="font-mono text-[10px] font-bold uppercase tracking-wider text-[var(--muted)]">
              OPPORTUNITY SCORE
            </span>
            <span className="font-mono text-xs font-bold text-[var(--foreground)]">
              {normalizedScore} <span className="text-[var(--muted)] font-normal">/ 10</span>
            </span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="text-[10px] font-mono text-[var(--muted)]">EVIDENCE:</span>
            <span className="rounded bg-[var(--surface)] border border-[var(--border)] px-1.5 py-0.2 text-[10px] font-mono font-semibold text-[var(--success)]">
              {evidenceStrength}
            </span>
          </div>
        </div>

        <div className="h-1.5 w-full rounded-full bg-[var(--surface)] overflow-hidden">
          <div
            className="h-full rounded-full bg-[var(--accent)] score-fill-bar"
            style={{ width: `${scorePercent}%` }}
          />
        </div>
      </div>

      {/* Bottom Action Buttons: [ Save ] [ Compare ] [ Explore ] */}
      <div className="mt-5 flex flex-wrap items-center gap-2 border-t border-[var(--border-subtle)] pt-4">
        {onToggleSave && (
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              onToggleSave(opportunity);
            }}
            className={`flex h-8 items-center gap-1.5 rounded-lg border px-3 text-xs font-medium transition-all duration-160 ease-out active:scale-95 ${
              isSaved
                ? "border-amber-500/40 bg-amber-500/10 text-amber-400 font-semibold"
                : "border-[var(--border)] bg-[var(--surface-raised)] text-[var(--text-secondary)] hover:border-[var(--border)]/80 hover:text-[var(--foreground)]"
            }`}
          >
            <span>{isSaved ? "★ Saved" : "☆ Save"}</span>
          </button>
        )}

        {onToggleCompare && (
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              onToggleCompare(opportunity);
            }}
            className={`flex h-8 items-center gap-1.5 rounded-lg border px-3 text-xs font-medium transition-all duration-160 ease-out active:scale-95 ${
              isSelectedForCompare
                ? "border-[var(--accent)] bg-[var(--accent-subtle)] text-[var(--accent)] font-semibold"
                : "border-[var(--border)] bg-[var(--surface-raised)] text-[var(--text-secondary)] hover:border-[var(--accent)]/30 hover:text-[var(--foreground)]"
            }`}
          >
            <span>{isSelectedForCompare ? "✓ Compared" : "Compare"}</span>
          </button>
        )}

        <button
          type="button"
          onClick={() => setExpanded((v) => !v)}
          className="flex h-8 items-center gap-1.5 rounded-lg border border-[var(--border)] bg-[var(--surface-raised)] px-3 text-xs font-medium text-[var(--foreground)] transition-colors hover:border-[var(--accent)]/40 hover:text-[var(--accent)] ml-auto"
        >
          <span>{expanded ? "Close Details" : "Explore"}</span>
          <span className={`text-[10px] transition-transform duration-160 ${expanded ? "rotate-90" : ""}`}>
            ↗
          </span>
        </button>
      </div>

      {/* ── Expanded Full Intelligence Details ───────────────────────────── */}
      {expanded && (
        <div
          id={`opp-body-${index}`}
          className="mt-5 border-t border-[var(--border)] bg-[var(--surface-raised)]/30 -mx-6 -mb-6 sm:-mx-7 sm:-mb-7 p-6 sm:p-7 space-y-5 rounded-b-2xl animate-[motionFadeSlideDown_200ms_cubic-bezier(0.16,1,0.3,1)_both]"
        >
          {/* Why this matters */}
          {opportunity.why_now && (
            <div>
              <h4 className="font-mono text-[10px] font-bold uppercase tracking-wider text-[var(--accent)]">
                WHY THIS MATTERS
              </h4>
              <p className="mt-1 text-xs text-[var(--foreground)] leading-relaxed">
                {opportunity.why_now}
              </p>
            </div>
          )}
          {/* MVP Scopes */}
          {opportunity.mvp_features && opportunity.mvp_features.length > 0 && (
            <div>
              <h4 className="font-mono text-[10px] font-bold uppercase tracking-wider text-[var(--accent)]">
                4-WEEK MVP SCOPE
              </h4>
              <ul className="mt-2 space-y-1.5">
                {opportunity.mvp_features.map((feature, i) => (
                  <li key={i} className="flex items-start gap-2 text-xs text-[var(--text-secondary)]">
                    <span className="font-mono text-[var(--accent)] text-[10px]">0{i + 1}.</span>
                    <span>{feature}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Competitors & Incumbents */}
          {opportunity.competitors && opportunity.competitors.length > 0 && (
            <div>
              <h4 className="font-mono text-[10px] font-bold uppercase tracking-wider text-[var(--muted)]">
                OBSERVED COMPETITORS & INCUMBENTS
              </h4>
              <div className="mt-2 flex flex-wrap gap-1.5">
                {opportunity.competitors.map((comp, i) => (
                  <span
                    key={i}
                    className="rounded-md border border-[var(--border-subtle)] bg-[var(--surface)] px-2 py-0.5 text-xs text-[var(--text-secondary)] font-mono"
                  >
                    {comp}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Risks & Mitigations */}
          {opportunity.risks && opportunity.risks.length > 0 && (
            <div>
              <h4 className="font-mono text-[10px] font-bold uppercase tracking-wider text-red-400/90">
                EXECUTION & MARKET RISKS
              </h4>
              <ul className="mt-2 space-y-1.5">
                {opportunity.risks.map((risk, i) => (
                  <li key={i} className="flex items-start gap-2 text-xs text-[var(--text-secondary)]">
                    <span className="text-red-400 text-xs">⚠</span>
                    <span>{risk}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Direct Citations / Evidence */}
          {opportunity.evidence && opportunity.evidence.length > 0 && (
            <div>
              <h4 className="font-mono text-[10px] font-bold uppercase tracking-wider text-[var(--success)]">
                CORROBORATING SOURCES
              </h4>
              <ul className="mt-2 space-y-1.5">
                {opportunity.evidence.map((ev, i) => (
                  <li key={i} className="text-xs text-[var(--text-secondary)]">
                    {ev.startsWith("http") ? (
                      <a
                        href={ev}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-[var(--accent)] hover:underline inline-flex items-center gap-1 font-mono text-[11px]"
                      >
                        <span>🔗 {ev}</span>
                      </a>
                    ) : (
                      <span className="font-mono text-[11px] text-[var(--muted)]">
                        • {ev}
                      </span>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </article>
  );
}
