/** MetricInput — 조건부 입력 필드 (시공능력 OR 실적 + 잔액·자본금) */
"use client";

import { FormField } from "@/components/shared/form-field";
import { NumberInput } from "@/components/shared/number-input";

interface MetricInputProps {
  scaleMode: "specialty" | "sales";
  specialty: string;
  sales3: string;
  sales5: string;
  balanceEok: string;
  capitalEok: string;
  surplusEok: string;
  fieldErrors?: Record<string, string | undefined>;
  onChange: (field: string, value: string) => void;
  onBlur?: (field: string) => void;
}

export function MetricInput({
  scaleMode, specialty, sales3, sales5, balanceEok, capitalEok, surplusEok,
  fieldErrors, onChange, onBlur,
}: MetricInputProps) {
  const err = fieldErrors ?? {};
  const blur = (f: string) => onBlur?.(f);

  return (
    <div className="calc-form">
      {scaleMode === "specialty" ? (
        <FormField label="시공능력 평가액" hint="건설산업지식정보시스템(KISCON) 공시 금액" error={err.specialty} required>
          {({ fieldId, describedBy, hasError }) => (
            <NumberInput
              id={fieldId}
              value={specialty}
              onChange={(v) => onChange("specialty", v)}
              onBlur={() => blur("specialty")}
              placeholder="예: 15"
              suffix="억원"
              min={0}
              aria-describedby={describedBy}
              aria-invalid={hasError}
            />
          )}
        </FormField>
      ) : (
        <div className="calc-row">
          <FormField label="최근 3년 연평균 실적" hint="공시 매출액 기준" error={err.sales3}>
            {({ fieldId, describedBy, hasError }) => (
              <NumberInput
                id={fieldId}
                value={sales3}
                onChange={(v) => onChange("sales3", v)}
                onBlur={() => blur("sales3")}
                placeholder="예: 10"
                suffix="억원"
                min={0}
                aria-describedby={describedBy}
                aria-invalid={hasError}
              />
            )}
          </FormField>
          <FormField label="최근 5년 연평균 실적" error={err.sales5}>
            {({ fieldId, describedBy, hasError }) => (
              <NumberInput
                id={fieldId}
                value={sales5}
                onChange={(v) => onChange("sales5", v)}
                onBlur={() => blur("sales5")}
                placeholder="예: 8"
                suffix="억원"
                min={0}
                aria-describedby={describedBy}
                aria-invalid={hasError}
              />
            )}
          </FormField>
        </div>
      )}

      <div className="calc-row">
        <FormField label="공제조합 출자금 잔액" hint="보증서 발급 가능 잔액">
          {({ fieldId, describedBy }) => (
            <NumberInput
              id={fieldId}
              value={balanceEok}
              onChange={(v) => onChange("balanceEok", v)}
              placeholder="예: 0.5"
              suffix="억원"
              min={0}
              aria-describedby={describedBy}
            />
          )}
        </FormField>
        <FormField label="자본금">
          {({ fieldId }) => (
            <NumberInput
              id={fieldId}
              value={capitalEok}
              onChange={(v) => onChange("capitalEok", v)}
              placeholder="예: 2"
              suffix="억원"
              min={0}
            />
          )}
        </FormField>
      </div>

      <FormField label="잉여금">
        {({ fieldId }) => (
          <NumberInput
            id={fieldId}
            value={surplusEok}
            onChange={(v) => onChange("surplusEok", v)}
            placeholder="예: 1"
            suffix="억원"
          />
        )}
      </FormField>
    </div>
  );
}
