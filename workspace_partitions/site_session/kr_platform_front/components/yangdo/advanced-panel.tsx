/** AdvancedPanel — 접이식 고급 옵션 */
"use client";

import { CollapsiblePanel } from "@/components/shared/collapsible-panel";
import { FormField } from "@/components/shared/form-field";
import { NumberInput } from "@/components/shared/number-input";

interface AdvancedPanelProps {
  debtRatio: string;
  liqRatio: string;
  reorgMode: string;
  creditLevel: string;
  adminHistory: string;
  balanceUsageMode: string;
  onChange: (field: string, value: string) => void;
}

export function AdvancedPanel({
  debtRatio, liqRatio, reorgMode, creditLevel, adminHistory, balanceUsageMode, onChange,
}: AdvancedPanelProps) {
  return (
    <CollapsiblePanel title="고급 옵션">
      <div className="calc-form" style={{ paddingTop: 12 }}>
        <div className="calc-row">
          <FormField label="부채비율" hint="높을수록 재무 리스크 증가">
            <NumberInput
              value={debtRatio}
              onChange={(v) => onChange("debtRatio", v)}
              placeholder="예: 150"
              suffix="%"
              min={0}
            />
          </FormField>
          <FormField label="유동비율" hint="100% 이상 권장">
            <NumberInput
              value={liqRatio}
              onChange={(v) => onChange("liqRatio", v)}
              placeholder="예: 120"
              suffix="%"
              min={0}
            />
          </FormField>
        </div>

        <div className="calc-row">
          <FormField label="조직변경 모드">
            <select
              className="calc-number-input-field"
              value={reorgMode}
              onChange={(e) => onChange("reorgMode", e.target.value)}
            >
              <option value="">해당 없음</option>
              <option value="upgrade">업종 추가 (합병)</option>
              <option value="split">업종 분리</option>
            </select>
          </FormField>
          <FormField label="신용등급">
            <select
              className="calc-number-input-field"
              value={creditLevel}
              onChange={(e) => onChange("creditLevel", e.target.value)}
            >
              <option value="">기본</option>
              <option value="A">A (우수)</option>
              <option value="B">B (보통)</option>
              <option value="C">C (저조)</option>
            </select>
          </FormField>
        </div>

        <div className="calc-row">
          <FormField label="행정처분 이력">
            <select
              className="calc-number-input-field"
              value={adminHistory}
              onChange={(e) => onChange("adminHistory", e.target.value)}
            >
              <option value="">없음</option>
              <option value="minor">경미 (과태료 등)</option>
              <option value="major">중대 (영업정지 등)</option>
            </select>
          </FormField>
          <FormField label="출자금 활용 방식">
            <select
              className="calc-number-input-field"
              value={balanceUsageMode}
              onChange={(e) => onChange("balanceUsageMode", e.target.value)}
            >
              <option value="">자동 결정</option>
              <option value="auto">정산 후 반환</option>
              <option value="loan">보증대출 승계</option>
              <option value="credit">여신한도 승계</option>
            </select>
          </FormField>
        </div>
      </div>
    </CollapsiblePanel>
  );
}
