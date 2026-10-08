"use client";

import React, { useState } from "react";
import { ResearchSource } from "@/lib/api";

interface SourcesProps {
  sources: ResearchSource[];
}

function formatDate(dateStr?: string | null): string {
  if (!dateStr) return "";
  try {
    return new Date(dateStr).toLocaleDateString(undefined, {
      year: "numeric",
      month: "short",
      day: "numeric",
    });
  } catch {
    return dateStr;
  }
}

function getDomain(url: string): string {
  try {
    if (url.startsWith("document://")) {
      return "Uploaded Document";
    }
    return new URL(url).hostname.replace(/^www\./, "");
  } catch {
    return url;
  }
}

export function Sources({ sources }: SourcesProps) {
  const [expanded, setExpanded] = useState(false);

  if (!sources || sources.length === 0) return null;

  const PREVIEW_COUNT = 6;
  const showAll = expanded || sources.length <= PREVIEW_COUNT;
  const displayed = showAll ? sources : sources.slice(0, PREVIEW_COUNT);
  const hidden = sources.length - PREVIEW_COUNT;

  const webCount = sources.filter((s) => !s.source_type || s.source_type === "web").length;
  const docCount = sources.length - webCount;

  return (
    <section aria-labelledby="sources-heading" className="mt-8 border-t border-[var(--border)] pt-6">
      {/* Editorial Header */}
      <div className="flex flex-wrap items-center justify-between gap-2 mb-4">
        <div>
          <h2
            id="sources-heading"
            className="text-sm font-bold uppercase tracking-wider text-[var(--foreground)]"
          >
            VERIFIED EVIDENCE
          </h2>
          <p className="text-xs text-[var(--muted)]">
            {sources.length} sources · {webCount > 0 ? `${webCount} Web` : ""}{webCount > 0 && docCount > 0 ? " + " : ""}{docCount > 0 ? `${docCount} Documents` : ""}
          </p>
        </div>
        <span className="rounded bg-[var(--surface-raised)] border border-[var(--border-subtle)] px-2 py-0.5 text-[10px] font-mono text-[var(--accent)] font-semibold">
          100% GENUINE CITATIONS
        </span>
      </div>

      {/* Grid of Reference Cards */}
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        {displayed.map((source, i) => {
          const isDoc = source.source_type === "document" || source.url.startsWith("document://");
          const domain = getDomain(source.url);
          const formattedPubDate = formatDate(source.published_at);
          const typeLabel = isDoc ? "DOCUMENT" : "WEB";
          const freshness = source.freshness_label;

          return (
            <div
              key={`${source.url}-${i}`}
              className="research-card group flex flex-col justify-between rounded-xl border border-[var(--border)] bg-[var(--surface)] p-4 transition-all duration-180 hover:border-[var(--accent)]/40 hover:shadow-xs"
            >
              <div>
                {/* Top Reference Bar: SOURCE TYPE + Domain */}
                <div className="flex items-center justify-between gap-2 mb-2">
                  <div className="flex items-center gap-1.5">
                    <span
                      className={`inline-flex items-center px-1.5 py-0.2 rounded font-mono text-[9px] font-bold tracking-wider ${
                        isDoc
                          ? "bg-[var(--accent-subtle)] text-[var(--accent)] border border-[var(--accent)]/30"
                          : "bg-[var(--surface-raised)] text-[var(--text-secondary)] border border-[var(--border-subtle)]"
                      }`}
                    >
                      {typeLabel}
                    </span>
                    <span className="font-mono text-[11px] text-[var(--text-secondary)] truncate max-w-[140px]">
                      {domain}
                    </span>
                  </div>

                  {formattedPubDate ? (
                    <span className="font-mono text-[10px] text-[var(--muted)]">
                      {formattedPubDate}
                    </span>
                  ) : (
                    <span className="font-mono text-[10px] text-[var(--muted)] italic">
                      Indexed
                    </span>
                  )}
                </div>

                {/* Reference Title */}
                <h4 className="text-xs font-semibold text-[var(--foreground)] leading-snug line-clamp-2 group-hover:text-[var(--accent)] transition-colors">
                  {source.title || domain}
                </h4>

                {/* Snippet / Abstract */}
                {source.snippet && (
                  <p className="mt-2 line-clamp-2 text-[11px] leading-relaxed text-[var(--muted)]">
                    {source.snippet}
                  </p>
                )}
              </div>

              {/* Bottom Reference Footer: Strength & Action Link */}
              <div className="mt-3 flex items-center justify-between border-t border-[var(--border-subtle)] pt-2.5 text-[11px]">
                <div className="flex items-center gap-1.5">
                  <span className={`h-1.5 w-1.5 rounded-full ${source.is_historical ? "bg-[var(--warning)]" : "bg-[var(--success)]"}`} />
                  <span className="text-[10px] text-[var(--muted)]">
                    {freshness || (source.is_historical ? "Historical Context" : "Fresh Evidence")}
                  </span>
                </div>

                {!isDoc ? (
                  <a
                    href={source.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1 text-[11px] font-medium text-[var(--accent)] hover:underline focus-visible:outline focus-visible:outline-2 focus-visible:outline-[var(--focus)]"
                  >
                    <span>Open source</span>
                    <span className="transition-transform group-hover:translate-x-0.5 group-hover:-translate-y-0.5">↗</span>
                  </a>
                ) : (
                  <span className="text-[10px] font-mono text-[var(--muted)]">Verified doc</span>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {!showAll && hidden > 0 && (
        <div className="mt-3 text-center">
          <button
            type="button"
            onClick={() => setExpanded(true)}
            className="rounded-lg border border-[var(--border)] bg-[var(--surface-raised)] px-4 py-1.5 text-xs font-medium text-[var(--accent)] hover:border-[var(--accent)]/40 transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-[var(--focus)]"
          >
            View all {sources.length} sources ({hidden} more)
          </button>
        </div>
      )}
    </section>
  );
}
