/** PermitCalculator — AI 인허가 사전검토 계산기 루트 컴포넌트 */
"use client";

import { useReducer, useEffect, useRef, useCallback, useState, useMemo } from "react";
import type { PermitMetaResponse, PermitPrecheckResponse, PermitIndustry } from "@/lib/permit-types";
import { fetchPermitMeta, fetchPermitPrecheck } from "@/lib/api-client";
import { IndustrySelector } from "./industry-selector";
import { AssetInput } from "./asset-input";
import { RequirementToggles } from "./requirement-toggles";
import { DiagnosisResult } from "./diagnosis-result";
import { ScrollAnimate } from "@/components/scroll-animate";
import { CriteriaList } from "./criteria-list";
import { NextActions } from "./next-actions";
import { CopyResultButton } from "@/components/shared/copy-result-button";
import { AiThinkingOverlay } from "@/components/shared/ai-thinking-overlay";
import { StepIndicator } from "@/components/shared/step-indicator";
import { ErrorBanner } from "@/components/shared/error-banner";
import { ResultPlaceholder } from "@/components/shared/result-placeholder";
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
  | { type: "RESET" }
  | { type: "RETRY_META" };

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

const FORM_STORAGE_KEY = "permit_calc_form";

function saveFormToStorage(state: CalcState): void {
  try {
    const data = {
      selectedIndustry: state.selectedIndustry,
      capitalEok: state.capitalEok,
      technicians: state.technicians,
      equipment: state.equipment,
      office: state.office,
      facility: state.facility,
      qualification: state.qualification,
      insurance: state.insurance,
      depositEok: state.depositEok,
    };
    sessionStorage.setItem(FORM_STORAGE_KEY, JSON.stringify(data));
  } catch { /* quota exceeded — ignore */ }
}

function loadFormFromStorage(): Partial<CalcState> | null {
  try {
    const raw = sessionStorage.getItem(FORM_STORAGE_KEY);
    if (!raw) return null;
    const data = JSON.parse(raw) as Record<string, unknown>;
    const restored: Partial<CalcState> = {};
    if (data.selectedIndustry && typeof data.selectedIndustry === "object") {
      restored.selectedIndustry = data.selectedIndustry as PermitIndustry;
    }
    for (const k of ["capitalEok", "technicians", "equipment", "depositEok"] as const) {
      if (typeof data[k] === "string") (restored as Record<string, string>)[k] = data[k] as string;
    }
    for (const k of ["office", "facility", "qualification", "insurance"] as const) {
      if (typeof data[k] === "boolean") (restored as Record<string, boolean>)[k] = data[k] as boolean;
    }
    return Object.keys(restored).length > 0 ? restored : null;
  } catch { return null; }
}

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
      try { sessionStorage.removeItem(FORM_STORAGE_KEY); } catch { /* ignore */ }
      return { ...initialState, phase: "ready", meta: state.meta };
    case "RETRY_META":
      return { ...state, phase: "idle", metaError: null };
    default:
      return state;
  }
}

function lazyInit(): CalcState {
  const saved = loadFormFromStorage();
  return saved ? { ...initialState, ...saved } : initialState;
}

