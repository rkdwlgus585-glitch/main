#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LAB_ROOT = ROOT / "workspace_partitions" / "site_session" / "wp_surface_lab"
DEFAULT_IA = ROOT / "logs" / "wordpress_platform_ia_latest.json"
DEFAULT_YANGDO_COPY = ROOT / "logs" / "yangdo_service_copy_packet_latest.json"
DEFAULT_PERMIT_COPY = ROOT / "logs" / "permit_service_copy_packet_latest.json"


def _load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _blueprint_basename(page: Dict[str, Any]) -> str:
    explicit = str(page.get("wordpress_page_slug") or "").strip().strip("/")
    if explicit:
        return explicit
    return str(page.get("slug") or "/").strip("/").replace("/", "-") or "home"


def _gutenberg_group(title: str, body: str, extra_class: str = "smna-shell smna-platform-band") -> str:
    return (
        f'<!-- wp:group {{"className":"{extra_class}"}} --><div class="wp-block-group {extra_class}">'
        f'<!-- wp:heading {{"level":2}} --><h2>{title}</h2><!-- /wp:heading -->'
        f'<!-- wp:paragraph --><p>{body}</p><!-- /wp:paragraph -->'
        f'</div><!-- /wp:group -->'
    )


def _buttons(buttons: List[Dict[str, str]]) -> str:
    items: List[str] = []
    for button in buttons:
        href = str(button.get("href") or "#")
        label = str(button.get("label") or "")
        class_name = str(button.get("className") or "smna-button")
        items.append(
            f'<!-- wp:button {{"className":"{class_name}"}} --><div class="wp-block-button {class_name}">'
            f'<a class="wp-block-button__link wp-element-button" href="{href}">{label}</a>'
            f"</div><!-- /wp:button -->"
        )
    return '<!-- wp:buttons {"className":"smna-button-row"} --><div class="wp-block-buttons smna-button-row">' + "".join(items) + "</div><!-- /wp:buttons -->"


def _columns(cards: List[Dict[str, str]]) -> str:
    rendered: List[str] = []
    for card in cards:
        rendered.append(
            '<!-- wp:column --><div class="wp-block-column">'
            f'<!-- wp:heading {{"level":3}} --><h3>{card.get("title")}</h3><!-- /wp:heading -->'
            f'<!-- wp:paragraph --><p>{card.get("body")}</p><!-- /wp:paragraph -->'
            "</div><!-- /wp:column -->"
        )
    return '<!-- wp:columns --><div class="wp-block-columns">' + "".join(rendered) + "</div><!-- /wp:columns -->"


def _home_page() -> str:
    return "\n".join(
        [
            '<!-- wp:pattern {"slug":"seoulmna-platform/home-hero"} /-->',
            _gutenberg_group(
                "서비스를 먼저 분기하고, 계산은 전용 페이지에서만 실행합니다.",
                "메인 플랫폼은 브랜드와 흐름 설명에 집중하고 실제 계산기는 서비스 페이지에서 버튼 클릭 후에만 엽니다.",
            ),
            _columns(
                [
                    {
                        "title": "AI 양도가 산정 + 유사매물 추천",
                        "body": "가격 범위만이 아니라 추천 라벨, 추천 이유, 추천 정밀도까지 함께 읽고 서비스 페이지에서 계산을 시작합니다.",
                    },
                    {
                        "title": "AI 인허가 사전검토",
                        "body": "등록기준, 증빙 체크리스트, 다음 조치를 분리된 서비스 페이지에서 단계적으로 확인합니다.",
                    },
                ]
            ),
            _buttons(
                [
                    {"href": "/yangdo", "label": "양도가 서비스 보기"},
                    {"href": "/permit", "label": "인허가 서비스 보기", "className": "smna-button--ghost"},
                ]
            ),
            _columns(
                [
                    {
                        "title": "매물은 .co.kr",
                        "body": "실제 매물 확인은 별도 매물 사이트에서 처리하고 계산·상담은 메인 플랫폼에서 해석합니다.",
                    },
                    {
                        "title": "계산은 .kr/_calc",
                        "body": "공개 계약은 .kr/_calc/*로 고정하고 실제 엔진 원점은 숨긴 채 유지합니다.",
                    },
                    {
                        "title": "상담 분기 우선",
                        "body": "사용자 입력과 추천 정밀도에 따라 시장 확인과 상담형 상세를 분리합니다.",
                    },
                ]
            ),
        ]
    )


