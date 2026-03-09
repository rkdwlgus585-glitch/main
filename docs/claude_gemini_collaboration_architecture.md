# Claude ↔ Gemini CLI 협업 아키텍처
> 최종 업데이트: 2026-03-09

## 1. 개요

Claude의 토큰/한도 소진을 최소화하면서 최대 생산성을 달성하기 위한 멀티-AI 협업 시스템.

```
┌─────────────────────────────────────────────────────┐
│                  사용자 (총괄 지시)                     │
└───────────────────────┬─────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────┐
│              Claude Code (총괄 두뇌)                    │
│  • 전략적 판단 / 아키텍처 설계                            │
│  • 코드 생성 (yangdo_calculator.py 등)                  │
│  • 최종 품질 검증 / 통합                                 │
│  • Gemini 작업 지시 및 결과 검수                          │
└──────┬──────────────┬───────────────┬───────────────┘
       │              │               │
       ▼              ▼               ▼
┌────────────┐ ┌────────────┐ ┌────────────┐
│ Gemini CLI │ │ Codex App  │ │ Claude Sub │
│ (일꾼 A)   │ │ (일꾼 B)   │ │  Agents    │
│            │ │            │ │ (내부 병렬) │
│ • 대량 조사│ │ • 독립 사고│ │ • 코드 탐색│
│ • 문서 생성│ │ • UI/UX    │ │ • 코드 리뷰│
│ • 번역     │ │ • 디자인   │ │ • 테스트   │
│ • QA 생성  │ │            │ │            │
└────────────┘ └────────────┘ └────────────┘

무료 1000/일    GUI 수동      Claude 한도 내
```

## 2. 역할 분담 매트릭스

| 작업 유형 | Claude (두뇌) | Gemini CLI (일꾼) | Codex App (보조) |
|-----------|:---:|:---:|:---:|
| 전략적 판단 | ●● | - | - |
| 코드 생성/수정 | ●● | ○ | ● |
| 코드 리뷰 | ● | ●● | - |
| 시장 조사 | ○ | ●● | - |
| 문서 생성 | ○ | ●● | ● |
| 브레인스토밍 | ● | ●● | ● |
| QA 시나리오 | ○ | ●● | - |
| 번역 | - | ●● | - |
| 특허 근거 정리 | ● | ●● | - |
| UI/UX 디자인 | ● | ○ | ●● |
| 아키텍처 설계 | ●● | - | - |
| 최종 검증/통합 | ●● | - | - |

**●● = 주담당, ● = 보조, ○ = 가능하나 비효율, - = 부적합**

## 3. 토큰 절약 효과

### Before (Claude 단독)
```
Claude 토큰: 100% 소진
├─ 조사/분석: 30%    ← 낭비
├─ 문서 생성: 25%    ← 낭비
├─ 코드 작업: 30%    ← 핵심
└─ 검증/통합: 15%    ← 핵심
```

### After (Claude + Gemini 협업)
```
Claude 토큰: 45% 소진 (55% 절약)
├─ 코드 작업: 30%    ← Claude
├─ 검증/통합: 15%    ← Claude
└─ 지시/검수:  5%    ← Claude (Gemini 결과 확인)

Gemini 무료: 55% 흡수
├─ 조사/분석: 30%    ← Gemini (무료)
└─ 문서 생성: 25%    ← Gemini (무료)
```

## 4. 실행 방법

### 4-1. 단일 작업 위임
```bash
# 템플릿 사용
python scripts/claude_gemini_orchestrator.py delegate -t marketing_analysis
python scripts/claude_gemini_orchestrator.py delegate -t design_system
python scripts/claude_gemini_orchestrator.py delegate -t qa_scenarios

# 커스텀 프롬프트
echo "경쟁사 가격 정책 분석" | python scripts/claude_gemini_orchestrator.py delegate -o logs/pricing.md

# 컨텍스트 파일 포함
python scripts/claude_gemini_orchestrator.py delegate -t patent_evidence -c config/permit_focus_family_registry.json
```

### 4-2. 배치 실행 (전체 or 선택)
```bash
# 전체 템플릿 실행
python scripts/claude_gemini_orchestrator.py batch

# 선택 템플릿만
python scripts/claude_gemini_orchestrator.py batch -t marketing_analysis,design_system,qa_scenarios
```

### 4-3. 히스토리 조회
```bash
python scripts/claude_gemini_orchestrator.py status
```

## 5. 1회 셋업 (인증)

```bash
# Gemini CLI Google OAuth 로그인 (브라우저 팝업)
gemini

# → 브라우저에서 Google 계정 로그인
# → 무료 티어 활성화 (60 req/min, 1000 req/day)
# → 이후 gemini -p "..." 비대화형 사용 가능
```

## 6. Claude에서 Gemini 호출 패턴

Claude Code 세션 내에서:
```bash
# Claude가 Bash 도구로 직접 호출
python scripts/claude_gemini_orchestrator.py delegate -t marketing_analysis

# 결과 파일을 Claude가 Read 도구로 확인
# → 품질 검증 후 필요 시 보완 지시
```

## 7. 템플릿 목록

| 템플릿 | 출력 파일 | 용도 |
|--------|----------|------|
| `marketing_analysis` | `logs/marketing_strategy_analysis_latest.md` | 타겟/차별화/가격/채널 전략 |
| `design_system` | `docs/design_system_spec.md` | #003764 디자인 시스템 스펙 |
| `codex_commands` | `docs/codex_command_implementation_notes.md` | 배너 정렬 + 전년비교 구현노트 |
| `qa_scenarios` | `tests/qa_scenario_matrix_latest.md` | 전기/통신/소방 QA 매트릭스 |
| `patent_evidence` | `docs/patent_evidence_latest.md` | 특허 근거 정리 |
