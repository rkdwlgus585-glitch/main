"use client";

import { useEffect, useState } from "react";

type StatusState = "ok" | "degraded" | "loading";

/**
 * Platform status bar — fetches /api/platform-status on mount and
 * displays live operational status.  Falls back to a static "정상 운영 중"
 * message if the health check fails or times out.
 */
export function PlatformStatus() {
  const [status, setStatus] = useState<StatusState>("loading");
  const [label, setLabel] = useState("AI 분석 엔진 상태 확인 중");

  useEffect(() => {
    const ctrl = new AbortController();
    fetch("/api/platform-status", { signal: ctrl.signal })
      .then((res) => (res.ok ? res.json() : Promise.reject(new Error("not ok"))))
      .then((data: { ok?: boolean; systems?: { ready?: boolean }[] }) => {
        const allReady =
          data.ok !== false &&
          Array.isArray(data.systems) &&
          data.systems.every((s) => s.ready !== false);
        setStatus(allReady ? "ok" : "degraded");
        setLabel(allReady ? "AI 분석 엔진 정상 운영 중" : "일부 시스템 점검 중");
      })
      .catch(() => {
        // Network error or timeout — assume OK to avoid alarming users
        setStatus("ok");
        setLabel("AI 분석 엔진 정상 운영 중");
      });
    return () => ctrl.abort();
  }, []);

  return (
    <div
      className={`status-bar${status === "degraded" ? " status-bar--degraded" : ""}`}
      role="status"
      aria-label="서비스 상태"
    >
      <span className="status-dot" aria-hidden="true" />
      <span>{label}</span>
    </div>
  );
}
