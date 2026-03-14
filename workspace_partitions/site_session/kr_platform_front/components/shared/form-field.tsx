/** FormField — label + input + hint + error wrapper for calculator forms. */

import { useId, type ReactNode } from "react";

interface ChildContext {
  fieldId: string;
  describedBy: string | undefined;
  /** True when the field has a validation error — use for aria-invalid. */
  hasError: boolean;
}

interface FormFieldProps {
  label: string;
  htmlFor?: string;
  hint?: string;
  error?: string;
  required?: boolean;
  children: ReactNode | ((ctx: ChildContext) => ReactNode);
}

export function FormField({ label, htmlFor, hint, error, required, children }: FormFieldProps) {
  const autoId = useId();
  const fieldId = htmlFor ?? `${autoId}-field`;
  const hintId = hint && !error ? `${autoId}-hint` : undefined;
  const errorId = error ? `${autoId}-error` : undefined;
  const describedBy = errorId ?? hintId;
  const hasError = !!error;

  return (
    <div className={`calc-field${hasError ? " calc-field--error calc-field-error-shake" : ""}`}>
      <label className="calc-field-label" htmlFor={fieldId}>
        {label}
        {required && <span className="calc-field-required" aria-hidden="true">*</span>}
      </label>
      {typeof children === "function" ? children({ fieldId, describedBy, hasError }) : children}
      {hint && !error && <p id={hintId} className="calc-field-hint">{hint}</p>}
      {hasError && (
        <p id={errorId} className="calc-field-error" role="alert">
          {error}
        </p>
      )}
    </div>
  );
}
