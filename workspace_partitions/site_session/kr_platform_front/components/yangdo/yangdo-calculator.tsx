/** YangdoCalculator — AI 양도가 산정 계산기 루트 컴포넌트 */
"use client";

import { useReducer, useEffect, useRef, useCallback } from "react";
import type { YangdoMetaResponse, YangdoEstimateRequest, YangdoEstimateResponse, LicenseProfile } from "@/lib/yangdo-types";
import { fetchYangdoMeta, fetchYangdoEstimate } from "@/lib/api-client";
import { LicenseInput } from "./license-input";
import { ScaleModeSelector } from "./scale-mode-selector";
import { MetricInput } from "./metric-input";
import { AdvancedPanel, isSpecialBalanceSector } from "./advanced-panel";
import { ScrollAnimate } from "@/components/scroll-animate";
import { ResultPanel } from "./result-panel";
import { SettlementPanel } from "./settlement-panel";
import { RecommendedListings } from "./recommended-listings";
import { CopyResultButton } from "@/components/shared/copy-result-button";
import { Calculator, Loader2 } from "lucide-react";

type Phase = "idle" | "ready" | "submitting" | "result" | "error";

interface CalcState {
  phase: Phase;
  meta: YangdoMetaResponse | null;
  metaError: string | null;
  // Form
  licenseText: string;
  selectedToken: string;
  scaleMode: "specialty" | "sales";
  specialty: string;
  sales3: string;
  sales5: string;
  balanceEok: string;
  capitalEok: string;
  surplusEok: string;
  debtRatio: string;
  liqRatio: string;
  reorgMode: string;
  creditLevel: string;
  adminHistory: string;
  balanceUsageMode: string;
  // Result
  result: YangdoEstimateResponse | null;
  errorMsg: string | null;
}

type Action =
  | { type: "META_LOADED"; payload: YangdoMetaResponse }
  | { type: "META_ERROR"; payload: string }
  | { type: "SET_LICENSE"; payload: { text: string; token: string; profile?: LicenseProfile } }
  | { type: "SET_SCALE_MODE"; payload: "specialty" | "sales" }
  | { type: "SET_FIELD"; field: string; value: string }
  | { type: "SUBMIT" }
  | { type: "RESULT"; payload: YangdoEstimateResponse }
  | { type: "ERROR"; payload: string }
  | { type: "RESET" }
  | { type: "RETRY_META" };

const initialState: CalcState = {
  phase: "idle",
  meta: null,
  metaError: null,
  licenseText: "",
  selectedToken: "",
  scaleMode: "specialty",
  specialty: "",
  sales3: "",
  sales5: "",
  balanceEok: "",
  capitalEok: "",
  surplusEok: "",
  debtRatio: "",
  liqRatio: "",
  reorgMode: "",
  creditLevel: "",
  adminHistory: "",
  balanceUsageMode: "",
  result: null,
  errorMsg: null,
};

function reducer(state: CalcState, action: Action): CalcState {
  switch (action.type) {
    case "META_LOADED":
      return { ...state, phase: "ready", meta: action.payload, metaError: null };
    case "META_ERROR":
      return { ...state, phase: "error", metaError: action.payload };
    case "SET_LICENSE": {
      const p = action.payload.profile;
      return {
        ...state,
        licenseText: action.payload.text,
        selectedToken: action.payload.token,
        capitalEok: p ? String(p.prefill_capital_eok) : state.capitalEok,
        surplusEok: p ? String(p.prefill_surplus_eok) : state.surplusEok,
        balanceEok: p ? String(p.default_balance_eok) : state.balanceEok,
        specialty: p?.typical_specialty_eok != null ? String(p.typical_specialty_eok) : "",
        sales3: p?.typical_sales3_eok != null ? String(p.typical_sales3_eok) : "",
        sales5: p?.typical_sales5_eok != null ? String(p.typical_sales5_eok) : "",
      };
    }
    case "SET_SCALE_MODE":
      return { ...state, scaleMode: action.payload };
    case "SET_FIELD":
      return { ...state, [action.field]: action.value };
    case "SUBMIT":
      return { ...state, phase: "submitting", errorMsg: null };
    case "RESULT":
      return { ...state, phase: "result", result: action.payload };
    case "ERROR":
      return { ...state, phase: "ready", errorMsg: action.payload, result: null };
    case "RESET":
      return { ...initialState, phase: "ready", meta: state.meta };
    case "RETRY_META":
      return { ...state, phase: "idle", metaError: null };
    default:
      return state;
  }
}

