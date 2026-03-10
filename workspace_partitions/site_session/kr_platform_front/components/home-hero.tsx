import Link from "next/link";
import { ArrowRight, Phone } from "lucide-react";
import { platformConfig } from "@/components/platform-config";

const metrics = [
  { value: "191+", label: "분석 대상 업종" },
  { value: "AI", label: "데이터 기반 산정" },
  { value: "무료", label: "양도가·등록 검토" },
];

export function HomeHero() {
  return (
    <section className="home-hero">
      <div className="home-hero-grid">
        <div className="home-hero-copy">
          <p className="home-hero-kicker">건설업 양도양수 · 건설업등록 전문 플랫폼</p>
          <h1>
            건설업 면허 양도가 산정부터
            <br />
            <span>신규 등록까지 한 곳에서</span>
          </h1>
          <p className="home-hero-body">
            AI가 시장 데이터를 분석해 적정 양도가격을 산정하고,
            191개 업종의 등록기준 충족 여부를 사전검토합니다.
            전문 행정사 상담까지 원스톱으로 연결됩니다.
          </p>

          <div className="home-hero-actions">
            <Link className="cta-primary home-cta-primary" href="/yangdo">
              양도가 무료 산정
              <ArrowRight size={18} strokeWidth={2.2} />
            </Link>
            <Link className="cta-secondary home-cta-secondary" href="/permit">
              건설업등록 검토
            </Link>
            <a className="home-call-link" href={`tel:${platformConfig.contactPhone}`}>
              <Phone size={16} />
              {platformConfig.contactPhone}
            </a>
          </div>

          <div className="home-hero-metrics">
            {metrics.map((metric) => (
              <div key={metric.label} className="home-metric-card">
                <strong>{metric.value}</strong>
                <span>{metric.label}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="home-hero-media">
          <div className="home-video-frame">
            <video
              autoPlay
              muted
              loop
              playsInline
              preload="metadata"
              aria-label="건설 현장 영상"
            >
              <source src="/media/hero-construction.mp4" type="video/mp4" />
            </video>
            <div className="home-video-overlay" />
          </div>
        </div>
      </div>
    </section>
  );
}