def _yangdo_page(copy_packet: Dict[str, Any], listing_host: str) -> str:
    hero = copy_packet.get("hero") if isinstance(copy_packet.get("hero"), dict) else {}
    explanation_cards = copy_packet.get("explanation_cards") if isinstance(copy_packet.get("explanation_cards"), list) else []
    precision_sections = copy_packet.get("precision_sections") if isinstance(copy_packet.get("precision_sections"), list) else []
    cta_ladder = copy_packet.get("cta_ladder") if isinstance(copy_packet.get("cta_ladder"), dict) else {}
    public_detail_split = copy_packet.get("public_detail_split") if isinstance(copy_packet.get("public_detail_split"), dict) else {}
    copy_guardrails = copy_packet.get("copy_guardrails") if isinstance(copy_packet.get("copy_guardrails"), list) else []

    public_story = str(public_detail_split.get("public_story") or "공개 화면은 가격 범위, 추천 라벨, 추천 이유만 보여줍니다.")
    detail_story = str(public_detail_split.get("detail_story") or "상담형 상세에서는 일치축, 비일치축, 주의 신호를 함께 설명합니다.")
    market_cta = cta_ladder.get("primary_market_bridge") if isinstance(cta_ladder.get("primary_market_bridge"), dict) else {}
    consult_cta = cta_ladder.get("secondary_consult") if isinstance(cta_ladder.get("secondary_consult"), dict) else {}
    gate_shortcode = str(hero.get("gate_shortcode") or '[seoulmna_calc_gate type="yangdo"]')
    guardrail_text = "".join(f"<li>{item}</li>" for item in copy_guardrails)

    precision_columns = _columns(
        [
            {
                "title": str(section.get("label") or ""),
                "body": str(section.get("description") or ""),
            }
            for section in precision_sections
        ]
    )
    ctas = _buttons(
        [
            {
                "href": str(market_cta.get("target") or "/mna-market"),
                "label": str(market_cta.get("label") or "추천 매물 흐름 보기"),
            },
            {
                "href": str(consult_cta.get("target") or "/consult?intent=yangdo"),
                "label": str(consult_cta.get("label") or "상담형 상세 요청"),
                "className": "smna-button--ghost",
            },
        ]
    )
    return "\n".join(
        [
            '<!-- wp:group {"className":"smna-shell smna-card"} --><div class="wp-block-group smna-shell smna-card">'
            f'<!-- wp:paragraph {{"className":"smna-kicker"}} --><p class="smna-kicker">{hero.get("kicker")}</p><!-- /wp:paragraph -->'
            f'<!-- wp:heading {{"level":1}} --><h1>{hero.get("title")}</h1><!-- /wp:heading -->'
            f'<!-- wp:paragraph --><p>{hero.get("body")}</p><!-- /wp:paragraph -->'
            "</div><!-- /wp:group -->",
            f"<!-- wp:shortcode -->{gate_shortcode}<!-- /wp:shortcode -->",
            _gutenberg_group(
                "추천 결과는 가격표가 아니라 시장 적합도 해석입니다.",
                "추천은 가격 범위, 추천 라벨, 추천 이유를 먼저 보여주고 실제 매물 확인과 상담형 상세를 분기합니다.",
            ),
            _columns(explanation_cards[:3]),
            _gutenberg_group(
                "추천 정밀도는 세 단계로 공개합니다.",
                "우선 추천은 시장 확인 CTA를, 보조 검토는 상담형 상세 CTA를 먼저 강조합니다.",
            ),
            precision_columns,
            _gutenberg_group("공개 요약과 상담형 상세는 다르게 노출합니다.", public_story + " " + detail_story),
            _columns(
                [
                    {
                        "title": "공개 요약",
                        "body": "가격 범위, 추천 라벨, 추천 이유까지만 노출합니다.",
                    },
                    {
                        "title": "상담형 상세",
                        "body": "일치축, 비일치축, 주의 신호를 함께 설명합니다.",
                    },
                    {
                        "title": "운영 검수",
                        "body": "중복 매물 보정과 내부 지표는 운영 검수 화면에서만 확인합니다.",
                    },
                ]
            ),
            _gutenberg_group(
                "추천 매물은 .kr에서 해석하고 실제 확인은 별도 매물 사이트에서 합니다.",
                f"추천 매물 실제 확인은 별도 매물 사이트({listing_host})에서 진행하고, 계산과 해석은 메인 플랫폼에서 유지합니다.",
            ),
            ctas,
            '<!-- wp:group {"className":"smna-shell smna-platform-band"} --><div class="wp-block-group smna-shell smna-platform-band">'
            '<!-- wp:heading {"level":2} --><h2>운영 가드레일</h2><!-- /wp:heading -->'
            f'<!-- wp:list --><ul>{guardrail_text}</ul><!-- /wp:list -->'
            "</div><!-- /wp:group -->",
        ]
    )


