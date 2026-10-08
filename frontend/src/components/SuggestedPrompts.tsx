"use client";

import React from "react";

interface SuggestedPromptsProps {
  onSelectPrompt: (prompt: string) => void;
  disabled?: boolean;
}

const PROMPTS = [
  {
    id: "opportunities",
    title: "Find startup opportunities",
    promptText: "Find startup opportunities in AI and automation",
    icon: (
      <svg className="h-4 w-4 text-[var(--accent)] transition-transform duration-200 group-hover:scale-110" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
        <circle cx="12" cy="12" r="10" />
        <line x1="12" y1="8" x2="12" y2="12" />
        <line x1="12" y1="16" x2="12.01" y2="16" />
        <path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3" />
      </svg>
    ),
  },
  {
    id: "market-size",
    title: "Analyze market size",
    promptText: "Analyze market size, growth trends, and macro signals for AI developer tools",
    icon: (
      <svg className="h-4 w-4 text-[var(--accent)] transition-transform duration-200 group-hover:scale-110" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
        <path d="M3 3v18h18" />
        <path d="M18 9l-5 5-4-4-6 6" />
      </svg>
    ),
  },
  {
    id: "competitors",
    title: "Show key competitors",
    promptText: "Show me key competitors and underserved gaps in AI agents for business workflows",
    icon: (
      <svg className="h-4 w-4 text-[var(--accent)] transition-transform duration-200 group-hover:scale-110" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
        <circle cx="12" cy="12" r="10" />
        <circle cx="12" cy="12" r="6" />
        <circle cx="12" cy="12" r="2" />
      </svg>
    ),
  },
  {
    id: "unique-ideas",
    title: "Suggest unique startup ideas",
    promptText: "Suggest unique startup ideas with high conviction and 4-week MVP scopes",
    icon: (
      <svg className="h-4 w-4 text-[var(--accent)] transition-transform duration-200 group-hover:scale-110" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
        <path d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
      </svg>
    ),
  },
];

export function SuggestedPrompts({ onSelectPrompt, disabled = false }: SuggestedPromptsProps) {
  return (
    <div className="w-full max-w-[860px] px-1">
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-2 sm:gap-2.5">
        {PROMPTS.map((prompt) => (
          <button
            key={prompt.id}
            type="button"
            disabled={disabled}
            onClick={() => onSelectPrompt(prompt.promptText)}
            className={[
              "group relative flex h-11 sm:h-12 items-center gap-2.5 rounded-xl border border-[var(--border)] bg-[var(--surface)] px-3 text-left shadow-2xs",
              "transition-all duration-[180ms] ease-out",
              "hover:-translate-y-[2px] hover:border-[var(--accent)]/40 hover:bg-[var(--surface-hover)] hover:shadow-xs",
              "focus-visible:outline focus-visible:outline-2 focus-visible:outline-[var(--focus)]",
              "disabled:cursor-not-allowed disabled:opacity-50 cursor-pointer",
            ].join(" ")}
          >
            <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded-lg border border-[var(--border-subtle)] bg-[var(--surface-raised)] transition-colors duration-[180ms] group-hover:border-[var(--accent)]/30 group-hover:bg-[var(--accent-subtle)]">
              {prompt.icon}
            </div>
            <span className="text-xs font-medium text-[var(--foreground)] group-hover:text-[var(--accent)] transition-colors duration-[180ms] truncate">
              {prompt.title}
            </span>
          </button>
        ))}
      </div>
    </div>
  );
}
