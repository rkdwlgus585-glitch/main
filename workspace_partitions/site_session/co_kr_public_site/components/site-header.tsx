"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { ContactLink } from "@/components/contact-link";
import { primaryMenu, siteConfig } from "@/components/site-config";

export function SiteHeader() {
  const [open, setOpen] = useState(false);
  const toggleRef = useRef<HTMLButtonElement>(null);
  const navRef = useRef<HTMLElement>(null);

  useEffect(() => {
    const onResize = () => {
      if (window.innerWidth > 960) {
        setOpen(false);
      }
    };

    window.addEventListener("resize", onResize);
    return () => window.removeEventListener("resize", onResize);
  }, []);

  useEffect(() => {
    if (!open) {
      document.body.style.overflow = "";
      return;
    }

    const focusable = [
      toggleRef.current,
      ...Array.from(navRef.current?.querySelectorAll<HTMLElement>('a[href], button:not([disabled]), [tabindex]:not([tabindex="-1"])') ?? []),
    ].filter((element): element is HTMLElement => Boolean(element));

    const firstFocusable = focusable[0];
    const lastFocusable = focusable[focusable.length - 1];
    document.body.style.overflow = "hidden";
    navRef.current?.querySelector<HTMLElement>('a[href], button:not([disabled]), [tabindex]:not([tabindex="-1"])')?.focus();

    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setOpen(false);
        toggleRef.current?.focus();
        return;
      }

      if (event.key !== "Tab" || !firstFocusable || !lastFocusable) {
        return;
      }

      if (event.shiftKey && document.activeElement === firstFocusable) {
        event.preventDefault();
        lastFocusable.focus();
      } else if (!event.shiftKey && document.activeElement === lastFocusable) {
        event.preventDefault();
        firstFocusable.focus();
      }
    };

    document.addEventListener("keydown", onKeyDown);

    return () => {
      document.body.style.overflow = "";
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [open]);

  return (
    <header className="site-header">
      <Link href="/" className="site-brand" onClick={() => setOpen(false)}>
        <span className="site-brand-mark">CB</span>
        <span className="site-brand-copy">
          <strong>{siteConfig.brandName}</strong>
          <small>{siteConfig.brandTagline}</small>
        </span>
      </Link>

      <button
        type="button"
        ref={toggleRef}
        className="nav-toggle"
        aria-label={open ? "메뉴 닫기" : "메뉴 열기"}
        aria-expanded={open}
        aria-controls="site-primary-nav"
        onClick={() => setOpen((value) => !value)}
      >
        <span className={`hamburger${open ? " hamburger--open" : ""}`} />
      </button>

      <nav
        id="site-primary-nav"
        ref={navRef}
        className={`site-nav${open ? " site-nav--open" : ""}`}
        aria-label="주요 메뉴"
      >
        {primaryMenu.map((item) => (
          <Link key={item.href} href={item.href} onClick={() => setOpen(false)}>
            {item.label}
          </Link>
        ))}
        <ContactLink
          href={`tel:${siteConfig.phone}`}
          className="nav-phone"
          eventName="click_phone"
          eventLabel="header_phone"
        >
          {siteConfig.phone}
        </ContactLink>
      </nav>
    </header>
  );
}
