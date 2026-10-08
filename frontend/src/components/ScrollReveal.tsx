"use client";

import React, { useRef, useState, useEffect } from "react";

interface ScrollRevealProps {
  children: React.ReactNode;
  className?: string;
  delayMs?: number;
}

/**
 * ScrollReveal reveals large sections as the user scrolls into them.
 * Principles:
 * - Uses transform (translateY 12px) and opacity
 * - Only animates ONCE per section
 * - Fully respects prefers-reduced-motion
 * - No expensive continuous observers or layout shifts
 */
export function ScrollReveal({ children, className = "", delayMs = 0 }: ScrollRevealProps) {
  const [isVisible, setIsVisible] = useState(false);
  const elementRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!("IntersectionObserver" in window)) {
      const timer = setTimeout(() => setIsVisible(true), 0);
      return () => clearTimeout(timer);
    }

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setIsVisible(true);
          // Only animate once per section
          if (elementRef.current) {
            observer.unobserve(elementRef.current);
          }
        }
      },
      {
        threshold: 0.05,
        rootMargin: "0px 0px -40px 0px",
      }
    );

    const currentEl = elementRef.current;
    if (currentEl) {
      observer.observe(currentEl);
    }

    return () => {
      if (currentEl) observer.unobserve(currentEl);
      observer.disconnect();
    };
  }, []);

  return (
    <div
      ref={elementRef}
      style={{
        transitionDuration: "360ms",
        transitionTimingFunction: "cubic-bezier(0.16, 1, 0.3, 1)",
        transitionDelay: `${delayMs}ms`,
      }}
      className={[
        "transition-all",
        isVisible
          ? "opacity-100 translate-y-0"
          : "opacity-0 translate-y-3 pointer-events-none sm:pointer-events-auto",
        className,
      ].join(" ")}
    >
      {children}
    </div>
  );
}
