# seoulmna.kr 디자인 시스템 스펙 (v1.0)

본 가이드는 **seoulmna.kr**의 브랜드 정체성을 확립하고, 사용자 경험을 극대화하기 위한 디자인 원칙을 정의합니다. 토스(Toss)의 '1-thing-per-1-page' 철학과 'Casual Concept'을 계승하여 복잡한 M&A 프로세스를 친숙하고 직관적으로 전달합니다.

---

## 1. 브랜드 철학
- **One thing per page**: 한 화면에서는 하나의 핵심 액션에만 집중합니다.
- **Casual & Trust**: M&A의 무거움을 덜어내되, 깊은 네이비 컬러로 신뢰감을 유지합니다.
- **Accessibility First**: 모든 연령층이 제약 없이 정보를 소비할 수 있도록 시각적 명확성을 우선합니다.

---

## 2. 컬러 시스템 (Color System)

| 구분 | 이름 | Hex Code | 용도 |
| :--- | :--- | :--- | :--- |
| **Primary** | Navy | `#003764` | 브랜드 대표 컬러, 핵심 버튼, 강조 |
| **Light** | Blue Light | `#0A4D8C` | 호버 상태, 상호작용 요소 |
| **Dark** | Blue Dark | `#002244` | 헤더, 깊이감 있는 배경 |
| **Secondary** | Point Blue | `#00A3FF` | 포인트 UI, 링크, 진행률 |
| **Success** | Mint | `#00C48C` | 완료, 승인, 긍정 상태 |
| **Warning** | Amber | `#FFB800` | 주의, 대기, 확인 필요 |
| **Error** | Red | `#FF4757` | 오류, 삭제, 경고 |
| **Background** | Ice Gray | `#F8FAFB` | 전체 페이지 배경 |
| **Text Primary** | Deep Ink | `#1A1A2E` | 본문 및 타이틀 메인 텍스트 |
| **Text Secondary**| Slate Gray | `#6B7280` | 부가 설명, 비활성 텍스트 |
| **Border** | Soft Gray | `#E5E7EB` | 디바이더, 필드 테두리 |

---

## 3. 타이포그래피 (Typography)
**Font Family:** `Pretendard`, `-apple-system`, `sans-serif` (가독성과 현대적 느낌 강조)

| Scale | Weight | Size | Line Height | Usage |
| :--- | :--- | :--- | :--- | :--- |
| **Display** | Bold (700) | 40px | 1.4 | 메인 히어로 섹션 |
| **Heading 1** | Bold (700) | 32px | 1.4 | 페이지 주요 타이틀 |
| **Heading 2** | SemiBold (600) | 24px | 1.5 | 카드 및 섹션 타이틀 |
| **Body Large** | Medium (500) | 18px | 1.6 | 리스트 타이틀, 강조 본문 |
| **Body Medium** | Regular (400) | 16px | 1.6 | 일반 본문 텍스트 (Default) |
| **Caption** | Regular (400) | 14px | 1.5 | 부가 정보, 캡션 |

---

## 4. 스페이싱 & 그리드 (Spacing & Grid)
- **Base Unit**: `4px`
- **Container Padding**: 
  - Mobile: `20px` (Gutter 16px)
  - Desktop: `32px` (Max-width 1200px)
- **Radius**: 기본 `12px`, 카드 `16px`, 버튼 `8px` (Toss 스타일의 둥근 모서리)

---

## 5. 모션 (Motion)
- **Base Interaction**: `200ms ease-in-out` (버튼 호버, 컬러 변경)
- **Page Transition**: `300ms slide-left` (다음 단계 이동 시 화면 전환 효과)
- **Feedback**: 클릭 시 미세한 스케일 다운 (`scale(0.98)`)으로 물리적 피드백 제공.

---

## 6. 컴포넌트 패턴 (Component Patterns)

### 6.1 SectorChip (업종 칩)
카테고리 분류 및 필터링에 사용됩니다.
```html
<span class="sector-chip active">IT/소프트웨어</span>
<style>
.sector-chip {
    padding: 6px 14px;
    border-radius: 20px;
    background: #F3F4F6;
    color: #6B7280;
    font-size: 14px;
    cursor: pointer;
    transition: 0.2s;
}
.sector-chip.active {
    background: #003764;
    color: #FFFFFF;
}
</style>
```

### 6.2 BottomCTA (하단 고정 버튼)
모바일 최적화된 하단 고정 액션 버튼입니다.
```html
<div class="bottom-cta-wrap">
    <button class="btn-primary">다음 단계로</button>
</div>
<style>
.bottom-cta-wrap {
    position: fixed;
    bottom: 0; left: 0; right: 0;
    padding: 20px;
    background: linear-gradient(to top, #fff 80%, transparent);
}
.btn-primary {
    width: 100%;
    height: 56px;
    background: #003764;
    color: white;
    border-radius: 12px;
    font-size: 18px;
    font-weight: 600;
}
</style>
```

### 6.3 ResultCard (매물/결과 카드)
```html
<div class="result-card">
    <div class="badge">매도 중</div>
    <h3>강남구 IT 법인 양도</h3>
    <p>매매가 5.5억 · 매출액 12억</p>
</div>
<style>
.result-card {
    background: #FFFFFF;
    padding: 24px;
    border-radius: 16px;
    box-shadow: 0 4px 20px rgba(0,0,0,0.05);
    margin-bottom: 16px;
}
.result-card .badge {
    background: #EBF5FF;
    color: #00A3FF;
    padding: 4px 8px;
    border-radius: 4px;
    font-size: 12px;
    display: inline-block;
}
</style>
```

### 6.4 InputGroup (입력 그룹)
```html
<div class="input-group">
    <label>회사명</label>
    <input type="text" placeholder="회사명을 입력해주세요">
</div>
<style>
.input-group label { display: block; margin-bottom: 8px; color: #1A1A2E; font-weight: 500; }
.input-group input {
    width: 100%;
    padding: 16px;
    border: 1px solid #E5E7EB;
    border-radius: 12px;
    background: #F9FAFB;
}
.input-group input:focus { border-color: #003764; outline: none; background: #fff; }
</style>
```

### 6.5 기타 컴포넌트 명세
- **StepIndicator**: 화면 상단 `4px` 높이의 진행 바. `#00A3FF` 컬러 사용.
- **ListRow**: 아이콘 + 텍스트 + `Chevron-right` 화살표 조합. 터치 영역 최소 `56px`.
- **AlertBanner**: 상단 고정 안내. `#F8FAFB` 배경에 `success/error` 아이콘 활용.

---

## 7. 접근성 (Accessibility)
- **Touch Target**: 모든 클릭 요소는 최소 `44px x 44px` 이상의 영역을 확보합니다.
- **Contrast**: APCA(Advanced Perceptual Contrast Algorithm) 기준을 준수하여 텍스트 가독성을 확보합니다. (Text Primary vs Background 대비비 7:1 이상 유지)
- **Focus State**: 키보드 네비게이션을 위해 초점이 맞춰진 요소에는 `#00A3FF` 아웃라인을 명확히 제공합니다.
