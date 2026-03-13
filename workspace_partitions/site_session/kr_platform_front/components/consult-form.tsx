"use client";

import { useCallback, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import { CheckCircle } from "lucide-react";

type FormState = "idle" | "submitting" | "success" | "error";

const API_ENDPOINT = "/api/consult-intake";

/** Map URL query params from calculator CTAs to form defaults. */
function deriveDefaults(params: URLSearchParams) {
  // From yangdo: /consult?license=건축공사업&estimate=2.5
  // From permit: /consult?service=전기공사업&status=pass
  const license = params.get("license") ?? "";
  const estimate = params.get("estimate") ?? "";
  const service = params.get("service") ?? "";
  const status = params.get("status") ?? "";

  let serviceTrack = "";
  let message = "";

  if (license) {
    serviceTrack = "transfer_price_estimation";
    message = `[AI 양도가 산정 결과] 업종: ${license}`;
    if (estimate) message += `, 추정 양도가: ${estimate}억원`;
    message += "\n\n";
  } else if (service) {
    serviceTrack = "permit_precheck_new_registration";
    const statusLabel = status === "pass" ? "충족" : status === "shortfall" ? "미충족" : status;
    message = `[AI 인허가 검토 결과] 업종: ${service}`;
    if (statusLabel) message += `, 판정: ${statusLabel}`;
    message += "\n\n";
  }

  return { serviceTrack, message };
}

export function ConsultForm() {
  const searchParams = useSearchParams();
  const defaults = useMemo(() => deriveDefaults(searchParams), [searchParams]);

  const [state, setState] = useState<FormState>("idle");
  const [errorMsg, setErrorMsg] = useState("");

  const handleSubmit = useCallback(
    async (e: React.FormEvent<HTMLFormElement>) => {
      e.preventDefault();
      setState("submitting");
      setErrorMsg("");

      const form = e.currentTarget;
      const data = new FormData(form);
      const payload = {
        customer_name: (data.get("name") as string)?.trim() || "",
        customer_phone: (data.get("phone") as string)?.trim() || "",
        customer_email: (data.get("email") as string)?.trim() || "",
        service_track: (data.get("service") as string) || "",
        message: (data.get("message") as string)?.trim() || "",
        source: "kr-platform-consult-form",
        page_mode: "consult",
      };

      if (!payload.customer_name) {
        setErrorMsg("이름을 입력해 주세요.");
        setState("idle");
        return;
      }
      if (!payload.customer_phone && !payload.customer_email) {
        setErrorMsg("전화번호 또는 이메일 중 하나를 입력해 주세요.");
        setState("idle");
        return;
      }
      if (payload.customer_email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(payload.customer_email)) {
        setErrorMsg("올바른 이메일 주소를 입력해 주세요.");
        setState("idle");
        return;
      }

      try {
        const res = await fetch(API_ENDPOINT, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });
        if (!res.ok) {
          const body = await res.json().catch(() => null);
          throw new Error(body?.error || `서버 오류 (${res.status})`);
        }
        setState("success");
        form.reset();
      } catch {
        setErrorMsg("전송에 실패했습니다. 잠시 후 다시 시도해 주세요.");
        setState("error");
      }
    },
    [],
  );

  if (state === "success") {
    return (
      <div className="consult-form-success" role="status">
        <span className="consult-form-success-icon" aria-hidden="true"><CheckCircle size={32} /></span>
        <h3>상담 요청이 접수되었습니다</h3>
        <p>확인 후 영업일 기준 1일 이내에 연락드리겠습니다.</p>
        <button
          type="button"
          className="cta-secondary consult-form-reset"
          onClick={() => setState("idle")}
        >
          추가 문의하기
        </button>
      </div>
    );
  }

  return (
    <form className="consult-form" onSubmit={handleSubmit} noValidate>
      <div className="consult-form-field">
        <label htmlFor="cf-name">이름 *</label>
        <input
          id="cf-name"
          name="name"
          type="text"
          required
          autoComplete="name"
          placeholder="홍길동"
          maxLength={50}
        />
      </div>

      <div className="consult-form-row">
        <div className="consult-form-field">
          <label htmlFor="cf-phone">전화번호</label>
          <input
            id="cf-phone"
            name="phone"
            type="tel"
            inputMode="tel"
            autoComplete="tel"
            placeholder="010-1234-5678"
            pattern="[0-9\-]{9,20}"
            maxLength={20}
          />
        </div>
        <div className="consult-form-field">
          <label htmlFor="cf-email">이메일</label>
          <input
            id="cf-email"
            name="email"
            type="email"
            autoComplete="email"
            placeholder="example@email.com"
            maxLength={100}
          />
        </div>
      </div>

      <div className="consult-form-field">
        <label htmlFor="cf-service">상담 분야</label>
        <select id="cf-service" name="service" defaultValue={defaults.serviceTrack || ""}>
          <option value="">선택해 주세요</option>
          <option value="transfer_price_estimation">면허 양도 (양도가 산정)</option>
          <option value="permit_precheck_new_registration">AI 인허가 검토</option>
          <option value="general">일반 문의</option>
        </select>
      </div>

      <div className="consult-form-field">
        <label htmlFor="cf-message">문의 내용</label>
        <textarea
          id="cf-message"
          name="message"
          rows={4}
          defaultValue={defaults.message}
          placeholder="상담받고 싶은 내용을 간략히 적어 주세요."
          maxLength={2000}
        />
      </div>

      {(state === "error" || errorMsg) && (
        <p className="consult-form-error" role="alert">
          {errorMsg}
        </p>
      )}

      <button
        type="submit"
        className="cta-primary consult-form-submit"
        disabled={state === "submitting"}
      >
        {state === "submitting" ? "전송 중..." : "상담 요청하기"}
      </button>

      <p className="consult-form-note">
        * 이름은 필수, 전화번호 또는 이메일 중 하나 이상을 입력해 주세요.
      </p>
    </form>
  );
}
