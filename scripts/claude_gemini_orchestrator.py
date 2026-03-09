#!/usr/bin/env python3
"""
claude_gemini_orchestrator.py — Claude ↔ Gemini CLI 협업 오케스트레이터
=====================================================================

Claude의 토큰 소진을 최소화하면서 Gemini CLI에 작업을 위임하는 파이프라인.

아키텍처:
┌──────────┐   지시    ┌──────────┐   위임    ┌──────────┐
│  Claude   │ ──────→ │ Orchestr │ ──────→ │  Gemini  │
│  (Brain)  │ ←────── │   ator   │ ←────── │  (Hands) │
└──────────┘   결과    └──────────┘   출력    └──────────┘

역할 분담:
  Claude  → 전략적 판단, 코드 생성, 최종 검증, 아키텍처 설계
  Gemini  → 대량 조사, 문서 생성, 코드 리뷰, 번역, 브레인스토밍

사용법:
  python scripts/claude_gemini_orchestrator.py delegate --task research --prompt "마케팅 분석" --output logs/result.md
  python scripts/claude_gemini_orchestrator.py batch --manifest scripts/batch_manifest.json
  python scripts/claude_gemini_orchestrator.py status
"""

import argparse
import json
import subprocess
import sys
import os
import time
from datetime import datetime
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
LOGS_DIR = PROJECT_DIR / "logs"
QUEUE_FILE = PROJECT_DIR / "logs" / "gemini_task_queue.json"
HISTORY_FILE = PROJECT_DIR / "logs" / "gemini_task_history.json"


# ─── Task Templates ──────────────────────────────────────────
TASK_TEMPLATES = {
    "marketing_analysis": {
        "type": "research",
        "prompt": """seoulmna.kr 플랫폼의 마케팅 전략을 분석하세요.

## 분석 항목
1. **타겟 세그먼트**: 개인 vs 기관, 건설업체 규모별
2. **서비스 차별화**: admini.kr/superlawyer.co.kr 대비 강점
3. **가격 전략**: Free/Premium/Enterprise 3티어
4. **채널 전략**: SEO, 커뮤니티, 네트워크, 카카오톡
5. **핵심 메시지**: 가치 제안 5개

## 주요 경쟁사
- admini.kr: AI행정사 (20+ 서비스, SaaS 9~25만/월)
- superlawyer.co.kr: AI법률 (법률 서비스 전문)

## 우리 강점
- 건설업 양도양수 AI (특허 출원 중)
- 전기/정보통신/소방 업종 전문
- 시장 적합도 해석 (단순 가격 계산기 X)

한국어 마크다운 보고서로 작성.""",
        "output": "logs/marketing_strategy_analysis_latest.md",
        "context_file": "MASTERPLAN.md"
    },

    "design_system": {
        "type": "document",
        "prompt": """seoulmna.kr 디자인 시스템 스펙을 작성하세요.

## 기본 원칙
- 메인 컬러: #003764 (네이비)
- 디자인 모티브: 토스(Toss) — 1-thing-per-1-page, Casual Concept
- 100% 오리지널 (저작권 무관)

## 포함 항목
1. **컬러 시스템**: Primary/Secondary/Accent/Semantic/Neutral
   - Primary: #003764, Light: #0A4D8C, Dark: #002244
   - Secondary: #00A3FF, Success: #00C48C, Warning: #FFB800, Error: #FF4757

2. **타이포그래피**: Pretendard 기반 스케일 (14/16/18/24/32/40px)

3. **컴포넌트 패턴** (토스 모티브, 오리지널 구현):
   - BottomCTA, ResultCard, StepIndicator, ListRow, Badge
   - InputGroup, AlertBanner, SectorChip

4. **스페이싱**: 4px 베이스 유닛, 20/32px 패딩

5. **모션**: 200ms ease-in-out, 슬라이드 전환 300ms

6. **접근성**: APCA 기준 명도 대비, 터치 타겟 44px

한국어 마크다운 스펙 문서로 작성.""",
        "output": "docs/design_system_spec.md"
    },

    "codex_commands": {
        "type": "document",
        "prompt": """다음 두 가지 기능의 구현 노트를 작성하세요.

## 기능 1: 배너 텍스트 정렬 최적화
- 현재: 오른쪽 사이드바 배너에 "대표 행정사 카카오톡 오픈채팅 상담 / 010-9926-8661" 텍스트
- 요구사항: 줄바꿈을 자연스럽게, 왼쪽/가운데/오른쪽 정렬을 콘텐츠 밸런스에 따라 자동 판단
- 대상 파일: yangdo_calculator.py (Python f-string HTML 생성)
- 고려사항: CSS text-align 동적 결정 로직

## 기능 2: 전년 대비 증감률 표시
- 현재: 양도가 계산 결과만 표시
- 요구사항: 같은 업종/실적 조건의 전년 양도가 대비 증감% 표시
  - 예: "2026년 양도가 0.9억 (전년 대비 +4.7%, 2025년 0.86억)"
- 대상 파일: yangdo_calculator.py
- 고려사항:
  - 전년 데이터 소스 (DB? 캐시? 하드코딩?)
  - 동일 조건 매칭 알고리즘
  - UI 표시 위치 (결과 카드 내부)

각 기능에 대해:
1. 수정 대상 파일 및 함수
2. 구현 접근법 2-3가지
3. 추천 접근법 및 이유
4. 코드 스켈레톤 (pseudo-code)

한국어 마크다운으로 작성.""",
        "output": "docs/codex_command_implementation_notes.md"
    },

    "qa_scenarios": {
        "type": "qa",
        "prompt": """전기/정보통신/소방 업종별 테스트 시나리오 매트릭스를 생성하세요.

## 시나리오 축
- 업종: 전기공사업, 정보통신공사업, 소방시설공사업
- 모드: 일반 양도, 분할, 합병
- 실적: 고실적, 중실적, 저실적, 무실적
- 자본금: 충족, 미달, 경계값
- 특수상황: zero-display, confidence cap 적용

## 출력 형식
| # | 업종 | 모드 | 실적 | 자본금 | 예상결과 | 검증포인트 |
각 시나리오에 대해 구체적인 입력값과 예상 출력값을 포함하세요.

한국어 마크다운 테이블로 작성.""",
        "output": "tests/qa_scenario_matrix_latest.md"
    },

    "patent_evidence": {
        "type": "document",
        "prompt": """seoulmna.kr AI 양도가 산정 시스템의 특허 근거를 정리하세요.

## 핵심 알고리즘
1. specialBalanceSectorName() — 전기/정보통신/소방 업종 판별
2. SPECIAL_BALANCE_AUTO_POLICIES — 업종별 정산 정책
3. singleCorePublicationCap() — 신뢰도 캡 제한
4. zero-display recovery guard — 3단계 CTA 복구
5. buildRecommendPanelFollowupPlan — 업종별 맞춤 안내

## 작성 항목
1. 각 알고리즘의 기술적 독창성
2. 선행 기술 대비 차별점
3. 산업적 효과 (양도가 정확도 향상, 리스크 감소)
4. 특허 청구항 초안 (3개)

한국어 마크다운으로 작성.""",
        "output": "docs/patent_evidence_latest.md"
    }
}


