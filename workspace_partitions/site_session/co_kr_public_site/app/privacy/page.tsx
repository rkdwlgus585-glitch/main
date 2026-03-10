import type { Metadata } from "next";
import { Breadcrumbs } from "@/components/breadcrumbs";
import { buildPageMetadata } from "@/lib/page-metadata";

export const metadata: Metadata = buildPageMetadata(
  "/privacy",
  "개인정보처리방침",
  "상담형 퍼블릭 사이트 운영을 위한 기본 개인정보처리방침 페이지입니다.",
  { indexable: false },
);

const sections = [
  {
    title: "수집 항목",
    body: "전화, 이메일, 상담 과정에서 자발적으로 제공한 회사명, 담당자명, 연락처, 상담 내용이 포함될 수 있습니다.",
  },
  {
    title: "이용 목적",
    body: "양도양수 상담, 건설업등록 검토, 법인 및 구조 검토, 고객 문의 응대, 운영 공지 전달 목적으로만 사용합니다.",
  },
  {
    title: "보관 기간",
    body: "상담 이력과 관련 자료는 법령 또는 내부 운영 기준에 따라 필요한 기간 동안만 보관하며, 보관 목적이 종료되면 지체 없이 파기합니다.",
  },
  {
    title: "제3자 제공",
    body: "법령상 의무가 있는 경우를 제외하고, 고객 동의 없이 제3자에게 제공하지 않습니다. 외부 전문가와 협업이 필요한 경우 사전 안내 후 진행합니다.",
  },
];

export default function PrivacyPage() {
  return (
    <div className="page-shell page-shell--inner">
      <Breadcrumbs items={[{ href: "/", label: "홈" }, { href: "/privacy", label: "개인정보처리방침" }]} />
      <section className="inner-hero">
        <p className="eyebrow">Privacy Policy</p>
        <h1>개인정보처리방침</h1>
        <p>독립 퍼블릭 사이트 운영 시 필요한 기본 개인정보처리 원칙입니다. 실제 운영 전에는 법률 검토를 거쳐 최종 문안으로 확정해야 합니다.</p>
      </section>

      <section className="legal-section-list">
        {sections.map((section) => (
          <article key={section.title} className="legal-card">
            <h2>{section.title}</h2>
            <p>{section.body}</p>
          </article>
        ))}
      </section>
    </div>
  );
}
