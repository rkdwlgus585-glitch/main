# Codex 위임 태스크 배치 — 2026-03-09
> Codex Desktop에 순서대로 붙여넣기. 각 태스크는 독립적이므로 병렬 실행 가능.

---

## Task 1: 양도가 산정기 입력변수 E2E 테스트 확장 (토큰 집약)

```
프로젝트 루트: H:/auto
파일: yangdo_calculator.py (10164줄)
기존 테스트: tests/test_yangdo_calculator_input_variables.py (4개 테스트만 있음)

이 파일을 읽고 아래 테스트를 tests/test_yangdo_calculator_input_variables.py에 추가해줘.
기존 4개 테스트는 유지하고 아래를 추가:

1. test_special_sector_detection:
   - yangdo_calculator 모듈에서 build_page_html 함수의 시그니처를 확인하고
   - 전기공사업, 정보통신공사업, 소방시설공사업 문자열이 포함된 license_text가
   - SPECIAL_BALANCE_AUTO_POLICIES 딕셔너리에서 올바른 sector ("전기", "정보통신", "소방")로 매핑되는지 검증
   - 힌트: specialBalanceSectorName 함수 로직을 Python 레벨에서 검증 (JS 코드지만 로직을 Python으로 재현)

2. test_build_meta_price_statistics:
   - build_meta() 함수에 학습 데이터셋을 넣었을 때
   - all_record_count, train_count, priced_ratio 키가 존재하는지
   - priced_ratio가 0~100 사이인지 검증

3. test_build_page_html_returns_valid_html:
   - build_page_html()을 최소 데이터셋으로 호출
   - 반환 HTML에 <section id="seoulmna-yangdo-calculator"> 태그 존재 확인
   - CSS 변수 --smna-primary 존재 확인
   - view_mode="customer"와 view_mode="owner" 각각 테스트

4. test_build_page_html_special_sector_css:
   - build_page_html() 반환 HTML에서
   - SPECIAL_BALANCE_AUTO_POLICIES 객체가 JS 코드에 포함되어 있는지
   - "전기", "정보통신", "소방" 3개 키가 모두 존재하는지 문자열 검색으로 확인

5. test_price_token_edge_cases:
   - _price_token_to_eok() 함수에 다음 입력 테스트:
     "10억", "0.5억", "500만", "1억 3000만", "3.7억~4.2억", "", None, "비공개", "문의"
   - 각각 예상 결과와 비교

6. test_build_training_dataset_special_sectors:
   - 전기/정보통신/소방 license_text를 가진 레코드 3개를 만들어서
   - build_training_dataset()에 넣고
   - 모든 레코드가 포함되는지 검증

unittest 형식으로 작성하고, 실행 가능한지 확인: python -m pytest tests/test_yangdo_calculator_input_variables.py -v
```

---

## Task 2: 인허가 사전검토 CTA 모드 분기 테스트 (신규)

```
프로젝트 루트: H:/auto
파일: permit_diagnosis_calculator.py (8691줄)
기존 테스트: tests/test_permit_diagnosis_calculator_rules.py

permit_diagnosis_calculator.py를 읽고, 아래 내용으로 새 테스트 파일을 만들어줘:
tests/test_permit_cta_mode_branches.py

검증 대상 (JS 코드가 Python f-string 안에 있음):
1. build_html() 함수를 호출해서 HTML을 생성
2. 생성된 HTML 안에 아래 JS 문자열이 있는지 검증:
   - 'ctaMode' 변수가 존재하는지
   - "shortfall" 문자열이 존재하는지
   - "manual_review" 문자열이 존재하는지
   - "pass" 문자열이 존재하는지
   - "보완 필요 서류" 문자열이 존재하는지
   - "확인 권장 서류" 문자열이 존재하는지
   - "전문가 검토 안내" 문자열이 존재하는지
   - "#FFF8E1" (manual_review 경고색) 문자열이 존재하는지

3. customer 모드와 owner 모드 양쪽에서 동일한 CTA 로직이 있는지 확인:
   - HTML 내에서 'ctaMode' 가 2번 이상 등장하는지 (customer + owner)

build_html() 시그니처를 먼저 확인하고, 최소 인자로 호출할 수 있도록 만들어줘.
실행: python -m pytest tests/test_permit_cta_mode_branches.py -v
```

---

## Task 3: Customer vs Owner 모드 일관성 검증 (코드 리뷰)

```
프로젝트 루트: H:/auto
파일: yangdo_calculator.py (10164줄)

이 파일에서 build_page_html() 함수를 찾아서:
1. view_mode="customer"일 때와 view_mode="owner"일 때 분기하는 모든 곳을 찾아줘
2. 각 분기점에서 customer에만 있고 owner에 없는 기능, 또는 그 반대를 목록으로 정리
3. 의도적 차이(보안/권한)와 실수로 누락된 것을 구분

결과를 logs/customer_owner_mode_audit.md에 저장해줘.
형식:
## Customer vs Owner 모드 감사 결과

### 의도적 차이
| 줄번호 | 기능 | customer | owner | 사유 |

### 잠재적 누락
| 줄번호 | 기능 | 누락 모드 | 권장 조치 |

### 통계
- 총 분기점: N개
- 의도적 차이: N개
- 잠재적 누락: N개
```

