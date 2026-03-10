import type { Metadata } from "next";
import { LegacyContentPage } from "@/components/legacy-content-page";
import { getFaqPage, getFaqPreviewItems } from "@/lib/legacy-content";
import { buildPageMetadata } from "@/lib/page-metadata";

export const revalidate = 3600;

export const metadata: Metadata = buildPageMetadata(
  "/tl_faq",
  "자주하는 질문",
  "건설업 등록과 양도양수 실무에서 자주 묻는 질문을 정리한 FAQ 페이지입니다.",
);

export default function FaqPage() {
  const faqPage = getFaqPage();
  const faqItems = getFaqPreviewItems(10);
  const faqSchema = {
    "@context": "https://schema.org",
    "@type": "FAQPage",
    mainEntity: faqItems.map((item) => ({
      "@type": "Question",
      name: item.question,
      acceptedAnswer: {
        "@type": "Answer",
        text: item.answer,
      },
    })),
  };

  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(faqSchema) }}
      />
      <LegacyContentPage
        breadcrumbs={[
          { href: "/", label: "홈" },
          { href: "/tl_faq", label: "자주하는 질문" },
        ]}
        eyebrow="FAQ"
        title="자주하는 질문"
        description={faqPage.summary}
        publishedAt={faqPage.publishedAt}
        updatedAt={faqPage.updatedAt}
        contentHtml={faqPage.contentHtml}
      />
    </>
  );
}
