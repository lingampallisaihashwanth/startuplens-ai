"use client";

import React from "react";
import { Opportunity } from "@/lib/api";
import { OpportunityCard } from "./OpportunityCard";

interface SavedIdeasViewProps {
  savedIdeas: Opportunity[];
  onToggleSave: (opp: Opportunity) => void;
  onBackToChat: () => void;
}

export function SavedIdeasView({
  savedIdeas,
  onToggleSave,
  onBackToChat,
}: SavedIdeasViewProps) {
  return (
    <div className="mx-auto max-w-3xl px-4 py-8 sm:px-6">
      <div className="flex items-center justify-between border-b border-[var(--border)] pb-4 mb-6">
        <div>
          <div className="flex items-center gap-2">
            <span className="flex h-6 w-6 items-center justify-center rounded-md bg-[var(--warning)]/15 text-[var(--warning)]">
              ★
            </span>
            <h1 className="text-xl font-bold text-[var(--foreground)]">Saved Ideas</h1>
          </div>
          <p className="mt-1 text-xs text-[var(--muted)]">
            Starred startup hypotheses and opportunity cards saved from research dossiers.
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

      {savedIdeas.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-[var(--border)] bg-[var(--surface)]/50 p-12 text-center">
          <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-full bg-[var(--surface-raised)] text-[var(--muted)]">
            <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.5">
              <path strokeLinecap="round" strokeLinejoin="round" d="M11.049 2.927c.3-.921 1.603-.921 1.902 0l1.519 4.674a1 1 0 00.95.69h4.915c.969 0 1.371 1.24.588 1.81l-3.976 2.888a1 1 0 00-.363 1.118l1.518 4.674c.3.922-.755 1.688-1.538 1.118l-3.976-2.888a1 1 0 00-1.176 0l-3.976 2.888c-.783.57-1.838-.197-1.538-1.118l1.518-4.674a1 1 0 00-.363-1.118l-3.976-2.888c-.784-.57-.38-1.81.588-1.81h4.914a1 1 0 00.951-.69l1.519-4.674z" />
            </svg>
          </div>
          <h3 className="text-sm font-semibold text-[var(--foreground)]">No saved ideas yet</h3>
          <p className="mt-1 max-w-sm mx-auto text-xs text-[var(--muted)]">
            Click the star icon on any startup opportunity card during research to bookmark it here for later review.
          </p>
          <button
            type="button"
            onClick={onBackToChat}
            className="mt-5 inline-flex items-center gap-2 rounded-xl bg-[var(--accent)] px-4 py-2 text-xs font-semibold text-[var(--background)] hover:bg-[var(--accent-hover)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-[var(--focus)]"
          >
            Start a Research Search
          </button>
        </div>
      ) : (
        <div className="space-y-3">
          {savedIdeas.map((opp, index) => (
            <OpportunityCard
              key={`${opp.title}-${index}`}
              opportunity={opp}
              index={index}
              isSaved={true}
              onToggleSave={onToggleSave}
            />
          ))}
        </div>
      )}
    </div>
  );
}