---

## Task 4: CSS 디자인 시스템 준수 감사

```
프로젝트 루트: H:/auto
파일: yangdo_calculator.py, permit_diagnosis_calculator.py

두 파일에서 하드코딩된 색상값을 모두 찾아줘.
디자인 시스템 변수:
- --smna-primary: #003764
- --smna-primary-strong: #002244
- --smna-primary-soft: #0A4D8C
- --smna-accent: #00A3FF
- --smna-accent-strong: #0080CC
- --smna-text: #1A1A2E
- --smna-sub: #6B7280
- --smna-warning: #FFB800
- --smna-success: #00C48C
- --smna-error: #FF4757
- --smna-border: #E5E7EB
- --smna-neutral: #F8FAFB

작업:
1. 각 파일에서 #으로 시작하는 색상 코드를 모두 추출 (CSS 속성 내부)
2. 위 디자인 시스템 변수로 교체 가능한 것을 식별
3. 교체 불가능한 것(의도적 하드코딩)은 사유와 함께 분류

결과를 logs/css_design_system_audit.md에 저장:
## CSS 디자인 시스템 감사

### 교체 권장 (var() 사용 가능)
| 파일 | 줄번호 | 현재 값 | 권장 변수 |

### 의도적 하드코딩 (유지)
| 파일 | 줄번호 | 값 | 사유 |

### 통계
- yangdo: 교체 가능 N개 / 유지 N개
- permit: 교체 가능 N개 / 유지 N개
```

---

## Task 5: 데드코드 및 미사용 함수 탐지

```
프로젝트 루트: H:/auto
파일: yangdo_calculator.py (10164줄)

이 대용량 파일에서:
1. Python 레벨 함수 중 파일 내부/외부에서 호출되지 않는 것을 찾아줘
   - def _로 시작하는 private 함수 위주
   - 외부 호출은 all.py, tests/ 디렉토리에서 import 여부 확인

2. JavaScript 코드(f-string 내부) 중:
   - 선언만 되고 사용되지 않는 const/let 변수
   - 정의만 되고 호출되지 않는 function
   - console.log 또는 디버깅 코드가 남아있는 곳

3. 주석 처리된 코드 블록 (5줄 이상)

결과를 logs/dead_code_audit.md에 저장:
## 데드코드 감사 — yangdo_calculator.py

### 미사용 Python 함수
| 함수명 | 줄번호 | 외부 참조 유무 | 권장 |

### 미사용 JS 변수/함수
| 이름 | 줄번호 | 타입 | 권장 |

### 주석 처리된 코드
| 시작 줄 | 끝 줄 | 내용 요약 |

### 디버깅 코드
| 줄번호 | 코드 | 권장 |
```

---

## Task 6: 전기/정보통신/소방 업종별 계산 로직 크로스체크

```
프로젝트 루트: H:/auto
파일: yangdo_calculator.py

이 파일에서 전기/정보통신/소방 3개 업종에 대한 모든 분기 로직을 찾아서 크로스체크해줘.

확인 항목:
1. SPECIAL_BALANCE_AUTO_POLICIES 객체에서 3업종의 파라미터 비교 테이블 생성
2. specialBalanceSectorName() 함수의 판별 순서가 올바른지 (정보통신 > 소방 > 전기)
3. singleCorePublicationCap() 함수에서 3업종에 대한 confidence cap 적용 로직 검증
4. 분할/합병 모드에서 reorgOverrides가 3업종 모두에 적용되는지
5. 시평 검색과 실적 검색 모드에서 3업종의 특수 처리가 일관적인지
6. 추천 패널(buildRecommendPanelFollowupPlan)에서 3업종 메시지가 각각 존재하는지

결과를 logs/special_sector_crosscheck.md에 저장:
## 전기/정보통신/소방 크로스체크

### 파라미터 비교
| 항목 | 전기 | 정보통신 | 소방 | 일관성 |

### 분기점 목록
| 줄번호 | 함수/컨텍스트 | 전기 | 정보통신 | 소방 | 상태 |

### 발견된 불일치
| 줄번호 | 설명 | 심각도 | 권장 조치 |
```

---

## 실행 순서 권장
1. **Task 1 + Task 2** (테스트 작성) → 먼저 실행, 결과가 다른 태스크의 기준이 됨
2. **Task 3 + Task 4 + Task 5 + Task 6** (감사/리뷰) → 병렬 실행 가능
