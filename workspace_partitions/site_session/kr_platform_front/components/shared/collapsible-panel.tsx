/** CollapsiblePanel — expandable section for advanced options. */

"use client";

import { useState, useId, type ReactNode } from "react";
import { ChevronDown } from "lucide-react";

interface CollapsiblePanelProps {
  title: string;
  defaultOpen?: boolean;
  children: ReactNode;
}

export function CollapsiblePanel({ title, defaultOpen = false, children }: CollapsiblePanelProps) {
  const [open, setOpen] = useState(defaultOpen);
  const contentId = useId();

  return (
    <div className={`calc-collapsible${open ? " calc-collapsible--open" : ""}`}>
      <button
        type="button"
        className="calc-collapsible-trigger"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        aria-controls={contentId}
      >
        <span>{title}</span>
        <ChevronDown size={16} className="calc-collapsible-icon" aria-hidden="true" />
      </button>
      <div
        id={contentId}
        className="calc-collapsible-content"
        role="region"
        aria-label={title}
        hidden={!open}
      >
        {open && children}
      </div>
    </div>
  );
}
