# Codex 위임 태스크 배치 3 — 2026-03-10
> Codex Desktop에 순서대로 붙여넣기. 각 태스크는 독립적이므로 병렬 실행 가능.
> ⚠️ 이전 배치에서 write 권한 문제 발생 — 이번에는 결과를 **stdout에 출력**하도록 설계.

---

## Task 1: 인허가 JS 핵심 함수 정합성 감사

```
프로젝트 루트: H:/auto
파일: permit_diagnosis_calculator.py

build_html() 함수 내부의 html_template에서 핵심 JS 함수들의 정합성을 감사해줘.
(참고: _repair_generated_permit_html은 Session 17에서 완전 제거됨 — template이 유일 source of truth)

감사 대상 JS 함수 (template 내부):
1. renderResult — 진단 결과 렌더링 핵심
2. renderProofClaim — 증거/근거 패킷 렌더링
3. renderStructuredReview — 자동 점검 결과 렌더링
4. evaluateTypedCriteriaLocal — typed_criteria 로컬 평가

분석 작업:
1. 각 함수가 호출하는 하위 함수 목록 추출
2. 함수 간 호출 순서가 올바른지 검증 (renderResult → renderRuleBasis → renderRuntimeReasoningCard → renderStructuredReview)
3. null/undefined 방어가 누락된 변수 접근 패턴 식별
4. DOM 요소 참조(ui.xxx)가 모두 초기화 맵에 정의되어 있는지 크로스체크

결과 형식:
## JS 핵심 함수 정합성 감사
### 호출 체인
renderResult → [함수1, 함수2, ...]
### 미방어 참조
| 변수 | 위치 | 위험도 |
### DOM 참조 누락
| element ID | 사용 위치 | 초기화 여부 |
### 권장 조치
- [조치 1]

stdout으로 마크다운 출력해줘.
```

---

## Task 2: 인허가 진단 결과 UI 접근성 감사

```
프로젝트 루트: H:/auto
파일: permit_diagnosis_calculator.py

build_html() 함수가 생성하는 HTML에서 접근성(a11y) 이슈를 찾아줘.

검사 항목:
1. <input> 요소에 associated <label> 또는 aria-label이 있는지
2. 색상 대비: CSS에서 color와 background-color 조합이 WCAG AA 기준(4.5:1)을 충족하는지
3. 인터랙티브 요소(button, a)에 키보드 접근성(tabindex, role)이 있는지
4. 이미지/아이콘에 alt text가 있는지
5. 시맨틱 태그 사용 (div 남용 vs section/article/nav)

build_html("테스트", {}, {}) 를 호출하여 HTML을 생성한 뒤 분석.

결과 형식 (stdout 출력):
## 접근성 감사 — 인허가 사전검토
### Critical (즉시 수정)
| 이슈 | 위치 | 권장 조치 |
### Warning (개선 권장)
| 이슈 | 위치 | 권장 조치 |
### 통계
- input 요소: N개 (labeled: N개, unlabeled: N개)
- 색상 대비 위반: N건
- 키보드 접근성: N건
```

---

## Task 3: 양도가 산정기 특허 claim 기술 요약 생성

```
프로젝트 루트: H:/auto
파일: yangdo_calculator.py, MASTERPLAN.md

양도가 산정 시스템의 특허 출원을 위한 기술 요약서를 작성해줘.

1. yangdo_calculator.py에서 핵심 알고리즘을 분석:
   - specialBalanceSectorName(): 업종 판별 로직
   - singleCorePublicationCap(): 신뢰도 상한 적용
   - SPECIAL_BALANCE_AUTO_POLICIES: 업종별 정산 정책
   - 전체 양도가 산정 파이프라인 (입력 → 유사업체 매칭 → 가격 산정 → 신뢰도 보정 → 공개 모드 결정)

2. MASTERPLAN.md에서 특허 claim 항목 확인

3. 기술 요약서 작성 (stdout 출력):
## 기술 요약: AI 기반 건설업 양도가 산정 시스템

### 발명의 명칭
### 기술 분야
### 해결하고자 하는 과제
### 과제 해결 수단
- 업종 판별 모듈
- 신뢰도 기반 공개/비공개 결정 모듈
- 업종별 정산 정책 자동 적용 모듈
- 실시간 양도가 범위 산정 모듈
### 발명의 효과
### 주요 청구항 초안 (5개)

변리사에게 전달할 수 있는 수준으로 작성해줘.
```

---

## Task 4: Gemini CLI — 경쟁사 UX 분석 보고서

```
아래 사이트들의 양도/양수 관련 서비스를 분석하고 seoulmna.kr의 AI 양도가 산정 시스템과 비교해줘:

경쟁사:
1. 건설경영정보 (www.cmis.or.kr) — 건설업 양도양수 정보
2. 전문건설신문 (www.jknews.co.kr) — 건설업 매물 정보
3. 대한건설신문 (www.kconews.co.kr) — 건설업 시세 정보

seoulmna.kr의 특장점:
- AI 기반 실시간 양도가 범위 산정
- 업종별(전기/정보통신/소방) 특화 정산 정책
- 신뢰도 기반 공개/비공개 자동 결정
- 체크박스 기반 사전검토 진단

비교 항목:
1. 가격 정보 제공 방식 (AI vs 수동)
2. 업종 특화 수준
3. 사용자 경험 (입력 → 결과 단계)
4. 모바일 대응
5. 실시간성

결과를 마크다운으로 stdout 출력해줘.
```
