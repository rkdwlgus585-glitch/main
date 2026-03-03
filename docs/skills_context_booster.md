# SeoulMNA 계산기 작업용 Skills + Context 부스터

## 목적
- 계산기(양도양수/신규등록) 개선 속도와 품질을 동시에 올리기 위한 기본 컨텍스트.
- 세션 시작 시 아래 스킬/컨텍스트를 같이 선언하면 재작업과 누락을 줄일 수 있음.

## 우선 Skills (긍정 효과 높은 순)
1. `seoulmna-listing-ops`
- 매물 데이터/시트/게시 정합성 확보.
- 유사 매물 기반 계산 정확도 개선에 직접 영향.

2. `seoulmna-crm-ops`
- 상담 전환 흐름(문의 입력, 매칭, 제안) 검증.
- 계산기 결과 이후 고객 액션 품질 향상.

3. `playwright`
- 실제 화면/버튼/반응형 동작을 빠르게 반복 검증.
- "작동 안 함"류 오류의 조기 발견 효과가 큼.

4. `security-best-practices`
- 입력값/엔드포인트/민감정보 처리 점검.
- 계산기 공개 페이지의 악성 입력 리스크 방어.

5. `seoulmna-blog-ops`
- 계산기와 블로그 유입 연결(키워드, CTA, 전환 동선) 강화.
- 상담 유입 확대에 간접적 긍정 효과.

## 고정 컨텍스트 (항상 포함)
- 배포 가드레일: `KR only`, `CO publish 금지 기본값`.
- 전기/정보통신/소방: 공제조합 잔액은 양도가 산정 영향 제외.
- 40~60대 대표 고객군 기준으로 초간편 모드 우선.
- 내부 계산식 상세 노출 최소화, "AI 계산 완료 + 핵심 안내" 중심.

상세 JSON:
- [calculator_autopilot_context.json](/c:/Users/rkdwl/Desktop/auto/docs/calculator_autopilot_context.json)

## 추천 시작 프롬프트 (복붙용)
```text
이번 턴은 seoulmna-listing-ops + seoulmna-crm-ops + playwright를 사용.
컨텍스트는 docs/calculator_autopilot_context.json을 기준으로 적용.
KR 전용으로만 작업/검증하고 co.kr은 반영 금지.
양도양수/신규등록 계산 로직과 UI를 테스트-수정-재검증 루프로 진행.
```

## 완료 체크리스트
- KR 페이지 동작/폼/버튼/결과 표시 정상.
- 전기/정보통신/소방 balance_excluded 정상.
- 일반 업종에서 공제조합 잔액 반영 정상.
- 배포 로그에서 `co.skipped=true` 확인.
- 상담 CTA(전화/오픈채팅/이메일) 클릭 동선 정상.

## 실행 바로가기
- 시작: `계산기자율주행_시작.bat`
- 상태: `계산기자율주행_상태.bat`
- 중지: `계산기자율주행_중지.bat`
