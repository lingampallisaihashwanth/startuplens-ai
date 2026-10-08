"use client";

import React from "react";

/**
 * IntelligenceNetworkVisual
 * A very subtle, slow-animated AI research network topology visual.
 * Features:
 * - Tiny dots at graph vertices
 * - Flowing connection paths with slow dash offset
 * - Slow-moving signal pulses
 * - Extremely low opacity to stay non-distracting and grounded in editorial aesthetic
 */
export function IntelligenceNetworkVisual() {
  return (
    <div
      aria-hidden="true"
      className="pointer-events-none absolute inset-0 overflow-hidden flex items-center justify-center opacity-[0.18] dark:opacity-[0.24] transition-opacity duration-500"
    >
      <svg
        viewBox="0 0 1000 420"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        className="w-full h-full max-w-5xl max-h-[380px] text-[var(--accent)]"
        preserveAspectRatio="xMidYMid meet"
      >
        <defs>
          <linearGradient id="networkGradient" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="currentColor" stopOpacity="0.3" />
            <stop offset="50%" stopColor="currentColor" stopOpacity="0.75" />
            <stop offset="100%" stopColor="currentColor" stopOpacity="0.3" />
          </linearGradient>

          <filter id="softGlow" x="-20%" y="-20%" width="140%" height="140%">
            <feGaussianBlur stdDeviation="3" result="blur" />
            <feComposite in="SourceGraphic" in2="blur" operator="over" />
          </filter>
        </defs>

        {/* ── Flowing Connection Paths ── */}
        <g stroke="url(#networkGradient)" strokeWidth="1" strokeLinecap="round">
          {/* Main lateral spine */}
          <path
            d="M 120 210 C 240 140, 360 160, 500 210 C 640 260, 760 280, 880 210"
            strokeDasharray="4 8"
            className="animate-[networkFlow_24s_linear_infinite]"
          />
          {/* Upper converging branch */}
          <path
            d="M 220 110 C 320 180, 410 130, 500 210 C 590 290, 680 180, 780 120"
            strokeDasharray="3 6"
            className="animate-[networkFlow_20s_linear_infinite]"
          />
          {/* Lower divergent branch */}
          <path
            d="M 180 300 C 290 260, 390 270, 500 210 C 610 150, 710 240, 820 310"
            strokeDasharray="4 7"
            className="animate-[networkFlowReverse_26s_linear_infinite]"
          />
          {/* Cross signal lines */}
          <path
            d="M 320 160 C 370 230, 440 250, 500 210"
            strokeDasharray="2 5"
            strokeOpacity="0.6"
          />
          <path
            d="M 500 210 C 560 170, 630 190, 680 230"
            strokeDasharray="2 5"
            strokeOpacity="0.6"
          />
        </g>

        {/* ── Stationary Vertex Dots ── */}
        <g fill="currentColor" opacity="0.6">
          <circle cx="120" cy="210" r="2" />
          <circle cx="220" cy="110" r="2.5" />
          <circle cx="180" cy="300" r="2" />
          <circle cx="320" cy="160" r="2" />
          <circle cx="500" cy="210" r="3.5" filter="url(#softGlow)" />
          <circle cx="680" cy="230" r="2" />
          <circle cx="780" cy="120" r="2.5" />
          <circle cx="820" cy="310" r="2" />
          <circle cx="880" cy="210" r="2" />
        </g>

        {/* ── Slow-moving Signal Pulse Nodes ── */}
        <g fill="currentColor">
          {/* Central hub pulse */}
          <circle
            cx="500"
            cy="210"
            r="5"
            opacity="0.35"
            className="animate-[networkPulse_4s_ease-in-out_infinite]"
          />
          {/* Left node pulse */}
          <circle
            cx="320"
            cy="160"
            r="3"
            opacity="0.4"
            className="animate-[networkPulse_5s_ease-in-out_1s_infinite]"
          />
          {/* Right node pulse */}
          <circle
            cx="680"
            cy="230"
            r="3"
            opacity="0.4"
            className="animate-[networkPulse_4.5s_ease-in-out_2s_infinite]"
          />
        </g>
      </svg>
    </div>
  );
}
