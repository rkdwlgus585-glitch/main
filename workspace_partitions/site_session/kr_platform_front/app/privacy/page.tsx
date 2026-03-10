import type { Metadata } from "next";
import { platformConfig } from "@/components/platform-config";

export const metadata: Metadata = {
  title: "개인정보처리방침 | 서울건설정보",
  description: "서울건설정보 개인정보처리방침입니다.",
};

export default function PrivacyPage() {
  return (
    <main id="main" className="page-shell">
      <h1>개인정보처리방침</h1>

      <section>
        <h2>1. 개인정보의 수집 항목 및 목적</h2>
        <p>
          서울건설정보(이하 &quot;회사&quot;)는 AI 양도가 산정 및 AI 인허가 사전검토 서비스 제공을 위해 최소한의 정보를 수집합니다.
        </p>
        <ul>
          <li>수집 항목: 업종 선택 정보, 자본금·기술인력 등 분석 조건 입력값</li>
          <li>수집 목적: AI 분석 결과 제공, 서비스 품질 개선</li>
        </ul>
        <p>
          회사는 회원가입을 요구하지 않으며, 별도의 개인 식별 정보(이름, 연락처, 이메일 등)를 필수로 수집하지 않습니다.
        </p>
      </section>

      <section>
        <h2>2. 개인정보의 보유 및 이용 기간</h2>
        <p>
          입력된 분석 조건은 서비스 제공 후 별도의 식별 정보 없이 통계 목적으로만 보관되며, 관련 법령에서 정한 기간 동안 보존합니다.
        </p>
      </section>

      <section>
        <h2>3. 개인정보의 제3자 제공</h2>
        <p>
          회사는 이용자의 동의 없이 개인정보를 제3자에게 제공하지 않습니다. 단, 법령에 의한 요청이 있는 경우에는 예외로 합니다.
        </p>
      </section>

      <section>
        <h2>4. 개인정보의 파기</h2>
        <p>
          보유 기간이 경과하거나 처리 목적이 달성된 개인정보는 지체 없이 파기합니다. 전자적 파일 형태의 정보는 복구할 수 없는 방법으로 삭제합니다.
        </p>
      </section>

      <section>
        <h2>5. 개인정보 보호 책임자</h2>
        <p>
          개인정보 보호와 관련한 문의는 아래 연락처로 문의하시기 바랍니다.
        </p>
        <ul>
          <li>전화: {platformConfig.contactPhone}</li>
          <li>이메일: {platformConfig.contactEmail}</li>
        </ul>
      </section>

      <section>
        <h2>6. 방침의 변경</h2>
        <p>
          본 개인정보처리방침은 관련 법령 및 내부 정책 변경에 따라 수정될 수 있으며, 변경 시 서비스 내 공지를 통해 안내합니다.
        </p>
      </section>

      <p className="legal-effective-date">시행일: 2026년 3월 1일</p>
    </main>
  );
}
