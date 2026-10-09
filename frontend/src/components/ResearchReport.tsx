"use client";

import React, { useState } from "react";
import { AnalyzeResponse, Opportunity, exportSession } from "@/lib/api";
import { OpportunityCard } from "./OpportunityCard";
import { OpportunityComparison } from "./OpportunityComparison";
import { Sources } from "./Sources";

interface ResearchReportProps {
  data: AnalyzeResponse;
  topic: string;
  savedOpportunityTitles?: Set<string>;
  onToggleSaveOpportunity?: (opp: Opportunity) => void;
  onTrackTopic?: (topic: string) => void;
}

export function ResearchReport({
  data,
  topic,
  savedOpportunityTitles = new Set(),
  onToggleSaveOpportunity,
  onTrackTopic,
}: ResearchReportProps) {
  const { research, analysis, opportunities = [], sources = [], company_analysis } = data;
  const [copied, setCopied] = useState(false);
  const [exportingFmt, setExportingFmt] = useState<string | null>(null);
  const [selectedForCompare, setSelectedForCompare] = useState<Opportunity[]>([]);
  const [showCompareModal, setShowCompareModal] = useState(false);
  const [trackingDone, setTrackingDone] = useState(false);

  const handleCopyMarkdown = () => {
    const md = generateMarkdown(topic, data);
    navigator.clipboard.writeText(md);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleExport = async (format: "pdf" | "markdown" | "json") => {
    if (!data.session_id) return;
    setExportingFmt(format);
    try {
      const blob = await exportSession(data.session_id, format);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      const ext = format === "markdown" ? "md" : format;
      a.download = `startuplens_${topic.replace(/\s+/g, "_").toLowerCase()}.${ext}`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Export failed";
      alert(`Export failed: ${msg}`);
    } finally {
      setExportingFmt(null);
    }
  };

  const handleToggleCompare = (opp: Opportunity) => {
    setSelectedForCompare((prev) => {
      const exists = prev.some((o) => o.title === opp.title);
      if (exists) {
        return prev.filter((o) => o.title !== opp.title);
      }
      if (prev.length >= 3) {
        alert("You can compare up to 3 opportunities at once.");
        return prev;
      }
      return [...prev, opp];
    });
  };

  const handleTrack = () => {
    if (onTrackTopic) {
      onTrackTopic(topic);
      setTrackingDone(true);
    }
  };

  const collectedTime = data.retrieved_at || data.created_at;
  const formattedCollected = collectedTime
    ? new Date(collectedTime).toLocaleString(undefined, {
        dateStyle: "medium",
        timeStyle: "short",
      })
    : "Live session";

  const modelDisplay = data.provider_used
    ? `${data.provider_used} · ${data.model_used}`
    : data.model_used || "Auto";

  return (
    <div className="w-full space-y-7">
      {/* ── 1. HERO RESEARCH HEADER ────────────────────────────────────────── */}
      <div className="motion-section-1 relative overflow-hidden rounded-2xl border border-[var(--border)] bg-[var(--surface)] p-6 sm:p-8 console-grid shadow-xs">
        {/* Subtle animated intelligence scanline */}
        <div className="console-radar-line" aria-hidden="true" />

        <div className="relative z-10 flex flex-col justify-between gap-6 md:flex-row md:items-start">
          <div className="max-w-2xl">
            <div className="flex flex-wrap items-center gap-2 mb-3">
              <span className="rounded bg-[var(--accent-subtle)] border border-[var(--accent)]/30 px-2 py-0.5 text-[10px] font-mono font-bold uppercase tracking-widest text-[var(--accent)]">
                {company_analysis ? "COMPANY INTELLIGENCE" : "INTELLIGENCE BRIEFING"}
              </span>
              <span className="text-xs text-[var(--muted)]">·</span>
              <span className="text-xs text-[var(--muted)] font-mono">
                {formattedCollected}
              </span>
            </div>

            <h1 className="text-2xl font-bold tracking-tight text-[var(--foreground)] sm:text-3xl leading-snug">
              {company_analysis?.company_name || topic}
            </h1>

            <p className="mt-2 text-xs text-[var(--muted)] sm:text-sm leading-relaxed">
              {company_analysis?.overview || "Discover unmet customer needs, market gaps, and startup opportunities grounded in verified web evidence."}
            </p>

            {/* Status & Evidence Indicators */}
            <div className="mt-4 flex flex-wrap items-center gap-2 text-xs">
              <div className="inline-flex items-center gap-1.5 rounded-full border border-[var(--border)] bg-[var(--surface-raised)] px-2.5 py-1 text-[11px] font-medium text-[var(--foreground)]">
                <span className="h-1.5 w-1.5 rounded-full bg-[var(--success)]" />
                <span>{company_analysis ? "Company analysis complete" : "Research complete"}</span>
              </div>

              <div className="inline-flex items-center gap-1.5 rounded-full border border-[var(--border)] bg-[var(--surface-raised)] px-2.5 py-1 text-[11px] text-[var(--text-secondary)]">
                <span className="font-semibold text-[var(--foreground)]">{sources.length}</span>
                <span>verified sources</span>
              </div>

              {opportunities.length > 0 && (
                <div className="inline-flex items-center gap-1.5 rounded-full border border-[var(--border)] bg-[var(--surface-raised)] px-2.5 py-1 text-[11px] text-[var(--text-secondary)]">
                  <span className="font-semibold text-[var(--foreground)]">{opportunities.length}</span>
                  <span>opportunities</span>
                </div>
              )}

              <div className="inline-flex items-center gap-1.5 rounded-full border border-[var(--border)] bg-[var(--surface-raised)] px-2.5 py-1 text-[11px] text-[var(--text-secondary)] font-mono">
                <span>AI Model:</span>
                <span className="text-[var(--foreground)] font-semibold">{modelDisplay}</span>
              </div>
            </div>
          </div>

          {/* Action buttons: Track Research, Export formats, Copy */}
          <div className="flex flex-wrap items-center gap-2 shrink-0">
            {onTrackTopic && (
              <button
                type="button"
                onClick={handleTrack}
                disabled={trackingDone}
                className={`flex items-center gap-1.5 rounded-xl border px-3 py-1.5 text-xs font-medium transition-colors duration-180 ${
                  trackingDone
                    ? "border-[var(--success)]/40 bg-[var(--success)]/10 text-[var(--success)]"
                    : "border-[var(--border)] bg-[var(--surface-raised)] text-[var(--text-secondary)] hover:text-[var(--foreground)] hover:bg-[var(--surface-hover)]"
                }`}
              >
                <span>{trackingDone ? "✓ Tracking Active" : "📡 Track Research"}</span>
              </button>
            )}

            {/* Export Dropdown / Buttons */}
            <div className="inline-flex rounded-xl border border-[var(--border)] bg-[var(--surface-raised)] p-0.5 text-xs">
              <button
                type="button"
                onClick={() => handleExport("pdf")}
                disabled={exportingFmt === "pdf"}
                className="px-2.5 py-1 font-medium text-[var(--text-secondary)] hover:text-[var(--foreground)] hover:bg-[var(--surface-hover)] rounded-lg transition-colors duration-140"
                title="Export formatted PDF"
              >
                {exportingFmt === "pdf" ? "PDF..." : "PDF"}
              </button>
              <button
                type="button"
                onClick={() => handleExport("markdown")}
                disabled={exportingFmt === "markdown"}
                className="px-2.5 py-1 font-medium text-[var(--text-secondary)] hover:text-[var(--foreground)] hover:bg-[var(--surface-hover)] rounded-lg transition-colors duration-140"
                title="Export Markdown"
              >
                {exportingFmt === "markdown" ? "MD..." : "MD"}
              </button>
              <button
                type="button"
                onClick={() => handleExport("json")}
                disabled={exportingFmt === "json"}
                className="px-2.5 py-1 font-medium text-[var(--text-secondary)] hover:text-[var(--foreground)] hover:bg-[var(--surface-hover)] rounded-lg transition-colors duration-140"
                title="Export structured JSON"
              >
                {exportingFmt === "json" ? "JSON..." : "JSON"}
              </button>
            </div>

            <button
              type="button"
              onClick={handleCopyMarkdown}
              aria-label="Copy markdown"
              className="flex items-center gap-1.5 rounded-xl border border-[var(--border)] bg-[var(--surface-raised)] px-3 py-1.5 text-xs font-medium text-[var(--text-secondary)] hover:text-[var(--foreground)] hover:bg-[var(--surface-hover)] transition-colors duration-140 active:scale-95"
            >
              {copied ? (
                <span className="text-[var(--success)] font-medium">Copied!</span>
              ) : (
                <span>Copy</span>
              )}
            </button>
          </div>
        </div>
      </div>

      {/* ── 2. COMPACT INTELLIGENCE STATUS STRIP ───────────────────────────── */}
      <section aria-labelledby="heading-status" className="motion-section-1">
        <div className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-3">
          <div className="flex flex-wrap items-center justify-between gap-3 text-xs">
            <div className="flex items-center gap-2">
              <span className="text-[10px] font-mono font-bold uppercase tracking-wider text-[var(--muted)]">
                {company_analysis ? "COMPANY DOSSIER STATUS" : "RESEARCH STATUS"}
              </span>
            </div>

            <div className="flex flex-wrap items-center gap-3 sm:gap-6 font-mono text-[11px]">
              <div className="flex items-center gap-1.5 text-[var(--foreground)]">
                <span className="text-[var(--muted)]">Web Research</span>
                <span className="text-[var(--success)] font-semibold">✓ Complete</span>
              </div>
              <div className="flex items-center gap-1.5 text-[var(--foreground)]">
                <span className="text-[var(--muted)]">{company_analysis ? "Company Dossier" : "Market Analysis"}</span>
                <span className="text-[var(--success)] font-semibold">✓ Complete</span>
              </div>
              {!company_analysis && (
                <div className="flex items-center gap-1.5 text-[var(--foreground)]">
                  <span className="text-[var(--muted)]">Opportunity Engine</span>
                  <span className="text-[var(--success)] font-semibold">✓ Complete</span>
                </div>
              )}
              {company_analysis && (
                <div className="flex items-center gap-1.5 text-[var(--foreground)]">
                  <span className="text-[var(--muted)]">Evidence Classification</span>
                  <span className="text-[var(--success)] font-semibold">✓ Verified</span>
                </div>
              )}
              <div className="flex items-center gap-1.5 text-[var(--foreground)]">
                <span className="text-[var(--muted)]">Evidence</span>
                <span className="text-[var(--success)] font-semibold">✓ Verified</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ── COMPANY ANALYSIS DOSSIER (IF APPLICABLE) ────────────────────────── */}
      {company_analysis ? (
        <CompanyDossier analysis={company_analysis} />
      ) : (
        <>
          {/* ── 3. RESEARCH FINDINGS (RESEARCH SIGNALS) ─────────────────────────── */}
          <section aria-labelledby="heading-signals" className="motion-section-2">
            <div className="mb-3 flex items-center justify-between">
              <div>
                <h2 id="heading-signals" className="text-sm font-bold uppercase tracking-wider text-[var(--foreground)]">
                  RESEARCH SIGNALS
                </h2>
                <p className="text-[11px] text-[var(--muted)]">What the evidence is telling us</p>
              </div>
              <span className="rounded bg-[var(--surface-raised)] border border-[var(--border-subtle)] px-2 py-0.5 text-[10px] font-mono font-semibold uppercase tracking-wider text-[var(--accent)]">
                EVIDENCE • Grounded Signals
              </span>
            </div>

            {/* 2x2 Grid Layout */}
            <div className="grid grid-cols-1 items-start gap-4 sm:grid-cols-2">
              {/* Top-Left: Emerging Trends */}
              <SignalModule
                title="EMERGING TRENDS"
                items={research.trends}
                accentColor="var(--accent)"
                evidenceLabel="Market Trend"
              />

              {/* Top-Right: Active Startups */}
              <StartupModule
                title="ACTIVE STARTUPS"
                items={research.startups}
                statusColor="var(--success)"
              />

              {/* Bottom-Left: Customer Problems */}
              <SignalModule
                title="CUSTOMER PROBLEMS"
                items={research.problems}
                accentColor="var(--warning)"
                evidenceLabel="Friction Point"
              />

              {/* Bottom-Right: Market Signals */}
              <SignalModule
                title="MARKET SIGNALS"
                items={research.market_signals}
                accentColor="#a78bfa"
                evidenceLabel="Observed Signal"
              />
            </div>
          </section>

          {/* ── 4. MARKET ANALYSIS (MARKET INTELLIGENCE) ───────────────────────── */}
          <section aria-labelledby="heading-intelligence" className="motion-section-3">
            <div className="mb-3 flex items-center justify-between">
              <div>
                <h2 id="heading-intelligence" className="text-sm font-bold uppercase tracking-wider text-[var(--foreground)]">
                  MARKET INTELLIGENCE
                </h2>
                <p className="text-[11px] text-[var(--muted)]">Strategic landscape decomposition</p>
              </div>
              <span className="rounded bg-[var(--surface-raised)] border border-[var(--border-subtle)] px-2 py-0.5 text-[10px] font-mono font-semibold uppercase tracking-wider text-[var(--muted)]">
                SYNTHESIS • 4 Structural Modules
              </span>
            </div>

            {/* 4 Strong Modules */}
            <div className="grid grid-cols-1 items-start gap-4 sm:grid-cols-2">
              {/* Module 1: Customers */}
              <MarketIntelligenceModule
                label="CUSTOMERS"
                subtext="Who has the problem?"
                items={analysis.customer_segments}
                accentColor="var(--accent)"
                badgeText="Target Profiles"
              />

              {/* Module 2: Competition */}
              <MarketIntelligenceModule
                label="COMPETITION"
                subtext="Who is solving it?"
                items={analysis.competitors}
                accentColor="var(--muted)"
                badgeText="Incumbent Landscape"
              />

              {/* Module 3: Gaps */}
              <MarketIntelligenceModule
                label="GAPS"
                subtext="What remains underserved?"
                items={analysis.market_gaps}
                accentColor="var(--success)"
                badgeText="White Space"
              />

              {/* Module 4: Why Now */}
              <MarketIntelligenceModule
                label="WHY NOW"
                subtext="Why is this opportunity timely?"
                items={analysis.why_now}
                accentColor="#a78bfa"
                badgeText="Adoption Catalyst"
              />
            </div>
          </section>

          {/* ── 5. STARTUP OPPORTUNITIES (HERO SECTION) ─────────────────────────── */}
          {opportunities.length > 0 && (
            <section aria-labelledby="heading-opportunities" className="motion-section-4">
              <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
                <div>
                  <h2 id="heading-opportunities" className="text-base font-bold uppercase tracking-wider text-[var(--foreground)] sm:text-lg">
                    STARTUP OPPORTUNITIES
                  </h2>
                  <p className="text-xs text-[var(--muted)]">Evidence-informed hypotheses worth exploring</p>
                </div>

                <div className="flex items-center gap-2">
                  {selectedForCompare.length >= 2 && (
                    <button
                      type="button"
                      onClick={() => setShowCompareModal(true)}
                      className="rounded-xl bg-[var(--accent)] px-3.5 py-1.5 text-xs font-semibold text-[var(--background)] shadow-sm hover:bg-[var(--accent-hover)] transition-all duration-180 ease-out active:scale-95"
                    >
                      Compared · {selectedForCompare.length} →
                    </button>
                  )}
                  <span className="rounded bg-[var(--surface-raised)] border border-[var(--border-subtle)] px-2.5 py-1 text-[10px] font-mono font-semibold uppercase tracking-wider text-[var(--warning)]">
                    {opportunities.length} HYPOTHESES
                  </span>
                </div>
              </div>

              <div className="space-y-4">
                {opportunities.map((opp, i) => (
                  <OpportunityCard
                    key={`${opp.title}-${i}`}
                    opportunity={opp}
                    index={i}
                    isTopSignal={i === 0}
                    isSaved={savedOpportunityTitles.has(opp.title)}
                    onToggleSave={onToggleSaveOpportunity}
                    isSelectedForCompare={selectedForCompare.some((o) => o.title === opp.title)}
                    onToggleCompare={handleToggleCompare}
                  />
                ))}
              </div>
            </section>
          )}
        </>
      )}

      {/* Comparison Modal */}
      {showCompareModal && (
        <OpportunityComparison
          opportunities={selectedForCompare}
          onClose={() => setShowCompareModal(false)}
        />
      )}

      {/* ── 6. SOURCES (VERIFIED EVIDENCE) ─────────────────────────────────── */}
      {sources.length > 0 && (
        <div className="motion-section-5">
          <Sources sources={sources} />
        </div>
      )}
    </div>
  );
}

