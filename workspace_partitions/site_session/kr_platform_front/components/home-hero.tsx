import Link from "next/link";
import { ArrowRight, Phone } from "lucide-react";
import { platformConfig } from "@/components/platform-config";
import { AnimatedCounter } from "@/components/animated-counter";

export function HomeHero() {
  return (
    <section className="home-hero" aria-label="메인 소개">
      {/* ── Full-width background video ── */}
      <div className="home-hero-bg" aria-hidden="true">
        <video
          autoPlay
          muted
          loop
          playsInline
          preload="metadata"
          poster="/media/hero-poster.svg"
        >
          <source src="/media/hero-construction.mp4" type="video/mp4" />
        </video>
        <div className="home-hero-scrim" />
      </div>

      {/* ── Overlay content ── */}
      <div className="home-hero-content">
        <p className="home-hero-kicker">건설업 AI 분석 플랫폼</p>
        <h1>
          AI가 분석하는
          <br />
          <span>양도가 산정 · 인허가 사전검토</span>
        </h1>
        <p className="home-hero-body">
          건설업 면허 양도가를 AI가 무료로 산정하고,{" "}
          191개 업종의 등록 비용·요건을 사전검토합니다.
        </p>

        {/* ── Two AI Systems: Primary CTA ── */}
        <div className="home-hero-twin-cta">
          <Link className="hero-system-card" href="/yangdo">
            <span className="hero-system-badge">AI 시스템 1</span>
            <strong>양도가 산정</strong>
            <span className="hero-system-desc">면허 적정 가격을 AI가 무료 분석</span>
            <span className="hero-system-arrow"><ArrowRight size={18} strokeWidth={2.4} aria-hidden="true" /></span>
          </Link>
          <Link className="hero-system-card" href="/permit">
            <span className="hero-system-badge">AI 시스템 2</span>
            <strong>인허가 사전검토</strong>
            <span className="hero-system-desc">등록기준 충족 여부·비용 즉시 확인</span>
            <span className="hero-system-arrow"><ArrowRight size={18} strokeWidth={2.4} aria-hidden="true" /></span>
          </Link>
        </div>

        <div className="home-hero-sub-actions">
          <a className="home-call-link" href={`tel:${platformConfig.contactPhone}`}>
            <Phone size={16} aria-hidden="true" />
            전문 행정사 상담 {platformConfig.contactPhone}
          </a>
        </div>

        <div className="home-hero-metrics">
          <div className="home-metric-card">
            <strong><AnimatedCounter end={191} suffix="+" /></strong>
            <span>분석 대상 업종</span>
          </div>
          <div className="home-metric-card">
            <strong>AI</strong>
            <span>데이터 기반 산정</span>
          </div>
          <div className="home-metric-card">
            <strong>특허 출원</strong>
            <span>AI 분석 알고리즘</span>
          </div>
        </div>
      </div>
    </section>
  );
}
