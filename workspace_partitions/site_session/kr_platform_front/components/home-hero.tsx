import Link from "next/link";
import { ArrowRight, Phone, PlayCircle } from "lucide-react";
import { platformConfig } from "@/components/platform-config";

const signals = [
  "실시간 매물 동선과 상담 유도를 한 화면에서 정리",
  "건설업등록, 양도양수, 실무 브리프를 같은 톤으로 통합",
  "영상형 히어로와 카드형 브리프를 조합한 운영형 메인",
];

const metrics = [
  { value: "24H", label: "상담 접수" },
  { value: "ONE", label: "메인 집중 흐름" },
  { value: "5개", label: "빠른 진입 메뉴" },
];

const briefing = [
  { title: "양도양수 브리프", body: "조건 확인, 상담 연결, 다음 액션까지 한 번에 이어집니다." },
  { title: "건설업등록 검토", body: "등록기준과 준비 항목을 메인에서 바로 진입시킵니다." },
  { title: "고객센터 동선", body: "전화, 문의, 실무 가이드를 분산 없이 묶어 둡니다." },
];

export function HomeHero() {
  return (
    <section className="home-hero">
      <div className="home-hero-grid">
        <div className="home-hero-copy">
          <p className="home-live-pill">
            <span className="home-live-dot" />
            메인 브리핑 운영 중
          </p>
          <p className="home-hero-kicker">서울건설정보 업그레이드 메인</p>
          <h1>
            건설업 양도양수와 등록 실무를
            <br />
            <span>한 화면에서 빠르게 판단하는 메인</span>
          </h1>
          <p className="home-hero-body">
            현재 메인의 강점인 현장감, 빠른 매물 진입, 상담 유도를 유지하면서
            정보 구조와 모바일 가독성을 현대적으로 다시 정리했습니다.
          </p>

          <div className="home-hero-actions">
            <Link className="cta-primary home-cta-primary" href="/mna-market">
              실시간 매물 보기
              <ArrowRight size={18} strokeWidth={2.2} />
            </Link>
            <Link className="cta-secondary home-cta-secondary" href="/consult">
              전문 상담 연결
            </Link>
            <a className="home-call-link" href={`tel:${platformConfig.contactPhone}`}>
              <Phone size={16} />
              {platformConfig.contactPhone}
            </a>
          </div>

          <ul className="home-hero-signals">
            {signals.map((signal) => (
              <li key={signal}>{signal}</li>
            ))}
          </ul>

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
              aria-label="건설 현장 분위기를 보여주는 메인 영상"
            >
              <source src="/media/hero-construction.mp4" type="video/mp4" />
            </video>
            <div className="home-video-overlay" />
            <div className="home-video-caption">
              <span className="home-video-chip">
                <PlayCircle size={16} />
                Main Visual
              </span>
              <strong>현장 분위기와 매물 브리프를 한 시선에 담는 히어로</strong>
              <p>배경 영상 위에 핵심 액션을 겹치지 않게 올려, 첫 화면에서 판단이 가능하도록 구성했습니다.</p>
            </div>
          </div>

          <div className="home-brief-panel">
            <div className="home-brief-panel-header">
              <p>오늘의 메인 운영 포인트</p>
              <strong>빠른 진입 + 신뢰감 + 상담 전환</strong>
            </div>
            <div className="home-brief-list">
              {briefing.map((item) => (
                <article key={item.title} className="home-brief-item">
                  <h2>{item.title}</h2>
                  <p>{item.body}</p>
                </article>
              ))}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
