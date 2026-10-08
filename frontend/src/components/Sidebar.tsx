"use client";

import React, { useEffect, useState, useCallback, useMemo } from "react";
import { getResearch, deleteResearch, SessionSummary } from "@/lib/api";

interface SidebarProps {
  activeSessionId: string | null;
  onSelectSession: (sessionId: string) => void;
  onNewResearch: () => void;
  isOpenMobile: boolean;
  onCloseMobile: () => void;
  onSessionDeleted?: (sessionId: string) => void;
  currentNav: "chat" | "history" | "saved" | "tracker";
  onNavigate: (nav: "chat" | "history" | "saved" | "tracker") => void;
  onOpenSettings: () => void;
  savedIdeasCount?: number;
}

function formatRelativeTime(isoString?: string | null): string {
  if (!isoString) return "";
  try {
    const date = new Date(isoString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMins / 60);
    const diffDays = Math.floor(diffHours / 24);
    if (diffMins < 1) return "Just now";
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays === 1) return "Yesterday";
    if (diffDays < 7) return `${diffDays}d ago`;
    return date.toLocaleDateString(undefined, { month: "short", day: "numeric" });
  } catch {
    return "";
  }
}

export function Sidebar({
  activeSessionId,
  onSelectSession,
  onNewResearch,
  isOpenMobile,
  onCloseMobile,
  onSessionDeleted,
  currentNav,
  onNavigate,
  onOpenSettings,
  savedIdeasCount = 0,
}: SidebarProps) {
  const [sessions, setSessions] = useState<SessionSummary[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [showSearchInput, setShowSearchInput] = useState<boolean>(false);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [showUserMenu, setShowUserMenu] = useState<boolean>(false);
  const [isCollapsed, setIsCollapsed] = useState<boolean>(false);

  const fetchSessions = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getResearch(50, 0);
      setSessions(data);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to load recent research";
      setError(msg);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const data = await getResearch(50, 0);
        if (!cancelled) setSessions(data);
      } catch (err: unknown) {
        if (!cancelled) {
          const msg = err instanceof Error ? err.message : "Failed to load recent research";
          setError(msg);
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => {
      cancelled = true;
    };
  }, []);

  const handleDelete = useCallback(
    async (e: React.MouseEvent | React.KeyboardEvent, sessionId: string) => {
      e.stopPropagation();
      if (deletingId) return;
      if (!confirm("Are you sure you want to delete this research session?")) return;
      setDeletingId(sessionId);
      try {
        await deleteResearch(sessionId);
        setSessions((prev) => prev.filter((s) => s.id !== sessionId));
        if (onSessionDeleted) onSessionDeleted(sessionId);
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : "Could not delete session";
        alert(msg);
      } finally {
        setDeletingId(null);
      }
    },
    [deletingId, onSessionDeleted]
  );

  const filteredSessions = useMemo(() => {
    if (!searchQuery.trim()) return sessions;
    const q = searchQuery.toLowerCase();
    return sessions.filter((s) => s.topic.toLowerCase().includes(q));
  }, [sessions, searchQuery]);

  return (
    <>
      {/* Mobile Drawer Backdrop with smooth fade in/out */}
      <div
        className={`fixed inset-0 z-40 bg-black/60 backdrop-blur-xs transition-opacity duration-280 ease-out md:hidden ${
          isOpenMobile ? "opacity-100 pointer-events-auto" : "opacity-0 pointer-events-none"
        }`}
        onClick={onCloseMobile}
        aria-hidden={!isOpenMobile}
      />

      {/* Sidebar Container */}
      <aside
        aria-label="Sidebar navigation"
        className={[
          "fixed inset-y-0 left-0 z-50 flex flex-col",
          "border-r border-[var(--border)] bg-[var(--background)]",
          "transition-[width,transform] duration-280 ease-[cubic-bezier(0.16,1,0.3,1)]",
          "md:static shrink-0",
          isCollapsed ? "md:w-[72px]" : "md:w-[300px]",
          isOpenMobile ? "translate-x-0 w-72 shadow-2xl" : "-translate-x-full md:translate-x-0",
        ].join(" ")}
      >
        {/* Top Header: Logo + Mobile Close */}
        <div className="flex h-14 shrink-0 items-center justify-between border-b border-[var(--border)] px-4">
          <div className="flex items-center gap-2.5">
            <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-[var(--accent)] text-[var(--background)] shadow-sm">
              <svg
                className="h-4 w-4"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2.5"
                strokeLinecap="round"
                strokeLinejoin="round"
                aria-hidden="true"
              >
                <circle cx="12" cy="12" r="9" />
                <circle cx="12" cy="12" r="3" />
                <line x1="12" y1="3" x2="12" y2="6" />
                <line x1="12" y1="18" x2="12" y2="21" />
                <line x1="3" y1="12" x2="6" y2="12" />
                <line x1="18" y1="12" x2="21" y2="12" />
              </svg>
            </div>
            {!isCollapsed && (
              <div className="transition-all duration-200 ease-out min-w-0 flex flex-col justify-center">
                <div className="flex items-center gap-1.5">
                  <span className="text-sm font-semibold tracking-tight text-[var(--foreground)] truncate">
                    StartupLens AI
                  </span>
                </div>
                <span className="text-[9px] uppercase tracking-widest font-mono font-bold text-[var(--accent)] leading-none mt-0.5">
                  INTELLIGENCE
                </span>
              </div>
            )}
          </div>

          <div className="flex items-center gap-1">
            {/* Desktop Collapse / Expand Toggle */}
            <button
              type="button"
              onClick={() => setIsCollapsed((v) => !v)}
              className="hidden md:flex h-7 w-7 items-center justify-center rounded-lg text-[var(--muted)] hover:bg-[var(--surface-hover)] hover:text-[var(--foreground)] transition-colors duration-140 focus-visible:outline focus-visible:outline-2 focus-visible:outline-[var(--focus)]"
              title={isCollapsed ? "Expand sidebar" : "Collapse sidebar"}
              aria-label={isCollapsed ? "Expand sidebar" : "Collapse sidebar"}
            >
              <svg
                className={`h-3.5 w-3.5 transition-transform duration-200 ease-out ${isCollapsed ? "rotate-180" : ""}`}
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth="2"
              >
                <path strokeLinecap="round" strokeLinejoin="round" d="M11 19l-7-7 7-7m8 14l-7-7 7-7" />
              </svg>
            </button>

            {/* Mobile Close Button */}
            <button
              type="button"
              onClick={onCloseMobile}
              className="flex h-8 w-8 items-center justify-center rounded-lg text-[var(--muted)] hover:bg-[var(--surface)] hover:text-[var(--foreground)] transition-colors duration-140 focus-visible:outline focus-visible:outline-2 focus-visible:outline-[var(--focus)] md:hidden"
              aria-label="Close sidebar"
            >
              <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>

        {/* New Research Button */}
        <div className="p-2 sm:p-3">
          <button
            type="button"
            onClick={() => {
              onNewResearch();
              onNavigate("chat");
              onCloseMobile();
            }}
            title="New Research (Cmd+K)"
            className={`group flex w-full items-center rounded-xl border border-[var(--border)] bg-[var(--surface)] text-xs font-semibold text-[var(--foreground)] transition-all duration-140 hover:border-[var(--accent)]/50 hover:bg-[var(--surface-hover)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-[var(--focus)] active:scale-[0.98] ${
              isCollapsed ? "justify-center p-2.5" : "justify-between px-3.5 py-2.5"
            }`}
          >
            <div className="flex items-center gap-2 min-w-0">
              <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-md bg-[var(--accent-subtle)] text-[var(--accent)]">
                <svg className="h-3.5 w-3.5 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2.5">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" />
                </svg>
              </span>
              {!isCollapsed && <span className="truncate">New Research</span>}
            </div>
            {!isCollapsed && (
              <span className="text-[10px] font-mono text-[var(--muted)] group-hover:text-[var(--foreground)]">
                ⌘K
              </span>
            )}
          </button>
        </div>

        {/* Navigation list: Chat, Research History, Saved Ideas, Settings */}
        <div className="px-2 sm:px-3 pb-2 space-y-0.5">
          <button
            type="button"
            onClick={() => {
              onNavigate("chat");
              onCloseMobile();
            }}
            title="Chat"
            className={[
              "relative flex w-full items-center rounded-lg py-2 text-xs font-medium transition-all duration-140",
              "focus-visible:outline focus-visible:outline-2 focus-visible:outline-[var(--focus)]",
              isCollapsed ? "justify-center px-2" : "gap-2.5 px-3",
              currentNav === "chat"
                ? "bg-[var(--surface-raised)] text-[var(--foreground)] font-semibold shadow-xs"
                : "text-[var(--text-secondary)] hover:bg-[var(--surface-hover)] hover:text-[var(--foreground)]",
            ].join(" ")}
          >
            {currentNav === "chat" && (
              <span className="absolute left-0 top-1.5 bottom-1.5 w-1 rounded-r-full bg-[var(--accent)]" />
            )}
            <svg className="h-4 w-4 shrink-0 text-[var(--accent)]" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
              <path strokeLinecap="round" strokeLinejoin="round" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
            </svg>
            {!isCollapsed && <span className="truncate">Chat</span>}
          </button>

          <button
            type="button"
            onClick={() => {
              onNavigate("history");
              onCloseMobile();
            }}
            title="Research History"
            className={[
              "relative flex w-full items-center rounded-lg py-2 text-xs font-medium transition-all duration-140",
              "focus-visible:outline focus-visible:outline-2 focus-visible:outline-[var(--focus)]",
              isCollapsed ? "justify-center px-2" : "justify-between px-3",
              currentNav === "history"
                ? "bg-[var(--surface-raised)] text-[var(--foreground)] font-semibold shadow-xs"
                : "text-[var(--text-secondary)] hover:bg-[var(--surface-hover)] hover:text-[var(--foreground)]",
            ].join(" ")}
          >
            {currentNav === "history" && (
              <span className="absolute left-0 top-1.5 bottom-1.5 w-1 rounded-r-full bg-[var(--accent)]" />
            )}
            <div className="flex items-center gap-2.5 min-w-0">
              <svg className="h-4 w-4 shrink-0 text-[var(--muted)]" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              {!isCollapsed && <span className="truncate">Research History</span>}
            </div>
            {!isCollapsed && sessions.length > 0 && (
              <span className="rounded-full bg-[var(--surface-raised)] px-1.5 py-0.2 text-[10px] text-[var(--muted)]">
                {sessions.length}
              </span>
            )}
          </button>

          <button
            type="button"
            onClick={() => {
              onNavigate("saved");
              onCloseMobile();
            }}
            title="Saved Ideas"
            className={[
              "relative flex w-full items-center rounded-lg py-2 text-xs font-medium transition-all duration-140",
              "focus-visible:outline focus-visible:outline-2 focus-visible:outline-[var(--focus)]",
              isCollapsed ? "justify-center px-2" : "justify-between px-3",
              currentNav === "saved"
                ? "bg-[var(--surface-raised)] text-[var(--foreground)] font-semibold shadow-xs"
                : "text-[var(--text-secondary)] hover:bg-[var(--surface-hover)] hover:text-[var(--foreground)]",
            ].join(" ")}
          >
            {currentNav === "saved" && (
              <span className="absolute left-0 top-1.5 bottom-1.5 w-1 rounded-r-full bg-[var(--accent)]" />
            )}
            <div className="flex items-center gap-2.5 min-w-0">
              <svg className="h-4 w-4 shrink-0 text-[var(--warning)]" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                <path strokeLinecap="round" strokeLinejoin="round" d="M11.049 2.927c.3-.921 1.603-.921 1.902 0l1.519 4.674a1 1 0 00.95.69h4.915c.969 0 1.371 1.24.588 1.81l-3.976 2.888a1 1 0 00-.363 1.118l1.518 4.674c.3.922-.755 1.688-1.538 1.118l-3.976-2.888a1 1 0 00-1.176 0l-3.976 2.888c-.783.57-1.838-.197-1.538-1.118l1.518-4.674a1 1 0 00-.363-1.118l-3.976-2.888c-.784-.57-.38-1.81.588-1.81h4.914a1 1 0 00.951-.69l1.519-4.674z" />
              </svg>
              {!isCollapsed && <span className="truncate">Saved Ideas</span>}
            </div>
            {!isCollapsed && savedIdeasCount > 0 && (
              <span className="rounded-full bg-[var(--warning)]/15 px-1.5 py-0.2 text-[10px] font-semibold text-[var(--warning)]">
                {savedIdeasCount}
              </span>
            )}
          </button>

          <button
            type="button"
            onClick={() => {
              onNavigate("tracker");
              onCloseMobile();
            }}
            title="Research Tracker"
            className={[
              "relative flex w-full items-center rounded-lg py-2 text-xs font-medium transition-all duration-140",
              "focus-visible:outline focus-visible:outline-2 focus-visible:outline-[var(--focus)]",
              isCollapsed ? "justify-center px-2" : "gap-2.5 px-3",
              currentNav === "tracker"
                ? "bg-[var(--surface-raised)] text-[var(--foreground)] font-semibold shadow-xs"
                : "text-[var(--text-secondary)] hover:bg-[var(--surface-hover)] hover:text-[var(--foreground)]",
            ].join(" ")}
          >
            {currentNav === "tracker" && (
              <span className="absolute left-0 top-1.5 bottom-1.5 w-1 rounded-r-full bg-[var(--accent)]" />
            )}
            <svg className="h-4 w-4 shrink-0 text-[var(--accent)]" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
              <path strokeLinecap="round" strokeLinejoin="round" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
            </svg>
            {!isCollapsed && <span className="truncate">Research Tracker</span>}
          </button>

          <button
            type="button"
            onClick={onOpenSettings}
            title="Settings"
            className={[
              "relative flex w-full items-center rounded-lg py-2 text-xs font-medium transition-all duration-140",
              "focus-visible:outline focus-visible:outline-2 focus-visible:outline-[var(--focus)]",
              isCollapsed ? "justify-center px-2" : "gap-2.5 px-3",
              "text-[var(--text-secondary)] hover:bg-[var(--surface-hover)] hover:text-[var(--foreground)]",
            ].join(" ")}
          >
            <svg className="h-4 w-4 shrink-0 text-[var(--muted)]" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
              <path strokeLinecap="round" strokeLinejoin="round" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
              <path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
            </svg>
            {!isCollapsed && <span className="truncate">Settings</span>}
          </button>
        </div>

        {/* Divider */}
        <hr className="border-t border-[var(--border)] my-1" />

        {/* Recent Research Section */}
        <div className={`flex flex-1 flex-col overflow-hidden px-2 sm:px-3 pt-2 transition-opacity duration-200 ${isCollapsed ? "opacity-0 pointer-events-none md:hidden" : "opacity-100"}`}>
          {/* Header with Search Toggle */}
          <div className="mb-2 flex items-center justify-between px-1 text-[11px] font-semibold uppercase tracking-wider text-[var(--muted)]">
            <span>Recent Research</span>
            <div className="flex items-center gap-1">
              <button
                type="button"
                onClick={() => setShowSearchInput((v) => !v)}
                title="Search research sessions"
                aria-label="Search research sessions"
                className="rounded p-1 text-[var(--muted)] hover:text-[var(--foreground)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-[var(--focus)]"
              >
                <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                </svg>
              </button>
              <button
                type="button"
                onClick={fetchSessions}
                title="Refresh sessions list"
                aria-label="Refresh sessions list"
                className="rounded p-1 text-[var(--muted)] hover:text-[var(--foreground)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-[var(--focus)]"
              >
                <svg
                  className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`}
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                  strokeWidth="2"
                >
                  <path strokeLinecap="round" strokeLinejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
              </button>
            </div>
          </div>

          {/* Quick search input */}
          {showSearchInput && (
            <div className="mb-2 px-1">
              <div className="flex items-center gap-1.5 rounded-lg border border-[var(--border)] bg-[var(--surface)] px-2 py-1 text-xs">
                <svg className="h-3.5 w-3.5 text-[var(--muted)]" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                </svg>
                <input
                  type="text"
                  placeholder="Filter sessions..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full bg-transparent text-xs text-[var(--foreground)] placeholder-[var(--muted)] outline-none"
                  autoFocus
                />
                {searchQuery && (
                  <button type="button" onClick={() => setSearchQuery("")} className="text-[var(--muted)] hover:text-[var(--foreground)]">
                    ✕
                  </button>
                )}
              </div>
            </div>
          )}

          {/* Sessions List */}
          <div className="flex-1 overflow-y-auto space-y-0.5">
            {loading && sessions.length === 0 && (
              <div className="space-y-1.5 px-1 py-2">
                {[80, 60, 70].map((w, idx) => (
                  <div key={idx} className="h-8 animate-pulse rounded-lg bg-[var(--surface)]" style={{ width: `${w}%` }} />
                ))}
              </div>
            )}

            {error && (
              <div className="rounded-lg border border-red-900/40 bg-red-950/20 p-2 text-xs text-red-300">
                <p>{error}</p>
                <button type="button" onClick={fetchSessions} className="mt-1 font-semibold underline">
                  Retry
                </button>
              </div>
            )}

            {!loading && !error && filteredSessions.length === 0 && (
              <div className="px-2 py-6 text-center text-xs text-[var(--muted)]">
                <p>{searchQuery ? "No matching research" : "No research yet"}</p>
                <p className="mt-1 text-[11px] text-[var(--muted)]/70">
                  {searchQuery ? "Try a different search term" : "Ask anything in the chat"}
                </p>
              </div>
            )}

            {/* Grouped Timeline Sessions List */}
            {(() => {
              const maxDisplay = 8;
              const displayList = filteredSessions.slice(0, maxDisplay);
              const now = new Date();
              const startOfToday = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime();
              const startOfYesterday = startOfToday - 24 * 60 * 60 * 1000;

              const groups: { title: string; items: typeof filteredSessions }[] = [
                {
                  title: "TODAY",
                  items: displayList.filter((s) => s.created_at && new Date(s.created_at).getTime() >= startOfToday),
                },
                {
                  title: "YESTERDAY",
                  items: displayList.filter((s) => {
                    if (!s.created_at) return false;
                    const t = new Date(s.created_at).getTime();
                    return t < startOfToday && t >= startOfYesterday;
                  }),
                },
                {
                  title: "EARLIER",
                  items: displayList.filter((s) => {
                    if (!s.created_at) return true;
                    return new Date(s.created_at).getTime() < startOfYesterday;
                  }),
                },
              ].filter((g) => g.items.length > 0);

              return (
                <div className="space-y-3">
                  {groups.map((group) => (
                    <div key={group.title} className="space-y-1">
                      <p className="px-1 text-[9px] font-mono font-bold tracking-wider text-[var(--muted)]">
                        {group.title}
                      </p>

                      <div className="relative pl-3 space-y-1 before:absolute before:left-1 before:top-2 before:bottom-2 before:w-px before:bg-[var(--border)]">
                        {group.items.map((s) => {
                          const isActive = s.id === activeSessionId && currentNav === "chat";
                          const isDeleting = deletingId === s.id;

                          return (
                            <div key={s.id} className="group relative">
                              {/* Timeline bullet */}
                              <span
                                className={`absolute -left-[11px] top-3 h-1.5 w-1.5 rounded-full transition-colors duration-140 ${
                                  isActive
                                    ? "bg-[var(--accent)] ring-2 ring-[var(--accent)]/30"
                                    : "bg-[var(--muted)]/50 group-hover:bg-[var(--accent)]"
                                }`}
                                aria-hidden="true"
                              />

                              <button
                                type="button"
                                onClick={() => {
                                  onSelectSession(s.id);
                                  onNavigate("chat");
                                  onCloseMobile();
                                }}
                                disabled={isDeleting}
                                aria-current={isActive ? "page" : undefined}
                                className={[
                                  "flex w-full items-center justify-between rounded-lg px-2.5 py-1.5 text-left transition-colors duration-160 ease-out",
                                  "focus-visible:outline focus-visible:outline-2 focus-visible:outline-[var(--focus)]",
                                  isActive
                                    ? "bg-[var(--surface-raised)] text-[var(--foreground)] font-semibold shadow-xs"
                                    : "text-[var(--text-secondary)] hover:bg-[var(--surface-hover)] hover:text-[var(--foreground)]",
                                  isDeleting ? "opacity-40 cursor-not-allowed" : "",
                                ].join(" ")}
                              >
                                <div className="min-w-0 flex-1 pr-6">
                                  <p className="truncate text-xs font-medium">{s.topic}</p>
                                  <div className="mt-0.5 flex items-center gap-1.5 text-[10px] text-[var(--muted)]">
                                    <span>{formatRelativeTime(s.created_at)}</span>
                                    {s.opportunities_count > 0 && (
                                      <>
                                        <span>·</span>
                                        <span className="font-mono text-[10px] text-[var(--foreground)]">
                                          {s.opportunities_count} opps
                                        </span>
                                      </>
                                    )}
                                  </div>
                                </div>
                              </button>

                              {/* Delete button */}
                              <button
                                type="button"
                                onClick={(e) => handleDelete(e, s.id)}
                                aria-label={`Delete "${s.topic}"`}
                                title="Delete session"
                                className={[
                                  "absolute right-1.5 top-1/2 -translate-y-1/2 flex h-6 w-6 items-center justify-center rounded-md",
                                  "text-[var(--muted)] hover:bg-[var(--surface-hover)] hover:text-red-400",
                                  "opacity-0 group-hover:opacity-100 focus:opacity-100 transition-opacity",
                                ].join(" ")}
                              >
                                {isDeleting ? (
                                  <svg className="h-3 w-3 animate-spin" fill="none" viewBox="0 0 24 24">
                                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
                                  </svg>
                                ) : (
                                  <svg className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                                    <path strokeLinecap="round" strokeLinejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                                  </svg>
                                )}
                              </button>
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  ))}

                  {/* View All Action */}
                  {filteredSessions.length > maxDisplay && (
                    <button
                      type="button"
                      onClick={() => {
                        onNavigate("history");
                        onCloseMobile();
                      }}
                      className="mt-2 flex w-full items-center justify-between rounded-lg px-2.5 py-1.5 text-xs font-medium text-[var(--accent)] hover:bg-[var(--surface-hover)] transition-colors"
                    >
                      <span>View all {filteredSessions.length} sessions</span>
                      <span>→</span>
                    </button>
                  )}
                </div>
              );
            })()}
          </div>
        </div>

        {/* Bottom User Profile Section: Founder Workspace with Attached PRO Badge */}
        <div className="relative shrink-0 border-t border-[var(--border)] p-3">
          <div className="flex items-center justify-between rounded-xl border border-[var(--border)] bg-[var(--surface)] p-2.5 hover:border-[var(--border)]/80 transition-colors">
            <div className="flex items-center gap-2.5 min-w-0">
              <div className="relative flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-[var(--surface-raised)] border border-[var(--border-subtle)] text-xs font-bold text-[var(--accent)] font-mono">
                SL
                <span className="absolute -bottom-0.5 -right-0.5 h-2 w-2 rounded-full bg-[var(--success)] ring-2 ring-[var(--surface)]" />
              </div>
              <div className="min-w-0">
                <div className="flex items-center gap-1.5">
                  <p className="truncate text-xs font-semibold text-[var(--foreground)]">
                    Founder Workspace
                  </p>
                  <span className="shrink-0 rounded px-1.5 py-0.2 text-[9px] font-mono font-bold bg-[var(--accent-subtle)] text-[var(--accent)] border border-[var(--accent)]/30">
                    PRO
                  </span>
                </div>
                <p className="truncate text-[10px] text-[var(--muted)]">
                  Researcher Tier · Connected
                </p>
              </div>
            </div>

            <button
              type="button"
              onClick={() => setShowUserMenu((v) => !v)}
              aria-label="User account menu"
              className="flex h-7 w-7 items-center justify-center rounded-lg text-[var(--muted)] hover:text-[var(--foreground)] hover:bg-[var(--surface-hover)] transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-[var(--focus)]"
            >
              <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                <circle cx="12" cy="12" r="1" />
                <circle cx="19" cy="12" r="1" />
                <circle cx="5" cy="12" r="1" />
              </svg>
            </button>
          </div>

          {/* User Popover Menu */}
          {showUserMenu && (
            <div className="absolute bottom-full left-3 right-3 mb-2 rounded-xl border border-[var(--border)] bg-[var(--surface-raised)] p-2 shadow-2xl z-30 animate-in fade-in">
              <div className="px-2 py-1 border-b border-[var(--border)] pb-2 mb-1">
                <p className="text-xs font-semibold text-[var(--foreground)]">StartupLens AI</p>
                <p className="text-[10px] text-[var(--muted)]">Connected to FastAPI + SQLite</p>
              </div>
              <button
                type="button"
                onClick={() => {
                  setShowUserMenu(false);
                  onOpenSettings();
                }}
                className="flex w-full items-center gap-2 rounded-lg px-2 py-1.5 text-xs text-[var(--text-secondary)] hover:bg-[var(--surface)] hover:text-[var(--foreground)]"
              >
                <span>⚙️ System Info & Settings</span>
              </button>
              <button
                type="button"
                onClick={() => {
                  setShowUserMenu(false);
                  onNavigate("saved");
                }}
                className="flex w-full items-center gap-2 rounded-lg px-2 py-1.5 text-xs text-[var(--text-secondary)] hover:bg-[var(--surface)] hover:text-[var(--foreground)]"
              >
                <span>⭐ View Saved Ideas</span>
              </button>
            </div>
          )}
        </div>
      </aside>
    </>
  );
}
