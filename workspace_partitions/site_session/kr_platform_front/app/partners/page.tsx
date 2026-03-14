import type { Metadata } from "next";
import Link from "next/link";
import { Phone, Building2, Users, Briefcase, ArrowRight, CheckCircle2, Zap, Shield, Palette } from "lucide-react";
import { ScrollAnimate } from "@/components/scroll-animate";
import { platformConfig } from "@/components/platform-config";
import { breadcrumbSchema, organizationRef, siteBase } from "@/lib/json-ld";

const pageTitle = "시스템 도입 | 서울건설정보";
const pageDescription =
  "행정사사무소 대상 AI 양도가·인허가 시스템 도입, 건설 컨설팅·공공기관 대상 시장 데이터·뉴스레터 제공. 맞춤 솔루션 안내.";

export const metadata: Metadata = {
  title: pageTitle,
  description: pageDescription,
  alternates: { canonical: "/partners" },
  openGraph: {
    title: pageTitle,
    description: pageDescription,
    url: "/partners",
    type: "website",
    locale: "ko_KR",
  },
  twitter: {
    card: "summary",
    title: pageTitle,
    description: pageDescription,
  },
};

const targets = [
  {
    title: "행정사사무소",
    description:
      "면허 상담 시 AI 양도가 산정 · AI 인허가 검토 시스템을 즉시 활용하세요. 고객 신뢰도와 업무 효율이 높아집니다.",
    icon: Briefcase,
    benefits: ["AI 양도가 산정 시스템 직접 운영", "AI 인허가 검토 시스템 탑재", "복합면허 분해 분석 · 근거 자료 자동 생성"],
  },
  {
    title: "건설 컨설팅 · 법인",
    description:
      "업종별 시장 동향, 면허 시세 데이터, 정책 변동 뉴스레터를 주기적으로 제공합니다.",
    icon: Building2,
    benefits: ["면허 시세 · 업종 트렌드 데이터 수신", "정책 변동 뉴스레터 정기 발송", "맞춤 데이터 리포트 · API 연동"],
  },
  {
    title: "공공기관 · 협회",
    description:
      "건설업 면허 시장 분석 데이터와 업종별 통계를 기관 업무·정책 수립에 활용할 수 있습니다.",
    icon: Users,
    benefits: ["시장 통계 대시보드 제공", "업종별 트렌드 분석 리포트", "정기 데이터 뉴스레터 발송"],
  },
];

const steps = [
  { step: "01", title: "도입 문의", description: "전화 또는 이메일로 도입 목적과 규모를 알려주세요." },
  { step: "02", title: "맞춤 데모", description: "귀사 환경에 맞는 시스템 시연과 활용 방안을 안내합니다." },
  { step: "03", title: "도입 · 연동", description: "시스템 설정, 데이터 연동, 담당자 교육을 진행합니다." },
  { step: "04", title: "운영 · 지원", description: "지속적인 업데이트와 기술 지원으로 안정적 운영을 돕습니다." },
];

const benefitStats = [
  { label: "업무 시간 절감", value: "70%", detail: "수작업 분석 대비 AI 자동 산정으로 대폭 절감" },
  { label: "분석 업종 수", value: "191개", detail: "건설업 전 업종 등록기준 실시간 비교" },
  { label: "특허 출원 기술", value: "2건", detail: "AI 양도가 산정 + AI 인허가 검토 알고리즘" },
];

/*
 * NOTE: JSON-LD uses dangerouslySetInnerHTML which is safe here because
 * all data comes from compile-time string literals — no user input is
 * interpolated. This is the standard Next.js pattern for structured data.
 */
function PartnersJsonLd() {
  const schema = {
    "@context": "https://schema.org",
    "@type": "Service",
    name: "AI 건설업 분석 시스템 도입",
    description: pageDescription,
    url: `${siteBase}/partners`,
    provider: organizationRef,
    serviceType: "AI 시스템 도입 · B2B 솔루션",
    areaServed: { "@type": "Country", name: "KR" },
  };
  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(breadcrumbSchema("시스템 도입", "/partners")) }}
      />
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(schema) }}
      />
    </>
  );
}

