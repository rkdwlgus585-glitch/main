"use client";

import { useState, useEffect, useRef } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { platformConfig } from "@/components/platform-config";

const navItems = [
  { href: "/yangdo", label: "AI 양도가 산정" },
  { href: "/permit", label: "AI 인허가 검토" },
  { href: "/pricing", label: "요금제" },
  { href: "/partners", label: "시스템 도입" },
  { href: "/consult", label: "고객센터" },
];

export function SiteHeader() {
  const [open, setOpen] = useState(false);
  const navRef = useRef<HTMLElement>(null);
  const toggleRef = useRef<HTMLButtonElement>(null);
  const pathname = usePathname();

  /* Close drawer on desktop resize */
  useEffect(() => {
    const onResize = () => { if (window.innerWidth > 960) setOpen(false); };
    window.addEventListener("resize", onResize);
    return () => window.removeEventListener("resize", onResize);
  }, []);

  /* Escape key closes drawer + return focus to toggle (WCAG 2.1 AA) */
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setOpen(false);
        toggleRef.current?.focus();
      }
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open]);

  /* Focus first nav link when drawer opens */
  useEffect(() => {
    if (open) {
      const firstLink = navRef.current?.querySelector<HTMLElement>("a");
      firstLink?.focus();
    }
  }, [open]);

  return (
    <header className="site-header">
      <Link href="/" className="site-brand" onClick={() => setOpen(false)}>
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src="/media/logo.png"
          alt={platformConfig.brandName}
          className="site-brand-logo"
          width={44}
          height={44}
        />
        <span className="site-brand-copy">
          <strong>{platformConfig.brandName}</strong>
          <small>{platformConfig.brandTagline}</small>
        </span>
      </Link>

      <button
        ref={toggleRef}
        className="nav-toggle"
        aria-label={open ? "메뉴 닫기" : "메뉴 열기"}
        aria-expanded={open}
        aria-controls="main-nav"
        onClick={() => setOpen((v) => !v)}
      >
        <span className={`hamburger${open ? " hamburger--open" : ""}`} />
      </button>

      <nav
        ref={navRef}
        id="main-nav"
        className={`site-nav${open ? " site-nav--open" : ""}`}
        aria-label="주요 메뉴"
      >
        {navItems.map((item) => (
          <Link
            key={item.href}
            href={item.href}
            onClick={() => setOpen(false)}
            {...(pathname === item.href || pathname.startsWith(item.href + "/")
              ? { "aria-current": "page" as const }
              : {})}
          >
            {item.label}
          </Link>
        ))}
        <a href={`tel:${platformConfig.contactPhone}`} className="nav-phone">
          {platformConfig.contactPhone}
        </a>
      </nav>
    </header>
  );
}