def ensure_dirs():
    """필요한 디렉토리 생성"""
    LOGS_DIR.mkdir(exist_ok=True)
    (PROJECT_DIR / "docs").mkdir(exist_ok=True)
    (PROJECT_DIR / "tests").mkdir(exist_ok=True)


def load_json(path: Path, default=None):
    if default is None:
        default = []
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def save_json(path: Path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def run_gemini(prompt: str, output_file: str = None, timeout: int = 120) -> dict:
    """Gemini CLI 실행 (비대화형 헤드리스 모드)"""
    cmd = ["gemini", "-p", prompt, "-o", "text"]

    # Google OAuth 인증 설정
    env = os.environ.copy()
    env["GOOGLE_GENAI_USE_GCA"] = "true"

    start = time.time()
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(PROJECT_DIR),
            encoding="utf-8",
            env=env
        )
        elapsed = time.time() - start

        if result.returncode != 0:
            return {
                "success": False,
                "error": result.stderr[:500],
                "elapsed_sec": round(elapsed, 1)
            }

        output = result.stdout.strip()

        # 파일 저장
        if output_file:
            out_path = PROJECT_DIR / output_file
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(output, encoding="utf-8")

        return {
            "success": True,
            "output_length": len(output),
            "output_file": output_file,
            "elapsed_sec": round(elapsed, 1),
            "preview": output[:300] + "..." if len(output) > 300 else output
        }

    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "error": f"Timeout after {timeout}s",
            "elapsed_sec": timeout
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "elapsed_sec": round(time.time() - start, 1)
        }


def delegate(args):
    """단일 작업 위임"""
    ensure_dirs()

    # 템플릿 사용 or 커스텀
    if args.template and args.template in TASK_TEMPLATES:
        tmpl = TASK_TEMPLATES[args.template]
        prompt = tmpl["prompt"]
        output = args.output or tmpl["output"]
        print(f"📋 Using template: {args.template}")
    else:
        prompt = args.prompt or sys.stdin.read()
        output = args.output

    # 컨텍스트 추가
    if args.context:
        ctx_path = PROJECT_DIR / args.context
        if ctx_path.exists():
            ctx = ctx_path.read_text(encoding="utf-8")[:3000]
            prompt = f"{prompt}\n\n---\n추가 컨텍스트:\n{ctx}"

    print(f"🚀 Gemini에 위임 중... (output: {output or 'stdout'})")
    result = run_gemini(prompt, output, timeout=args.timeout)

    if result["success"]:
        print(f"✅ 완료! {result['output_length']} chars, {result['elapsed_sec']}s")
        if output:
            print(f"   📄 {output}")
        else:
            print(result.get("preview", ""))
    else:
        print(f"❌ 실패: {result['error']}")

    # 히스토리 기록
    history = load_json(HISTORY_FILE)
    history.append({
        "timestamp": datetime.now().isoformat(),
        "template": getattr(args, "template", None),
        "output": output,
        **result
    })
    save_json(HISTORY_FILE, history[-50:])  # 최근 50건만 보관

    return result