def _permit_page_from_packet(copy_packet: Dict[str, Any]) -> str:
    hero = copy_packet.get("hero") if isinstance(copy_packet.get("hero"), dict) else {}
    explanation_cards = copy_packet.get("explanation_cards") if isinstance(copy_packet.get("explanation_cards"), list) else []
    cta_ladder = copy_packet.get("cta_ladder") if isinstance(copy_packet.get("cta_ladder"), dict) else {}
    gate_shortcode = str(hero.get("gate_shortcode") or '[seoulmna_calc_gate type="permit"]')
    consult_cta = cta_ladder.get("secondary_consult") if isinstance(cta_ladder.get("secondary_consult"), dict) else {}
    knowledge_cta = cta_ladder.get("supporting_knowledge") if isinstance(cta_ladder.get("supporting_knowledge"), dict) else {}
    decision_paths = copy_packet.get("decision_paths") if isinstance(copy_packet.get("decision_paths"), list) else []
    guardrails = copy_packet.get("copy_guardrails") if isinstance(copy_packet.get("copy_guardrails"), list) else []
    guardrail_text = "".join(f"<li>{item}</li>" for item in guardrails)
    decision_cards = _columns(
        [
            {
                "title": str(item.get("when") or ""),
                "body": str(item.get("decision") or ""),
            }
            for item in decision_paths
        ]
    )
    return "\n".join(
        [
            '<!-- wp:group {"className":"smna-shell smna-card"} --><div class="wp-block-group smna-shell smna-card">',
            f'<!-- wp:paragraph {{"className":"smna-kicker"}} --><p class="smna-kicker">{hero.get("kicker")}</p><!-- /wp:paragraph -->',
            f'<!-- wp:heading {{"level":1}} --><h1>{hero.get("title")}</h1><!-- /wp:heading -->',
            f'<!-- wp:paragraph --><p>{hero.get("body")}</p><!-- /wp:paragraph -->',
            "</div><!-- /wp:group -->",
            f"<!-- wp:shortcode -->{gate_shortcode}<!-- /wp:shortcode -->",
            _gutenberg_group(
                "사전검토는 즉시 승인처럼 보이게 하지 않고 부족 항목과 다음 조치를 먼저 분리합니다.",
                "등록기준 부족 항목, 증빙 체크리스트, 수동 검토 전환을 한 화면에서 읽을 수 있게 고정합니다.",
            ),
            _columns(explanation_cards[:3]),
            decision_cards,
            _buttons(
                [
                    {
                        "href": str(consult_cta.get("target") or "/consult?intent=permit"),
                        "label": str(consult_cta.get("label") or "인허가 상담 연결"),
                    },
                    {
                        "href": str(knowledge_cta.get("target") or "/knowledge"),
                        "label": str(knowledge_cta.get("label") or "등록기준 안내 보기"),
                        "className": "smna-button--ghost",
                    },
                ]
            ),
            '<!-- wp:group {"className":"smna-shell smna-platform-band"} --><div class="wp-block-group smna-shell smna-platform-band">'
            '<!-- wp:heading {"level":2} --><h2>운영 가드레일</h2><!-- /wp:heading -->'
            f'<!-- wp:list --><ul>{guardrail_text}</ul><!-- /wp:list -->'
            "</div><!-- /wp:group -->",
        ]
    )


