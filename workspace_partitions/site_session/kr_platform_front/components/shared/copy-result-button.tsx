/** CopyResultButton — copies text summary to clipboard with feedback. */
"use client";

import { useState, useCallback } from "react";
import { Copy, Check } from "lucide-react";

interface CopyResultButtonProps {
  getText: () => string;
  label?: string;
}

export function CopyResultButton({ getText, label = "결과 복사" }: CopyResultButtonProps) {
  const [copied, setCopied] = useState(false);

  const handleCopy = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(getText());
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Fallback for older browsers / insecure contexts
      const ta = document.createElement("textarea");
      ta.value = getText();
      ta.style.position = "fixed";
      ta.style.left = "-9999px";
      document.body.appendChild(ta);
      ta.select();
      document.execCommand("copy");
      document.body.removeChild(ta);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  }, [getText]);

  return (
    <button
      type="button"
      className="calc-copy-btn"
      onClick={handleCopy}
      aria-label={copied ? "복사 완료" : label}
    >
      {copied ? (
        <><Check size={14} aria-hidden="true" />복사 완료</>
      ) : (
        <><Copy size={14} aria-hidden="true" />{label}</>
      )}
    </button>
  );
}
