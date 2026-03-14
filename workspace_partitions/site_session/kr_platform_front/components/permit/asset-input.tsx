/** AssetInput — 자본금 + 기술인력 + 장비 + 보증금 입력 */
"use client";

import { FormField } from "@/components/shared/form-field";
import { NumberInput } from "@/components/shared/number-input";

interface AssetInputProps {
  capitalEok: string;
  technicians: string;
  equipment: string;
  depositEok: string;
  fieldErrors?: Record<string, string | undefined>;
  onChange: (field: string, value: string) => void;
  onBlur?: (field: string) => void;
}

export function AssetInput({
  capitalEok, technicians, equipment, depositEok,
  fieldErrors, onChange, onBlur,
}: AssetInputProps) {
  const err = fieldErrors ?? {};
  const blur = (f: string) => onBlur?.(f);

  return (
    <div className="calc-form">
      <div className="calc-row">
        <FormField label="자본금 (실질자본)" hint="최근 재무제표 기준" required error={err.capitalEok}>
          {({ fieldId, describedBy, hasError }) => (
            <NumberInput
              id={fieldId}
              value={capitalEok}
              onChange={(v) => onChange("capitalEok", v)}
              onBlur={() => blur("capitalEok")}
              placeholder="예: 1.5"
              suffix="억원"
              min={0}
              aria-describedby={describedBy}
              aria-invalid={hasError}
            />
          )}
        </FormField>
        <FormField label="기술인력" hint="상시 고용 기준" required error={err.technicians}>
          {({ fieldId, describedBy, hasError }) => (
            <NumberInput
              id={fieldId}
              value={technicians}
              onChange={(v) => onChange("technicians", v)}
              onBlur={() => blur("technicians")}
              placeholder="예: 3"
              suffix="명"
              min={0}
              step={1}
              aria-describedby={describedBy}
              aria-invalid={hasError}
            />
          )}
        </FormField>
      </div>
      <div className="calc-row">
        <FormField label="장비 보유" hint="건설기계 등록 기준">
          {({ fieldId, describedBy }) => (
            <NumberInput
              id={fieldId}
              value={equipment}
              onChange={(v) => onChange("equipment", v)}
              placeholder="예: 2"
              suffix="대"
              min={0}
              step={1}
              aria-describedby={describedBy}
            />
          )}
        </FormField>
        <FormField label="보증금">
          {({ fieldId }) => (
            <NumberInput
              id={fieldId}
              value={depositEok}
              onChange={(v) => onChange("depositEok", v)}
              placeholder="예: 0.3"
              suffix="억원"
              min={0}
            />
          )}
        </FormField>
      </div>
    </div>
  );
}
