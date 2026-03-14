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
    const text = getText();
    let ok = false;
    try {
      await navigator.clipboard.writeText(text);
      ok = true;
    } catch {
      // Fallback for older browsers / insecure contexts
      const ta = document.createElement("textarea");
      ta.value = text;
      ta.style.position = "fixed";
      ta.style.left = "-9999px";
      document.body.appendChild(ta);
      ta.select();
      try { ok = document.execCommand("copy"); } catch { /* ignore */ }
      document.body.removeChild(ta);
    }
    if (ok) {
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
