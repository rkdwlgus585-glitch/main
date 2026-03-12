import type { Metadata } from "next";

const pageTitle = "이용약관 | 서울건설정보";
const pageDescription = "서울건설정보 서비스 이용약관입니다.";

export const metadata: Metadata = {
  title: pageTitle,
  description: pageDescription,
  alternates: { canonical: "/terms" },
  openGraph: {
    title: pageTitle,
    description: pageDescription,
    url: "/terms",
    type: "website",
    locale: "ko_KR",
  },
  twitter: {
    card: "summary",
    title: pageTitle,
    description: pageDescription,
  },
};

export default function TermsPage() {
  return (
    <main id="main" className="page-shell">
      <h1>이용약관</h1>

      <section>
        <h2>제1조 (목적)</h2>
        <p>
          본 약관은 서울건설정보(이하 &quot;회사&quot;)가 제공하는 AI 양도가 산정 서비스 및 AI 인허가 사전검토 서비스(이하 &quot;서비스&quot;)의 이용과 관련하여 회사와 이용자 간의 권리·의무 및 기타 필요한 사항을 규정합니다.
        </p>
      </section>

      <section>
        <h2>제2조 (서비스 내용)</h2>
        <p>회사는 다음의 서비스를 제공합니다.</p>
        <ul>
          <li>AI 양도가 산정: 건설업 면허 양도가격을 공시 데이터 기반으로 산정하는 서비스</li>
          <li>AI 인허가 사전검토: 건설업 및 유사 업종의 등록기준 충족 여부를 점검하고 신규 취득 비용을 계산하는 서비스</li>
        </ul>
      </section>

      <section>
        <h2>제3조 (면책 조항)</h2>
        <p>
          본 서비스의 AI 분석 결과는 참고용이며, 법적 효력이 있는 공식 감정 결과가 아닙니다. 정확한 양도가 확정, 신규 등록 비용 및 인허가 절차는 반드시 전문가와 상담하시기 바랍니다. 회사는 서비스 이용으로 인해 발생하는 직접적·간접적 손해에 대해 책임을 지지 않습니다.
        </p>
      </section>

      <section>
        <h2>제4조 (지적재산권)</h2>
        <p>
          본 서비스의 AI 분석 알고리즘, 데이터 처리 방법론, 소프트웨어 및 관련 기술은 회사의 지적재산으로서 특허 출원 중이며, 관련 법률에 의해 보호됩니다.
        </p>
      </section>

      <section>
        <h2>제5조 (약관의 변경)</h2>
        <p>
          회사는 관련 법령에 위배되지 않는 범위에서 본 약관을 변경할 수 있으며, 변경 시 서비스 내 공지를 통해 안내합니다.
        </p>
      </section>

      <p className="legal-effective-date">시행일: <time dateTime="2026-03-01">2026년 3월 1일</time></p>
    </main>
  );
}