export default function PartnersPage() {
  return (
    <main id="main" className="page-shell">
      <PartnersJsonLd />
      <Link className="back-link" href="/">
        ← 플랫폼 홈으로
      </Link>

      <section className="partners-hero" aria-label="시스템 도입 안내">
        <p className="eyebrow">시스템 도입</p>
        <h1>AI 분석 시스템, 귀사에 도입하세요</h1>
        <p className="partners-hero-body">
          AI 양도가 산정과 AI 인허가 검토, 두 가지 AI 시스템을<br />
          귀사 업무 환경에 맞춰 도입할 수 있습니다.
        </p>
        <div className="partners-hero-actions">
          <a className="cta-primary" href={`tel:${platformConfig.contactPhone}`}>
            <Phone size={18} aria-hidden="true" /> {platformConfig.contactPhone} 도입 문의
          </a>
          <a className="cta-secondary" href={`mailto:${platformConfig.contactEmail}`}>
            이메일 문의
          </a>
        </div>
      </section>

      {/* ── 도입 효과 수치 ── */}
      <ScrollAnimate>
        <section className="partners-stats" aria-label="도입 효과">
          <div className="partners-stats-grid">
            {benefitStats.map((b) => (
              <div key={b.label} className="partners-stat-card">
                <span className="partners-stat-value">{b.value}</span>
                <strong className="partners-stat-label">{b.label}</strong>
                <p className="partners-stat-detail">{b.detail}</p>
              </div>
            ))}
          </div>
        </section>
      </ScrollAnimate>

      {/* ── 도입 대상 ── */}
      <ScrollAnimate delay={80}>
        <section className="partners-targets" aria-label="도입 대상">
          <div className="section-header">
            <p className="eyebrow">도입 대상</p>
            <h2>이런 기관에 적합합니다</h2>
          </div>
          <div className="partners-targets-grid">
            {targets.map(({ title, description, icon: Icon, benefits: bens }) => (
              <div key={title} className="partners-target-card">
                <span className="partners-target-icon" aria-hidden="true">
                  <Icon size={28} />
                </span>
                <h3>{title}</h3>
                <p>{description}</p>
                <ul className="partners-benefit-list">
                  {bens.map((b) => (
                    <li key={b}>
                      <CheckCircle2 size={16} aria-hidden="true" /> {b}
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </section>
      </ScrollAnimate>

      {/* ── 도입 절차 ── */}
      <ScrollAnimate delay={120}>
        <section className="partners-steps" aria-label="도입 절차">
          <div className="section-header">
            <p className="eyebrow">도입 절차</p>
            <h2>4단계로 완료됩니다</h2>
          </div>
          <div className="partners-steps-grid">
            {steps.map((s) => (
              <div key={s.step} className="partners-step-item">
                <div className="partners-step-header">
                  <span className="partners-step-number">{s.step}</span>
                  <h3>{s.title}</h3>
                </div>
                <p>{s.description}</p>
              </div>
            ))}
          </div>
        </section>
      </ScrollAnimate>

      {/* ── 임베드 위젯 장점 ── */}
      <ScrollAnimate delay={80}>
        <section className="partners-embed" aria-label="위젯 설치 장점">
          <div className="section-header">
            <p className="eyebrow">간편 설치</p>
            <h2>귀사 웹사이트에 AI 분석 기능 탑재</h2>
          </div>
          <div className="partners-embed-benefits">
            <p className="partners-embed-lead">
              복잡한 개발 없이, 간단한 설치만으로 귀사 웹사이트에<br />
              AI 양도가 산정과 AI 인허가 검토 기능을 즉시 제공할 수 있습니다.
            </p>
            <div className="partners-embed-grid">
              <div className="partners-embed-card">
                <span className="partners-embed-icon" aria-hidden="true"><Zap size={24} /></span>
                <h3>5분 내 설치 완료</h3>
                <p>별도 서버나 인프라 없이 빠르게 적용됩니다.</p>
              </div>
              <div className="partners-embed-card">
                <span className="partners-embed-icon" aria-hidden="true"><Palette size={24} /></span>
                <h3>브랜드 맞춤 디자인</h3>
                <p>귀사 브랜드에 맞는 색상과 위치를 자유롭게 설정합니다.</p>
              </div>
              <div className="partners-embed-card">
                <span className="partners-embed-icon" aria-hidden="true"><Shield size={24} /></span>
                <h3>보안 · 성능 보장</h3>
                <p>별도 데이터 수집 없이, 안전하고 가볍게 동작합니다.</p>
              </div>
            </div>
          </div>
        </section>
      </ScrollAnimate>

      {/* ── 하단 CTA ── */}
      <ScrollAnimate delay={80}>
      <section className="consult-start" aria-label="도입 문의 안내">
        <h2>도입을 검토하고 계신가요?</h2>
        <p>
          무료 데모 시연부터 맞춤 견적까지 전문 담당자가 안내합니다.<br />
          부담 없이 문의해 주세요.
        </p>
        <div className="consult-start-actions">
          <a className="cta-primary" href={`tel:${platformConfig.contactPhone}`}>
            <Phone size={16} aria-hidden="true" /> 도입 문의 전화
          </a>
          <a className="cta-secondary" href={`mailto:${platformConfig.contactEmail}`}>
            이메일로 문의 <ArrowRight size={14} aria-hidden="true" />
          </a>
        </div>
      </section>
      </ScrollAnimate>
    </main>
  );
}
