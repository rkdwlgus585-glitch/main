import type { Metadata } from "next";
import Link from "next/link";
import { AiToolBridge } from "@/components/ai-tool-bridge";
import { Breadcrumbs } from "@/components/breadcrumbs";
import { ContactLink } from "@/components/contact-link";
import { SupportForm } from "@/components/support-form";
import { faqs, notices } from "@/components/sample-data";
import { siteConfig } from "@/components/site-config";
import { buildPageMetadata } from "@/lib/page-metadata";

export const metadata: Metadata = buildPageMetadata(
  "/support",
  "고객센터",
  "전화, 이메일, 카카오 채널과 함께 구조화된 문의 접수 폼을 제공하는 고객센터 페이지입니다.",
);

const intakeHighlights = [
  "양도양수, 등록, 법인설립, 분할합병 문의를 같은 흐름에서 정리",
  "문의 목적과 연락처를 함께 받아 후속 응대 누락을 줄이는 구조",
  "개인정보처리방침 동의와 스팸 억제를 반영한 기본 상담 폼",
];

export default function SupportPage() {
  const faqSchema = {
    "@context": "https://schema.org",
    "@type": "FAQPage",
    mainEntity: faqs.map((faq) => ({
      "@type": "Question",
      name: faq.question,
      acceptedAnswer: {
        "@type": "Answer",
        text: faq.answer,
      },
    })),
  };

  return (
    <div className="page-shell page-shell--inner">
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(faqSchema) }}
      />
      <Breadcrumbs items={[{ href: "/", label: "홈" }, { href: "/support", label: "고객센터" }]} />
      <section className="inner-hero">
        <p className="eyebrow">Customer Support</p>
        <h1>고객센터</h1>
        <p>독립 퍼블릭 사이트에서 가장 중요한 것은 문의 동선입니다. 전화, 모바일, 이메일, 카카오 채널을 명확하게 보여줍니다.</p>
      </section>

      <section className="support-intake-shell">
        <div className="support-intake-copy">
          <p className="eyebrow">Structured Intake</p>
          <h2>전화 전에 남길 내용을 먼저 정리할 수 있습니다</h2>
          <p>
            고객센터는 단순 연락처 노출에서 끝나지 않고, 상담 목적과 현재 상황을 같이 남길 수 있는 구조로 설계했습니다.
            초기 접수 정보가 정리되면 후속 응대 품질과 속도가 같이 올라갑니다.
          </p>

          <div className="support-intake-list">
            {intakeHighlights.map((item) => (
              <article key={item}>
                <strong>{item}</strong>
              </article>
            ))}
          </div>

          <div className="support-intake-meta">
            <strong>운영 기준</strong>
            <p>{siteConfig.officeHours}</p>
            <p>긴급 건은 대표전화 또는 직통상담을 우선 이용해 주세요.</p>
          </div>
        </div>

        <SupportForm />
      </section>

      <section className="support-card-grid">
        <article className="support-card">
          <strong>대표전화</strong>
          <ContactLink href={`tel:${siteConfig.phone}`} eventName="click_phone" eventLabel="support_phone">
            {siteConfig.phone}
          </ContactLink>
          <p>운영 시간 중 가장 먼저 연결되는 기본 채널입니다.</p>
        </article>
        <article className="support-card">
          <strong>직통상담</strong>
          <ContactLink href={`tel:${siteConfig.mobile}`} eventName="click_mobile" eventLabel="support_mobile">
            {siteConfig.mobile}
          </ContactLink>
          <p>긴급하거나 구체적인 상담이 필요한 경우를 위한 채널입니다.</p>
        </article>
        <article className="support-card">
          <strong>이메일</strong>
          <ContactLink href={`mailto:${siteConfig.email}`} eventName="click_email" eventLabel="support_email">
            {siteConfig.email}
          </ContactLink>
          <p>서류 검토나 정리된 문의를 받을 때 적합합니다.</p>
        </article>
        <article className="support-card">
          <strong>카카오 문의</strong>
          <ContactLink href={siteConfig.kakaoUrl} eventName="click_kakao" eventLabel="support_kakao" newTab>
            카카오 오픈채팅 이동
          </ContactLink>
          <p>운영 시 실제 채널 주소로 교체하면 됩니다.</p>
        </article>
      </section>

      <section className="section-block">
        <div className="section-header">
          <p className="eyebrow">FAQ</p>
          <h2>가장 자주 나오는 질문</h2>
        </div>
        <div className="faq-list">
          {faqs.map((faq) => (
            <article key={faq.question} className="faq-card">
              <h2>{faq.question}</h2>
              <p>{faq.answer}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="section-block">
        <div className="section-header">
          <p className="eyebrow">Recent Notice</p>
          <h2>운영 공지</h2>
        </div>
        <div className="notice-grid">
          {notices.map((notice) => (
            <article key={notice.title} className="notice-card">
              <span>{notice.date}</span>
              <h3>{notice.title}</h3>
              <p>{notice.summary}</p>
            </article>
          ))}
        </div>
      </section>

      <AiToolBridge variant="full" />

      <section className="inner-cta">
        <h2>상담 전에 AI 도구로 미리 확인하면 더 정확한 안내를 받을 수 있습니다</h2>
        <p>이 사이트에서 상담을 받기 전, 서울건설정보의 무료 AI 도구로 양도가 범위나 등록 기준을 먼저 확인해 보세요.</p>
        <Link className="cta-primary" href="/">
          메인으로 돌아가기
        </Link>
      </section>
    </div>
  );
}
