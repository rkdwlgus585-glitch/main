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
  onChange: (field: string, value: string) => void;
}

export function MetricInput({
  scaleMode, specialty, sales3, sales5, balanceEok, capitalEok, surplusEok, onChange,
}: MetricInputProps) {
  return (
    <div className="calc-form">
      {scaleMode === "specialty" ? (
        <FormField label="시공능력 평가액" hint="건설산업지식정보시스템(KISCON) 공시 금액">
          <NumberInput
            value={specialty}
            onChange={(v) => onChange("specialty", v)}
            placeholder="0"
            suffix="억원"
            min={0}
          />
        </FormField>
      ) : (
        <div className="calc-row">
          <FormField label="최근 3년 연평균 실적" hint="공시 매출액 기준">
            <NumberInput
              value={sales3}
              onChange={(v) => onChange("sales3", v)}
              placeholder="0"
              suffix="억원"
              min={0}
            />
          </FormField>
          <FormField label="최근 5년 연평균 실적">
            <NumberInput
              value={sales5}
              onChange={(v) => onChange("sales5", v)}
              placeholder="0"
              suffix="억원"
              min={0}
            />
          </FormField>
        </div>
      )}

      <div className="calc-row">
        <FormField label="공제조합 출자금 잔액" hint="보증서 발급 가능 잔액">
          <NumberInput
            value={balanceEok}
            onChange={(v) => onChange("balanceEok", v)}
            placeholder="0"
            suffix="억원"
            min={0}
          />
        </FormField>
        <FormField label="자본금">
          <NumberInput
            value={capitalEok}
            onChange={(v) => onChange("capitalEok", v)}
            placeholder="0"
            suffix="억원"
            min={0}
          />
        </FormField>
      </div>

      <FormField label="잉여금">
        <NumberInput
          value={surplusEok}
          onChange={(v) => onChange("surplusEok", v)}
          placeholder="0"
          suffix="억원"
        />
      </FormField>
    </div>
  );
}
