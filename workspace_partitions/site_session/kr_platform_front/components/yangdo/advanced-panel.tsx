/** AdvancedPanel — 접이식 고급 옵션 */
"use client";

import { CollapsiblePanel } from "@/components/shared/collapsible-panel";
import { FormField } from "@/components/shared/form-field";
import { NumberInput } from "@/components/shared/number-input";
import { AlertTriangle } from "lucide-react";

/** 전기/정보통신/소방 업종은 조직변경 모드가 필수 */
const SPECIAL_BALANCE_KEYWORDS = ["전기", "정보통신", "소방"] as const;

export function isSpecialBalanceSector(licenseText: string): boolean {
  return SPECIAL_BALANCE_KEYWORDS.some((kw) => licenseText.includes(kw));
}

interface AdvancedPanelProps {
  debtRatio: string;
  liqRatio: string;
  reorgMode: string;
  creditLevel: string;
  adminHistory: string;
  balanceUsageMode: string;
  licenseText?: string;
  onChange: (field: string, value: string) => void;
}

export function AdvancedPanel({
  debtRatio, liqRatio, reorgMode, creditLevel, adminHistory, balanceUsageMode, licenseText = "", onChange,
}: AdvancedPanelProps) {
  const needsReorg = isSpecialBalanceSector(licenseText);

  return (
    <CollapsiblePanel title="고급 옵션" defaultOpen={needsReorg}>
      <div className="calc-form yangdo-advanced-content">
        {needsReorg && !reorgMode && (
          <div className="calc-info-banner" role="status">
            <AlertTriangle size={16} aria-hidden="true" />
            <span>
              {licenseText} 업종은 <strong>양도양수 방식</strong> 선택이 필요합니다.
            </span>
          </div>
        )}

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
          <FormField
            label={needsReorg ? "양도양수 방식 (필수)" : "양도양수 방식"}
            hint={needsReorg ? "전기·정보통신·소방은 선택 필수" : undefined}
          >
            <select
              className={`calc-number-input-field${needsReorg && !reorgMode ? " calc-field-required" : ""}`}
              value={reorgMode}
              onChange={(e) => onChange("reorgMode", e.target.value)}
              aria-required={needsReorg}
            >
              <option value="">해당 없음</option>
              <option value="포괄">포괄 양도양수</option>
              <option value="분할/합병">분할/합병</option>
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
              <option value="loan_withdrawal">보증대출 인출</option>
              <option value="credit_transfer">잔액 1:1 승계</option>
              <option value="none">별도 정산 없음</option>
            </select>
          </FormField>
        </div>
      </div>
    </CollapsiblePanel>
  );
}
