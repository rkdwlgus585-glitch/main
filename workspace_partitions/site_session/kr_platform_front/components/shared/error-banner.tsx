/** ErrorBanner — contextual error message with optional retry action. */
"use client";

import { forwardRef } from "react";
import { AlertCircle, RefreshCw } from "lucide-react";

interface ErrorBannerProps {
  message: string;
  /** If provided, shows a "다시 시도" button that calls this handler. */
  onRetry?: () => void;
}

/** Returns true for validation errors (user must fix input, not retry). */
function isValidationError(msg: string): boolean {
  return /선택|입력/.test(msg);
}

export const ErrorBanner = forwardRef<HTMLDivElement, ErrorBannerProps>(
  function ErrorBanner({ message, onRetry }, ref) {
    const showRetry = onRetry && !isValidationError(message);
    return (
      <div ref={ref} className="calc-error-banner" role="alert" tabIndex={-1}>
        <AlertCircle size={16} className="calc-error-banner-icon" aria-hidden="true" />
        <span className="calc-error-banner-text">{message}</span>
        {showRetry && (
          <button type="button" className="calc-error-retry" onClick={onRetry}>
            <RefreshCw size={14} aria-hidden="true" />
            다시 시도
          </button>
        )}
      </div>
    );
  },
);
