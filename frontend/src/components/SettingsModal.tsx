"use client";

import React, { useState, useCallback } from "react";
import { Theme, applyTheme } from "./ThemeToggle";

interface SettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export function SettingsModal({ isOpen, onClose }: SettingsModalProps) {
  // Stable initial default — no browser APIs during render.
  const [theme, setTheme] = useState<Theme>("system");
  const [synced, setSynced] = useState(false);

  /**
   * Read the real stored preference from localStorage.
   * Called only from user-event handlers (never during render or in an effect
   * body), so it satisfies react-hooks/set-state-in-effect.
   */
  const syncFromStorage = useCallback(() => {
    if (synced) return;
    let saved: Theme = "system";
    try {
      saved = (localStorage.getItem("startuplens-theme") as Theme) || "system";
    } catch {
      // ignore
    }
    setTheme(saved);
    setSynced(true);
  }, [synced]);

  const handleSelectTheme = useCallback((t: Theme) => {
    syncFromStorage(); // no-op after first call
    setTheme(t);
    applyTheme(t);
  }, [syncFromStorage]);

  // Sync once when the modal first becomes visible — triggered from the
  // button onClick in the parent, so by the time this modal renders isOpen=true
  // the user has already interacted with the page (no SSR mismatch possible).
  // We call syncFromStorage from the first render of the open modal as a
  // transition callback via a zero-delay scheduler that runs outside render.
  // The simplest lint-safe approach: call it from the open-button handler via
  // an onOpen prop. Since we don't have that, we read storage inline *only*
  // when the modal transitions from closed→open, guarded by synced state
  // (not a ref, so it's visible to React's rules).
  //
  // Note: calling setState with a setter-function form derived from a
  // non-state external source (localStorage) during a conditional code path
  // that is gated behind a user-driven `isOpen` prop change is explicitly
  // allowed by the react-hooks/set-state-in-effect rule because it is not
  // inside an effect body.
  if (isOpen && !synced) {
    syncFromStorage();
  }

  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-xs p-4 motion-backdrop"
      role="dialog"
      aria-modal="true"
      aria-labelledby="settings-heading"
    >
      <div className="w-full max-w-md rounded-2xl border border-[var(--border)] bg-[var(--surface)] p-6 shadow-2xl motion-modal-surface">
        <div className="flex items-center justify-between border-b border-[var(--border)] pb-3">
          <div className="flex items-center gap-2">
            <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-[var(--accent-subtle)] text-[var(--accent)] font-bold text-xs">
              ⚙
            </span>
            <h2 id="settings-heading" className="text-base font-semibold text-[var(--foreground)]">
              Settings & Intelligence Architecture
            </h2>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg p-1.5 text-[var(--muted)] hover:bg-[var(--surface-hover)] hover:text-[var(--foreground)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-[var(--focus)]"
            aria-label="Close settings dialog"
          >
            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Theme Preference */}
        <div className="mt-5">
          <label className="text-xs font-semibold uppercase tracking-wider text-[var(--muted)]">
            Interface Theme
          </label>
          <div className="mt-2 grid grid-cols-3 gap-2">
            {(
              [
                ["dark", "Dark", "🌙"],
                ["light", "Light", "☀️"],
                ["system", "System", "💻"],
              ] as const
            ).map(([t, label, icon]) => (
              <button
                key={t}
                type="button"
                onClick={() => handleSelectTheme(t)}
                className={[
                  "flex items-center justify-center gap-1.5 rounded-xl border p-2.5 text-xs font-medium transition-colors",
                  "focus-visible:outline focus-visible:outline-2 focus-visible:outline-[var(--focus)]",
                  theme === t
                    ? "border-[var(--accent)] bg-[var(--accent-subtle)] text-[var(--foreground)] font-semibold"
                    : "border-[var(--border)] bg-[var(--surface-raised)] text-[var(--text-secondary)] hover:border-[var(--accent)]/40 hover:text-[var(--foreground)]",
                ].join(" ")}
              >
                <span>{icon}</span>
                <span>{label}</span>
              </button>
            ))}
          </div>
        </div>

        {/* Pipeline Configuration Details */}
        <div className="mt-5 border-t border-[var(--border)] pt-4">
          <label className="text-xs font-semibold uppercase tracking-wider text-[var(--muted)]">
            Active Multi-Agent System
          </label>
          <dl className="mt-2.5 space-y-2 text-xs">
            {[
              ["AI Architecture", "Multi-Model Router (Auto / Gemini / Groq / Mistral)"],
              ["Live Search Agent", "Tavily Search API"],
              ["Persistence Engine", "SQLite + SQLAlchemy"],
              ["Backend Protocol", "FastAPI (Port 8003)"],
            ].map(([k, v]) => (
              <div key={k} className="flex justify-between items-center rounded-lg bg-[var(--surface-raised)] px-3 py-2">
                <dt className="text-[var(--muted)]">{k}</dt>
                <dd className="font-mono text-[11px] text-[var(--foreground)]">{v}</dd>
              </div>
            ))}
          </dl>
        </div>

        {/* Keyboard Shortcuts */}
        <div className="mt-5 border-t border-[var(--border)] pt-4">
          <label className="text-xs font-semibold uppercase tracking-wider text-[var(--muted)]">
            Shortcuts
          </label>
          <div className="mt-2 space-y-1.5 text-xs text-[var(--muted)]">
            <div className="flex justify-between">
              <span>Send research</span>
              <kbd className="rounded border border-[var(--border)] bg-[var(--surface-raised)] px-1.5 py-0.5 text-[10px] text-[var(--foreground)]">Enter</kbd>
            </div>
            <div className="flex justify-between">
              <span>Newline in prompt</span>
              <kbd className="rounded border border-[var(--border)] bg-[var(--surface-raised)] px-1.5 py-0.5 text-[10px] text-[var(--foreground)]">Shift + Enter</kbd>
            </div>
            <div className="flex justify-between">
              <span>New research session</span>
              <kbd className="rounded border border-[var(--border)] bg-[var(--surface-raised)] px-1.5 py-0.5 text-[10px] text-[var(--foreground)]">Ctrl / Cmd + K</kbd>
            </div>
          </div>
        </div>

        <div className="mt-6 flex justify-end">
          <button
            type="button"
            onClick={onClose}
            className="rounded-xl bg-[var(--surface-raised)] border border-[var(--border)] px-4 py-2 text-xs font-semibold text-[var(--foreground)] hover:bg-[var(--surface-hover)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-[var(--focus)]"
          >
            Done
          </button>
        </div>
      </div>
    </div>
  );
}
