/** CollapsiblePanel — expandable section for advanced options. */

"use client";

import { useState, useId, useImperativeHandle, forwardRef, type ReactNode, type Ref } from "react";
import { ChevronDown } from "lucide-react";

export interface CollapsiblePanelHandle {
  open: () => void;
}

interface CollapsiblePanelProps {
  title: string;
  defaultOpen?: boolean;
  children: ReactNode;
}

export const CollapsiblePanel = forwardRef(function CollapsiblePanel(
  { title, defaultOpen = false, children }: CollapsiblePanelProps,
  ref: Ref<CollapsiblePanelHandle>,
) {
  const [open, setOpen] = useState(defaultOpen);
  const contentId = useId();

  useImperativeHandle(ref, () => ({
    open: () => setOpen(true),
  }), []);

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
        {children}
      </div>
    </div>
  );
});
