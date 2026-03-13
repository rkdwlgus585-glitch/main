/** FormField — label + input + hint + error wrapper for calculator forms. */

import { useId, type ReactNode } from "react";

interface FormFieldProps {
  label: string;
  htmlFor?: string;
  hint?: string;
  error?: string;
  required?: boolean;
  children: ReactNode | ((descId: string | undefined) => ReactNode);
}

export function FormField({ label, htmlFor, hint, error, required, children }: FormFieldProps) {
  const autoId = useId();
  const hintId = hint && !error ? `${autoId}-hint` : undefined;
  const errorId = error ? `${autoId}-error` : undefined;
  const describedBy = errorId ?? hintId;

  return (
    <div className={`calc-field${error ? " calc-field--error" : ""}`}>
      <label className="calc-field-label" htmlFor={htmlFor}>
        {label}
        {required && <span className="calc-field-required" aria-hidden="true">*</span>}
      </label>
      {typeof children === "function" ? children(describedBy) : children}
      {hint && !error && <p id={hintId} className="calc-field-hint">{hint}</p>}
      {error && (
        <p id={errorId} className="calc-field-error" role="alert">
          {error}
        </p>
      )}
    </div>
  );
}