def batch(args):
    """배치 실행 (매니페스트 기반)"""
    ensure_dirs()

    if args.manifest:
        manifest = load_json(Path(args.manifest))
    elif args.templates:
        manifest = [{"template": t} for t in args.templates.split(",")]
    else:
        # 기본: 전체 템플릿 실행
        manifest = [{"template": k} for k in TASK_TEMPLATES]

    print(f"📦 Batch execution: {len(manifest)} tasks")
    results = []

    for i, task in enumerate(manifest, 1):
        tmpl_name = task.get("template", "custom")
        print(f"\n{'='*50}")
        print(f"[{i}/{len(manifest)}] {tmpl_name}")
        print(f"{'='*50}")

        if tmpl_name in TASK_TEMPLATES:
            tmpl = TASK_TEMPLATES[tmpl_name]
            prompt = task.get("prompt", tmpl["prompt"])
            output = task.get("output", tmpl["output"])
        else:
            prompt = task.get("prompt", "")
            output = task.get("output")

        result = run_gemini(prompt, output, timeout=args.timeout)
        result["template"] = tmpl_name
        results.append(result)

        status = "✅" if result["success"] else "❌"
        print(f"{status} {tmpl_name}: {result.get('output_length', 0)} chars, {result['elapsed_sec']}s")

        # 요청 간 딜레이 (rate limit 방지)
        if i < len(manifest):
            time.sleep(2)

    # 결과 요약
    success = sum(1 for r in results if r["success"])
    print(f"\n{'='*50}")
    print(f"📊 결과: {success}/{len(results)} 성공")
    print(f"{'='*50}")

    # 배치 결과 저장
    batch_log = LOGS_DIR / f"gemini_batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    save_json(batch_log, results)
    print(f"📄 배치 로그: {batch_log}")

    return results


def status(args):
    """실행 히스토리 조회"""
    history = load_json(HISTORY_FILE)

    if not history:
        print("📭 실행 히스토리 없음")
        return

    print(f"📋 최근 실행 히스토리 ({len(history)}건)")
    print(f"{'─'*60}")

    for entry in history[-10:]:
        ts = entry.get("timestamp", "?")[:19]
        tmpl = entry.get("template", "custom") or "custom"
        success = "✅" if entry.get("success") else "❌"
        chars = entry.get("output_length", 0)
        secs = entry.get("elapsed_sec", 0)
        out = entry.get("output", "-")
        print(f"  {success} [{ts}] {tmpl:20s} → {out} ({chars} chars, {secs}s)")


def list_templates(args):
    """사용 가능한 템플릿 목록"""
    print("📋 사용 가능한 태스크 템플릿:")
    print(f"{'─'*60}")
    for name, tmpl in TASK_TEMPLATES.items():
        out = tmpl.get("output", "-")
        desc = tmpl["prompt"][:80].replace("\n", " ")
        print(f"  • {name:25s} → {out}")
        print(f"    {desc}...")
        print()


def main():
    parser = argparse.ArgumentParser(
        description="Claude ↔ Gemini CLI 협업 오케스트레이터"
    )
    subparsers = parser.add_subparsers(dest="command", help="명령")

    # delegate
    p_delegate = subparsers.add_parser("delegate", help="단일 작업 위임")
    p_delegate.add_argument("--template", "-t", help="태스크 템플릿 이름")
    p_delegate.add_argument("--prompt", "-p", help="커스텀 프롬프트")
    p_delegate.add_argument("--output", "-o", help="출력 파일 경로")
    p_delegate.add_argument("--context", "-c", help="컨텍스트 파일 경로")
    p_delegate.add_argument("--timeout", type=int, default=120, help="타임아웃(초)")
    p_delegate.set_defaults(func=delegate)

    # batch
    p_batch = subparsers.add_parser("batch", help="배치 실행")
    p_batch.add_argument("--manifest", "-m", help="매니페스트 JSON 파일")
    p_batch.add_argument("--templates", "-t", help="쉼표 구분 템플릿 목록")
    p_batch.add_argument("--timeout", type=int, default=120, help="개별 타임아웃(초)")
    p_batch.set_defaults(func=batch)

    # status
    p_status = subparsers.add_parser("status", help="실행 히스토리")
    p_status.set_defaults(func=status)

    # list
    p_list = subparsers.add_parser("list", help="템플릿 목록")
    p_list.set_defaults(func=list_templates)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    args.func(args)


if __name__ == "__main__":
    main()
