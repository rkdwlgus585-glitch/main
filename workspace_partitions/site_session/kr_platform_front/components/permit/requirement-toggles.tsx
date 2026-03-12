/** RequirementToggles — 불린 요건 체크박스 (사무실/시설/자격증/보증) */
"use client";

import { useId } from "react";
import { Building2, Warehouse, Award, Shield } from "lucide-react";

interface RequirementTogglesProps {
  office: boolean;
  facility: boolean;
  qualification: boolean;
  insurance: boolean;
  onChange: (field: string, value: boolean) => void;
}

const TOGGLES = [
  { field: "office", label: "사무실 보유", icon: Building2, hint: "건설업 영업 전용 사무실" },
  { field: "facility", label: "시설 보유", icon: Warehouse, hint: "업종별 필수 시설 및 장비" },
  { field: "qualification", label: "자격증 보유", icon: Award, hint: "업종별 필수 자격 또는 면허" },
  { field: "insurance", label: "보증/보험 가입", icon: Shield, hint: "건설공제조합 보증 등" },
] as const;

export function RequirementToggles({ office, facility, qualification, insurance, onChange }: RequirementTogglesProps) {
  const groupId = useId();
  const values: Record<string, boolean> = { office, facility, qualification, insurance };

  return (
    <fieldset className="permit-toggles" aria-label="보유 요건 확인">
      <legend className="calc-field-label">보유 요건</legend>
      <div className="permit-toggle-grid">
        {TOGGLES.map((t) => {
          const Icon = t.icon;
          const checked = values[t.field] ?? false;
          return (
            <label
              key={t.field}
              className={`permit-toggle${checked ? " permit-toggle--checked" : ""}`}
              htmlFor={`${groupId}-${t.field}`}
            >
              <input
                id={`${groupId}-${t.field}`}
                type="checkbox"
                className="permit-toggle-input"
                checked={checked}
                onChange={(e) => onChange(t.field, e.target.checked)}
              />
              <Icon size={18} aria-hidden="true" />
              <div className="permit-toggle-text">
                <span className="permit-toggle-label">{t.label}</span>
                <span className="permit-toggle-hint">{t.hint}</span>
              </div>
            </label>
          );
        })}
      </div>
    </fieldset>
  );
}
