#!/bin/bash
# ============================================================
# gemini_delegate.sh — Claude → Gemini CLI 위임 파이프라인
# ============================================================
# 용도: Claude가 토큰 절약을 위해 Gemini CLI에 작업 위임
# 사용법: ./scripts/gemini_delegate.sh <task_type> <output_file> [extra_context_file]
#
# task_type:
#   research    - 조사/분석 (마케팅, 경쟁사, 시장)
#   document    - 문서 생성 (마케팅 전략, 디자인 스펙)
#   codereview  - 코드 리뷰/분석
#   translate   - 번역/로컬라이제이션
#   brainstorm  - 아이디어 브레인스토밍
#   qa          - QA 시나리오 생성
#   custom      - 커스텀 프롬프트 (stdin으로 전달)
#
# 예시:
#   echo "마케팅 전략 분석해줘" | ./scripts/gemini_delegate.sh custom logs/result.md
#   ./scripts/gemini_delegate.sh research logs/market_analysis.md config/context.json

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Google OAuth 인증 설정 (API 키 대신 Google 로그인 사용)
export GOOGLE_GENAI_USE_GCA=true
TASK_TYPE="${1:-custom}"
OUTPUT_FILE="${2:-/dev/stdout}"
CONTEXT_FILE="${3:-}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log() { echo -e "${BLUE}[Gemini Delegate]${NC} $*"; }
ok()  { echo -e "${GREEN}[✓]${NC} $*"; }
err() { echo -e "${RED}[✗]${NC} $*" >&2; }
warn(){ echo -e "${YELLOW}[!]${NC} $*"; }

# Gemini CLI 존재 확인
if ! command -v gemini &>/dev/null; then
    err "Gemini CLI 미설치. npm install -g @google/gemini-cli"
    exit 1
fi

# 프로젝트 컨텍스트 로드
MASTER_CONTEXT=""
if [ -f "$PROJECT_DIR/MASTERPLAN.md" ]; then
    MASTER_CONTEXT=$(head -100 "$PROJECT_DIR/MASTERPLAN.md" 2>/dev/null || true)
fi

# 추가 컨텍스트 파일 로드
EXTRA_CONTEXT=""
if [ -n "$CONTEXT_FILE" ] && [ -f "$PROJECT_DIR/$CONTEXT_FILE" ]; then
    EXTRA_CONTEXT=$(cat "$PROJECT_DIR/$CONTEXT_FILE" 2>/dev/null || true)
fi

# 태스크별 시스템 프롬프트 구성
build_prompt() {
    local base_prompt=""

    case "$TASK_TYPE" in
        research)
            base_prompt="당신은 건설업 행정 서비스 시장 분석 전문가입니다.
seoulmna.kr 플랫폼은 AI 양도가 산정 + AI 인허가 사전검토 서비스를 제공합니다.
전기공사업, 정보통신공사업, 소방시설공사업이 핵심 업종입니다.
경쟁사: admini.kr(AI행정사), superlawyer.co.kr(AI법률)
한국어로 구조화된 마크다운 보고서를 작성하세요."
            ;;
        document)
            base_prompt="당신은 기술 문서 작성 전문가입니다.
seoulmna.kr 플랫폼의 기술 문서를 작성합니다.
마크다운 형식, 한국어로 작성하세요.
구조: ## 섹션 > ### 하위섹션 > 표/코드블록"
            ;;
        codereview)
            base_prompt="당신은 Python/JavaScript 코드 리뷰 전문가입니다.
이 프로젝트는 Python f-string으로 HTML/JS를 생성합니다.
JS 코드 내 {}는 {{}}로 이스케이프되어 있습니다.
버그, 성능, 보안 관점에서 분석하세요."
            ;;
        translate)
            base_prompt="당신은 한국어↔영어 기술 번역 전문가입니다.
건설업/행정 분야 전문 용어를 정확히 사용하세요."
            ;;
        brainstorm)
            base_prompt="당신은 건설업 IT 서비스 혁신 전문가입니다.
토스(Toss) 스타일의 UX/UI 철학을 기반으로 아이디어를 제시합니다.
메인 컬러: #003764 (네이비)
원칙: 1-thing-per-1-page, Casual Concept, 접근성 우선"
            ;;
        qa)
            base_prompt="당신은 QA 테스트 시나리오 설계 전문가입니다.
전기/정보통신/소방 업종별 양도가 산정 및 인허가 검토 시나리오를 생성합니다.
엣지케이스, 경계값, 오류 시나리오를 포함하세요."
            ;;
        custom)
            base_prompt="당신은 seoulmna.kr 프로젝트의 AI 어시스턴트입니다.
건설업 양도양수 및 인허가 전문 플랫폼 개발을 지원합니다."
            ;;
    esac

    # stdin에서 사용자 프롬프트 읽기
    local user_prompt=""
    if [ ! -t 0 ]; then
        user_prompt=$(cat)
    fi

    # 최종 프롬프트 조합
    echo "${base_prompt}

---
프로젝트 컨텍스트:
${MASTER_CONTEXT}

${EXTRA_CONTEXT:+추가 컨텍스트:
$EXTRA_CONTEXT}

---
${user_prompt:+작업 요청:
$user_prompt}"
}

# 실행
log "Task: ${TASK_TYPE} | Output: ${OUTPUT_FILE}"
log "Building prompt..."

FULL_PROMPT=$(build_prompt)

log "Calling Gemini CLI (headless mode)..."

# 출력 디렉토리 확인
OUTPUT_DIR=$(dirname "$PROJECT_DIR/$OUTPUT_FILE")
mkdir -p "$OUTPUT_DIR" 2>/dev/null || true

# Gemini CLI 실행 (비대화형, 텍스트 출력)
RESULT=$(cd "$PROJECT_DIR" && gemini -p "$FULL_PROMPT" -o text 2>"$PROJECT_DIR/logs/gemini_delegate_${TIMESTAMP}_error.log") || {
    err "Gemini CLI 실행 실패. 에러 로그: logs/gemini_delegate_${TIMESTAMP}_error.log"
    cat "$PROJECT_DIR/logs/gemini_delegate_${TIMESTAMP}_error.log" >&2
    exit 1
}

# 결과 저장
if [ "$OUTPUT_FILE" != "/dev/stdout" ]; then
    echo "$RESULT" > "$PROJECT_DIR/$OUTPUT_FILE"
    ok "결과 저장: $OUTPUT_FILE ($(wc -c < "$PROJECT_DIR/$OUTPUT_FILE") bytes)"
else
    echo "$RESULT"
fi

# 에러 로그 정리 (성공 시)
rm -f "$PROJECT_DIR/logs/gemini_delegate_${TIMESTAMP}_error.log" 2>/dev/null

ok "Gemini delegate 완료: ${TASK_TYPE}"
