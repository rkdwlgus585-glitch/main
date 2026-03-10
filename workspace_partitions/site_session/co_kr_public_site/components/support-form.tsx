"use client";

import Link from "next/link";
import { useState, useTransition } from "react";
import { trackContactEvent } from "@/components/contact-link";
import { consultServiceOptions, type ConsultService } from "@/lib/consult-schema";

type FormState = {
  name: string;
  phone: string;
  email: string;
  service: ConsultService;
  message: string;
  acceptPrivacy: boolean;
  website: string;
};

const initialFormState: FormState = {
  name: "",
  phone: "",
  email: "",
  service: "양도양수",
  message: "",
  acceptPrivacy: false,
  website: "",
};

export function SupportForm() {
  const [isPending, startTransition] = useTransition();
  const [form, setForm] = useState<FormState>(initialFormState);
  const [result, setResult] = useState<{ type: "idle" | "success" | "error"; message: string }>({
    type: "idle",
    message: "",
  });

  function updateField<K extends keyof FormState>(key: K, value: FormState[K]) {
    setForm((current) => ({ ...current, [key]: value }));
  }

  function submitForm(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setResult({ type: "idle", message: "" });

    startTransition(async () => {
      try {
        const response = await fetch("/api/consult", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(form),
        });

        const payload = (await response.json()) as { ok: boolean; message?: string; id?: string };

        if (!response.ok || !payload.ok) {
          setResult({
            type: "error",
            message: payload.message ?? "문의 접수에 실패했습니다. 잠시 후 다시 시도해 주세요.",
          });
          return;
        }

        trackContactEvent("submit_consult", `consult_${form.service}`);
        setForm(initialFormState);
        setResult({
          type: "success",
          message: `문의가 접수되었습니다. 접수 번호: ${payload.id}`,
        });
      } catch {
        setResult({
          type: "error",
          message: "문의 접수 중 네트워크 오류가 발생했습니다. 잠시 후 다시 시도해 주세요.",
        });
      }
    });
  }

  return (
    <form className="support-form-card" onSubmit={submitForm}>
      <div className="support-form-header">
        <p className="eyebrow">Consult Request</p>
        <h2>구조화된 문의 접수</h2>
        <p>연락처와 문의 목적을 남기면 운영자가 순차적으로 검토 후 회신할 수 있도록 정리됩니다.</p>
      </div>

      <div className="support-form-grid">
        <label className="support-field">
          <span>이름</span>
          <input
            value={form.name}
            onChange={(event) => updateField("name", event.target.value)}
            placeholder="담당자명"
            autoComplete="name"
            minLength={2}
            maxLength={40}
            required
          />
        </label>

        <label className="support-field">
          <span>연락처</span>
          <input
            value={form.phone}
            onChange={(event) => updateField("phone", event.target.value)}
            placeholder="연락 가능한 번호"
            autoComplete="tel"
            inputMode="tel"
            pattern="[0-9()+ -]{8,20}"
            title="숫자, 공백, 괄호, 하이픈을 포함해 8자 이상 입력해 주세요."
            minLength={8}
            maxLength={20}
            required
          />
        </label>

        <label className="support-field">
          <span>이메일</span>
          <input
            type="email"
            value={form.email}
            onChange={(event) => updateField("email", event.target.value)}
            placeholder="선택 입력"
            autoComplete="email"
          />
        </label>

        <label className="support-field">
          <span>상담 유형</span>
          <select value={form.service} onChange={(event) => updateField("service", event.target.value as FormState["service"])}>
            {consultServiceOptions.map((option) => (
              <option key={option} value={option}>
                {option}
              </option>
            ))}
          </select>
        </label>
      </div>

      <label className="support-field">
        <span>문의 내용</span>
        <textarea
          value={form.message}
          onChange={(event) => updateField("message", event.target.value)}
          placeholder="현재 상황, 원하는 방향, 보유 자료 등을 간단히 적어 주세요."
          rows={6}
          minLength={10}
          maxLength={1000}
          required
        />
      </label>

      <label className="support-field support-field--trap" aria-hidden="true">
        <span>웹사이트</span>
        <input
          tabIndex={-1}
          autoComplete="off"
          value={form.website}
          onChange={(event) => updateField("website", event.target.value)}
        />
      </label>

      <label className="support-consent">
        <input
          type="checkbox"
          checked={form.acceptPrivacy}
          onChange={(event) => updateField("acceptPrivacy", event.target.checked)}
          required
        />
        <span>
          <Link href="/privacy">개인정보처리방침</Link>을 확인했고 문의 접수에 동의합니다.
        </span>
      </label>

      <div className="support-form-footer">
        <button type="submit" className="cta-primary support-submit" disabled={isPending}>
          {isPending ? "접수 중..." : "문의 접수"}
        </button>
        <p>운영 시간 내 순차 확인 후 회신하는 구조입니다. 긴급 건은 전화 상담이 더 빠릅니다.</p>
      </div>

      {result.type !== "idle" ? (
        <p className={`support-form-status support-form-status--${result.type}`} aria-live="polite">
          {result.message}
        </p>
      ) : null}
    </form>
  );
}
