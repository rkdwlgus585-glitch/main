"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { platformConfig } from "@/components/platform-config";

const navItems = [
  { href: "/mna-market", label: "실시간 매물" },
  { href: "/permit", label: "건설업등록" },
  { href: "/yangdo", label: "양도가 산정" },
  { href: "/knowledge", label: "건설실무" },
  { href: "/consult", label: "고객센터" },
];

export function SiteHeader() {
  const [open, setOpen] = useState(false);

  /* close drawer on route change (resize) */
  useEffect(() => {
    const onResize = () => { if (window.innerWidth > 960) setOpen(false); };
    window.addEventListener("resize", onResize);
    return () => window.removeEventListener("resize", onResize);
  }, []);

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
        className="nav-toggle"
        aria-label={open ? "메뉴 닫기" : "메뉴 열기"}
        aria-expanded={open}
        onClick={() => setOpen((v) => !v)}
      >
        <span className={`hamburger${open ? " hamburger--open" : ""}`} />
      </button>

      <nav
        className={`site-nav${open ? " site-nav--open" : ""}`}
        aria-label="주요 메뉴"
      >
        {navItems.map((item) => (
          <Link key={item.href} href={item.href} onClick={() => setOpen(false)}>
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
