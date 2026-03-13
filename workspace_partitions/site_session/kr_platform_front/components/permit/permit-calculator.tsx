/** PermitCalculator — AI 인허가 사전검토 계산기 루트 컴포넌트 */
"use client";

import { useReducer, useEffect } from "react";
import type { PermitMetaResponse, PermitPrecheckResponse, PermitIndustry } from "@/lib/permit-types";
import { fetchPermitMeta, fetchPermitPrecheck } from "@/lib/api-client";
import { IndustrySelector } from "./industry-selector";
import { AssetInput } from "./asset-input";
import { RequirementToggles } from "./requirement-toggles";
import { DiagnosisResult } from "./diagnosis-result";
import { ScrollAnimate } from "@/components/scroll-animate";
import { CriteriaList } from "./criteria-list";
import { NextActions } from "./next-actions";
import { ShieldCheck, Loader2 } from "lucide-react";

type Phase = "idle" | "ready" | "submitting" | "result" | "error";

interface CalcState {
  phase: Phase;
  meta: PermitMetaResponse | null;
  metaError: string | null;
  // Form
  selectedIndustry: PermitIndustry | null;
  capitalEok: string;
  technicians: string;
  equipment: string;
  office: boolean;
  facility: boolean;
  qualification: boolean;
  insurance: boolean;
  depositEok: string;
  // Result
  result: PermitPrecheckResponse | null;
  errorMsg: string | null;
}

type Action =
  | { type: "META_LOADED"; payload: PermitMetaResponse }
  | { type: "META_ERROR"; payload: string }
  | { type: "SET_INDUSTRY"; payload: PermitIndustry | null }
  | { type: "SET_FIELD"; field: string; value: string | boolean }
  | { type: "SUBMIT" }
  | { type: "RESULT"; payload: PermitPrecheckResponse }
  | { type: "ERROR"; payload: string }
  | { type: "RESET" };

const initialState: CalcState = {
  phase: "idle",
  meta: null,
  metaError: null,
  selectedIndustry: null,
  capitalEok: "",
  technicians: "",
  equipment: "",
  office: false,
  facility: false,
  qualification: false,
  insurance: false,
  depositEok: "",
  result: null,
  errorMsg: null,
};

function reducer(state: CalcState, action: Action): CalcState {
  switch (action.type) {
    case "META_LOADED":
      return { ...state, phase: "ready", meta: action.payload, metaError: null };
    case "META_ERROR":
      return { ...state, phase: "error", metaError: action.payload };
    case "SET_INDUSTRY":
      return { ...state, selectedIndustry: action.payload };
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
    default:
      return state;
  }
}

export function PermitCalculator() {
  const [state, dispatch] = useReducer(reducer, initialState);

  useEffect(() => {
    let cancelled = false;
    fetchPermitMeta()
      .then((data) => { if (!cancelled) dispatch({ type: "META_LOADED", payload: data }); })
      .catch(() => { if (!cancelled) dispatch({ type: "META_ERROR", payload: "업종 데이터를 불러올 수 없습니다." }); });
    return () => { cancelled = true; };
  }, []);

  const handleSubmit = async () => {
    if (!state.selectedIndustry) {
      dispatch({ type: "ERROR", payload: "업종을 선택해 주세요." });
      return;
    }
    dispatch({ type: "SUBMIT" });
    try {
      const res = await fetchPermitPrecheck({
        service_code: state.selectedIndustry.service_code,
        inputs: {
          capital_eok: state.capitalEok ? Number(state.capitalEok) : undefined,
          technicians: state.technicians ? Number(state.technicians) : undefined,
          equipment: state.equipment ? Number(state.equipment) : undefined,
          office: state.office,
          facility: state.facility,
          qualification: state.qualification,
          insurance: state.insurance,
          deposit_eok: state.depositEok ? Number(state.depositEok) : undefined,
        },
      });
      if (!res.ok) {
        dispatch({ type: "ERROR", payload: res.error ?? "검토에 실패했습니다." });
      } else {
        dispatch({ type: "RESULT", payload: res });
      }
    } catch {
      dispatch({ type: "ERROR", payload: "서버 연결에 실패했습니다. 잠시 후 다시 시도해 주세요." });
    }
  };

  if (state.phase === "idle") {
    return (
      <div className="permit-calc" aria-busy="true" aria-label="인허가 검토기 로딩 중">
        <div className="permit-loading">
          <div className="calc-skeleton" style={{ height: 40, width: "60%" }} />
          <div className="calc-skeleton" style={{ height: 120 }} />
          <div className="calc-skeleton" style={{ height: 48, width: "40%" }} />
        </div>
      </div>
    );
  }

  if (state.metaError) {
    return (
      <div className="permit-calc">
        <div className="calc-error-banner" role="alert">{state.metaError}</div>
      </div>
    );
  }

  return (
    <div className="permit-calc">
      <form
        className="calc-form"
        onSubmit={(e) => { e.preventDefault(); handleSubmit(); }}
        aria-label="AI 인허가 사전검토"
      >
        <IndustrySelector
          industries={state.meta?.industries ?? []}
          categories={state.meta?.major_categories ?? []}
          selected={state.selectedIndustry}
          onSelect={(ind) => dispatch({ type: "SET_INDUSTRY", payload: ind })}
        />

        <AssetInput
          capitalEok={state.capitalEok}
          technicians={state.technicians}
          equipment={state.equipment}
          depositEok={state.depositEok}
          onChange={(field, value) => dispatch({ type: "SET_FIELD", field, value })}
        />

        <RequirementToggles
          office={state.office}
          facility={state.facility}
          qualification={state.qualification}
          insurance={state.insurance}
          onChange={(field, value) => dispatch({ type: "SET_FIELD", field, value })}
        />

        {state.errorMsg && (
          <div className="calc-error-banner" role="alert">{state.errorMsg}</div>
        )}

        <button
          type="submit"
          className="calc-submit"
          disabled={state.phase === "submitting"}
        >
          {state.phase === "submitting" ? (
            <><Loader2 size={18} className="permit-spinner" aria-hidden="true" />AI가 검토 중입니다...</>
          ) : (
            <><ShieldCheck size={18} aria-hidden="true" />등록기준 검토하기</>
          )}
        </button>
      </form>

      {state.phase === "result" && state.result && (
        <div className="permit-results" aria-live="polite">
          <ScrollAnimate>
            <DiagnosisResult result={state.result} />
          </ScrollAnimate>

          {state.result.criteria_results && state.result.criteria_results.length > 0 && (
            <ScrollAnimate delay={150}>
              <CriteriaList criteria={state.result.criteria_results} />
            </ScrollAnimate>
          )}

          {state.result.next_actions && state.result.next_actions.length > 0 && (
            <ScrollAnimate delay={300}>
              <NextActions actions={state.result.next_actions} />
            </ScrollAnimate>
          )}

          <div className="permit-result-actions">
            <a
              href={`/consult?service=${encodeURIComponent(state.selectedIndustry?.service_name ?? "")}&status=${state.result?.overall_status ?? ""}`}
              className="calc-submit"
            >전문가 상담 연결</a>
            <button
              type="button"
              className="permit-reset-btn"
              onClick={() => dispatch({ type: "RESET" })}
            >
              다시 검토하기
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
