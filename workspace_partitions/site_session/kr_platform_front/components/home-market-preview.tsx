"use client";

import Link from "next/link";
import { useState } from "react";

type Listing = {
  code: string;
  status: string;
  sector: string;
  region: string;
  licenseYear: number;
  performance: string;
  note: string;
  price: string;
};

const listings: Listing[] = [
  {
    code: "SM-2401",
    status: "가능",
    sector: "실내건축",
    region: "수도권",
    licenseYear: 2018,
    performance: "3년 18억",
    note: "재무정리 완료 · 상담 우선",
    price: "협의",
  },
  {
    code: "SM-2407",
    status: "검토중",
    sector: "건축",
    region: "영남",
    licenseYear: 2014,
    performance: "3년 74억",
    note: "법인 이력 깔끔 · 실적 우수",
    price: "6.8억",
  },
  {
    code: "SM-2412",
    status: "가능",
    sector: "토목",
    region: "충청",
    licenseYear: 2016,
    performance: "3년 26억",
    note: "잔액 안정 · 기술자 이관 용이",
    price: "협의",
  },
  {
    code: "SM-2418",
    status: "가능",
    sector: "전기",
    region: "호남",
    licenseYear: 2020,
    performance: "3년 11억",
    note: "무리 없는 인수 구조",
    price: "2.4억",
  },
  {
    code: "SM-2420",
    status: "가능",
    sector: "조경",
    region: "수도권",
    licenseYear: 2021,
    performance: "3년 8억",
    note: "신규 확장용으로 적합",
    price: "1.9억",
  },
  {
    code: "SM-2426",
    status: "협의중",
    sector: "기계설비",
    region: "영남",
    licenseYear: 2017,
    performance: "3년 22억",
    note: "조합 상태 안정",
    price: "4.2억",
  },
];

const sectors = ["전체", "건축", "토목", "실내건축", "전기", "조경", "기계설비"] as const;
const regions = ["전체", "수도권", "충청", "영남", "호남"] as const;

export function HomeMarketPreview() {
  const [sector, setSector] = useState<(typeof sectors)[number]>("전체");
  const [region, setRegion] = useState<(typeof regions)[number]>("전체");

  const filtered = listings.filter((listing) => {
    const sectorMatch = sector === "전체" || listing.sector === sector;
    const regionMatch = region === "전체" || listing.region === region;
    return sectorMatch && regionMatch;
  });

  return (
    <section className="market-brief-section" id="market-brief">
      <div className="market-brief-header">
        <div className="section-header">
          <p className="eyebrow">Market Brief</p>
          <h2>게시판형 매물 탐색을 더 읽기 쉬운 브리프로 재정리</h2>
        </div>
        <div className="market-brief-note">
          <strong>운영형 메인 포인트</strong>
          <p>필터 감성은 유지하고, 실제 사용자가 빠르게 읽는 정보만 앞에 배치했습니다.</p>
        </div>
      </div>

      <div className="market-brief-grid">
        <aside className="market-filter-card" aria-label="대표 필터">
          <div className="market-filter-group">
            <p>업종</p>
            <div className="market-filter-chips">
              {sectors.map((item) => (
                <button
                  key={item}
                  type="button"
                  className={`market-chip${item === sector ? " market-chip--active" : ""}`}
                  onClick={() => setSector(item)}
                >
                  {item}
                </button>
              ))}
            </div>
          </div>

          <div className="market-filter-group">
            <p>지역</p>
            <div className="market-filter-chips">
              {regions.map((item) => (
                <button
                  key={item}
                  type="button"
                  className={`market-chip${item === region ? " market-chip--active" : ""}`}
                  onClick={() => setRegion(item)}
                >
                  {item}
                </button>
              ))}
            </div>
          </div>

          <div className="market-filter-summary">
            <strong>{filtered.length}건 브리프 표시</strong>
            <span>현재 화면은 메인 UI용 대표 유형 예시입니다.</span>
          </div>
        </aside>

        <div className="market-list-card">
          <div className="market-list-head" aria-hidden="true">
            <span>등록번호</span>
            <span>상태</span>
            <span>업종</span>
            <span>면허년도</span>
            <span>핵심 메모</span>
            <span>양도가</span>
          </div>

          <div className="market-list-body">
            {filtered.map((listing) => (
              <article key={listing.code} className="market-row">
                <div className="market-row-code">
                  <strong>{listing.code}</strong>
                  <small>{listing.region}</small>
                </div>
                <div className="market-row-status">
                  <span className={`market-status market-status--${listing.status}`}>
                    {listing.status}
                  </span>
                </div>
                <div className="market-row-sector">
                  <strong>{listing.sector}</strong>
                  <small>{listing.performance}</small>
                </div>
                <div className="market-row-year">{listing.licenseYear}</div>
                <div className="market-row-note">{listing.note}</div>
                <div className="market-row-price">{listing.price}</div>
              </article>
            ))}
          </div>

          <div className="market-list-foot">
            <p>대표 유형을 빠르게 훑은 뒤 전체 화면으로 이동하는 흐름을 의도했습니다.</p>
            <Link href="/mna-market">전체 매물 화면 보기</Link>
          </div>
        </div>
      </div>
    </section>
  );
}
