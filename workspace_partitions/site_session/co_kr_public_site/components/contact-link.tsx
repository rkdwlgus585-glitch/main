"use client";

import type { ReactNode } from "react";

type ContactLinkProps = {
  href: string;
  eventName: string;
  eventLabel: string;
  className?: string;
  children: ReactNode;
  newTab?: boolean;
};

declare global {
  interface Window {
    gtag?: (...args: unknown[]) => void;
  }
}

export function trackContactEvent(eventName: string, eventLabel: string) {
  if (typeof window === "undefined") {
    return;
  }

  window.gtag?.("event", eventName, {
    event_category: "contact",
    event_label: eventLabel,
  });
}

export function ContactLink({
  href,
  eventName,
  eventLabel,
  className,
  children,
  newTab = false,
}: ContactLinkProps) {
  return (
    <a
      href={href}
      className={className}
      target={newTab ? "_blank" : undefined}
      rel={newTab ? "noreferrer" : undefined}
      onClick={() => trackContactEvent(eventName, eventLabel)}
    >
      {children}
    </a>
  );
}
