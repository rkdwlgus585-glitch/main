# Codex Desktop 반복 작업 프롬프트 모음
> 아래 프롬프트를 Codex Desktop에 복사-붙여넣기하여 실행

---

## Task 1: 디자인 시스템 컬러 적용 (CSS 일괄 치환)

```
output/yangdo_price_calculator.html과 output/yangdo_price_calculator_owner.html 파일에서
다음 CSS 컬러를 일괄 치환해줘:

기존 → 변경:
- #2563eb, #3b82f6 → #003764 (Primary Navy)
- #1d4ed8 → #002244 (Primary Dark)
- #60a5fa → #0A4D8C (Primary Light)
- #10b981 → #00C48C (Success)
- #f59e0b → #FFB800 (Warning)
- #ef4444 → #FF4757 (Error)

주의사항:
- background-color, color, border-color, box-shadow 모두 포함
- gradient 안의 색상도 변경
- JavaScript 문자열 내 색상 코드는 제외
```

---

## Task 2: 배너 텍스트 정렬 개선

```
output/yangdo_price_calculator.html에서 오른쪽 사이드바 배너를 찾아서 다음을 수행해줘:

1. "대표 행정사 카카오톡 오픈채팅 상담" 과 "010-9926-8661" 사이에
   <br> 태그로 줄바꿈 추가
2. 텍스트를 가운데 정렬 (text-align: center)
3. 전화번호에 font-weight: 600 적용
4. 간격 조절: line-height: 1.6

동일한 변경을 owner 버전에도 적용.
```

---

## Task 3: Badge 컴포넌트 일괄 추가

```
output/yangdo_price_calculator.html에서 다음 CSS 클래스를 <style> 태그 안에 추가해줘:

.badge-success { background: #E6F9F1; color: #00C48C; padding: 2px 8px; border-radius: 4px; font-size: 12px; font-weight: 500; }
.badge-warning { background: #FFF8E1; color: #FFB800; padding: 2px 8px; border-radius: 4px; font-size: 12px; font-weight: 500; }
.badge-error { background: #FFEBEE; color: #FF4757; padding: 2px 8px; border-radius: 4px; font-size: 12px; font-weight: 500; }
.badge-info { background: #E3F2FD; color: #003764; padding: 2px 8px; border-radius: 4px; font-size: 12px; font-weight: 500; }
.sector-chip { padding: 6px 14px; border-radius: 20px; background: #F3F4F6; color: #6B7280; font-size: 14px; cursor: pointer; transition: 0.2s; }
.sector-chip.active { background: #003764; color: #FFFFFF; }

동일한 변경을 owner 버전에도 적용.
```

---

## Task 4: 주석 정리 (한국어 통일)

```
output/yangdo_price_calculator.html에서:
1. 영어 주석을 한국어로 변환 (<!-- Section --> → <!-- 섹션 -->)
2. TODO/FIXME 주석을 찾아서 목록으로 정리
3. 빈 주석 (<!-- -->) 제거

결과를 보고서 형식으로 알려줘.
```

---

## Task 5: 소방/전기/통신 업종 텍스트 패턴 복제

```
yangdo_calculator.py에서 전기공사업에 대한 안내 메시지 패턴을 찾아서,
동일한 패턴으로 정보통신공사업, 소방시설공사업 버전을 생성해줘.

찾아야 할 패턴: "전기공사업"이 포함된 사용자 안내 문구
변환 규칙:
- "전기공사업" → "정보통신공사업" / "소방시설공사업"
- "전기" → "정보통신" / "소방"
- 자본금 1.5억 → 1.5억(통신) / 1.0억(소방)
- 기술자 3인 → 3인(통신) / 2-3인(소방)

변경 전/후를 diff 형식으로 보여줘.
```