def _permit_page() -> str:
    return "\n".join(
        [
            '<!-- wp:group {"className":"smna-shell smna-card"} --><div class="wp-block-group smna-shell smna-card">'
            '<!-- wp:paragraph {"className":"smna-kicker"} --><p class="smna-kicker">AI Permit</p><!-- /wp:paragraph -->'
            '<!-- wp:heading {"level":1} --><h1>등록기준 부족 항목을 먼저 확인하고 사전검토로 연결합니다.</h1><!-- /wp:heading -->'
            '<!-- wp:paragraph --><p>입력값과 등록기준의 차이를 먼저 설명하고, 증빙 체크리스트와 다음 조치를 단계적으로 확인합니다.</p><!-- /wp:paragraph -->'
            "</div><!-- /wp:group -->",
            '<!-- wp:shortcode -->[seoulmna_calc_gate type="permit" title="AI 인허가 사전검토" summary="버튼 클릭 전에는 계산 요청을 보내지 않습니다." button_label="인허가 사전검토 열기"]<!-- /wp:shortcode -->',
            _gutenberg_group(
                "사전검토 후에 증빙 체크리스트로 이어집니다.",
                "초기 화면에서는 무거운 계산을 하지 않고 서비스 페이지에서만 사전검토와 체크리스트 생성을 시작합니다.",
            ),
            _buttons(
                [
                    {"href": "/consult?intent=permit", "label": "인허가 상담 연결"},
                ]
            ),
        ]
    )


def _knowledge_page() -> str:
    return "\n".join(
        [
            '<!-- wp:group {"className":"smna-shell smna-card"} --><div class="wp-block-group smna-shell smna-card">'
            '<!-- wp:paragraph {"className":"smna-kicker"} --><p class="smna-kicker">Knowledge Base</p><!-- /wp:paragraph -->'
            '<!-- wp:heading {"level":1} --><h1>등록기준과 양도양수 해석을 콘텐츠로 먼저 설명합니다.</h1><!-- /wp:heading -->'
            '<!-- wp:paragraph --><p>지식베이스는 검색 유입을 받고 서비스 페이지로만 보내며 계산기 iframe은 만들지 않습니다.</p><!-- /wp:paragraph -->'
            "</div><!-- /wp:group -->",
            _buttons(
                [
                    {"href": "/permit", "label": "인허가 사전검토 보기"},
                    {"href": "/yangdo", "label": "양도가 서비스 보기", "className": "smna-button--ghost"},
                ]
            ),
        ]
    )


def _consult_page() -> str:
    return "\n".join(
        [
            '<!-- wp:group {"className":"smna-shell smna-card"} --><div class="wp-block-group smna-shell smna-card">'
            '<!-- wp:paragraph {"className":"smna-kicker"} --><p class="smna-kicker">Consult Routing</p><!-- /wp:paragraph -->'
            '<!-- wp:heading {"level":1} --><h1>상담은 양도가, 인허가, 기업진단으로 먼저 분기합니다.</h1><!-- /wp:heading -->'
            '<!-- wp:paragraph --><p>상담 페이지는 계산기보다 분기와 기본 정보를 먼저 보여주고 운영자가 빠르게 lane을 정할 수 있게 합니다.</p><!-- /wp:paragraph -->'
            '<!-- wp:list --><ul><li>양도가 문의</li><li>인허가 사전검토</li><li>기업진단 및 기타</li></ul><!-- /wp:list -->'
            "</div><!-- /wp:group -->",
            _buttons(
                [
                    {"href": "/consult?lane=form", "label": "상담 플로우 시작"},
                    {"href": "/yangdo", "label": "양도가 서비스 보기", "className": "smna-button--ghost"},
                    {"href": "/permit", "label": "인허가 서비스 보기", "className": "smna-button--ghost"},
                ]
            ),
        ]
    )


