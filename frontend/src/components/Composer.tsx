"use client";

import React, { useRef, useEffect, useCallback, useState, KeyboardEvent } from "react";
import { uploadDocument } from "@/lib/api";

interface ComposerProps {
  onSubmit: (topic: string, documentIds?: string[]) => void;
  isLoading: boolean;
  initialValue?: string;
  modelDisplay?: string;
  onOpenModelSelector?: () => void;
  className?: string;
}

export function Composer({
  onSubmit,
  isLoading,
  initialValue = "",
  modelDisplay = "Auto",
  onOpenModelSelector,
  className = "",
}: ComposerProps) {
  const [value, setValue] = useState(initialValue);
  const [prevInitialValue, setPrevInitialValue] = useState(initialValue);
  const [showWebMenu, setShowWebMenu] = useState(false);
  const [attachments, setAttachments] = useState<{
    file: File;
    status: "uploading" | "ready" | "error";
    docId?: string;
    error?: string;
  }[]>([]);

  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  if (initialValue !== prevInitialValue) {
    setPrevInitialValue(initialValue);
    setValue(initialValue);
  }

  const adjustHeight = useCallback(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    const nextHeight = Math.min(el.scrollHeight, 180);
    el.style.height = `${Math.max(nextHeight, 36)}px`;
  }, []);

  useEffect(() => {
    if (!isLoading && textareaRef.current) {
      textareaRef.current.focus();
    }
  }, [isLoading]);

  useEffect(() => {
    adjustHeight();
  }, [value, adjustHeight]);

  const handleInput = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setValue(e.target.value);
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files || files.length === 0) return;

    for (let i = 0; i < files.length; i++) {
      const file = files[i];
      const tempItem = { file, status: "uploading" as const };
      setAttachments((prev) => [...prev, tempItem]);

      try {
        const uploaded = await uploadDocument(file);
        setAttachments((prev) =>
          prev.map((item) =>
            item.file === file
              ? { ...item, status: "ready", docId: uploaded.id }
              : item
          )
        );
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : "Upload failed";
        setAttachments((prev) =>
          prev.map((item) =>
            item.file === file
              ? { ...item, status: "error", error: msg }
              : item
          )
        );
      }
    }

    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  const removeAttachment = (fileToRemove: File) => {
    setAttachments((prev) => prev.filter((a) => a.file !== fileToRemove));
  };

  const handleSend = useCallback(() => {
    const trimmed = value.trim();
    if (!trimmed || isLoading) return;

    const readyDocIds = attachments
      .filter((a) => a.status === "ready" && a.docId)
      .map((a) => a.docId as string);

    onSubmit(trimmed, readyDocIds);
    setValue("");
    setAttachments([]);
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }
  }, [value, isLoading, attachments, onSubmit]);

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className={`relative z-10 w-full ${className}`}>
      {/* Hidden file input */}
      <input
        ref={fileInputRef}
        type="file"
        accept=".pdf,.docx,.txt,.md"
        multiple
        className="hidden"
        onChange={handleFileUpload}
      />

      {/* Attachment chips display */}
      {attachments.length > 0 && (
        <div className="mb-2.5 flex flex-wrap items-center gap-2 px-1">
          <span className="text-[11px] font-medium text-[var(--muted)]">
            {attachments.length} file{attachments.length > 1 ? "s" : ""} attached:
          </span>
          {attachments.map(({ file, status, error }, idx) => (
            <div
              key={`${file.name}-${idx}`}
              className="inline-flex items-center gap-1.5 rounded-lg border border-[var(--border)] bg-[var(--surface-raised)] px-2.5 py-1 text-xs text-[var(--foreground)] shadow-xs animate-in fade-in"
            >
              <span className="font-medium truncate max-w-[140px]" title={file.name}>
                {file.name}
              </span>
              <span className="text-[10px] uppercase text-[var(--muted)]">
                ({(file.size / 1024).toFixed(0)} KB)
              </span>
              {status === "uploading" && (
                <svg className="h-3 w-3 animate-spin text-[var(--accent)]" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
                </svg>
              )}
              {status === "ready" && (
                <span className="text-[var(--success)] text-[11px]" title="Extracted and ready">✓</span>
              )}
              {status === "error" && (
                <span className="text-[var(--error)] text-[11px]" title={error || "Error"}>⚠</span>
              )}
              <button
                type="button"
                onClick={() => removeAttachment(file)}
                className="ml-1 text-[var(--muted)] hover:text-red-400"
                title="Remove file"
                aria-label={`Remove ${file.name}`}
              >
                ✕
              </button>
            </div>
          ))}
        </div>
      )}

      {/* Main Composer Box */}
      <div
        className={[
          "group relative flex flex-col rounded-2xl border bg-[var(--surface)] p-3 sm:p-4 shadow-xs",
          "transition-[border-color,box-shadow] duration-180 ease-out",
          isLoading
            ? "border-[var(--border)] opacity-85"
            : "border-[var(--border)] hover:border-[var(--border)]/90 focus-within:border-[var(--accent)]/50 focus-within:shadow-[0_4px_24px_-4px_rgba(94,158,240,0.14)]",
        ].join(" ")}
      >
        {/* Text input area */}
        <div className="flex items-start px-1 pt-0.5">
          <textarea
            ref={textareaRef}
            id="composer-input"
            value={value}
            onChange={handleInput}
            onKeyDown={handleKeyDown}
            disabled={isLoading}
            rows={1}
            placeholder="Ask StartupLens about a market, problem, or startup idea..."
            aria-label="Research topic input"
            aria-describedby="composer-hint"
            className="w-full resize-none border-0 outline-none ring-0 focus:outline-none focus:ring-0 focus:border-0 focus-visible:outline-none focus-visible:ring-0 shadow-none focus:shadow-none bg-transparent text-sm sm:text-base leading-relaxed text-[var(--foreground)] placeholder-[var(--muted)] disabled:cursor-not-allowed transition-colors duration-140"
            style={{ maxHeight: "180px", minHeight: "38px" }}
          />
        </div>

        {/* Divider */}
        <div className="border-t border-[var(--border-subtle)] mt-2.5 mb-2.5" />

        {/* Bottom Control Bar: [Attach...] on left, [Web + Docs] [AI Model] [→] on right */}
        <div className="flex items-center justify-between gap-2 px-0.5">
          {/* Bottom Left: Attach document */}
          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            title="Attach PDF, DOCX, TXT, or MD"
            aria-label="Attach documents"
            className="h-8 inline-flex items-center gap-1.5 rounded-lg border border-[var(--border-subtle)] bg-[var(--surface-raised)]/60 px-2.5 text-xs font-medium text-[var(--muted)] hover:border-[var(--border)] hover:text-[var(--foreground)] hover:bg-[var(--surface-raised)] transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-[var(--focus)]"
          >
            <span className="text-[var(--accent)] font-bold text-xs leading-none">+</span>
            <span className="hidden sm:inline">Attach PDF/DOCX/TXT/MD</span>
            <span className="sm:hidden">Attach</span>
          </button>

          {/* Bottom Right: Web + Docs · AI Model · Send */}
          <div className="flex items-center gap-2">
            {/* Web + Docs toggle */}
            <div className="relative">
              <button
                type="button"
                onClick={() => setShowWebMenu((v) => !v)}
                aria-expanded={showWebMenu}
                aria-label="Web search mode toggle"
                className="h-8 flex items-center gap-1.5 rounded-lg border border-[var(--border-subtle)] bg-[var(--surface-raised)]/70 px-2.5 text-xs font-medium text-[var(--text-secondary)] transition-colors hover:border-[var(--accent)]/40 hover:text-[var(--foreground)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-[var(--focus)]"
              >
                <span className="h-1.5 w-1.5 rounded-full bg-[var(--success)]" aria-hidden="true" />
                <span className="hidden xs:inline">Web + Docs</span>
                <span className="xs:hidden">Web</span>
                <svg className="h-3 w-3 text-[var(--muted)]" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2" aria-hidden="true">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
                </svg>
              </button>

              {showWebMenu && (
                <div className="absolute bottom-full right-0 mb-2 w-56 rounded-xl border border-[var(--border)] bg-[var(--surface-raised)] p-2.5 shadow-xl z-20 animate-[motionFadeSlideDown_160ms_cubic-bezier(0.16,1,0.3,1)_both]">
                  <p className="px-1 py-0.5 text-[10px] font-semibold uppercase tracking-wider text-[var(--muted)]">
                    Intelligence Sources
                  </p>
                  <div className="mt-1 space-y-1 rounded-lg bg-[var(--surface)] p-2 text-xs">
                    <p className="font-medium text-[var(--foreground)]">Live Web + Documents</p>
                    <p className="text-[11px] text-[var(--muted)]">Tavily live crawl + User uploaded PDF/DOCX (Web evidence takes priority)</p>
                  </div>
                </div>
              )}
            </div>

            {/* AI Model Button / Pill */}
            <button
              type="button"
              onClick={onOpenModelSelector}
              aria-label="Select AI model"
              className="h-8 inline-flex items-center gap-1.5 rounded-lg border border-[var(--border-subtle)] bg-[var(--surface-raised)]/70 px-2.5 text-xs font-mono text-[var(--muted)] hover:border-[var(--accent)]/40 hover:text-[var(--foreground)] transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-[var(--focus)]"
            >
              <span className="h-1.5 w-1.5 rounded-full bg-[var(--accent)]" />
              <span className="hidden sm:inline">AI Model · </span>
              <span className="text-[var(--foreground)] font-semibold">{modelDisplay}</span>
            </button>

            {/* Send Button → */}
            <button
              type="button"
              onClick={handleSend}
              disabled={isLoading || !value.trim()}
              aria-label={isLoading ? "Analyzing..." : "Send research request"}
              className={[
                "h-8 w-8 flex items-center justify-center rounded-xl transition-all duration-140 ease-out",
                "focus-visible:outline focus-visible:outline-2 focus-visible:outline-[var(--focus)]",
                isLoading || !value.trim()
                  ? "cursor-not-allowed bg-[var(--surface-raised)] text-[var(--muted)] opacity-40"
                  : "bg-[var(--accent)] text-[var(--background)] hover:brightness-105 active:scale-95 cursor-pointer shadow-xs",
              ].join(" ")}
            >
              {isLoading ? (
                <svg className="h-4 w-4 animate-spin text-[var(--foreground)]" fill="none" viewBox="0 0 24 24" aria-hidden="true">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
                </svg>
              ) : (
                <span className="text-base font-bold leading-none">→</span>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
