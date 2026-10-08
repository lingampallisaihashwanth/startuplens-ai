"use client";

import React from "react";

export type AgentStep =
  | "searching"
  | "extracting"
  | "analyzing"
  | "generating"
  | "validating"
  | "done"
  | "idle";

interface StepConfig {
  key: AgentStep;
  label: string;
}

const STEPS: StepConfig[] = [
  { key: "searching", label: "Web Research" },
  { key: "extracting", label: "Market Signals" },
  { key: "analyzing", label: "Customer Problems" },
  { key: "generating", label: "Opportunity Engine" },
  { key: "validating", label: "Evidence Audit" },
];

type StepState = "done" | "active" | "pending";

function getStepState(stepKey: AgentStep, currentStep: AgentStep): StepState {
  const order: AgentStep[] = [
    "searching",
    "extracting",
    "analyzing",
    "generating",
    "validating",
    "done",
  ];
  const stepIdx = order.indexOf(stepKey);
  const currentIdx = order.indexOf(currentStep);

  if (currentStep === "done") return "done";
  if (currentIdx > stepIdx) return "done";
  if (stepIdx === currentIdx) return "active";
  return "pending";
}

function getProgressPercent(currentStep: AgentStep): number {
  switch (currentStep) {
    case "searching":
      return 20;
    case "extracting":
      return 40;
    case "analyzing":
      return 60;
    case "generating":
      return 80;
    case "validating":
      return 95;
    case "done":
      return 100;
    default:
      return 5;
  }
}

interface AgentStatusProps {
  currentStep: AgentStep;
  topic?: string;
}

export function AgentStatus({ currentStep, topic }: AgentStatusProps) {
  if (currentStep === "idle") return null;

  if (currentStep === "done") {
    return (
      <div
        role="status"
        aria-live="polite"
        className="my-3 flex items-center gap-2 rounded-xl border border-[var(--success)]/30 bg-[var(--success)]/10 px-3.5 py-2.5 text-xs text-[var(--success)] animate-[motionFadeSlideDown_200ms_cubic-bezier(0.16,1,0.3,1)_both]"
      >
        <span className="flex h-4 w-4 items-center justify-center rounded-full bg-[var(--success)]/20 text-[10px] font-bold">
          ✓
        </span>
        <span className="font-medium tracking-wide">Research complete · Evidence verified</span>
      </div>
    );
  }

  const topicName = topic || "Market Intelligence";
  const progressPercent = getProgressPercent(currentStep);

  return (
    <div
      role="status"
      aria-live="polite"
      aria-label="Active research pipeline"
      className="my-5 rounded-2xl border border-[var(--border)] bg-[var(--surface)] p-5 max-w-md shadow-sm transition-all duration-200 ease-out"
    >
      {/* Header */}
      <div className="pb-3 mb-3 border-b border-[var(--border-subtle)]">
        <p className="text-[10px] font-mono font-bold uppercase tracking-wider text-[var(--accent)]">
          RESEARCHING
        </p>
        <h3 className="mt-1 text-base font-bold text-[var(--foreground)] truncate">
          {topicName}
        </h3>
      </div>

      {/* Thin Animated Progress Line */}
      <div className="mb-4 space-y-1">
        <div className="h-1 w-full rounded-full bg-[var(--surface-raised)] overflow-hidden">
          <div
            className="h-full rounded-full bg-[var(--accent)] transition-all duration-500 ease-out"
            style={{ width: `${progressPercent}%` }}
          />
        </div>
        <div className="flex justify-between text-[10px] text-[var(--muted)] font-mono">
          <span>Synthesizing live web evidence</span>
          <span>{progressPercent}%</span>
        </div>
      </div>

      {/* 5 Distinct Stages */}
      <div className="space-y-2">
        {STEPS.map((step) => {
          const state = getStepState(step.key, currentStep);

          return (
            <div
              key={step.key}
              className={[
                "flex items-center justify-between py-1.5 px-2.5 rounded-lg text-xs transition-all duration-180 ease-out",
                state === "active"
                  ? "bg-[var(--accent-subtle)] text-[var(--foreground)] font-medium translate-x-0.5"
                  : state === "done"
                  ? "text-[var(--text-secondary)] opacity-90"
                  : "text-[var(--muted)] opacity-60",
              ].join(" ")}
            >
              <span className="font-medium">{step.label}</span>

              <span className="font-mono text-xs font-semibold">
                {state === "done" && (
                  <span className="text-[var(--success)]">✓</span>
                )}
                {state === "active" && (
                  <span className="inline-block text-[var(--accent)] animate-pulse">●</span>
                )}
                {state === "pending" && (
                  <span className="text-[var(--muted)]">○</span>
                )}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
