# co_kr_public_site

`seoulmna.kr`와 분리된 독립 퍼블릭 운영 사이트입니다.

## 목적

- 건설업 양도양수, 건설업등록, 법인설립, 분할합병, 건설실무, 고객센터를 안내하는 공개용 사이트
- 상담 유도와 정보 제공이 우선이며, AI 시스템용 사이트와 역할을 섞지 않음

## 실행

```bash
npm install
npm run export:listings:sheet
npm run dev
npm run lint
```

기본 로컬 주소:

```bash
http://127.0.0.1:3000
```

## 환경 변수

`.env.example`를 참고해 실제 회사 정보와 연락처를 넣습니다.

중요 항목:

- `NEXT_PUBLIC_SITE_HOST`
- `NEXT_PUBLIC_REPRESENTATIVE_NAME`
- `NEXT_PUBLIC_BUSINESS_NUMBER`
- `NEXT_PUBLIC_MAIL_ORDER_NUMBER`
- `NEXT_PUBLIC_CONTACT_PHONE`
- `NEXT_PUBLIC_CONTACT_EMAIL`
- `NEXT_PUBLIC_KAKAO_URL`
- `NEXT_PUBLIC_GA_MEASUREMENT_ID`
- `CONSULT_WEBHOOK_URL` (선택, 문의를 외부 CRM/자동화로 전달할 때)

주의:

- `NEXT_PUBLIC_SITE_HOST`가 `example.com` 계열 기본값이면 사이트는 자동으로 `noindex`와 `robots disallow` 상태로 동작합니다.
- 실제 운영 도메인으로 바꾸면 인덱싱이 활성화됩니다.

## 데이터 교체 지점

- 매물 샘플 데이터: `components/sample-data.ts`
- 샘플 매물 갱신 시각: `components/sample-data.ts`의 `updatedAt`
- 브랜드/법인/연락처 설정: `components/site-config.ts`
- 매물 접근 추상화: `lib/listings.ts`
- 공개 게시판 보존본 갱신: `npm run import:legacy`
- 구글시트 원본 매물 스냅샷 갱신: `npm run export:listings:sheet`

현재 포함된 기본 기능:

- 영상 히어로 메인
- 매물 검색 및 업종/지역 필터
- 매물 상세 페이지 `/mna/[id]`
- 고객센터, FAQ, 공지, 개인정보처리방침, 이용약관
- 구조화된 문의 접수 API `/api/consult`
- robots, sitemap, manifest, OG 이미지, LocalBusiness/Breadcrumb JSON-LD
- route-level SEO 메타데이터, `humans.txt`, `favicon.ico`, PWA 아이콘
- 기본 보안 응답 헤더 (`nosniff`, `DENY`, `Referrer-Policy`, `Permissions-Policy`)
- 매물 상세 canonical 정규화와 1시간 단위 ISR 재검증
- 공개 게시판 보존본과 구글시트 원본을 병합한 매물 목록

## 문의 저장 방식

- 기본 구현에서는 고객센터 문의가 `data/consult-inquiries.ndjson`에 줄 단위 JSON으로 저장됩니다.
- 이 파일은 Git에서 제외되며, 초기 디렉터리 유지를 위해 `data/.gitkeep`만 보관합니다.
- `CONSULT_WEBHOOK_URL`을 설정하면 저장 후 외부 CRM, Make, Zapier, 사내 API 등으로도 동시에 전달할 수 있습니다.
- 실운영 단계에서는 이 저장 지점을 메일, CRM, 데이터베이스로 교체하는 것이 권장됩니다.

## 다음 단계 권장

1. 매물 데이터를 DB 또는 CMS로 교체
2. 고객센터 문의 저장을 메일, CRM, DB 중 하나로 연결
3. 카카오 채널, 사업자 정보, 실제 주소를 운영값으로 교체

## 매물 원본 규칙

- `notice`, `premium`, `news`, 정적 안내 페이지는 공개 게시판 보존본을 유지합니다.
- `/mna` 매물은 공개 게시판 보존본을 유지하면서도, 노출 기준은 구글시트 원본 스냅샷을 우선합니다.
- 시트에만 있고 공개 게시판에 없는 매물은 synthetic detail로 노출되며, 공개 게시판 본문이 존재하는 매물은 해당 보존본 위에 시트 최신 상태를 덮어씁니다.
