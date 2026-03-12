"use client";

import { useEffect, useRef, type ReactNode } from "react";

type ScrollAnimateProps = {
  children: ReactNode;
  className?: string;
  /** Delay in ms before the animation starts (stagger effect) */
  delay?: number;
};

/**
 * Wraps children in an element that fades + slides up when scrolled into view.
 * Uses IntersectionObserver for performance — no scroll event listeners.
 * Respects prefers-reduced-motion by showing content immediately.
 */
export function ScrollAnimate({
  children,
  className = "",
  delay = 0,
}: ScrollAnimateProps) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;

    /* Respect reduced motion preference */
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      el.classList.add("sa-visible");
      return;
    }

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          if (delay > 0) {
            setTimeout(() => el.classList.add("sa-visible"), delay);
          } else {
            el.classList.add("sa-visible");
          }
          observer.unobserve(el);
        }
      },
      { threshold: 0.12, rootMargin: "0px 0px -40px 0px" },
    );

    observer.observe(el);
    return () => observer.disconnect();
  }, [delay]);

  return (
    <div ref={ref} className={`sa-hidden ${className}`}>
      {children}
    </div>
  );
}