export function YangdoCalculator() {
  const [state, dispatch] = useReducer(reducer, initialState);
  const resultsRef = useRef<HTMLDivElement>(null);

  /* ── Load meta on mount + retry ── */
  const loadMeta = useCallback(() => {
    dispatch({ type: "RETRY_META" });
    fetchYangdoMeta()
      .then((data) => dispatch({ type: "META_LOADED", payload: data }))
      .catch(() => dispatch({ type: "META_ERROR", payload: "업종 데이터를 불러올 수 없습니다." }));
  }, []);

  useEffect(() => { loadMeta(); }, [loadMeta]);

  /* ── Auto-scroll to results ── */
  useEffect(() => {
    if (state.phase === "result" && resultsRef.current) {
      resultsRef.current.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }, [state.phase]);

  /* ── Submit handler ── */
  const handleSubmit = async () => {
    if (state.phase === "submitting") return;
    if (!state.licenseText.trim()) {
      dispatch({ type: "ERROR", payload: "업종을 선택해 주세요." });
      return;
    }
    if (state.scaleMode === "specialty" && !state.specialty) {
      dispatch({ type: "ERROR", payload: "시공능력 평가액을 입력해 주세요." });
      return;
    }
    if (state.scaleMode === "sales" && !state.sales3 && !state.sales5) {
      dispatch({ type: "ERROR", payload: "실적(3년 또는 5년)을 하나 이상 입력해 주세요." });
      return;
    }
    if (isSpecialBalanceSector(state.licenseText) && !state.reorgMode) {
      dispatch({ type: "ERROR", payload: "전기·정보통신·소방 업종은 고급 옵션에서 양도양수 방식(포괄/분할)을 선택해 주세요." });
      return;
    }
    dispatch({ type: "SUBMIT" });
    try {
      const body: YangdoEstimateRequest = {
        license_text: state.licenseText,
        scale_mode: state.scaleMode,
        ...(state.scaleMode === "specialty" && state.specialty ? { specialty: Number(state.specialty) } : {}),
        ...(state.scaleMode === "sales" && state.sales3 ? { sales3_eok: Number(state.sales3) } : {}),
        ...(state.scaleMode === "sales" && state.sales5 ? { sales5_eok: Number(state.sales5) } : {}),
        ...(state.balanceEok ? { balance_eok: Number(state.balanceEok) } : {}),
        ...(state.capitalEok ? { capital_eok: Number(state.capitalEok) } : {}),
        ...(state.surplusEok ? { surplus_eok: Number(state.surplusEok) } : {}),
        ...(state.debtRatio ? { debt_ratio: Number(state.debtRatio) } : {}),
        ...(state.liqRatio ? { liq_ratio: Number(state.liqRatio) } : {}),
        ...(state.reorgMode ? { reorg_mode: state.reorgMode } : {}),
        ...(state.creditLevel ? { credit_level: state.creditLevel } : {}),
        ...(state.adminHistory ? { admin_history: state.adminHistory } : {}),
        ...(state.balanceUsageMode ? { balance_usage_mode: state.balanceUsageMode } : {}),
      };

      const res = await fetchYangdoEstimate(body);
      if (!res.ok) {
        dispatch({ type: "ERROR", payload: res.error ?? "산정에 실패했습니다." });
      } else {
        dispatch({ type: "RESULT", payload: res });
      }
    } catch (err) {
      const code = err instanceof Error && "code" in err ? (err as { code: string }).code : "";
      const msg = code === "timeout"
        ? "요청 시간이 초과되었습니다. 잠시 후 다시 시도해 주세요."
        : code === "mapping_required"
          ? "해당 업종은 자동 산정이 어렵습니다. 전문가 상담을 이용해 주세요."
          : "서버 연결에 실패했습니다. 잠시 후 다시 시도해 주세요.";
      dispatch({ type: "ERROR", payload: msg });
    }
  };

  /* ── Loading skeleton ── */
  if (state.phase === "idle") {
    return (
      <div className="yangdo-calc" aria-busy="true" aria-label="양도가 계산기 로딩 중">
        <div className="yangdo-loading">
          <div className="calc-skeleton" style={{ height: 40, width: "60%" }} />
          <div className="calc-skeleton" style={{ height: 120 }} />
          <div className="calc-skeleton" style={{ height: 48, width: "40%" }} />
        </div>
      </div>
    );
  }

  /* ── Meta error ── */
  if (state.metaError) {
    return (
      <div className="yangdo-calc">
        <div className="calc-error-banner" role="alert">
          {state.metaError}
          <button type="button" className="calc-retry-btn" onClick={loadMeta}>다시 시도</button>
        </div>
      </div>
    );
  }

  const profiles = state.meta?.license_profiles;

  return (
    <div className="yangdo-calc">
      <form
        className="calc-form"
        onSubmit={(e) => { e.preventDefault(); handleSubmit(); }}
        aria-label="AI 양도가 산정"
      >
        {/* 1. 업종 선택 */}
        <LicenseInput
          profiles={profiles ?? { profiles: {}, quick_tokens: [] }}
          selectedToken={state.selectedToken}
          licenseText={state.licenseText}
          onSelect={(text, token, profile) =>
            dispatch({ type: "SET_LICENSE", payload: { text, token, profile } })
          }
        />

        {/* 2. 기준 모드 */}
        <ScaleModeSelector
          mode={state.scaleMode}
          onChange={(m) => dispatch({ type: "SET_SCALE_MODE", payload: m })}
        />

        {/* 3. 수치 입력 */}
        <MetricInput
          scaleMode={state.scaleMode}
          specialty={state.specialty}
          sales3={state.sales3}
          sales5={state.sales5}
          balanceEok={state.balanceEok}
          capitalEok={state.capitalEok}
          surplusEok={state.surplusEok}
          onChange={(field, value) => dispatch({ type: "SET_FIELD", field, value })}
        />

        {/* 4. 고급 옵션 */}
        <AdvancedPanel
          debtRatio={state.debtRatio}
          liqRatio={state.liqRatio}
          reorgMode={state.reorgMode}
          creditLevel={state.creditLevel}
          adminHistory={state.adminHistory}
          balanceUsageMode={state.balanceUsageMode}
          licenseText={state.licenseText}
          onChange={(field, value) => dispatch({ type: "SET_FIELD", field, value })}
        />

        {/* Error banner */}
        {state.errorMsg && (
          <div className="calc-error-banner" role="alert">{state.errorMsg}</div>
        )}

        {/* Submit */}
        <button
          type="submit"
          className="calc-submit"
          disabled={state.phase === "submitting"}
        >
          {state.phase === "submitting" ? (
            <><Loader2 size={18} className="yangdo-spinner" aria-hidden="true" />AI가 분석 중입니다...</>
          ) : (
            <><Calculator size={18} aria-hidden="true" />양도가 산정하기</>
          )}
        </button>
      </form>

      {/* 5. 결과 */}
      {state.phase === "result" && state.result && (
        <div ref={resultsRef} className="yangdo-results" aria-live="polite">
          <ScrollAnimate>
            <ResultPanel result={state.result} />
          </ScrollAnimate>

          {state.result.settlement_scenarios && state.result.settlement_scenarios.length > 0 && (
            <ScrollAnimate delay={150}>
              <SettlementPanel scenarios={state.result.settlement_scenarios} />
            </ScrollAnimate>
          )}

          {state.result.recommended_listings && state.result.recommended_listings.length > 0 && (
            <ScrollAnimate delay={300}>
              <RecommendedListings listings={state.result.recommended_listings} />
            </ScrollAnimate>
          )}

          {state.result.risk_notes && state.result.risk_notes.length > 0 && (
            <div className="yangdo-risk-notes">
              {state.result.risk_notes.map((note, i) => (
                <p key={note.slice(0, 60)} className="yangdo-risk-note">{note}</p>
              ))}
            </div>
          )}

          <div className="yangdo-result-actions">
            <a
              href={`/consult?license=${encodeURIComponent(state.licenseText)}&estimate=${state.result?.public_center_eok ?? state.result?.estimate_center_eok ?? ""}`}
              className="calc-submit"
            >전문가 상담 연결</a>
            <CopyResultButton getText={() => {
              const r = state.result;
              if (!r) return "";
              const c = r.public_center_eok ?? r.estimate_center_eok;
              const lo = r.public_low_eok ?? r.estimate_low_eok;
              const hi = r.public_high_eok ?? r.estimate_high_eok;
              let txt = `[AI 양도가 산정 결과]\n업종: ${state.licenseText}\n`;
              if (c) txt += `추정 양도가: ${c}억원 (${lo ?? "?"}~${hi ?? "?"}억원)\n`;
              if (r.confidence_percent) txt += `신뢰도: ${r.confidence_percent}%\n`;
              if (r.risk_notes?.length) txt += `\n주의사항:\n${r.risk_notes.map(n => `- ${n}`).join("\n")}\n`;
              txt += `\n서울건설정보 (seoulmna.kr)`;
              return txt;
            }} />
            <button
              type="button"
              className="yangdo-reset-btn"
              onClick={() => dispatch({ type: "RESET" })}
            >
              다시 산정하기
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
