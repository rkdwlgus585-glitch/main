/** AssetInput — 자본금 + 기술인력 + 장비 + 보증금 입력 */
"use client";

import { FormField } from "@/components/shared/form-field";
import { NumberInput } from "@/components/shared/number-input";

interface AssetInputProps {
  capitalEok: string;
  technicians: string;
  equipment: string;
  depositEok: string;
  onChange: (field: string, value: string) => void;
}

export function AssetInput({ capitalEok, technicians, equipment, depositEok, onChange }: AssetInputProps) {
  return (
    <div className="calc-form">
      <div className="calc-row">
        <FormField label="자본금 (실질자본)" hint="최근 재무제표 기준" required>
          <NumberInput
            value={capitalEok}
            onChange={(v) => onChange("capitalEok", v)}
            placeholder="0"
            suffix="억원"
            min={0}
          />
        </FormField>
        <FormField label="기술인력" hint="상시 고용 기준" required>
          <NumberInput
            value={technicians}
            onChange={(v) => onChange("technicians", v)}
            placeholder="0"
            suffix="명"
            min={0}
            step={1}
          />
        </FormField>
      </div>
      <div className="calc-row">
        <FormField label="장비 보유" hint="건설기계 등록 기준">
          <NumberInput
            value={equipment}
            onChange={(v) => onChange("equipment", v)}
            placeholder="0"
            suffix="대"
            min={0}
            step={1}
          />
        </FormField>
        <FormField label="보증금">
          <NumberInput
            value={depositEok}
            onChange={(v) => onChange("depositEok", v)}
            placeholder="0"
            suffix="억원"
            min={0}
          />
        </FormField>
      </div>
    </div>
  );
}
