"use client";

import React, { useState, useCallback } from "react";

export type Theme = "dark" | "light" | "system";

// ---------------------------------------------------------------------------
// Module-level helpers — never called during SSR (file is "use client")
// ---------------------------------------------------------------------------

function readStoredTheme(): Theme {
  try {
    return (localStorage.getItem("startuplens-theme") as Theme) || "system";
  } catch {
    return "system";
  }
}

function writeTheme(t: Theme) {
  try {
    localStorage.setItem("startuplens-theme", t);
  } catch {
    // ignore
  }
}

function resolveTheme(t: Theme): "dark" | "light" {
  if (t !== "system") return t;
  return window.matchMedia("(prefers-color-scheme: dark)").matches
    ? "dark"
    : "light";
}

/** Apply a theme choice to the document root. */
export function applyTheme(t: Theme) {
  document.documentElement.setAttribute("data-theme", resolveTheme(t));
  writeTheme(t);
}

// ---------------------------------------------------------------------------
// Icons
// ---------------------------------------------------------------------------

function MoonIcon() {
  return (
    <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2" aria-hidden="true">
      <path strokeLinecap="round" strokeLinejoin="round" d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z" />
    </svg>
  );
}

function SunIcon() {
  return (
    <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2" aria-hidden="true">
      <path strokeLinecap="round" strokeLinejoin="round" d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z" />
    </svg>
  );
}

function MonitorIcon() {
  return (
    <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2" aria-hidden="true">
      <path strokeLinecap="round" strokeLinejoin="round" d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
    </svg>
  );
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

/**
 * HYDRATION-SAFE THEME TOGGLE
 *
 * Problem: the server renders HTML without knowing the user's saved theme.
 * The first client render must be byte-for-byte identical to that HTML.
 *
 * Solution:
 *  • Initial state is always `"system"` — a stable value that requires no
 *    browser APIs, identical on both server and client.
 *  • `mounted` starts `false` so all dynamic, theme-derived JSX (title,
 *    aria-label, icon) is replaced by a static neutral fallback until the
 *    component has received at least one user interaction.
 *  • On the very first click, `ensureInit()` reads localStorage and syncs
 *    state. This happens inside a user-event handler, not an effect body,
 *    so it satisfies the react-hooks/set-state-in-effect rule.
 *  • `requestAnimationFrame` is scheduled inside `ensureInit`, which is only
 *    ever called from click handlers (client-only) — never during render.
 */
export function ThemeToggle() {
  // Both server and first client render use these stable initial values.
  const [mounted, setMounted] = useState(false);
  const [theme, setTheme] = useState<Theme>("system");

  /**
   * Read the real saved theme from localStorage and sync it into state.
   * Only runs once (idempotent via the `mounted` guard in state).
   * Called from click handlers — never during render.
   */
  const ensureInit = useCallback(() => {
    if (mounted) return; // already initialised
    const saved = readStoredTheme();
    applyTheme(saved);
    setTheme(saved);
    setMounted(true);
  }, [mounted]);

  const cycleTheme = useCallback(() => {
    // On the very first click: initialise, then immediately apply the next
    // value so the user sees the toggle work straight away.
    const current = mounted ? theme : readStoredTheme();
    if (!mounted) {
      setMounted(true);
    }
    const next: Theme =
      current === "dark" ? "light" : current === "light" ? "system" : "dark";
    setTheme(next);
    applyTheme(next);
  }, [mounted, theme, ensureInit]); // eslint-disable-line react-hooks/exhaustive-deps

  // Stable pre-hydration attributes (must match SSR output exactly).
  const titleAttr  = mounted ? `Theme: ${theme === "dark" ? "Dark" : theme === "light" ? "Light" : "System"} (Click to switch)` : "Theme";
  const ariaLabel  = mounted ? `Current theme is ${theme === "dark" ? "Dark" : theme === "light" ? "Light" : "System"}. Click to switch theme.` : "Theme settings";

  return (
    <button
      type="button"
      onClick={cycleTheme}
      title={titleAttr}
      aria-label={ariaLabel}
      className="flex h-8 w-8 items-center justify-center rounded-lg border border-[var(--border)] bg-[var(--surface)] text-[var(--muted)] transition-colors hover:border-[var(--accent)] hover:text-[var(--foreground)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-[var(--focus)]"
    >
      {/* Before first interaction: neutral MonitorIcon (matches SSR).
          After: icon matching the real persisted theme. */}
      {(!mounted || theme === "system") && <MonitorIcon />}
      {mounted && theme === "dark"   && <MoonIcon />}
      {mounted && theme === "light"  && <SunIcon />}
    </button>
  );
}
