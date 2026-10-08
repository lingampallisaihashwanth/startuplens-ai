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
  const { research, analysis, opportunities, sources } = data;
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
                INTELLIGENCE BRIEFING
              </span>
              <span className="text-xs text-[var(--muted)]">·</span>
              <span className="text-xs text-[var(--muted)] font-mono">
                {formattedCollected}
              </span>
            </div>

            <h1 className="text-2xl font-bold tracking-tight text-[var(--foreground)] sm:text-3xl leading-snug">
              {topic}
            </h1>

            <p className="mt-2 text-xs text-[var(--muted)] sm:text-sm leading-relaxed">
              Discover unmet customer needs, market gaps, and startup opportunities grounded in verified web evidence.
            </p>

            {/* Status & Evidence Indicators */}
            <div className="mt-4 flex flex-wrap items-center gap-2 text-xs">
              <div className="inline-flex items-center gap-1.5 rounded-full border border-[var(--border)] bg-[var(--surface-raised)] px-2.5 py-1 text-[11px] font-medium text-[var(--foreground)]">
                <span className="h-1.5 w-1.5 rounded-full bg-[var(--success)]" />
                <span>Research complete</span>
              </div>

              <div className="inline-flex items-center gap-1.5 rounded-full border border-[var(--border)] bg-[var(--surface-raised)] px-2.5 py-1 text-[11px] text-[var(--text-secondary)]">
                <span className="font-semibold text-[var(--foreground)]">{sources.length}</span>
                <span>verified sources</span>
              </div>

              <div className="inline-flex items-center gap-1.5 rounded-full border border-[var(--border)] bg-[var(--surface-raised)] px-2.5 py-1 text-[11px] text-[var(--text-secondary)]">
                <span className="font-semibold text-[var(--foreground)]">{opportunities.length}</span>
                <span>opportunities</span>
              </div>

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
                RESEARCH STATUS
              </span>
            </div>

            <div className="flex flex-wrap items-center gap-3 sm:gap-6 font-mono text-[11px]">
              <div className="flex items-center gap-1.5 text-[var(--foreground)]">
                <span className="text-[var(--muted)]">Web Research</span>
                <span className="text-[var(--success)] font-semibold">✓ Complete</span>
              </div>
              <div className="flex items-center gap-1.5 text-[var(--foreground)]">
                <span className="text-[var(--muted)]">Market Analysis</span>
                <span className="text-[var(--success)] font-semibold">✓ Complete</span>
              </div>
              <div className="flex items-center gap-1.5 text-[var(--foreground)]">
                <span className="text-[var(--muted)]">Opportunity Engine</span>
                <span className="text-[var(--success)] font-semibold">✓ Complete</span>
              </div>
              <div className="flex items-center gap-1.5 text-[var(--foreground)]">
                <span className="text-[var(--muted)]">Evidence</span>
                <span className="text-[var(--success)] font-semibold">✓ Verified</span>
              </div>
            </div>
          </div>
        </div>
      </section>

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

function generateMarkdown(topic: string, data: AnalyzeResponse): string {
  const { research, analysis, opportunities, sources } = data;
  let md = `# StartupLens AI Intelligence Dossier: ${topic}\n\n`;
  md += `*Collected: ${data.retrieved_at || data.created_at || "N/A"}*\n\n`;

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

  md += `## 4. Sources\n\n`;
  sources?.forEach((s) => {
    md += `- [${s.title}](${s.url}) (${(s.source_type || "web").toUpperCase()})\n`;
  });

  return md;
}
