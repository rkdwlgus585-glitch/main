import { CapabilityStrip } from "@/components/capability-strip";
import { ConsultationCTA } from "@/components/consultation-cta";
import { Hero } from "@/components/hero";
import { PlatformStatus } from "@/components/platform-status";
import { PlatformTopology } from "@/components/platform-topology";
import { PricingComparison } from "@/components/pricing-comparison";
import { ProductCard } from "@/components/product-card";
import { TrustSignals } from "@/components/trust-signals";
import { WorkflowGrid } from "@/components/workflow-grid";

export default function HomePage() {
  return (
    <main className="page-shell">
      <PlatformStatus />
      <Hero />

      {/* ── 서비스 카드 ── */}
      <section className="product-section" id="services">
        <div className="section-header">
          <p className="eyebrow">AI 서비스</p>
          <h2>무엇을 도와드릴까요?</h2>
        </div>
        <div className="product-grid">
          <ProductCard
            href="/yangdo"
            badge="무료 AI 분석"
            title="건설업 AI 양도가 산정"
            description="건설업 면허 양도가격을 공시 데이터 기반으로 산정합니다. 매물 중복 보정과 신뢰도를 함께 확인하세요."
            bullets={[
              "복합면허 매칭 오차 감점 반영",
              "중복매물 군집 보정 자동 적용",
              "산정 근거와 비교군 전량 공개",
            ]}
          />
          <ProductCard
            href="/permit"
            badge="무료 AI 진단"
            title="등록기준 AI 인허가 사전검토"
            description="건설업 등록기준 충족 여부를 항목별로 진단합니다. 부족 항목과 다음 조치를 바로 안내합니다."
            bullets={[
              "191개 업종 등록기준 전수 점검",
              "증빙 체크리스트와 다음 조치 제시",
              "자본금·기술인력·사무실·장비 종합 진단",
            ]}
          />
        </div>
      </section>

      <TrustSignals />
      <WorkflowGrid />
      <PricingComparison />
      <CapabilityStrip />
      <PlatformTopology />
      <ConsultationCTA />
    </main>
  );
}
