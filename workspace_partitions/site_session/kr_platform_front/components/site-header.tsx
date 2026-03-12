"use client";

import { useState, useEffect, useRef } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { platformConfig } from "@/components/platform-config";

const navItems = [
  { href: "/about", label: "회사소개" },
  { href: "/mna-market", label: "실시간 매물" },
  { href: "/permit", label: "건설업등록" },
  { href: "/yangdo", label: "양도가 산정" },
  { href: "/knowledge", label: "건설실무" },
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
        <span className="site-brand-mark">SM</span>
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
