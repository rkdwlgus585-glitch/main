# Architecture Scorecard

Date: 2026-03-11
Project: `co_kr_public_site`

## Goal

`seoulmna.co.kr`를 벤치마킹하되, 구조를 그대로 복제하지 않고 최신 기술 적용이 실제로 더 유리한 경우에만 반영한다. 단, 현재 발행된 게시글과 정적 안내 컨텐츠는 모두 유지한다.

## Candidates

1. `Next.js 16 App Router` + TypeScript + imported JSON/assets
2. `PHP 8.4 + Laravel 12` + Blade + imported data or DB

## Weighted Score

| Criterion | Weight | Next.js 16 | Laravel 12 / PHP 8.4 | Why it matters |
| --- | ---: | ---: | ---: | --- |
| Public content performance / SEO | 25 | 9.5 | 7.5 | 게시글과 상세 매물 페이지가 많아 정적 생성과 캐시 효율이 중요하다. |
| Maintenance effort | 20 | 9.0 | 6.5 | 퍼블릭 사이트는 서버 운영보다 컨텐츠 안정성이 중요하다. |
| Hosting cost | 15 | 9.0 | 7.5 | Node 단일 런타임 또는 정적 중심 배포가 더 단순하다. |
| Migration speed from current codebase | 15 | 10.0 | 4.0 | 현재 구현이 이미 Next.js 16 기준이므로 갈아엎는 비용이 크다. |
| Content preservation fit | 10 | 9.5 | 7.0 | 가져온 JSON, assets, route mapping을 그대로 유지하기 쉽다. |
| Long-term stability | 10 | 7.5 | 9.0 | PHP 생태계의 장기 호환성은 강점이지만, 현재 요구와 직접 맞닿는 항목은 아니다. |
| Future CMS / DB expansion | 5 | 8.5 | 8.5 | 두 스택 모두 확장 가능하나, 현재 단계에서는 차이가 크지 않다. |

### Final Weighted Score

- `Next.js 16`: `9.12 / 10`
- `Laravel 12 / PHP 8.4`: `6.91 / 10`

## Decision

현재 퍼블릭 사이트 메인 스택은 `Next.js 16 App Router`를 유지한다.

이 결정은 다음 이유로 유효하다.

- 이미 이관된 게시글과 정적 페이지가 `data/imported/*.json`과 `public/imported-assets/*`에 정리되어 있어 재구축 비용이 낮다.
- 컨텐츠성 페이지가 많아 SSG/ISR 중심 구조가 유리하다.
- 퍼블릭 사이트는 복잡한 백오피스보다 운영비와 수정 안정성이 더 중요하다.
- Laravel로 전환하면 React/Next 기반 UI와 라우팅, import 파이프라인을 다시 써야 하므로 실익보다 비용이 크다.

## Technology Rule

최신 기술은 무조건 넣지 않는다. 아래 조건을 만족할 때만 반영한다.

1. 유지보수 비용이 줄어든다.
2. 배포 또는 장애 대응이 단순해진다.
3. SEO, 성능, 운영 안정성 중 하나 이상이 분명히 좋아진다.
4. 기존 게시글과 이관 자산의 보존성이 깨지지 않는다.

## Applied Decision

현재 프로젝트에서 최신 기술 반영으로 인정한 항목:

- `Next.js 16 App Router`
- `React 19`
- route-level metadata
- `ISR`
- JSON-LD structured data
- imported content route normalization
- static-first content archive

반영하지 않은 항목:

- `Laravel` 재구축
- `PHP` 복귀
- 조기 DB 전환

이 항목들은 현 시점 점수 계산상 긍정 효과보다 재구축 비용과 운영 복잡도 증가가 더 크다.

## When Re-evaluation Is Valid

아래 조건이 생기면 스택 재평가를 다시 한다.

- 운영자가 브라우저 기반 관리자에서 글을 대량 직접 수정해야 한다.
- 게시글 작성/수정 빈도가 import 방식보다 훨씬 높아진다.
- 회원, 결제, 권한, 내부 업무 프로세스가 이 퍼블릭 사이트 안으로 들어온다.
- 서버리스 파일 저장이 병목이 되어 DB/CMS가 필수가 된다.

## Official References

- Next.js App Router: https://nextjs.org/docs/app
- Next.js Deploying: https://nextjs.org/docs/app/getting-started/deploying
- Next.js ISR: https://nextjs.org/docs/app/guides/incremental-static-regeneration
- Laravel release notes: https://laravel.com/docs/releases
- Laravel deployment: https://laravel.com/docs/12.x/deployment
- PHP 8.4 release: https://www.php.net/releases/8.4/en.php