export function PermitCalculator() {
  const [state, dispatch] = useReducer(reducer, initialState, lazyInit);
  const resultsRef = useRef<HTMLDivElement>(null);
  const errorRef = useRef<HTMLDivElement>(null);
  const formRef = useRef<HTMLFormElement>(null);
  const abortRef = useRef<AbortController | null>(null);

  /* ── Inline validation: track touched fields ── */
  const [touched, setTouched] = useState<Set<string>>(new Set());
  const touchField = useCallback((field: string) => {
    setTouched((prev) => {
      if (prev.has(field)) return prev;
      const next = new Set(prev);
      next.add(field);
      return next;
    });
  }, []);

  const fieldErrors = useMemo<Record<string, string | undefined>>(() => {
    const errs: Record<string, string | undefined> = {};
    if (touched.has("capitalEok") && touched.has("technicians") && !state.capitalEok && !state.technicians) {
      errs.capitalEok = "자본금 또는 기술인력 중 하나 이상을 입력해 주세요.";
    }
    if (touched.has("selectedIndustry") && !state.selectedIndustry) {
      errs.selectedIndustry = "업종을 선택해 주세요.";
    }
    return errs;
  }, [state.capitalEok, state.technicians, state.selectedIndustry, touched]);

  /* ── Persist form inputs to sessionStorage ── */
  useEffect(() => {
    if (state.phase === "ready" || state.phase === "result") saveFormToStorage(state);
  }, [state.selectedIndustry, state.capitalEok, state.technicians, state.equipment, state.office, state.facility, state.qualification, state.insurance, state.depositEok, state.phase]);

  /* ── Focus error banner when validation fails ── */
  useEffect(() => {
    if (state.errorMsg && errorRef.current) {
      errorRef.current.focus();
    }
  }, [state.errorMsg]);

  const loadMeta = useCallback(() => {
    dispatch({ type: "RETRY_META" });
    fetchPermitMeta()
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

  /* ── Abort in-flight request on unmount ── */
  useEffect(() => () => { abortRef.current?.abort(); }, []);

  const handleSubmit = async () => {
    /* Touch all required fields to show inline errors */
    setTouched((prev) => {
      const next = new Set(prev);
      next.add("selectedIndustry");
      next.add("capitalEok");
      next.add("technicians");
      return next;
    });

    if (!state.selectedIndustry) {
      dispatch({ type: "ERROR", payload: "업종을 선택해 주세요." });
      return;
    }
    if (!state.capitalEok && !state.technicians) {
      dispatch({ type: "ERROR", payload: "자본금 또는 기술인력 중 하나 이상을 입력해 주세요." });
      return;
    }

    /* Cancel any in-flight request before starting a new one */
    abortRef.current?.abort();
    const ac = new AbortController();
    abortRef.current = ac;

    dispatch({ type: "SUBMIT" });
    try {
      const res = await fetchPermitPrecheck({
        service_code: state.selectedIndustry.service_code,
        service_name: state.selectedIndustry.service_name,
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
      }, { signal: ac.signal });
      if (ac.signal.aborted) return;
      if (!res.ok) {
        dispatch({ type: "ERROR", payload: res.error ?? "검토에 실패했습니다." });
      } else {
        dispatch({ type: "RESULT", payload: res });
      }
    } catch (err) {
      if (ac.signal.aborted) return; /* cancelled — ignore silently */
      const code = err instanceof Error && "code" in err ? (err as { code: string }).code : "";
      const msg = code === "timeout"
        ? "요청 시간이 초과되었습니다. 잠시 후 다시 시도해 주세요."
        : code === "mapping_required"
          ? "해당 업종은 법령 기준 매핑이 진행 중입니다. 전문가 상담을 이용해 주세요."
          : "서버 연결에 실패했습니다. 잠시 후 다시 시도해 주세요.";
      dispatch({ type: "ERROR", payload: msg });
    }
  };

  if (state.phase === "idle") {
    return (
      <div className="permit-calc" aria-busy="true" aria-label="인허가 검토기 로딩 중">
        <div className="calc-loading-skeleton">
          <div className="calc-skeleton-section">
            <div className="calc-skeleton" style={{ height: 12, width: "25%" }} />
            <div className="calc-skeleton" style={{ height: 44 }} />
          </div>
          <div className="calc-skeleton-section">
            <div className="calc-skeleton" style={{ height: 12, width: "30%" }} />
            <div className="calc-skeleton-row">
              <div className="calc-skeleton" style={{ height: 44, flex: 1 }} />
              <div className="calc-skeleton" style={{ height: 44, flex: 1 }} />
            </div>
            <div className="calc-skeleton-row">
              <div className="calc-skeleton" style={{ height: 44, flex: 1 }} />
              <div className="calc-skeleton" style={{ height: 44, flex: 1 }} />
            </div>
          </div>
          <div className="calc-skeleton" style={{ height: 52, borderRadius: 8 }} />
        </div>
      </div>
    );
  }

  if (state.metaError) {
    return (
      <div className="permit-calc">
        <ErrorBanner message={state.metaError} onRetry={loadMeta} />
      </div>
    );
  }

  const hasIndustry = !!state.selectedIndustry;
  const hasAssets = !!(state.capitalEok || state.technicians || state.equipment);
  const steps = [
    { label: "업종", complete: hasIndustry },
    { label: "자산", complete: hasIndustry && hasAssets },
    { label: "요건", complete: hasIndustry && hasAssets },
    { label: "진단", complete: state.phase === "result" },
  ];
  const currentStep = !hasIndustry ? 0 : !hasAssets ? 1 : state.phase === "result" ? 3 : 2;

  return (
    <div className="permit-calc">
      <StepIndicator steps={steps} currentStep={currentStep} />

      <form
        ref={formRef}
        className="calc-form"
        onSubmit={(e) => { e.preventDefault(); handleSubmit(); }}
        aria-label="AI 인허가 사전검토"
      >
        <fieldset className="calc-section">
          <legend className="calc-section-title">
            <span className="calc-section-num">1</span>업종 선택
          </legend>
          <IndustrySelector
            industries={state.meta?.industries ?? []}
            categories={state.meta?.major_categories ?? []}
            selected={state.selectedIndustry}
            error={fieldErrors.selectedIndustry}
            onSelect={(ind) => dispatch({ type: "SET_INDUSTRY", payload: ind })}
          />
        </fieldset>

        <fieldset className="calc-section">
          <legend className="calc-section-title">
            <span className="calc-section-num">2</span>자산 현황
          </legend>
          <AssetInput
            capitalEok={state.capitalEok}
            technicians={state.technicians}
            equipment={state.equipment}
            depositEok={state.depositEok}
            fieldErrors={fieldErrors}
            onChange={(field, value) => dispatch({ type: "SET_FIELD", field, value })}
            onBlur={touchField}
          />
        </fieldset>

        <fieldset className="calc-section">
          <legend className="calc-section-title">
            <span className="calc-section-num">3</span>요건 확인
          </legend>
          <RequirementToggles
            office={state.office}
            facility={state.facility}
            qualification={state.qualification}
            insurance={state.insurance}
            onChange={(field, value) => dispatch({ type: "SET_FIELD", field, value })}
          />
        </fieldset>

        {state.errorMsg && (
          <ErrorBanner ref={errorRef} message={state.errorMsg} onRetry={handleSubmit} />
        )}

        <button
          type="submit"
          className="calc-submit calc-submit--ai"
          disabled={state.phase === "submitting"}
        >
          {state.phase === "submitting" ? (
            <><Loader2 size={18} className="permit-spinner" aria-hidden="true" />AI가 검토 중입니다...</>
          ) : (
            <><ShieldCheck size={18} aria-hidden="true" />AI 등록기준 검토하기</>
          )}
        </button>
      </form>

      <AiThinkingOverlay
        active={state.phase === "submitting"}
        context="인허가 사전검토"
        expectedMs={4000}
      />

      {/* Result placeholder — shown before first submission */}
      {state.phase !== "result" && state.phase !== "submitting" && !state.errorMsg && (
        <ResultPlaceholder
          title="AI 등록기준 검토 결과가 여기에 표시됩니다"
          description="업종을 선택하고 자산 현황을 입력한 후 검토 버튼을 눌러 주세요."
        />
      )}

      {state.phase === "result" && state.result && (
        <div ref={resultsRef} className="permit-results" aria-live="polite">
          <h2 className="calc-results-heading">검토 결과</h2>
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
            <CopyResultButton getText={() => {
              const r = state.result;
              if (!r) return "";
              const status = r.overall_status === "pass" ? "충족" : r.overall_status === "shortfall" ? "미충족" : r.overall_status ?? "";
              let txt = `[AI 인허가 검토 결과]\n업종: ${state.selectedIndustry?.service_name ?? ""}\n판정: ${status}\n`;
              if (r.criteria_results?.length) {
                txt += `\n항목별 결과:\n`;
                for (const c of r.criteria_results) {
                  const mark = c.status === "pass" ? "✓" : c.status === "fail" ? "✗" : "?";
                  txt += `${mark} ${c.label || c.field}\n`;
                }
              }
              if (r.next_actions?.length) {
                txt += `\n다음 조치:\n`;
                for (const a of r.next_actions) txt += `${a.priority}. ${a.action}\n`;
              }
              txt += `\n서울건설정보 (seoulmna.kr)`;
              return txt;
            }} />
            <button
              type="button"
              className="permit-reset-btn"
              onClick={() => {
                dispatch({ type: "RESET" });
                setTouched(new Set());
                formRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
                setTimeout(() => {
                  const first = formRef.current?.querySelector<HTMLElement>("input, select, [role='combobox']");
                  first?.focus();
                }, 400);
              }}
            >
              다시 검토하기
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