def _market_bridge_page(listing_host: str, page: Dict[str, Any]) -> str:
    cta = str(page.get("primary_cta") or f"https://{listing_host}")
    secondary = str(page.get("secondary_cta") or "/yangdo")
    return "\n".join(
        [
            '<!-- wp:group {"className":"smna-shell smna-card"} --><div class="wp-block-group smna-shell smna-card">'
            '<!-- wp:paragraph {"className":"smna-kicker"} --><p class="smna-kicker">Listing Market</p><!-- /wp:paragraph -->'
            '<!-- wp:heading {"level":1} --><h1>매물은 별도 사이트에서 보고 계산과 상담은 메인 플랫폼에서 처리합니다.</h1><!-- /wp:heading -->'
            '<!-- wp:paragraph --><p>.co.kr은 매물 사이트이고 계산기와 사전검토는 .kr 서비스 페이지에서만 실행합니다.</p><!-- /wp:paragraph -->'
            "</div><!-- /wp:group -->",
            _buttons(
                [
                    {"href": cta, "label": "매물 사이트 열기"},
                    {"href": secondary, "label": "양도가 서비스 보기", "className": "smna-button--ghost"},
                ]
            ),
        ]
    )


def _fallback_page(page: Dict[str, Any]) -> str:
    title = str(page.get("title") or "")
    goal = str(page.get("goal") or "")
    return (
        '<!-- wp:group {"className":"smna-shell smna-card"} --><div class="wp-block-group smna-shell smna-card">'
        f'<!-- wp:heading {{"level":1}} --><h1>{title}</h1><!-- /wp:heading -->'
        f'<!-- wp:paragraph --><p>{goal}</p><!-- /wp:paragraph -->'
        "</div><!-- /wp:group -->"
    )


def _gutenberg_page(page: Dict[str, Any], listing_host: str, yangdo_copy_packet: Dict[str, Any], permit_copy_packet: Dict[str, Any]) -> str:
    page_id = str(page.get("page_id") or "")
    if page_id == "home":
        return _home_page()
    if page_id == "yangdo":
        if bool((yangdo_copy_packet.get("summary") or {}).get("packet_ready")):
            return _yangdo_page(yangdo_copy_packet, listing_host)
        return _fallback_page(page)
    if page_id == "permit":
        if bool((permit_copy_packet.get("summary") or {}).get("packet_ready")):
            return _permit_page_from_packet(permit_copy_packet)
        return _permit_page()
    if page_id == "knowledge":
        return _knowledge_page()
    if page_id == "consult":
        return _consult_page()
    if page_id == "market_bridge":
        return _market_bridge_page(listing_host, page)
    return _fallback_page(page)


