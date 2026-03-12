import type { Metadata } from "next";
import { platformConfig } from "@/components/platform-config";

const pageTitle = "개인정보처리방침 | 서울건설정보";
const pageDescription = "서울건설정보 개인정보처리방침입니다.";

export const metadata: Metadata = {
  title: pageTitle,
  description: pageDescription,
  alternates: { canonical: "/privacy" },
  openGraph: {
    title: pageTitle,
    description: pageDescription,
    url: "/privacy",
    type: "website",
    locale: "ko_KR",
  },
  twitter: {
    card: "summary",
    title: pageTitle,
    description: pageDescription,
  },
};

export default function PrivacyPage() {
  return (
    <main id="main" className="page-shell legal-page">
      <h1>개인정보처리방침</h1>

      <p>
        서울건설정보(이하 &quot;회사&quot;)는 개인정보보호법,
        정보통신망 이용촉진 및 정보보호 등에 관한 법률 등 관련
        법령을 준수하며, 회원의 개인정보를 보호하기 위해 다음과
        같이 개인정보처리방침을 수립·공개합니다.
      </p>

      <section>
        <h2>1. 개인정보의 수집 항목 및 수집 방법</h2>
        <h3>가. 필수 수집 항목</h3>
        <table className="legal-table">
          <thead>
            <tr>
              <th>수집 시점</th>
              <th>수집 항목</th>
              <th>수집 목적</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>회원가입 (소셜 로그인)</td>
              <td>이메일, 이름(닉네임), 프로필 이미지, 소셜 계정 고유 식별자</td>
              <td>회원 식별, 서비스 제공, 고객 상담</td>
            </tr>
            <tr>
              <td>회원가입 (휴대전화 인증)</td>
              <td>휴대전화 번호, 본인인증 결과(CI/DI)</td>
              <td>본인 확인, 회원 식별, 서비스 제공</td>
            </tr>
            <tr>
              <td>서비스 이용 시</td>
              <td>업종 선택 정보, 자본금·기술인력 등 분석 조건 입력값</td>
              <td>AI 분석 결과 제공, 서비스 품질 개선</td>
            </tr>
          </tbody>
        </table>

        <h3>나. 자동 수집 항목</h3>
        <p>
          접속 일시, IP 주소, 브라우저 종류, 기기 정보, 서비스
          이용 기록이 자동으로 수집됩니다.
        </p>

        <h3>다. 수집 방법</h3>
        <ul>
          <li>카카오, 네이버, 구글 소셜 로그인 API를 통한 수집</li>
          <li>휴대전화 본인인증 서비스를 통한 수집</li>
          <li>서비스 이용 과정에서의 자동 수집</li>
        </ul>
      </section>

      <section>
        <h2>2. 개인정보의 이용 목적</h2>
        <ul>
          <li>회원 관리: 가입 의사 확인, 본인 확인, 회원 식별, 탈퇴 처리</li>
          <li>서비스 제공: AI 양도가 산정, AI 인허가 사전검토 결과 제공</li>
          <li>상담 연결: 전문 행정사 상담 시 회원 정보 활용</li>
          <li>서비스 개선: 이용 통계 분석, 서비스 품질 향상</li>
          <li>고지사항 전달: 약관 변경, 서비스 변경 안내</li>
          <li>부정이용 방지: 자동화 접근 탐지, 비정상 이용 차단</li>
        </ul>
      </section>

      <section>
        <h2>3. 개인정보의 보유 및 이용 기간</h2>
        <p>
          회원 탈퇴 시 지체 없이 파기합니다. 단, 관련 법령에 따라
          다음 정보는 해당 기간 동안 보존합니다.
        </p>
        <table className="legal-table">
          <thead>
            <tr>
              <th>보존 항목</th>
              <th>보존 기간</th>
              <th>근거 법령</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>계약·청약 철회 기록</td>
              <td>5년</td>
              <td>전자상거래법</td>
            </tr>
            <tr>
              <td>소비자 불만·분쟁 처리 기록</td>
              <td>3년</td>
              <td>전자상거래법</td>
            </tr>
            <tr>
              <td>접속 기록(로그)</td>
              <td>3개월</td>
              <td>통신비밀보호법</td>
            </tr>
          </tbody>
        </table>
      </section>

      <section>
        <h2>4. 개인정보의 제3자 제공</h2>
        <p>
          회사는 이용자의 동의 없이 개인정보를 제3자에게 제공하지
          않습니다. 단, 다음의 경우는 예외로 합니다.
        </p>
        <ul>
          <li>법령에 의한 수사·재판 등 요청이 있는 경우</li>
          <li>이용자가 사전에 동의한 경우</li>
        </ul>
      </section>

      <section>
        <h2>5. 개인정보 처리 위탁</h2>
        <table className="legal-table">
          <thead>
            <tr>
              <th>수탁 업체</th>
              <th>위탁 업무</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>카카오</td>
              <td>소셜 로그인 인증</td>
            </tr>
            <tr>
              <td>네이버</td>
              <td>소셜 로그인 인증</td>
            </tr>
            <tr>
              <td>구글</td>
              <td>소셜 로그인 인증</td>
            </tr>
            <tr>
              <td>Cloudflare</td>
              <td>봇 탐지(Turnstile CAPTCHA), CDN 서비스</td>
            </tr>
            <tr>
              <td>Vercel</td>
              <td>웹 호스팅 및 서버 운영</td>
            </tr>
          </tbody>
        </table>
      </section>

      <section>
        <h2>6. 개인정보의 파기</h2>
        <ol>
          <li>
            보유 기간이 경과하거나 처리 목적이 달성된 개인정보는
            지체 없이 파기합니다.
          </li>
          <li>
            전자적 파일 형태의 정보는 복구할 수 없는 방법으로
            영구 삭제합니다.
          </li>
          <li>
            종이 문서에 기록된 정보는 분쇄하거나 소각하여
            파기합니다.
          </li>
        </ol>
      </section>

      <section>
        <h2>7. 이용자의 권리와 행사 방법</h2>
        <ol>
          <li>
            회원은 언제든지 자신의 개인정보를 열람, 정정, 삭제,
            처리 정지 요청할 수 있습니다.
          </li>
          <li>
            회원 탈퇴를 통해 개인정보 삭제를 요청할 수 있으며,
            회사는 지체 없이 처리합니다.
          </li>
          <li>
            권리 행사는 서비스 내 설정 또는 아래 연락처를 통해
            가능합니다.
          </li>
        </ol>
      </section>

      <section>
        <h2>8. 개인정보의 안전성 확보 조치</h2>
        <ul>
          <li>개인정보의 암호화 저장 및 전송</li>
          <li>접근 권한 관리 및 접근 통제</li>
          <li>보안 프로그램 설치 및 주기적 갱신</li>
          <li>개인정보 접근 기록 보관</li>
        </ul>
      </section>

      <section>
        <h2>9. 쿠키 및 행동정보 수집</h2>
        <h3>가. 쿠키 사용 목적</h3>
        <ul>
          <li>로그인 상태 유지 및 세션 관리</li>
          <li>서비스 이용 통계 분석 (방문 빈도, 이용 패턴)</li>
          <li>보안 검증 (Cloudflare Turnstile CAPTCHA)</li>
        </ul>
        <h3>나. 행동정보 수집 및 거부 방법</h3>
        <p>
          회사는 서비스 개선을 위해 페이지 방문 기록,
          클릭 패턴 등 이용 행태 정보를 수집할 수 있습니다.
          회원은 다음 방법으로 쿠키 저장 및 행동정보 수집을
          거부할 수 있습니다.
        </p>
        <ul>
          <li>
            브라우저 설정에서 쿠키 차단: 설정 &gt; 개인정보
            &gt; 쿠키 및 사이트 데이터에서 차단 설정
          </li>
          <li>
            광고식별자 초기화: 모바일 기기 설정에서
            광고식별자를 재설정하거나 추적 거부 가능
          </li>
        </ul>
        <p>
          쿠키를 거부하면 로그인이 필요한 일부 서비스
          이용에 제한이 있을 수 있습니다.
        </p>
      </section>

      <section>
        <h2>10. 자동화된 의사결정</h2>
        <p>
          회사는 AI 기반 양도가 산정 및 인허가 사전검토
          서비스에서 자동화된 의사결정을 수행합니다.
        </p>
        <ul>
          <li>
            <strong>양도가 산정:</strong> 공시 실적 데이터와
            시장 거래 패턴을 기반으로 AI가 적정 가격 범위를
            자동 산출합니다.
          </li>
          <li>
            <strong>인허가 사전검토:</strong> 입력된 자본금,
            기술인력 등의 정보를 등록기준과 자동 대조하여
            충족 여부를 판정합니다.
          </li>
        </ul>
        <p>
          위 자동화 결과는 참고용이며 법적 효력이 있는
          공식 판정이 아닙니다. 회원은 자동화된 결과에
          대해 설명을 요구하거나, 전문가 상담을 통해
          재검토를 요청할 수 있습니다.
        </p>
      </section>

      <section>
        <h2>11. 개인정보 전송요구권 (데이터 이동권)</h2>
        <p>
          회원은 개인정보 보호법 제35조의2에 따라 본인의
          개인정보를 본인 또는 제3자에게 전송하도록 요구할
          수 있습니다. 전송 가능한 정보의 범위, 형식 등
          세부 사항은 관련 시행령에서 정하는 바에 따릅니다.
        </p>
        <p>
          전송요구는 서비스 내 설정 또는 아래 연락처를
          통해 신청할 수 있으며, 회사는 관련 법령이 정하는
          기한 내에 처리합니다.
        </p>
      </section>

      <section>
        <h2>12. 14세 미만 아동의 개인정보</h2>
        <p>
          회사는 14세 미만 아동의 회원가입을 제한하고 있습니다.
          본 서비스는 건설업 전문 분석 서비스로서 사업자 및
          성인 실무자를 대상으로 합니다.
        </p>
      </section>

      <section>
        <h2>13. 개인정보 보호 책임자</h2>
        <ul>
          <li>성명: 강지현</li>
          <li>직위: 대표</li>
          <li>전화: {platformConfig.contactPhone}</li>
          <li>이메일: {platformConfig.contactEmail}</li>
        </ul>
        <p>
          개인정보 침해에 관한 상담이 필요한 경우
          한국인터넷진흥원(KISA) 개인정보침해신고센터(118),
          개인정보분쟁조정위원회(1833-6972)에 문의하실 수
          있습니다.
        </p>
      </section>

      <section>
        <h2>14. 방침의 변경</h2>
        <p>
          본 개인정보처리방침은 관련 법령 및 내부 정책 변경에
          따라 수정될 수 있으며, 변경 시 서비스 내 공지를 통해
          안내합니다. 이전 방침은 아카이브에서 확인할 수
          있습니다.
        </p>
      </section>

      <p className="legal-effective-date">
        시행일: <time dateTime="2026-03-12">2026년 3월 12일</time>
      </p>
      <p className="legal-contact">
        문의: {platformConfig.contactPhone} ·{" "}
        {platformConfig.contactEmail}
      </p>
    </main>
  );
}
