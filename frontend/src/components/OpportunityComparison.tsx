"use client";

import React from "react";
import { Opportunity } from "@/lib/api";

interface OpportunityComparisonProps {
  opportunities: Opportunity[];
  onClose: () => void;
}

export function OpportunityComparison({ opportunities, onClose }: OpportunityComparisonProps) {
  if (opportunities.length < 2) return null;

  // Compute key analytical takeaways
  const bestForMvp = [...opportunities].sort(
    (a, b) => (b.score?.execution_feasibility || 0) - (a.score?.execution_feasibility || 0)
  )[0];

  const lowestComp = [...opportunities].sort(
    (a, b) => (b.score?.competitive_pressure || 0) - (a.score?.competitive_pressure || 0)
  )[0];

  const highestDemand = [...opportunities].sort(
    (a, b) => (b.score?.market_demand || 0) - (a.score?.market_demand || 0)
  )[0];

  const highestRisk = [...opportunities].sort(
    (a, b) => (b.risks?.length || 0) - (a.risks?.length || 0)
  )[0];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4 backdrop-blur-xs motion-backdrop">
      <div className="relative flex max-h-[90vh] w-full max-w-4xl flex-col rounded-2xl border border-[var(--border)] bg-[var(--surface)] p-6 shadow-2xl motion-modal-surface">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-[var(--border)] pb-4">
          <div>
            <h2 className="text-lg font-bold text-[var(--foreground)]">Compare Opportunities</h2>
            <p className="text-xs text-[var(--muted)]">
              Analytical side-by-side comparison across 5 evidence-backed validation dimensions.
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="flex h-8 w-8 items-center justify-center rounded-lg text-[var(--muted)] hover:bg-[var(--surface-hover)] hover:text-[var(--foreground)]"
            aria-label="Close comparison"
          >
            ✕
          </button>
        </div>

        {/* Analytical Guidance Highlights */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5 my-4">
          <div className="rounded-xl border border-[var(--border)] bg-[var(--surface-raised)] p-2.5">
            <span className="text-[10px] font-bold uppercase tracking-wider text-[var(--success)]">
              Best for fast MVP
            </span>
            <p className="mt-1 text-xs font-semibold truncate text-[var(--foreground)]" title={bestForMvp.title}>
              {bestForMvp.title}
            </p>
            <span className="text-[10px] text-[var(--muted)]">
              Feasibility: {bestForMvp.score?.execution_feasibility || "N/A"}/10
            </span>
          </div>

          <div className="rounded-xl border border-[var(--border)] bg-[var(--surface-raised)] p-2.5">
            <span className="text-[10px] font-bold uppercase tracking-wider text-[var(--accent)]">
              Lowest Competition
            </span>
            <p className="mt-1 text-xs font-semibold truncate text-[var(--foreground)]" title={lowestComp.title}>
              {lowestComp.title}
            </p>
            <span className="text-[10px] text-[var(--muted)]">
              White space: {lowestComp.score?.competitive_pressure || "N/A"}/10
            </span>
          </div>

          <div className="rounded-xl border border-[var(--border)] bg-[var(--surface-raised)] p-2.5">
            <span className="text-[10px] font-bold uppercase tracking-wider text-[var(--warning)]">
              Highest Demand
            </span>
            <p className="mt-1 text-xs font-semibold truncate text-[var(--foreground)]" title={highestDemand.title}>
              {highestDemand.title}
            </p>
            <span className="text-[10px] text-[var(--muted)]">
              Demand: {highestDemand.score?.market_demand || "N/A"}/10
            </span>
          </div>

          <div className="rounded-xl border border-[var(--border)] bg-[var(--surface-raised)] p-2.5">
            <span className="text-[10px] font-bold uppercase tracking-wider text-[var(--error)]">
              Highest Risk
            </span>
            <p className="mt-1 text-xs font-semibold truncate text-[var(--foreground)]" title={highestRisk.title}>
              {highestRisk.title}
            </p>
            <span className="text-[10px] text-[var(--muted)]">
              {highestRisk.risks?.length || 0} documented risks
            </span>
          </div>
        </div>

        {/* Comparison Table */}
        <div className="flex-1 overflow-auto rounded-xl border border-[var(--border)] bg-[var(--background)]">
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="border-b border-[var(--border)] bg-[var(--surface-raised)]">
                <th className="p-3 font-semibold text-[var(--muted)] uppercase text-[10px] w-1/4">Metric</th>
                {opportunities.map((opp, idx) => (
                  <th key={idx} className="p-3 font-bold text-[var(--foreground)] min-w-[180px]">
                    {opp.title}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-[var(--border-subtle)]">
              <tr>
                <td className="p-3 font-medium text-[var(--muted)]">Overall Score</td>
                {opportunities.map((opp, idx) => (
                  <td key={idx} className="p-3 font-bold text-[var(--accent)]">
                    {opp.score ? `${opp.score.overall_score} / 50 (${opp.score.confidence_label})` : "N/A"}
                  </td>
                ))}
              </tr>
              <tr>
                <td className="p-3 font-medium text-[var(--muted)]">Market Demand</td>
                {opportunities.map((opp, idx) => (
                  <td key={idx} className="p-3">{opp.score?.market_demand ? `${opp.score.market_demand}/10` : "—"}</td>
                ))}
              </tr>
              <tr>
                <td className="p-3 font-medium text-[var(--muted)]">Competition</td>
                {opportunities.map((opp, idx) => (
                  <td key={idx} className="p-3">{opp.score?.competitive_pressure ? `${opp.score.competitive_pressure}/10` : "—"}</td>
                ))}
              </tr>
              <tr>
                <td className="p-3 font-medium text-[var(--muted)]">Feasibility (4-wk MVP)</td>
                {opportunities.map((opp, idx) => (
                  <td key={idx} className="p-3">{opp.score?.execution_feasibility ? `${opp.score.execution_feasibility}/10` : "—"}</td>
                ))}
              </tr>
              <tr>
                <td className="p-3 font-medium text-[var(--muted)]">Market Timing</td>
                {opportunities.map((opp, idx) => (
                  <td key={idx} className="p-3">{opp.score?.market_timing ? `${opp.score.market_timing}/10` : "—"}</td>
                ))}
              </tr>
              <tr>
                <td className="p-3 font-medium text-[var(--muted)]">AI Advantage</td>
                {opportunities.map((opp, idx) => (
                  <td key={idx} className="p-3">{opp.score?.ai_advantage ? `${opp.score.ai_advantage}/10` : "—"}</td>
                ))}
              </tr>
              <tr>
                <td className="p-3 font-medium text-[var(--muted)]">Target Customer</td>
                {opportunities.map((opp, idx) => (
                  <td key={idx} className="p-3 text-[var(--text-secondary)]">{opp.customer}</td>
                ))}
              </tr>
              <tr>
                <td className="p-3 font-medium text-[var(--muted)]">MVP Scope</td>
                {opportunities.map((opp, idx) => (
                  <td key={idx} className="p-3">
                    <ul className="list-disc pl-3 space-y-0.5 text-[11px] text-[var(--text-secondary)]">
                      {opp.mvp_features?.slice(0, 3).map((f, i) => (
                        <li key={i}>{f}</li>
                      ))}
                    </ul>
                  </td>
                ))}
              </tr>
              <tr>
                <td className="p-3 font-medium text-[var(--muted)]">Primary Risks</td>
                {opportunities.map((opp, idx) => (
                  <td key={idx} className="p-3 text-[11px] text-[var(--warning)]">
                    {opp.risks?.[0] || "None documented"}
                  </td>
                ))}
              </tr>
            </tbody>
          </table>
        </div>

        {/* Footer Disclaimer */}
        <div className="mt-4 flex items-center justify-between text-[11px] text-[var(--muted)]">
          <span>Analytical comparison derived from gathered evidence. Not an investment guarantee.</span>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg bg-[var(--surface-raised)] px-4 py-1.5 font-medium text-[var(--foreground)] hover:bg-[var(--surface-hover)]"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
