import type { Metadata } from "next";
import { Breadcrumbs } from "@/components/breadcrumbs";
import { buildPageMetadata } from "@/lib/page-metadata";

export const metadata: Metadata = buildPageMetadata(
  "/terms",
  "이용약관",
  "건설업 상담형 퍼블릭 사이트의 기본 이용조건과 면책 범위를 안내하는 페이지입니다.",
  { indexable: false },
);

const terms = [
  {
    title: "서비스 성격",
    body: "이 사이트는 건설업 양도양수 및 등록 실무에 관한 안내와 상담 접수를 제공하는 정보형 퍼블릭 사이트입니다.",
  },
  {
    title: "정보의 한계",
    body: "사이트에 표시된 매물 정보, 실무 설명, 상담 안내는 참고용이며 실제 계약과 거래 조건은 실사 및 별도 협의로 확정됩니다.",
  },
  {
    title: "상담 신청",
    body: "전화, 이메일, 카카오 등으로 문의한 내용은 상담 목적 범위 안에서 검토되며, 구체적인 계약 또는 위임은 별도 문서로 체결해야 합니다.",
  },
  {
    title: "면책",
    body: "운영자는 외부 환경 변화, 법령 개정, 고객 제공 정보의 오류로 인해 발생하는 결과에 대해 즉시 확정 책임을 부담하지 않으며, 최종 판단은 별도 검토가 필요합니다.",
  },
];

export default function TermsPage() {
  return (
    <div className="page-shell page-shell--inner">
      <Breadcrumbs items={[{ href: "/", label: "홈" }, { href: "/terms", label: "이용약관" }]} />
      <section className="inner-hero">
        <p className="eyebrow">Terms</p>
        <h1>이용약관</h1>
        <p>상담형 퍼블릭 사이트에서 기본적으로 표시해야 할 이용조건입니다. 실제 운영 전 최종 문안을 검토해 반영해야 합니다.</p>
      </section>

      <section className="legal-section-list">
        {terms.map((section) => (
          <article key={section.title} className="legal-card">
            <h2>{section.title}</h2>
            <p>{section.body}</p>
          </article>
        ))}
      </section>
    </div>
  );
}