// ─── Sub-Components ───────────────────────────────────────────────────────────

function SignalModule({
  title,
  items,
  accentColor,
  evidenceLabel,
}: {
  title: string;
  items: string[];
  accentColor: string;
  evidenceLabel: string;
}) {
  return (
    <div className="research-card rounded-xl border border-[var(--border)] bg-[var(--surface)] p-4 sm:p-5 transition-all">
      <div className="mb-3 flex items-center justify-between border-b border-[var(--border-subtle)] pb-2.5">
        <div className="flex items-center gap-2">
          <span className="h-1.5 w-1.5 rounded-full" style={{ backgroundColor: accentColor }} aria-hidden="true" />
          <h3 className="text-xs font-bold uppercase tracking-wider text-[var(--foreground)]">
            {title}
          </h3>
        </div>
        <span className="rounded bg-[var(--surface-raised)] border border-[var(--border-subtle)] px-1.5 py-0.2 font-mono text-[9px] text-[var(--muted)]">
          {evidenceLabel}
        </span>
      </div>

      {!items || items.length === 0 ? (
        <p className="text-xs text-[var(--muted)] italic">Insufficient recent evidence found.</p>
      ) : (
        <div className="space-y-2">
          {items.map((item, i) => (
            <div
              key={i}
              className="group flex items-start gap-2.5 text-xs text-[var(--text-secondary)] transition-colors hover:text-[var(--foreground)]"
            >
              <span
                className="mt-0.5 font-mono text-[10px] font-semibold tabular-nums shrink-0"
                style={{ color: accentColor }}
              >
                {String(i + 1).padStart(2, "0")}
              </span>
              <span className="leading-relaxed">{item}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function StartupModule({
  title,
  items,
  statusColor,
}: {
  title: string;
  items: string[];
  statusColor: string;
}) {
  return (
    <div className="research-card rounded-xl border border-[var(--border)] bg-[var(--surface)] p-4 sm:p-5 transition-all">
      <div className="mb-3 flex items-center justify-between border-b border-[var(--border-subtle)] pb-2.5">
        <div className="flex items-center gap-2">
          <span className="h-1.5 w-1.5 rounded-full" style={{ backgroundColor: statusColor }} aria-hidden="true" />
          <h3 className="text-xs font-bold uppercase tracking-wider text-[var(--foreground)]">
            {title}
          </h3>
        </div>
        <span className="rounded bg-[var(--surface-raised)] border border-[var(--border-subtle)] px-1.5 py-0.2 font-mono text-[9px] text-[var(--muted)]">
          Verified Entities
        </span>
      </div>

      {!items || items.length === 0 ? (
        <p className="text-xs text-[var(--muted)] italic">Landscape nascent or fragmented.</p>
      ) : (
        <div className="flex flex-wrap gap-2">
          {items.map((item, i) => (
            <span
              key={i}
              className="inline-flex items-center gap-1.5 rounded-lg border border-[var(--border)] bg-[var(--surface-raised)] px-2.5 py-1 text-xs font-medium text-[var(--foreground)] hover:border-[var(--accent)]/40 transition-colors"
            >
              <span className="h-1.5 w-1.5 rounded-full bg-[var(--success)]" aria-hidden="true" />
              {item}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

function MarketIntelligenceModule({
  label,
  subtext,
  items,
  accentColor,
  badgeText,
}: {
  label: string;
  subtext: string;
  items: string[];
  accentColor: string;
  badgeText: string;
}) {
  return (
    <div className="research-card rounded-xl border border-[var(--border)] bg-[var(--surface)] p-4 sm:p-5 transition-all">
      <div className="mb-3 flex items-start justify-between border-b border-[var(--border-subtle)] pb-2.5">
        <div>
          <h3 className="text-xs font-bold uppercase tracking-wider text-[var(--foreground)]">
            {label}
          </h3>
          <p className="text-[10px] text-[var(--muted)]">{subtext}</p>
        </div>
        <span
          className="rounded px-1.5 py-0.2 font-mono text-[9px] font-semibold uppercase tracking-wider"
          style={{ backgroundColor: `color-mix(in srgb, ${accentColor} 12%, transparent)`, color: accentColor }}
        >
          {badgeText}
        </span>
      </div>

      {!items || items.length === 0 ? (
        <p className="text-xs text-[var(--muted)] italic">No explicit signals identified.</p>
      ) : (
        <div className="space-y-2">
          {items.map((item, i) => (
            <div key={i} className="flex items-start gap-2 text-xs text-[var(--text-secondary)]">
              <span className="mt-1 h-1 w-1 shrink-0 rounded-full bg-[var(--muted)]" aria-hidden="true" />
              <span className="leading-relaxed">{item}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function toArray(val: string | string[] | undefined | null): string[] {
  if (!val) return [];
  if (Array.isArray(val)) return val;
  return [val];
}

function CompanyDossier({ analysis }: { analysis: NonNullable<AnalyzeResponse["company_analysis"]> }) {
  return (
    <div className="space-y-6 motion-section-2">
      {/* ── 1. COMPANY OVERVIEW & ORIGINS ── */}
      <section aria-labelledby="heading-dossier-origins">
        <div className="mb-3 flex items-center justify-between">
          <div>
            <h2 id="heading-dossier-origins" className="text-sm font-bold uppercase tracking-wider text-[var(--foreground)]">
              FOUNDING & BUSINESS MODEL
            </h2>
            <p className="text-[11px] text-[var(--muted)]">Core company identity and origin thesis</p>
          </div>
          <span className="rounded bg-[var(--surface-raised)] border border-[var(--border-subtle)] px-2 py-0.5 text-[10px] font-mono font-semibold uppercase tracking-wider text-[var(--accent)]">
            {analysis.company_name}
          </span>
        </div>

        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div className="research-card rounded-xl border border-[var(--border)] bg-[var(--surface)] p-4 sm:p-5">
            <h3 className="text-xs font-bold uppercase tracking-wider text-[var(--accent)] mb-2">Company Overview</h3>
            <p className="text-xs leading-relaxed text-[var(--text-secondary)]">{analysis.overview}</p>
            <div className="mt-4 pt-3 border-t border-[var(--border-subtle)]">
              <h4 className="text-[11px] font-semibold text-[var(--foreground)] mb-1">Founding Story</h4>
              <p className="text-xs leading-relaxed text-[var(--muted)]">{analysis.founding_story}</p>
            </div>
          </div>

          <div className="research-card rounded-xl border border-[var(--border)] bg-[var(--surface)] p-4 sm:p-5">
            <h3 className="text-xs font-bold uppercase tracking-wider text-[var(--accent)] mb-2">Original Problem & Business Model</h3>
            <div className="space-y-3">
              <div>
                <span className="text-[10px] font-mono uppercase text-[var(--muted)]">Original Problem:</span>
                <p className="text-xs leading-relaxed text-[var(--text-secondary)] mt-0.5">{analysis.original_problem}</p>
              </div>
              <div className="pt-2 border-t border-[var(--border-subtle)]">
                <span className="text-[10px] font-mono uppercase text-[var(--muted)]">Business Model:</span>
                <p className="text-xs leading-relaxed text-[var(--text-secondary)] mt-0.5">{analysis.business_model}</p>
              </div>
              <div className="pt-2 border-t border-[var(--border-subtle)]">
                <span className="text-[10px] font-mono uppercase text-[var(--muted)]">Target Customers:</span>
                <div className="flex flex-wrap gap-1.5 mt-1.5">
                  {toArray(analysis.target_customers).map((cust, i) => (
                    <span key={i} className="rounded bg-[var(--surface-raised)] border border-[var(--border-subtle)] px-2 py-0.5 text-[10px] text-[var(--foreground)]">
                      {cust}
                    </span>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ── 2. GROWTH ENGINE & EXPANSION ── */}
      <section aria-labelledby="heading-dossier-growth">
        <div className="mb-3 flex items-center justify-between">
          <div>
            <h2 id="heading-dossier-growth" className="text-sm font-bold uppercase tracking-wider text-[var(--foreground)]">
              GROWTH & SCALE TRAJECTORY
            </h2>
            <p className="text-[11px] text-[var(--muted)]">Expansion playbook, capital strategy, and milestones</p>
          </div>
          <span className="rounded bg-[var(--surface-raised)] border border-[var(--border-subtle)] px-2 py-0.5 text-[10px] font-mono font-semibold uppercase tracking-wider text-[var(--success)]">
            SCALE ENGINE
          </span>
        </div>

        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div className="research-card rounded-xl border border-[var(--border)] bg-[var(--surface)] p-4 sm:p-5">
            <h3 className="text-xs font-bold uppercase tracking-wider text-[var(--success)] mb-2">Early Growth & Strategy</h3>
            <p className="text-xs leading-relaxed text-[var(--text-secondary)] mb-3">{analysis.early_growth}</p>
            <div className="pt-3 border-t border-[var(--border-subtle)]">
              <span className="text-[10px] font-mono uppercase text-[var(--muted)]">Strategy Playbook:</span>
              <p className="text-xs leading-relaxed text-[var(--muted)] mt-1">{analysis.growth_strategy}</p>
            </div>
            <div className="pt-3 mt-3 border-t border-[var(--border-subtle)]">
              <span className="text-[10px] font-mono uppercase text-[var(--muted)]">Funding & Expansion:</span>
              <p className="text-xs leading-relaxed text-[var(--text-secondary)] mt-1">{analysis.funding_and_expansion}</p>
            </div>
          </div>

          <div className="research-card rounded-xl border border-[var(--border)] bg-[var(--surface)] p-4 sm:p-5">
            <h3 className="text-xs font-bold uppercase tracking-wider text-[var(--success)] mb-2">Growth Drivers & Major Milestones</h3>
            <div className="mb-3">
              <span className="text-[10px] font-mono uppercase text-[var(--muted)]">Primary Growth Drivers:</span>
              <div className="space-y-1.5 mt-1.5">
                {analysis.growth_drivers?.map((driver, i) => (
                  <div key={i} className="flex items-start gap-2 text-xs text-[var(--text-secondary)]">
                    <span className="mt-1 h-1.5 w-1.5 shrink-0 rounded-full bg-[var(--success)]" />
                    <span>{driver}</span>
                  </div>
                ))}
              </div>
            </div>
            <div className="pt-3 border-t border-[var(--border-subtle)]">
              <span className="text-[10px] font-mono uppercase text-[var(--muted)]">Key Milestones:</span>
              <div className="space-y-1.5 mt-1.5">
                {analysis.major_milestones?.map((milestone, i) => (
                  <div key={i} className="flex items-start gap-2 text-xs text-[var(--muted)]">
                    <span className="mt-1 font-mono text-[10px] text-[var(--success)]">▸</span>
                    <span>{milestone}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ── 3. TURNING POINTS, COMPETITION & ENVIRONMENT ── */}
      <section aria-labelledby="heading-dossier-landscape">
        <div className="mb-3 flex items-center justify-between">
          <div>
            <h2 id="heading-dossier-landscape" className="text-sm font-bold uppercase tracking-wider text-[var(--foreground)]">
              TURNING POINTS & COMPETITIVE DYNAMICS
            </h2>
            <p className="text-[11px] text-[var(--muted)]">Pivots, market changes, and competitive pressures</p>
          </div>
          <span className="rounded bg-[var(--surface-raised)] border border-[var(--border-subtle)] px-2 py-0.5 text-[10px] font-mono font-semibold uppercase tracking-wider text-[#a78bfa]">
            DYNAMICS
          </span>
        </div>

        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          <div className="research-card rounded-xl border border-[var(--border)] bg-[var(--surface)] p-4">
            <h3 className="text-xs font-bold uppercase tracking-wider text-[#a78bfa] mb-2">Turning Points</h3>
            <div className="space-y-2">
              {analysis.turning_points?.map((item, i) => (
                <div key={i} className="text-xs text-[var(--text-secondary)] flex items-start gap-1.5">
                  <span className="mt-1 h-1 w-1 shrink-0 rounded-full bg-[#a78bfa]" />
                  <span>{item}</span>
                </div>
              ))}
            </div>
          </div>

          <div className="research-card rounded-xl border border-[var(--border)] bg-[var(--surface)] p-4">
            <h3 className="text-xs font-bold uppercase tracking-wider text-[#a78bfa] mb-2">Market Changes</h3>
            <div className="space-y-2">
              {toArray(analysis.market_changes).map((item, i) => (
                <div key={i} className="text-xs text-[var(--text-secondary)] flex items-start gap-1.5">
                  <span className="mt-1 h-1 w-1 shrink-0 rounded-full bg-[#a78bfa]" />
                  <span>{item}</span>
                </div>
              ))}
            </div>
          </div>

          <div className="research-card rounded-xl border border-[var(--border)] bg-[var(--surface)] p-4">
            <h3 className="text-xs font-bold uppercase tracking-wider text-[#a78bfa] mb-2">Competitive Landscape</h3>
            <div className="space-y-2">
              {toArray(analysis.competition).map((item, i) => (
                <div key={i} className="text-xs text-[var(--text-secondary)] flex items-start gap-1.5">
                  <span className="mt-1 h-1 w-1 shrink-0 rounded-full bg-[#a78bfa]" />
                  <span>{item}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* ── 4. CHALLENGES, DECLINE & CURRENT STATUS ── */}
      <section aria-labelledby="heading-dossier-decline">
        <div className="mb-3 flex items-center justify-between">
          <div>
            <h2 id="heading-dossier-decline" className="text-sm font-bold uppercase tracking-wider text-[var(--foreground)]">
              VULNERABILITIES & REASONS FOR DECLINE
            </h2>
            <p className="text-[11px] text-[var(--muted)]">Strategic friction, business pitfalls, and current status</p>
          </div>
          <span className="rounded bg-[var(--surface-raised)] border border-[var(--border-subtle)] px-2 py-0.5 text-[10px] font-mono font-semibold uppercase tracking-wider text-[var(--warning)]">
            RISK & POST-MORTEM
          </span>
        </div>

        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div className="research-card rounded-xl border border-[var(--border)] bg-[var(--surface)] p-4 sm:p-5">
            <h3 className="text-xs font-bold uppercase tracking-wider text-[var(--warning)] mb-3">Warning Signs & Strategic Mistakes</h3>
            <div className="space-y-3">
              <div>
                <span className="text-[10px] font-mono uppercase text-[var(--muted)]">Early Warning Signs:</span>
                <div className="space-y-1 mt-1">
                  {analysis.warning_signs?.map((sign, i) => (
                    <div key={i} className="flex items-start gap-2 text-xs text-[var(--text-secondary)]">
                      <span className="mt-1 font-mono text-[10px] text-[var(--warning)]">⚠</span>
                      <span>{sign}</span>
                    </div>
                  ))}
                </div>
              </div>
              <div className="pt-2 border-t border-[var(--border-subtle)]">
                <span className="text-[10px] font-mono uppercase text-[var(--muted)]">Strategic Mistakes:</span>
                <div className="space-y-1 mt-1">
                  {analysis.strategic_mistakes?.map((mistake, i) => (
                    <div key={i} className="flex items-start gap-2 text-xs text-[var(--text-secondary)]">
                      <span className="mt-1 font-mono text-[10px] text-[var(--warning)]">✕</span>
                      <span>{mistake}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>

          <div className="research-card rounded-xl border border-[var(--border)] bg-[var(--surface)] p-4 sm:p-5">
            <h3 className="text-xs font-bold uppercase tracking-wider text-[var(--warning)] mb-3">Financial Problems & Decline Causes</h3>
            <div className="space-y-3">
              <div>
                <span className="text-[10px] font-mono uppercase text-[var(--muted)]">Financial & Capital Problems:</span>
                <div className="space-y-1 mt-1">
                  {analysis.financial_problems?.map((prob, i) => (
                    <div key={i} className="flex items-start gap-2 text-xs text-[var(--text-secondary)]">
                      <span className="mt-1 font-mono text-[10px] text-[var(--danger,#f87171)]">▪</span>
                      <span>{prob}</span>
                    </div>
                  ))}
                </div>
              </div>
              <div className="pt-2 border-t border-[var(--border-subtle)]">
                <span className="text-[10px] font-mono uppercase text-[var(--muted)]">Causes of Decline / Failure:</span>
                <div className="space-y-1 mt-1">
                  {analysis.reasons_for_decline_or_failure?.map((cause, i) => (
                    <div key={i} className="flex items-start gap-2 text-xs text-[var(--text-secondary)]">
                      <span className="mt-1 font-mono text-[10px] text-[var(--danger,#f87171)]">▸</span>
                      <span>{cause}</span>
                    </div>
                  ))}
                </div>
              </div>
              <div className="pt-2 border-t border-[var(--border-subtle)]">
                <span className="text-[10px] font-mono uppercase text-[var(--muted)]">Current Operational Status:</span>
                <p className="text-xs text-[var(--foreground)] font-medium mt-1">{analysis.current_status}</p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ── 5. LESSONS FOR FOUNDERS ── */}
      <section aria-labelledby="heading-dossier-lessons">
        <div className="research-card rounded-xl border border-[var(--border)] bg-[var(--surface)] p-5">
          <div className="mb-3 flex items-center justify-between border-b border-[var(--border-subtle)] pb-2.5">
            <div>
              <h3 id="heading-dossier-lessons" className="text-xs font-bold uppercase tracking-wider text-[var(--foreground)]">
                LESSONS FOR FOUNDERS
              </h3>
              <p className="text-[10px] text-[var(--muted)]">Actionable strategic principles extracted from this company&apos;s journey</p>
            </div>
            <span className="rounded bg-[var(--surface-raised)] border border-[var(--border-subtle)] px-2 py-0.5 text-[10px] font-mono font-semibold uppercase tracking-wider text-[var(--accent)]">
              EXECUTIVE TAKEAWAYS
            </span>
          </div>

          <div className="grid grid-cols-1 gap-2.5 sm:grid-cols-2">
            {analysis.lessons_for_founders?.map((lesson, i) => (
              <div key={i} className="flex items-start gap-2.5 rounded-lg border border-[var(--border-subtle)] bg-[var(--surface-raised)] p-3 text-xs text-[var(--text-secondary)]">
                <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-[var(--accent)]/10 text-[10px] font-bold text-[var(--accent)]">
                  {i + 1}
                </span>
                <span className="leading-relaxed">{lesson}</span>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── 6. EVIDENCE TAXONOMY: FACT vs INFERENCE vs HYPOTHESIS ── */}
      <section aria-labelledby="heading-dossier-evidence">
        <div className="mb-3 flex items-center justify-between">
          <div>
            <h2 id="heading-dossier-evidence" className="text-sm font-bold uppercase tracking-wider text-[var(--foreground)]">
              EVIDENCE GROUNDING TAXONOMY
            </h2>
            <p className="text-[11px] text-[var(--muted)]">Strict analytical classification of claims to prevent hallucination</p>
          </div>
          <span className="rounded bg-[var(--surface-raised)] border border-[var(--border-subtle)] px-2 py-0.5 text-[10px] font-mono font-semibold uppercase tracking-wider text-[var(--muted)]">
            EVIDENCE INTEGRITY
          </span>
        </div>

        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          {/* FACTS */}
          <div className="research-card rounded-xl border border-[var(--border)] bg-[var(--surface)] p-4">
            <div className="mb-2.5 flex items-center justify-between border-b border-[var(--border-subtle)] pb-2">
              <span className="text-[11px] font-bold uppercase tracking-wider text-[var(--success)]">
                FACT
              </span>
              <span className="text-[9px] font-mono rounded bg-[var(--success)]/10 text-[var(--success)] px-1.5 py-0.5">
                VERIFIABLE
              </span>
            </div>
            <p className="text-[10px] text-[var(--muted)] mb-2.5">Empirical events, reported figures, and corporate actions.</p>
            <div className="space-y-2">
              {analysis.facts?.map((f, i) => (
                <div key={i} className="flex items-start gap-1.5 text-xs text-[var(--text-secondary)]">
                  <span className="mt-1 h-1.5 w-1.5 shrink-0 rounded-full bg-[var(--success)]" />
                  <span className="leading-relaxed">{f}</span>
                </div>
              ))}
            </div>
          </div>

          {/* INFERENCES */}
          <div className="research-card rounded-xl border border-[var(--border)] bg-[var(--surface)] p-4">
            <div className="mb-2.5 flex items-center justify-between border-b border-[var(--border-subtle)] pb-2">
              <span className="text-[11px] font-bold uppercase tracking-wider text-[#a78bfa]">
                INFERENCE
              </span>
              <span className="text-[9px] font-mono rounded bg-[#a78bfa]/10 text-[#a78bfa] px-1.5 py-0.5">
                DERIVED
              </span>
            </div>
            <p className="text-[10px] text-[var(--muted)] mb-2.5">Analytical conclusions deduced directly from observed patterns.</p>
            <div className="space-y-2">
              {analysis.inferences?.map((inf, i) => (
                <div key={i} className="flex items-start gap-1.5 text-xs text-[var(--text-secondary)]">
                  <span className="mt-1 h-1.5 w-1.5 shrink-0 rounded-full bg-[#a78bfa]" />
                  <span className="leading-relaxed">{inf}</span>
                </div>
              ))}
            </div>
          </div>

          {/* HYPOTHESES */}
          <div className="research-card rounded-xl border border-[var(--border)] bg-[var(--surface)] p-4">
            <div className="mb-2.5 flex items-center justify-between border-b border-[var(--border-subtle)] pb-2">
              <span className="text-[11px] font-bold uppercase tracking-wider text-[var(--warning)]">
                HYPOTHESIS
              </span>
              <span className="text-[9px] font-mono rounded bg-[var(--warning)]/10 text-[var(--warning)] px-1.5 py-0.5">
                PROVISIONAL
              </span>
            </div>
            <p className="text-[10px] text-[var(--muted)] mb-2.5">Plausible interpretations subject to further corroboration.</p>
            <div className="space-y-2">
              {analysis.hypotheses?.map((hyp, i) => (
                <div key={i} className="flex items-start gap-1.5 text-xs text-[var(--text-secondary)]">
                  <span className="mt-1 h-1.5 w-1.5 shrink-0 rounded-full bg-[var(--warning)]" />
                  <span className="leading-relaxed">{hyp}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}

function generateMarkdown(topic: string, data: AnalyzeResponse): string {
  const { research, analysis, opportunities, sources, company_analysis } = data;
  let md = `# StartupLens AI Intelligence Dossier: ${topic}\n\n`;
  md += `*Collected: ${data.retrieved_at || data.created_at || "N/A"}*\n\n`;

  if (company_analysis) {
    md += `## Company Analysis: ${company_analysis.company_name}\n\n`;
    md += `### Overview\n${company_analysis.overview}\n\n`;
    md += `### Founding Story\n${company_analysis.founding_story}\n\n`;
    md += `### Original Problem\n${company_analysis.original_problem}\n\n`;
    md += `### Business Model\n${company_analysis.business_model}\n\n`;
    md += `### Target Customers\n`;
    toArray(company_analysis.target_customers).forEach((c) => (md += `- ${c}\n`));
    md += `\n### Early Growth\n${company_analysis.early_growth}\n\n`;
    md += `### Growth Strategy\n${company_analysis.growth_strategy}\n\n`;
    md += `### Funding & Expansion\n${company_analysis.funding_and_expansion}\n\n`;
    md += `### Major Milestones\n`;
    company_analysis.major_milestones?.forEach((m) => (md += `- ${m}\n`));
    md += `\n### Growth Drivers\n`;
    company_analysis.growth_drivers?.forEach((g) => (md += `- ${g}\n`));
    md += `\n### Turning Points\n`;
    company_analysis.turning_points?.forEach((t) => (md += `- ${t}\n`));
    md += `\n### Warning Signs\n`;
    company_analysis.warning_signs?.forEach((w) => (md += `- ${w}\n`));
    md += `\n### Competition\n`;
    toArray(company_analysis.competition).forEach((comp) => (md += `- ${comp}\n`));
    md += `\n### Market Changes\n`;
    toArray(company_analysis.market_changes).forEach((mc) => (md += `- ${mc}\n`));
    md += `\n### Strategic Mistakes\n`;
    company_analysis.strategic_mistakes?.forEach((sm) => (md += `- ${sm}\n`));
    md += `\n### Financial & Business Problems\n`;
    company_analysis.financial_problems?.forEach((fp) => (md += `- ${fp}\n`));
    md += `\n### Reasons for Decline or Failure\n`;
    company_analysis.reasons_for_decline_or_failure?.forEach((r) => (md += `- ${r}\n`));
    md += `\n### Current Status\n${company_analysis.current_status}\n\n`;
    md += `### Lessons for Founders\n`;
    company_analysis.lessons_for_founders?.forEach((l) => (md += `- ${l}\n`));
    md += `\n### Evidence Grounding (Facts)\n`;
    company_analysis.facts?.forEach((f) => (md += `- ${f}\n`));
    md += `\n### Evidence Grounding (Inferences)\n`;
    company_analysis.inferences?.forEach((inf) => (md += `- ${inf}\n`));
    md += `\n### Evidence Grounding (Hypotheses)\n`;
    company_analysis.hypotheses?.forEach((h) => (md += `- ${h}\n`));
    md += `\n`;
  } else {
    md += `## 1. Research Findings (Facts)\n\n`;
    md += `### Emerging Trends\n`;
    research.trends?.forEach((t) => (md += `- ${t}\n`));
    md += `\n### Active Startups\n`;
    research.startups?.forEach((s) => (md += `- ${s}\n`));
    md += `\n### Customer Problems\n`;
    research.problems?.forEach((p) => (md += `- ${p}\n`));
    md += `\n### Market Signals\n`;
    research.market_signals?.forEach((m) => (md += `- ${m}\n`));

    md += `\n## 2. Market Analysis (Interpretations)\n\n`;
    md += `### Customer Segments\n`;
    analysis.customer_segments?.forEach((c) => (md += `- ${c}\n`));
    md += `\n### Competitors\n`;
    analysis.competitors?.forEach((comp) => (md += `- ${comp}\n`));
    md += `\n### Market Gaps\n`;
    analysis.market_gaps?.forEach((g) => (md += `- ${g}\n`));
    md += `\n### Why Now Drivers\n`;
    analysis.why_now?.forEach((w) => (md += `- ${w}\n`));

    md += `\n## 3. Startup Opportunity Hypotheses & Validation\n\n`;
    opportunities?.forEach((opp, i) => {
      md += `### ${i + 1}. ${opp.title}\n`;
      if (opp.score) {
        md += `**Score:** ${opp.score.overall_score}/50 (${opp.score.confidence_label})\n`;
      }
      md += `**Target Customer:** ${opp.customer}\n`;
      md += `**Problem:** ${opp.problem}\n`;
      md += `**Solution:** ${opp.solution}\n`;
      md += `**Why Now:** ${opp.why_now}\n\n`;
    });
  }

  md += `## Sources\n\n`;
  sources?.forEach((s) => {
    md += `- [${s.title}](${s.url}) (${(s.source_type || "web").toUpperCase()})\n`;
  });

  return md;
}
