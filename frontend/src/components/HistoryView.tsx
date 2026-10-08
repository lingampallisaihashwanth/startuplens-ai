"use client";

import React, { useState, useEffect } from "react";
import { getResearch, deleteResearch, SessionSummary } from "@/lib/api";

interface HistoryViewProps {
  onSelectSession: (sessionId: string) => void;
  onBackToChat: () => void;
  onSessionDeleted?: (sessionId: string) => void;
}

export function HistoryView({
  onSelectSession,
  onBackToChat,
  onSessionDeleted,
}: HistoryViewProps) {
  const [sessions, setSessions] = useState<SessionSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [deletingId, setDeletingId] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setLoading(true);
      try {
        const data = await getResearch(100, 0);
        if (!cancelled) setSessions(data);
      } catch {
        // silent fallback
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => {
      cancelled = true;
    };
  }, []);

  const handleDelete = async (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    if (!confirm("Are you sure you want to delete this research session?")) return;
    setDeletingId(id);
    try {
      await deleteResearch(id);
      setSessions((prev) => prev.filter((s) => s.id !== id));
      if (onSessionDeleted) onSessionDeleted(id);
    } catch {
      alert("Failed to delete session");
    } finally {
      setDeletingId(null);
    }
  };

  const filtered = sessions.filter((s) =>
    s.topic.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="mx-auto max-w-3xl px-4 py-8 sm:px-6">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-[var(--border)] pb-4 mb-6">
        <div>
          <div className="flex items-center gap-2">
            <span className="flex h-6 w-6 items-center justify-center rounded-md bg-[var(--surface-raised)] text-[var(--accent)]">
              <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </span>
            <h1 className="text-xl font-bold text-[var(--foreground)]">Research History</h1>
          </div>
          <p className="mt-1 text-xs text-[var(--muted)]">
            Explore past market dossiers and opportunity analyses saved to SQLite.
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

      {/* Search Filter */}
      <div className="mb-4">
        <div className="flex items-center gap-2 rounded-xl border border-[var(--border)] bg-[var(--surface)] px-3 py-2 text-xs">
          <svg className="h-4 w-4 text-[var(--muted)]" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
            <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
          <input
            type="text"
            placeholder="Search past research topics..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full bg-transparent text-xs text-[var(--foreground)] placeholder-[var(--muted)] outline-none"
          />
        </div>
      </div>

      {loading ? (
        <div className="space-y-2 py-4">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="h-16 animate-pulse rounded-xl border border-[var(--border)] bg-[var(--surface)]" />
          ))}
        </div>
      ) : filtered.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-[var(--border)] bg-[var(--surface)]/50 p-12 text-center">
          <p className="text-xs text-[var(--muted)]">No research sessions found.</p>
        </div>
      ) : (
        <div className="space-y-2.5">
          {filtered.map((s) => (
            <div
              key={s.id}
              onClick={() => onSelectSession(s.id)}
              className="group flex cursor-pointer items-center justify-between rounded-xl border border-[var(--border)] bg-[var(--surface)] p-4 transition-all hover:border-[var(--accent)]/40 hover:bg-[var(--surface-hover)]"
            >
              <div className="min-w-0 flex-1">
                <h3 className="text-sm font-semibold text-[var(--foreground)] group-hover:text-[var(--accent)]">
                  {s.topic}
                </h3>
                <div className="mt-1 flex items-center gap-3 text-[11px] text-[var(--muted)]">
                  <span>{new Date(s.created_at).toLocaleDateString(undefined, { dateStyle: "medium" })}</span>
                  <span>·</span>
                  <span>{s.opportunities_count} opportunities</span>
                  <span>·</span>
                  <span>{s.sources_count} sources</span>
                </div>
              </div>

              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={(e) => handleDelete(e, s.id)}
                  disabled={deletingId === s.id}
                  aria-label={`Delete "${s.topic}"`}
                  className="rounded-lg p-2 text-[var(--muted)] hover:bg-[var(--surface-raised)] hover:text-red-400 focus-visible:outline focus-visible:outline-2 focus-visible:outline-[var(--focus)]"
                >
                  <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                  </svg>
                </button>

                <span className="text-xs font-semibold text-[var(--accent)] group-hover:translate-x-0.5 transition-transform">
                  View →
                </span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
