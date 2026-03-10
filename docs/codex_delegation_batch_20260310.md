# Codex 위임 태스크 배치 3 — 2026-03-10
> Codex Desktop에 순서대로 붙여넣기. 각 태스크는 독립적이므로 병렬 실행 가능.
> ⚠️ 이전 배치에서 write 권한 문제 발생 — 이번에는 결과를 **stdout에 출력**하도록 설계.

---

## Task 1: 인허가 JS 함수 정합성 크로스체크

```
프로젝트 루트: H:/auto
파일: permit_diagnosis_calculator.py

이 파일에서 두 위치를 비교 분석해줘:

위치 A: build_html() 함수 내부의 html_template 문자열 (약 L2388부터 시작)
위치 B: _repair_generated_permit_html() 함수 (약 L7961부터 시작)

_repair_generated_permit_html()는 A에서 생성된 HTML의 JS 함수를 regex로 교체합니다.
현재 유지 중인 패치: renderProofClaim, renderResult

분석 작업:
1. 위치 A에서 `const renderProofClaim` 함수의 전체 본문을 추출
2. 위치 B에서 교체되는 `renderProofClaim` 본문을 추출
3. 두 버전의 차이점을 줄 단위로 비교하여 보고
4. `renderResult`에 대해서도 동일 작업

결과 형식:
## renderProofClaim 비교
### 원본 (template)
[첫 5줄...]
### 패치 (repair)
[첫 5줄...]
### 핵심 차이
- [차이 1]
- [차이 2]
### 위험 평가
- 패치가 원본보다 기능이 누락된 부분이 있는지
- 원본이 업데이트되면 패치와 불일치가 생길 수 있는 부분

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
