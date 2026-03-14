# Content Preservation Policy

Date: 2026-03-11
Project: `co_kr_public_site`

## Core Rule

현재 `seoulmna.co.kr`에 발행된 공개 글과 정적 안내 페이지는 모두 가져오고, 원문 컨텐츠는 유지한다.

여기서 유지의 의미는 다음과 같다.

- 게시글 본문을 임의로 다시 쓰지 않는다.
- 제목, 요약, 발행일, 조회수, 본문 HTML, 자산 경로를 최대한 원문 기준으로 보존한다.
- 사이트 구조는 현대화할 수 있지만, 컨텐츠 누락은 허용하지 않는다.

## Current Imported Scope

기준 파일: `data/imported/manifest.json`

- `mna` legacy board import: 1701
- `mna` Google Sheet snapshot: 1701
- `notice`: 349
- `premium`: 35
- `news`: 1
- `tl_faq`: 1
- `pages`: 26

## Source of Truth

아래 경로가 퍼블릭 사이트 컨텐츠의 기준이다.

- `data/imported/listing-summaries.json`
- `data/imported/listing-details.json`
- `data/imported/listing-sheet-rows.json`
- `data/imported/notice-posts.json`
- `data/imported/premium-posts.json`
- `data/imported/news-posts.json`
- `data/imported/tl-faq-page.json`
- `data/imported/pages.json`
- `public/imported-assets/`

## Allowed Changes

허용되는 변경:

- 라우팅 현대화
- 레거시 내부 링크를 새 경로로 정규화
- 중복 제목을 slug로 구분해 탐색성 개선
- 메타데이터, schema, sitemap 보강
- 모바일/접근성/성능 개선

허용되지 않는 변경:

- 게시글 본문 대량 재작성
- 원문 게시글 삭제
- 자산 누락
- 이유 없는 slug 변경

## Refresh Workflow

원문 사이트의 공개 글이 늘어나거나 수정되면 아래 명령으로 다시 동기화한다.

```bash
npm run import:legacy
```

## Review Checklist

동기화 후 아래를 반드시 확인한다.

1. `manifest.json` 수량이 기대치와 맞는가
2. `/notice`, `/premium`, `/news`, `/tl_faq`, `/pages/*.php`, `/mna/*`가 모두 열리는가
3. 본문 안 레거시 링크가 새 경로로 연결되는가
4. imported assets가 깨지지 않았는가
5. sitemap에 세부 URL이 포함되는가

## Future Rule

나중에 CMS나 DB를 붙여도, 초기 마이그레이션 원문 데이터는 계속 보존한다. 운영 데이터 저장소가 바뀌더라도 `data/imported`는 백업 겸 기준 사본으로 남긴다.
