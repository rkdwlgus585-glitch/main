/** StepIndicator — horizontal step progress for multi-stage form flows.
 *  Shows completed/current/upcoming steps with labels.
 */

interface Step {
  label: string;
  /** If true, this step has a complete input value */
  complete: boolean;
}

interface StepIndicatorProps {
  steps: Step[];
  /** Which step is actively being edited (0-indexed) */
  currentStep?: number;
}

export function StepIndicator({ steps, currentStep }: StepIndicatorProps) {
  return (
    <nav className="calc-steps" aria-label="입력 진행 상태">
      <ol className="calc-steps-list">
        {steps.map((step, i) => {
          const state = step.complete
            ? "done"
            : currentStep === i
              ? "active"
              : "upcoming";
          return (
            <li
              key={step.label}
              className={`calc-step calc-step--${state}`}
              aria-current={state === "active" ? "step" : undefined}
            >
              <span className="calc-step-dot" aria-hidden="true">
                {state === "done" ? "✓" : i + 1}
              </span>
              <span className="calc-step-label">{step.label}</span>
            </li>
          );
        })}
      </ol>
    </nav>
  );
}