def build_wp_platform_blueprints(*, lab_root: Path, ia_path: Path, yangdo_service_copy_path: Path | None = None, permit_service_copy_path: Path | None = None) -> Dict[str, Any]:
    ia = _load_json(ia_path)
    yangdo_service_copy = _load_json(yangdo_service_copy_path or Path())
    permit_service_copy = _load_json(permit_service_copy_path or Path())
    theme_root = lab_root / "staging" / "wp-content" / "themes" / "seoulmna-platform-child"
    blueprint_root = theme_root / "blueprints"
    listing_host = str(ia.get("topology", {}).get("listing_host") or "seoulmna.co.kr").replace("https://", "").rstrip("/")
    pages: List[Dict[str, Any]] = list(ia.get("pages") or [])
    generated_files: List[str] = []
    for page in pages:
        slug = _blueprint_basename(page)
        content = _gutenberg_page(page, listing_host, yangdo_service_copy, permit_service_copy)
        path = blueprint_root / f"{slug}.html"
        _write(path, content)
        generated_files.append(str(path))

    navigation_path = blueprint_root / "navigation.json"
    _write(navigation_path, json.dumps(ia.get("navigation", {}), ensure_ascii=False, indent=2))
    generated_files.append(str(navigation_path))

    readme_path = blueprint_root / "README.md"
    _write(
        readme_path,
        "# SeoulMNA Platform Blueprints\n\n"
        "- Import these Gutenberg HTML snippets into staging pages first.\n"
        "- Keep homepage and knowledge pages CTA-only.\n"
        "- Use `[seoulmna_calc_gate]` only on dedicated service pages.\n"
        "- `/yangdo` copy is sourced from `yangdo_service_copy_packet_latest` when available.\n"
        "- `/permit` copy is sourced from `permit_service_copy_packet_latest` when available.\n",
    )
    generated_files.append(str(readme_path))

    lazy_gate_pages = [row["page_id"] for row in pages if row.get("calculator_policy") == "lazy_gate_shortcode"]
    cta_only_pages = [row["page_id"] for row in pages if row.get("calculator_policy") == "cta_only_no_iframe"]

    return {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "lab_root": str(lab_root),
        "theme_slug": "seoulmna-platform-child",
        "blueprint_root": str(blueprint_root),
        "service_copy_packet_used": bool((yangdo_service_copy.get("summary") or {}).get("packet_ready")),
        "permit_service_copy_packet_used": bool((permit_service_copy.get("summary") or {}).get("packet_ready")),
        "pages": [
            {
                "page_id": row.get("page_id"),
                "slug": row.get("slug"),
                "wordpress_page_slug": row.get("wordpress_page_slug"),
                "title": row.get("title"),
                "calculator_policy": row.get("calculator_policy"),
                "blueprint_file": str(blueprint_root / f"{_blueprint_basename(row)}.html"),
            }
            for row in pages
        ],
        "summary": {
            "blueprint_count": len(pages),
            "lazy_gate_pages_count": len(lazy_gate_pages),
            "cta_only_pages_count": len(cta_only_pages),
            "lazy_gate_pages": lazy_gate_pages,
            "cta_only_pages": cta_only_pages,
            "navigation_ready": True,
        },
        "next_actions": [
            "WordPress staging에 페이지를 만들고 blueprint HTML을 반영합니다.",
            "홈과 지식베이스 페이지는 계산기 iframe 없이 CTA만 유지합니다.",
            "양도가와 인허가 서비스 페이지에만 lazy gate shortcode를 둡니다.",
        ],
        "generated_files": generated_files,
    }


def _to_markdown(payload: Dict[str, Any]) -> str:
    lines = [
        "# WordPress Platform Blueprints",
        "",
        f"- blueprint_root: {payload.get('blueprint_root')}",
        f"- blueprint_count: {payload.get('summary', {}).get('blueprint_count')}",
        f"- service_copy_packet_used: {payload.get('service_copy_packet_used')}",
        f"- permit_service_copy_packet_used: {payload.get('permit_service_copy_packet_used')}",
        f"- lazy_gate_pages: {', '.join(payload.get('summary', {}).get('lazy_gate_pages') or []) or '(none)'}",
        f"- cta_only_pages: {', '.join(payload.get('summary', {}).get('cta_only_pages') or []) or '(none)'}",
        "",
        "## Files",
    ]
    for path in payload.get("generated_files", []):
        lines.append(f"- {path}")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Scaffold WordPress Gutenberg blueprint files for SeoulMNA platform pages.")
    parser.add_argument("--lab-root", type=Path, default=DEFAULT_LAB_ROOT)
    parser.add_argument("--ia", type=Path, default=DEFAULT_IA)
    parser.add_argument("--yangdo-service-copy", type=Path, default=DEFAULT_YANGDO_COPY)
    parser.add_argument("--permit-service-copy", type=Path, default=DEFAULT_PERMIT_COPY)
    parser.add_argument("--json", type=Path, default=ROOT / "logs" / "wp_platform_blueprints_latest.json")
    parser.add_argument("--md", type=Path, default=ROOT / "logs" / "wp_platform_blueprints_latest.md")
    args = parser.parse_args()

    payload = build_wp_platform_blueprints(
        lab_root=args.lab_root,
        ia_path=args.ia,
        yangdo_service_copy_path=args.yangdo_service_copy,
        permit_service_copy_path=args.permit_service_copy,
    )
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.md.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    args.md.write_text(_to_markdown(payload), encoding="utf-8")
    print(f"[ok] wrote {args.json}")
    print(f"[ok] wrote {args.md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
