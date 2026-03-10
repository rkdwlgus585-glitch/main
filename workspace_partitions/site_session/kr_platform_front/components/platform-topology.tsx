/**
 * Platform topology — kept as a lightweight data-disclosure section
 * for transparency (superlawyer.co.kr pattern). Rewritten for user-facing language.
 */
export function PlatformTopology() {
  return (
    <section className="disclosure-section">
      <div className="section-header">
        <p className="eyebrow">데이터 출처</p>
        <h2>어디서 데이터를 가져오나요?</h2>
      </div>
      <div className="disclosure-grid">
        <article className="disclosure-card">
          <strong>건설산업기본법</strong>
          <p>업종별 등록기준, 자본금, 기술인력 요건의 법적 근거</p>
        </article>
        <article className="disclosure-card">
          <strong>건설산업정보시스템</strong>
          <p>건설업 면허 현황, 업종 분류, 공시 정보 수집</p>
        </article>
        <article className="disclosure-card">
          <strong>공개 매물 네트워크</strong>
          <p>다수 중개 채널의 매물 데이터를 수집하여 중복 보정</p>
        </article>
      </div>
    </section>
  );
}
