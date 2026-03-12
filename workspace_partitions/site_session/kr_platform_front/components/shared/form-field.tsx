/** FormField — label + input + hint + error wrapper for calculator forms. */

import type { ReactNode } from "react";

interface FormFieldProps {
  label: string;
  htmlFor?: string;
  hint?: string;
  error?: string;
  required?: boolean;
  children: ReactNode;
}

export function FormField({ label, htmlFor, hint, error, required, children }: FormFieldProps) {
  return (
    <div className={`calc-field${error ? " calc-field--error" : ""}`}>
      <label className="calc-field-label" htmlFor={htmlFor}>
        {label}
        {required && <span className="calc-field-required" aria-hidden="true">*</span>}
      </label>
      {children}
      {hint && !error && <p className="calc-field-hint">{hint}</p>}
      {error && (
        <p className="calc-field-error" role="alert">
          {error}
        </p>
      )}
    </div>
  );
}
