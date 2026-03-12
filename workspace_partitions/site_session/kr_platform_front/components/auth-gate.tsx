"use client";

import { useState, useCallback } from "react";
import Link from "next/link";
import { Lock } from "lucide-react";
import { Turnstile } from "@/components/turnstile";

/**
 * AuthGate — widget 접근 전 로그인을 요구하는 게이트 컴포넌트.
 *
 * 현재는 UI 프레임워크만 구현. 실제 인증 연동 시:
 * 1. NextAuth.js (Auth.js) session 체크
 * 2. 세션 있으면 children 렌더링
 * 3. 세션 없으면 로그인 안내 표시
 *
 * Turnstile CAPTCHA:
 * - NEXT_PUBLIC_TURNSTILE_SITE_KEY가 설정되면 자동으로 표시
 * - 미설정 시 Turnstile 컴포넌트가 null 반환 (개발 편의)
 *
 * TODO: NextAuth.js 연동 후 useSession() 훅으로 실제 인증 체크
 */

interface AuthGateProps {
  /** 인증 후 표시할 콘텐츠 */
  children: React.ReactNode;
  /** 서비스 명 (예: "양도가 산정", "인허가 사전검토") */
  serviceName: string;
}

export function AuthGate({ children, serviceName }: AuthGateProps) {
  // Turnstile 검증 상태
  const [turnstileToken, setTurnstileToken] = useState<string | null>(null);
  const hasTurnstileKey = !!process.env.NEXT_PUBLIC_TURNSTILE_SITE_KEY;

  const handleTurnstileVerify = useCallback((token: string) => {
    setTurnstileToken(token);
  }, []);

  const handleTurnstileExpire = useCallback(() => {
    setTurnstileToken(null);
  }, []);

  // TODO: 실제 인증 연동 시 아래 주석 해제
  // const { data: session, status } = useSession();
  // if (status === "loading") return <AuthGateLoading />;
  // if (session) return <>{children}</>;

  // 현재는 인증 없이 바로 콘텐츠 표시 (개발 단계)
  const isAuthenticated = true; // TODO: 실제 세션 체크로 교체

  if (isAuthenticated) {
    return <>{children}</>;
  }

  /* Turnstile 활성화 시, 검증 완료 전까지 버튼 비활성화 */
  const captchaRequired = hasTurnstileKey && !turnstileToken;

  return (
    <div className="auth-gate">
      <div className="auth-gate-card">
        <div className="auth-gate-icon" aria-hidden="true">
          <Lock size={28} />
        </div>
        <h3 className="auth-gate-title">로그인이 필요합니다</h3>
        <p className="auth-gate-desc">
          <strong>{serviceName}</strong> 서비스를 이용하려면
          로그인해 주세요. 간편 소셜 로그인으로 바로 시작할 수
          있습니다.
        </p>

        {/* Cloudflare Turnstile — siteKey가 없으면 자동으로 숨김 */}
        <Turnstile
          onVerify={handleTurnstileVerify}
          onExpire={handleTurnstileExpire}
          theme="auto"
          size="normal"
        />

        <div className="auth-gate-providers">
          <button
            className="auth-provider auth-provider--kakao"
            type="button"
            disabled={captchaRequired}
            aria-describedby={captchaRequired ? "captcha-notice" : undefined}
          >
            카카오로 시작하기
          </button>
          <button
            className="auth-provider auth-provider--naver"
            type="button"
            disabled={captchaRequired}
          >
            네이버로 시작하기
          </button>
          <button
            className="auth-provider auth-provider--google"
            type="button"
            disabled={captchaRequired}
          >
            Google로 시작하기
          </button>
          <button
            className="auth-provider auth-provider--phone"
            type="button"
            disabled={captchaRequired}
          >
            휴대전화 인증
          </button>
        </div>

        {captchaRequired && (
          <p id="captcha-notice" className="auth-gate-captcha-notice">
            보안 검증을 완료하면 로그인 버튼이 활성화됩니다.
          </p>
        )}

        <p className="auth-gate-legal">
          로그인 시{" "}
          <Link href="/terms">이용약관</Link> 및{" "}
          <Link href="/privacy">개인정보처리방침</Link>에
          동의하는 것으로 간주합니다.
        </p>
      </div>
    </div>
  );
}
