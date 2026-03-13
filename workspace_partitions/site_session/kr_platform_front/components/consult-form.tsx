"use client";

import { useCallback, useState } from "react";
import { CheckCircle } from "lucide-react";

type FormState = "idle" | "submitting" | "success" | "error";

const API_ENDPOINT = "/api/consult-intake";

export function ConsultForm() {
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
      } catch (err) {
        setErrorMsg(
          err instanceof Error ? err.message : "전송에 실패했습니다. 잠시 후 다시 시도해 주세요.",
        );
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
            autoComplete="tel"
            placeholder="010-1234-5678"
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
        <select id="cf-service" name="service" defaultValue="">
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
