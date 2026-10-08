"use client";

import React, { useState, useEffect } from "react";
import { ResearchTracker, MarketSignal, getTrackers, deleteTracker, refreshTracker, getMarketSignals } from "@/lib/api";

interface ResearchTrackerViewProps {
  onBackToChat: () => void;
  onSelectTopic: (topic: string) => void;
  onSelectSession?: (sessionId: string) => void;
}

export function ResearchTrackerView({ onBackToChat, onSelectTopic, onSelectSession }: ResearchTrackerViewProps) {
  const [trackers, setTrackers] = useState<ResearchTracker[]>([]);
  const [signals, setSignals] = useState<MarketSignal[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [refreshingId, setRefreshingId] = useState<string | null>(null);

  const loadData = async () => {
    setIsLoading(true);
    try {
      const [tList, sList] = await Promise.all([getTrackers(), getMarketSignals()]);
      setTrackers(tList);
      setSignals(sList);
    } catch {
      // ignore
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    let active = true;
    Promise.all([getTrackers(), getMarketSignals()])
      .then(([tList, sList]) => {
        if (!active) return;
        setTrackers(tList);
        setSignals(sList);
        setIsLoading(false);
      })
      .catch(() => {
        if (!active) return;
        setIsLoading(false);
      });

    return () => {
      active = false;
    };
  }, []);

  const handleRefresh = async (trackerId: string) => {
    setRefreshingId(trackerId);
    try {
      await refreshTracker(trackerId);
      await loadData();
    } catch {
      // ignore
    } finally {
      setRefreshingId(null);
    }
  };

  const handleDelete = async (trackerId: string) => {
    try {
      await deleteTracker(trackerId);
      setTrackers((prev) => prev.filter((t) => t.id !== trackerId));
    } catch {
      // ignore
    }
  };

  return (
    <div className="mx-auto max-w-4xl px-4 py-8 sm:px-6">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-[var(--border)] pb-4 mb-6">
        <div>
          <div className="flex items-center gap-2">
            <span className="flex h-2.5 w-2.5 rounded-full bg-[var(--accent)]" />
            <h1 className="text-xl font-bold text-[var(--foreground)]">Research Tracker & Signals</h1>
          </div>
          <p className="mt-1 text-xs text-[var(--muted)]">
            Continuous background tracking for active market domains with automated delta change detection.
          </p>
        </div>

        <button
          type="button"
          onClick={onBackToChat}
          className="rounded-lg border border-[var(--border)] bg-[var(--surface)] px-3 py-1.5 text-xs font-medium text-[var(--text-secondary)] hover:text-[var(--foreground)] hover:border-[var(--accent)]/40 focus-visible:outline focus-visible:outline-2 focus-visible:outline-[var(--focus)]"
        >
          ← Back to Chat
        </button>
      </div>

      {isLoading ? (
        <div className="p-12 text-center text-xs text-[var(--muted)]">Loading trackers and market signals...</div>
      ) : (
        <div className="space-y-8">
          {/* Active Trackers */}
          <section>
            <h2 className="text-xs font-semibold uppercase tracking-wider text-[var(--muted)] mb-3">
              Tracked Domains ({trackers.length})
            </h2>

            {trackers.length === 0 ? (
              <div className="rounded-xl border border-dashed border-[var(--border)] p-8 text-center text-xs text-[var(--muted)]">
                No active research trackers. Click &quot;Track Research&quot; in any dossier to monitor market updates.
              </div>
            ) : (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {trackers.map((t) => (
                  <div
                    key={t.id}
                    className="flex flex-col justify-between rounded-xl border border-[var(--border)] bg-[var(--surface)] p-4 shadow-sm"
                  >
                    <div>
                      <div className="flex items-center justify-between gap-2">
                        <span className="inline-flex items-center gap-1.5 rounded-full bg-[var(--success)]/15 px-2 py-0.5 text-[10px] font-semibold text-[var(--success)]">
                          <span className="h-1.5 w-1.5 rounded-full bg-[var(--success)]" />
                          {t.status.toUpperCase()}
                        </span>
                        <span className="text-[10px] text-[var(--muted)]">Next: {t.next_update}</span>
                      </div>

                      <h3
                        onClick={() => {
                          if (t.session_id && onSelectSession) {
                            onSelectSession(t.session_id);
                          } else {
                            onSelectTopic(t.topic);
                          }
                        }}
                        className="mt-2 text-sm font-bold text-[var(--foreground)] hover:text-[var(--accent)] cursor-pointer truncate"
                      >
                        {t.topic}
                      </h3>
                      <p className="text-[11px] text-[var(--muted)] mt-0.5">Last updated: {t.last_updated}</p>
                    </div>

                    <div className="mt-4 flex items-center justify-between border-t border-[var(--border-subtle)] pt-2.5">
                      <button
                        type="button"
                        onClick={() => handleRefresh(t.id)}
                        disabled={refreshingId === t.id}
                        className="inline-flex items-center gap-1 text-xs font-medium text-[var(--accent)] hover:underline disabled:opacity-50"
                      >
                        {refreshingId === t.id ? "Refreshing..." : "↻ Refresh & Detect"}
                      </button>
                      <button
                        type="button"
                        onClick={() => handleDelete(t.id)}
                        className="text-xs text-[var(--muted)] hover:text-[var(--error)]"
                      >
                        Disable
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </section>

          {/* Detected Market Change Signals */}
          <section>
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-xs font-semibold uppercase tracking-wider text-[var(--muted)]">
                Detected Market Signals ({signals.length})
              </h2>
              <span className="text-[10px] text-[var(--muted)]">Automated delta signals from fresh web crawls</span>
            </div>

            {signals.length === 0 ? (
              <div className="rounded-xl border border-dashed border-[var(--border)] p-6 text-center text-xs text-[var(--muted)]">
                No new market signals detected yet. Signals appear when tracked research is refreshed with fresh web findings.
              </div>
            ) : (
              <div className="space-y-2.5">
                {signals.map((sig) => (
                  <div
                    key={sig.id}
                    className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-3.5 flex flex-col sm:flex-row sm:items-start justify-between gap-3"
                  >
                    <div className="space-y-1">
                      <div className="flex items-center gap-2">
                        <span className="rounded bg-[var(--accent-subtle)] px-1.5 py-0.5 text-[9px] font-bold text-[var(--accent)] uppercase">
                          {sig.signal_type || "Market Signal"}
                        </span>
                        <span className="text-xs font-bold text-[var(--foreground)]">{sig.title}</span>
                      </div>
                      <p className="text-xs text-[var(--text-secondary)] leading-relaxed">
                        {sig.change_summary || sig.what_changed}
                      </p>
                      {sig.evidence && (
                        <p className="text-[10px] text-[var(--muted)]">
                          Evidence:{" "}
                          <a
                            href={sig.evidence}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-[var(--accent)] hover:underline truncate inline-block max-w-[250px] align-bottom"
                          >
                            {sig.evidence}
                          </a>
                        </p>
                      )}
                    </div>
                    <span className="text-[10px] text-[var(--muted)] shrink-0 self-end sm:self-start">
                      {new Date(sig.detected_at).toLocaleDateString(undefined, {
                        month: "short",
                        day: "numeric",
                        hour: "2-digit",
                        minute: "2-digit",
                      })}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </section>
        </div>
      )}
    </div>
  );
}
