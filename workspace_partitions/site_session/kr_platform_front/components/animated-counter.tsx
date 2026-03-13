"use client";

import { useEffect, useRef, useState } from "react";

type AnimatedCounterProps = {
  /** Target number to count up to */
  end: number;
  /** Optional suffix like "+" or "개" */
  suffix?: string;
  /** Duration in milliseconds (default 1600) */
  duration?: number;
};

/**
 * Animated number counter that counts from 0 to `end` when scrolled into view.
 * Uses IntersectionObserver to trigger + requestAnimationFrame for smooth 60fps.
 * Respects prefers-reduced-motion by showing the final value immediately.
 */
export function AnimatedCounter({
  end,
  suffix = "",
  duration = 1600,
}: AnimatedCounterProps) {
  const ref = useRef<HTMLSpanElement>(null);
  /* Guard: NaN/Infinity → 0 */
  const safeEnd = Number.isFinite(end) ? end : 0;
  const [display, setDisplay] = useState(`${safeEnd}${suffix}`);
  const triggered = useRef(false);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;

    /* Reduced motion → show final value immediately */
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      setDisplay(`${safeEnd}${suffix}`);
      return;
    }

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting && !triggered.current) {
          triggered.current = true;
          observer.unobserve(el);
          animate();
        }
      },
      { threshold: 0.3 },
    );

    function animate() {
      const start = performance.now();

      function tick(now: number) {
        const elapsed = now - start;
        const progress = Math.min(elapsed / duration, 1);
        /* easeOutExpo: fast start, slow finish */
        const eased = progress === 1 ? 1 : 1 - Math.pow(2, -10 * progress);
        const current = Math.round(eased * safeEnd);
        setDisplay(`${current}${suffix}`);
        if (progress < 1) requestAnimationFrame(tick);
      }

      requestAnimationFrame(tick);
    }

    observer.observe(el);
    return () => observer.disconnect();
  }, [safeEnd, suffix, duration]);

  return <span ref={ref}>{display}</span>;
}
