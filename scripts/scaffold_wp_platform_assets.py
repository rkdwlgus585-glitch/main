#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LAB_ROOT = ROOT / "workspace_partitions" / "site_session" / "wp_surface_lab"
DEFAULT_SURFACE_AUDIT = ROOT / "logs" / "surface_stack_audit_latest.json"
DEFAULT_ASTRA_REFERENCE = ROOT / "logs" / "astra_design_reference_latest.json"
THEME_SLUG = "seoulmna-platform-child"
PLUGIN_SLUG = "seoulmna-platform-bridge"


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


def _theme_style_css() -> str:
    return """/*
Theme Name: SeoulMNA Platform Child
Theme URI: https://seoulmna.kr
Description: Astra child theme scaffold for the SeoulMNA platform surface.
Author: Codex
Template: astra
Version: 0.1.0
Text Domain: seoulmna-platform-child
*/

:root {
  --smna-bg: #f4f1ea;
  --smna-surface: #fffdf8;
  --smna-surface-strong: #f1e6d4;
  --smna-ink: #1f2a21;
  --smna-muted: #5b615f;
  --smna-line: #d6c4a8;
  --smna-accent: #c97b2a;
  --smna-accent-strong: #8d5220;
  --smna-forest: #254034;
  --smna-sand: #e8d5b5;
  --smna-radius: 28px;
  --smna-shadow: 0 18px 55px rgba(40, 34, 24, 0.12);
  --smna-content: min(1180px, calc(100vw - 48px));
}
"""


def _theme_platform_css() -> str:
    return """body.seoulmna-platform {
  background: radial-gradient(circle at top left, rgba(201,123,42,0.16), transparent 34%), var(--smna-bg);
  color: var(--smna-ink);
}

.smna-shell {
  width: var(--smna-content);
  margin: 0 auto;
}

.smna-hero {
  display: grid;
  grid-template-columns: 1.4fr 0.9fr;
  gap: 28px;
  padding: 56px 0 44px;
}

.smna-card,
.smna-feature,
.smna-service-card,
.smna-trust-card,
.smna-calc-gate {
  background: linear-gradient(180deg, rgba(255,255,255,0.95), rgba(255,249,240,0.95));
  border: 1px solid var(--smna-line);
  border-radius: var(--smna-radius);
  box-shadow: var(--smna-shadow);
}

.smna-card {
  padding: 32px;
}

.smna-kicker {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  padding: 8px 14px;
  border-radius: 999px;
  background: rgba(37, 64, 52, 0.08);
  color: var(--smna-forest);
  font-size: 13px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.smna-hero h1,
.smna-service-card h3,
.smna-feature h3,
.smna-calc-gate__title {
  font-family: "Noto Serif KR", "Malgun Gothic", serif;
  letter-spacing: -0.03em;
}

.smna-hero h1 {
  font-size: clamp(2.6rem, 4vw, 4.4rem);
  line-height: 1.05;
  margin: 20px 0 14px;
}

.smna-hero p,
.smna-feature p,
.smna-service-card p,
.smna-calc-gate__summary {
  color: var(--smna-muted);
  font-size: 1rem;
  line-height: 1.75;
}

.smna-button-row,
.smna-calc-gate__actions {
  display: flex;
  flex-wrap: wrap;
  gap: 14px;
  margin-top: 24px;
}

.smna-button,
.smna-calc-gate__button,
.smna-calc-gate__link {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  min-height: 48px;
  padding: 0 18px;
  border-radius: 999px;
  text-decoration: none;
  font-weight: 700;
}

.smna-button,
.smna-calc-gate__button {
  background: var(--smna-forest);
  color: #fff;
  border: 0;
  cursor: pointer;
}

.smna-button--ghost,
.smna-calc-gate__link {
  background: rgba(37, 64, 52, 0.06);
  color: var(--smna-forest);
}

.smna-stat-grid,
.smna-service-grid,
.smna-trust-grid,
.smna-calc-grid {
  display: grid;
  gap: 18px;
}

.smna-stat-grid {
  grid-template-columns: repeat(3, 1fr);
  margin-top: 18px;
}

.smna-service-grid,
.smna-calc-grid {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.smna-trust-grid {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.smna-feature,
.smna-service-card,
.smna-trust-card {
  padding: 24px;
}

.smna-platform-band {
  margin: 26px 0;
  padding: 20px 24px;
  border: 1px dashed rgba(37, 64, 52, 0.22);
  border-radius: 24px;
  background: rgba(255, 255, 255, 0.6);
}

.smna-calc-gate {
  padding: 24px;
}

.smna-calc-gate__frame-wrap {
  margin-top: 18px;
  min-height: 0;
}

.smna-calc-gate__frame-wrap[data-loaded="false"] {
  display: none;
}

.smna-calc-gate__frame {
  width: 100%;
  min-height: 780px;
  border: 1px solid var(--smna-line);
  border-radius: 24px;
  background: #fff;
}

.smna-calc-gate__hint {
  margin-top: 14px;
  font-size: 0.92rem;
  color: var(--smna-muted);
}

@media (max-width: 980px) {
  .smna-hero,
  .smna-service-grid,
  .smna-trust-grid,
  .smna-calc-grid {
    grid-template-columns: 1fr;
  }

  .smna-stat-grid {
    grid-template-columns: 1fr 1fr;
  }
}

@media (max-width: 640px) {
  .smna-shell {
    width: min(100vw - 28px, 100%);
  }

  .smna-hero {
    padding: 38px 0 30px;
  }

  .smna-card,
  .smna-feature,
  .smna-service-card,
  .smna-trust-card,
  .smna-calc-gate {
    padding: 20px;
  }

  .smna-stat-grid {
    grid-template-columns: 1fr;
  }

  .smna-calc-gate__frame {
    min-height: 640px;
  }
}
"""


def _theme_functions_php() -> str:
    return """<?php
if (!defined('ABSPATH')) {
    exit;
}

add_action('after_setup_theme', function () {
    load_child_theme_textdomain('seoulmna-platform-child', get_stylesheet_directory() . '/languages');
    add_theme_support('editor-styles');
    add_editor_style('assets/css/platform.css');
    register_nav_menus([
        'primary-platform' => __('Primary Platform Navigation', 'seoulmna-platform-child'),
        'knowledge-hub' => __('Knowledge Hub Navigation', 'seoulmna-platform-child'),
        'footer-platform' => __('Footer Platform Navigation', 'seoulmna-platform-child'),
    ]);
});

add_action('wp_enqueue_scripts', function () {
    wp_enqueue_style('astra-parent-style', get_template_directory_uri() . '/style.css', [], wp_get_theme(get_template())->get('Version'));
    wp_enqueue_style('seoulmna-platform-child-style', get_stylesheet_uri(), ['astra-parent-style'], wp_get_theme()->get('Version'));
    wp_enqueue_style('seoulmna-platform-child-platform', get_stylesheet_directory_uri() . '/assets/css/platform.css', ['seoulmna-platform-child-style'], wp_get_theme()->get('Version'));
    wp_enqueue_script('seoulmna-platform-child-runtime', get_stylesheet_directory_uri() . '/assets/js/platform.js', [], wp_get_theme()->get('Version'), true);
});

add_filter('body_class', function ($classes) {
    $classes[] = 'seoulmna-platform';
    return $classes;
});

add_action('init', function () {
    remove_action('wp_head', 'print_emoji_detection_script', 7);
    remove_action('wp_print_styles', 'print_emoji_styles');
});

require_once get_stylesheet_directory() . '/inc/platform-patterns.php';
"""


def _theme_runtime_js() -> str:
    return """document.addEventListener('click', function (event) {
  var target = event.target;
  if (!(target instanceof HTMLElement)) {
    return;
  }
  var anchor = target.closest('[data-smna-scroll-target]');
  if (!anchor) {
    return;
  }
  var selector = anchor.getAttribute('data-smna-scroll-target');
  if (!selector) {
    return;
  }
  var next = document.querySelector(selector);
  if (!next) {
    return;
  }
  event.preventDefault();
  next.scrollIntoView({ behavior: 'smooth', block: 'start' });
});
"""


def _theme_patterns_php() -> str:
    return """<?php
if (!defined('ABSPATH')) {
    exit;
}

add_action('init', function () {
    register_block_pattern_category('seoulmna-platform', [
        'label' => __('SeoulMNA Platform', 'seoulmna-platform-child'),
    ]);

    register_block_pattern('seoulmna-platform/home-hero', [
        'title' => __('Platform Hero', 'seoulmna-platform-child'),
        'categories' => ['seoulmna-platform'],
        'content' => '<!-- wp:group {"className":"smna-shell smna-hero"} --><div class="wp-block-group smna-shell smna-hero"><!-- wp:group {"className":"smna-card"} --><div class="wp-block-group smna-card"><!-- wp:paragraph {"className":"smna-kicker"} --><p class="smna-kicker">AI Construction Operations Platform</p><!-- /wp:paragraph --><!-- wp:heading {"level":1} --><h1>양도가와 인허가를 하나의 플랫폼에서 분기 운영합니다.</h1><!-- /wp:heading --><!-- wp:paragraph --><p>서울건설정보 메인 플랫폼은 WordPress/Astra를 유지하되, 계산기는 클릭 후 열리는 게이트형으로만 연결합니다. 초기 렌더에는 iframe을 만들지 않아 트래픽 누수를 막습니다.</p><!-- /wp:paragraph --><!-- wp:buttons {"className":"smna-button-row"} --><div class="wp-block-buttons smna-button-row"><!-- wp:button {"className":"smna-button"} --><div class="wp-block-button smna-button"><a class="wp-block-button__link wp-element-button" href="/yangdo">양도가 보기</a></div><!-- /wp:button --><!-- wp:button {"className":"smna-button--ghost"} --><div class="wp-block-button smna-button--ghost"><a class="wp-block-button__link wp-element-button" href="/permit">인허가 보기</a></div><!-- /wp:button --></div><!-- /wp:buttons --></div><!-- /wp:group --><!-- wp:group {"className":"smna-card"} --><div class="wp-block-group smna-card"><!-- wp:columns {"className":"smna-stat-grid"} --><div class="wp-block-columns smna-stat-grid"><!-- wp:column --><div class="wp-block-column"><!-- wp:heading {"level":3} --><h3>양도양수</h3><!-- /wp:heading --><!-- wp:paragraph --><p>비교 거래 정규화, 중복 매물 클러스터링, 신뢰도 기반 범위 산정</p><!-- /wp:paragraph --></div><!-- /wp:column --><!-- wp:column --><div class="wp-block-column"><!-- wp:heading {"level":3} --><h3>인허가</h3><!-- /wp:heading --><!-- wp:paragraph --><p>등록기준 카탈로그, 부족항목 판정, 증빙 체크리스트</p><!-- /wp:paragraph --></div><!-- /wp:column --><!-- wp:column --><div class="wp-block-column"><!-- wp:heading {"level":3} --><h3>운영</h3><!-- /wp:heading --><!-- wp:paragraph --><p>서울건설정보 메인 front와 .co.kr 내부 widget 채널을 분리 운영</p><!-- /wp:paragraph --></div><!-- /wp:column --></div><!-- /wp:columns --></div><!-- /wp:group --></div><!-- /wp:group -->',
    ]);

    register_block_pattern('seoulmna-platform/service-gateway', [
        'title' => __('Service Gateway', 'seoulmna-platform-child'),
        'categories' => ['seoulmna-platform'],
        'content' => '<!-- wp:group {"className":"smna-shell smna-service-grid"} --><div class="wp-block-group smna-shell smna-service-grid"><!-- wp:group {"className":"smna-service-card"} --><div class="wp-block-group smna-service-card"><!-- wp:heading {"level":3} --><h3>AI 양도가 산정</h3><!-- /wp:heading --><!-- wp:paragraph --><p>양도양수 서비스 페이지로 이동한 뒤 lazy gate를 통해 계산을 시작합니다. 홈과 지식 페이지에는 계산기 iframe을 직접 두지 않습니다.</p><!-- /wp:paragraph --><!-- wp:buttons {"className":"smna-button-row"} --><div class="wp-block-buttons smna-button-row"><!-- wp:button {"className":"smna-button"} --><div class="wp-block-button smna-button"><a class="wp-block-button__link wp-element-button" href="/yangdo">양도가 서비스 보기</a></div><!-- /wp:button --></div><!-- /wp:buttons --></div><!-- /wp:group --><!-- wp:group {"className":"smna-service-card"} --><div class="wp-block-group smna-service-card"><!-- wp:heading {"level":3} --><h3>AI 인허가 사전검토</h3><!-- /wp:heading --><!-- wp:paragraph --><p>인허가 서비스 페이지로 이동한 뒤 lazy gate를 통해 사전검토를 시작합니다. 초기 렌더에는 계산 트래픽을 발생시키지 않습니다.</p><!-- /wp:paragraph --><!-- wp:buttons {"className":"smna-button-row"} --><div class="wp-block-buttons smna-button-row"><!-- wp:button {"className":"smna-button"} --><div class="wp-block-button smna-button"><a class="wp-block-button__link wp-element-button" href="/permit">인허가 서비스 보기</a></div><!-- /wp:button --></div><!-- /wp:buttons --></div><!-- /wp:group --></div><!-- /wp:group -->',
    ]);
});
"""


def _theme_theme_json() -> str:
    payload = {
        "$schema": "https://schemas.wp.org/trunk/theme.json",
        "version": 3,
        "settings": {
            "appearanceTools": True,
            "layout": {
                "contentSize": "1180px",
                "wideSize": "1320px",
            },
            "color": {
                "palette": [
                    {"slug": "ink", "name": "Ink", "color": "#1f2a21"},
                    {"slug": "forest", "name": "Forest", "color": "#254034"},
                    {"slug": "sand", "name": "Sand", "color": "#e8d5b5"},
                    {"slug": "surface", "name": "Surface", "color": "#fffdf8"},
                    {"slug": "accent", "name": "Accent", "color": "#c97b2a"},
                ]
            },
            "typography": {
                "fontFamilies": [
                    {
                        "slug": "body",
                        "name": "Body",
                        "fontFamily": '"Noto Sans KR", "Malgun Gothic", sans-serif',
                    },
                    {
                        "slug": "display",
                        "name": "Display",
                        "fontFamily": '"Noto Serif KR", "Malgun Gothic", serif',
                    },
                ],
                "fontSizes": [
                    {"slug": "sm", "size": "14px", "name": "Small"},
                    {"slug": "md", "size": "18px", "name": "Medium"},
                    {"slug": "lg", "size": "32px", "name": "Large"},
                    {"slug": "xl", "size": "54px", "name": "XL"},
                ],
            },
        },
    }
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"


def _plugin_php(kr_host: str) -> str:
    consumer_base = f"https://{kr_host}/_calc"
    return f"""<?php
/**
 * Plugin Name: SeoulMNA Platform Bridge
 * Description: Lazy calculator gates for Yangdo and Permit without initial iframe traffic.
 * Version: 0.1.0
 * Author: Codex
 * Text Domain: seoulmna-platform-bridge
 */

if (!defined('ABSPATH')) {{
    exit;
}}

const SMNA_PLATFORM_BRIDGE_VERSION = '0.1.0';
const SMNA_PLATFORM_BRIDGE_DEFAULT_PUBLIC_MOUNT_BASE = '{consumer_base}';

function smna_platform_bridge_public_mount_base() {{
    $base = apply_filters('smna_platform_bridge_public_mount_base', SMNA_PLATFORM_BRIDGE_DEFAULT_PUBLIC_MOUNT_BASE);
    return untrailingslashit((string) $base);
}}

function smna_platform_bridge_widget_url($type) {{
    $map = [
        'yangdo' => smna_platform_bridge_public_mount_base() . '/yangdo?embed=1',
        'permit' => smna_platform_bridge_public_mount_base() . '/permit?embed=1',
    ];
    $type = sanitize_key((string) $type);
    $url = isset($map[$type]) ? $map[$type] : $map['yangdo'];
    return (string) apply_filters('smna_platform_bridge_widget_url', $url, $type, $map);
}}

add_action('wp_enqueue_scripts', function () {{
    wp_register_style(
        'smna-platform-bridge',
        plugins_url('assets/css/bridge.css', __FILE__),
        [],
        SMNA_PLATFORM_BRIDGE_VERSION
    );
    wp_register_script(
        'smna-platform-bridge',
        plugins_url('assets/js/bridge.js', __FILE__),
        [],
        SMNA_PLATFORM_BRIDGE_VERSION,
        true
    );
}});

function smna_platform_bridge_render_gate($atts = []) {{
    $atts = shortcode_atts([
        'type' => 'yangdo',
        'title' => 'AI calculator',
        'summary' => '',
        'button_label' => 'Open calculator',
        'mount_url' => '',
        'full_link_label' => 'Open full screen',
        'gate_notice' => 'Calculator traffic starts only after click.',
    ], $atts, 'seoulmna_calc_gate');

    $type = sanitize_key((string) $atts['type']);
    $title = sanitize_text_field((string) $atts['title']);
    $summary = wp_kses_post((string) $atts['summary']);
    $button_label = sanitize_text_field((string) $atts['button_label']);
    $full_link_label = sanitize_text_field((string) $atts['full_link_label']);
    $gate_notice = sanitize_text_field((string) $atts['gate_notice']);
    $mount_url = esc_url_raw((string) ($atts['mount_url'] ?: smna_platform_bridge_widget_url($type)));
    $instance_id = 'smna-calc-' . wp_generate_uuid4();

    wp_enqueue_style('smna-platform-bridge');
    wp_enqueue_script('smna-platform-bridge');

    ob_start();
    ?>
    <section class="smna-calc-gate" data-smna-calc-gate="true" data-smna-calc-type="<?php echo esc_attr($type); ?>">
        <div class="smna-calc-gate__header">
            <h3 class="smna-calc-gate__title"><?php echo esc_html($title); ?></h3>
            <?php if ($summary !== '') : ?>
                <div class="smna-calc-gate__summary"><?php echo wp_kses_post(wpautop($summary)); ?></div>
            <?php endif; ?>
        </div>
        <div class="smna-calc-gate__actions">
            <button
                type="button"
                class="smna-calc-gate__button"
                data-smna-calc-launch="true"
                data-smna-target="<?php echo esc_attr($instance_id); ?>"
                data-smna-src="<?php echo esc_url($mount_url); ?>"
                data-smna-title="<?php echo esc_attr($title); ?>"
            >
                <?php echo esc_html($button_label); ?>
            </button>
            <a class="smna-calc-gate__link" href="<?php echo esc_url($mount_url); ?>" target="_blank" rel="noopener noreferrer">
                <?php echo esc_html($full_link_label); ?>
            </a>
        </div>
        <p class="smna-calc-gate__hint"><?php echo esc_html($gate_notice); ?></p>
        <div id="<?php echo esc_attr($instance_id); ?>" class="smna-calc-gate__frame-wrap" data-loaded="false"></div>
    </section>
    <?php
    return (string) ob_get_clean();
}}
add_shortcode('seoulmna_calc_gate', 'smna_platform_bridge_render_gate');
"""


def _plugin_js() -> str:
    return """document.addEventListener('click', function (event) {
  var target = event.target;
  if (!(target instanceof HTMLElement)) {
    return;
  }
  var button = target.closest('[data-smna-calc-launch="true"]');
  if (!button) {
    return;
  }
  event.preventDefault();
  var mountId = button.getAttribute('data-smna-target');
  var src = button.getAttribute('data-smna-src');
  var title = button.getAttribute('data-smna-title') || 'Calculator';
  if (!mountId || !src) {
    return;
  }
  var mount = document.getElementById(mountId);
  if (!mount) {
    return;
  }
  if (mount.dataset.loaded === 'true') {
    mount.scrollIntoView({ behavior: 'smooth', block: 'start' });
    return;
  }
  var iframe = document.createElement('iframe');
  iframe.className = 'smna-calc-gate__frame';
  iframe.src = src;
  iframe.title = title;
  iframe.loading = 'lazy';
  iframe.referrerPolicy = 'strict-origin-when-cross-origin';
  iframe.setAttribute('sandbox', 'allow-scripts allow-forms allow-popups');
  mount.appendChild(iframe);
  mount.dataset.loaded = 'true';
  mount.scrollIntoView({ behavior: 'smooth', block: 'start' });
});
"""


def _plugin_css() -> str:
    return """.smna-calc-gate__summary p {
  margin: 0;
}

.smna-calc-gate__frame-wrap {
  transition: opacity 180ms ease;
}

.smna-calc-gate__frame-wrap[data-loaded="true"] {
  display: block;
  opacity: 1;
}
"""


def build_wp_platform_assets(*, lab_root: Path, surface_audit_path: Path, astra_reference_path: Path) -> Dict[str, Any]:
    surface_audit = _load_json(surface_audit_path)
    astra_reference = _load_json(astra_reference_path)
    kr_host = str(surface_audit.get('surfaces', {}).get('kr', {}).get('host') or 'seoulmna.kr')
    co_host = str(surface_audit.get('surfaces', {}).get('co', {}).get('host') or 'seoulmna.co.kr')
    staging_root = lab_root / 'staging' / 'wp-content'
    theme_root = staging_root / 'themes' / THEME_SLUG
    plugin_root = staging_root / 'plugins' / PLUGIN_SLUG

    files = {
        theme_root / 'style.css': _theme_style_css(),
        theme_root / 'functions.php': _theme_functions_php(),
        theme_root / 'theme.json': _theme_theme_json(),
        theme_root / 'assets' / 'css' / 'platform.css': _theme_platform_css(),
        theme_root / 'assets' / 'js' / 'platform.js': _theme_runtime_js(),
        theme_root / 'inc' / 'platform-patterns.php': _theme_patterns_php(),
        theme_root / 'README.md': "# SeoulMNA Platform Child\n\n- Parent theme: Astra\n- Purpose: platform IA, gated calculator mounting, and brand layout tokens for seoulmna.kr\n",
        plugin_root / f'{PLUGIN_SLUG}.php': _plugin_php(kr_host),
        plugin_root / 'assets' / 'js' / 'bridge.js': _plugin_js(),
        plugin_root / 'assets' / 'css' / 'bridge.css': _plugin_css(),
        plugin_root / 'README.md': "# SeoulMNA Platform Bridge\n\n- Shortcode: [seoulmna_calc_gate type=\"yangdo\"]\n- Policy: never render iframe before explicit click\n",
    }

    for path, content in files.items():
        _write(path, content)

    payload = {
        'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'lab_root': str(lab_root),
        'theme': {
            'slug': THEME_SLUG,
            'path': str(theme_root),
            'parent_theme': 'astra',
            'kr_host': kr_host,
            'ready': True,
            'files': [str(path) for path in files if str(path).startswith(str(theme_root))],
        },
        'plugin': {
            'slug': PLUGIN_SLUG,
            'path': str(plugin_root),
            'public_mount_host': kr_host,
            'public_mount_base': f'https://{kr_host}/_calc',
            'listing_host': co_host,
            'shortcodes': ['seoulmna_calc_gate'],
            'lazy_iframe_policy': True,
            'ready': True,
            'files': [str(path) for path in files if str(path).startswith(str(plugin_root))],
        },
        'calculator_mount_policy': {
            'homepage': 'cta_only_no_iframe',
            'service_pages': 'lazy_gate_shortcode',
            'knowledge_posts': 'cta_only',
            'full_session_runtime': f'https://{kr_host}/_calc/<type>?embed=1',
            'listing_site_policy': f'https://{co_host}/ stays listing-focused and should link users to {kr_host} service pages instead of embedding calculators inline.',
        },
        'astra_reference': {
            'theme_name': str(astra_reference.get('astra', {}).get('theme_name') or 'Astra'),
            'theme_version': str(astra_reference.get('astra', {}).get('theme_version') or ''),
            'strategy': str(astra_reference.get('decision', {}).get('strategy') or ''),
        },
        'summary': {
            'theme_ready': True,
            'plugin_ready': True,
            'generated_file_count': len(files),
        },
    }
    return payload


def _to_markdown(payload: Dict[str, Any]) -> str:
    theme = payload.get('theme', {})
    plugin = payload.get('plugin', {})
    policy = payload.get('calculator_mount_policy', {})
    lines = [
        '# WordPress Platform Assets',
        '',
        '## Theme',
        f"- slug: {theme.get('slug')}",
        f"- parent_theme: {theme.get('parent_theme')}",
        f"- ready: {theme.get('ready')}",
        f"- path: {theme.get('path')}",
        '',
        '## Plugin',
        f"- slug: {plugin.get('slug')}",
        f"- ready: {plugin.get('ready')}",
        f"- public_mount_host: {plugin.get('public_mount_host')}",
        f"- public_mount_base: {plugin.get('public_mount_base')}",
        f"- listing_host: {plugin.get('listing_host')}",
        f"- lazy_iframe_policy: {plugin.get('lazy_iframe_policy')}",
        f"- shortcodes: {', '.join(plugin.get('shortcodes') or []) or '(none)'}",
        '',
        '## Calculator Mount Policy',
        f"- homepage: {policy.get('homepage')}",
        f"- service_pages: {policy.get('service_pages')}",
        f"- knowledge_posts: {policy.get('knowledge_posts')}",
        f"- full_session_runtime: {policy.get('full_session_runtime')}",
        f"- listing_site_policy: {policy.get('listing_site_policy')}",
    ]
    return '\n'.join(lines) + '\n'


def main() -> int:
    parser = argparse.ArgumentParser(description='Scaffold WordPress platform theme/plugin assets in the isolated lab.')
    parser.add_argument('--lab-root', type=Path, default=DEFAULT_LAB_ROOT)
    parser.add_argument('--surface-audit', type=Path, default=DEFAULT_SURFACE_AUDIT)
    parser.add_argument('--astra-reference', type=Path, default=DEFAULT_ASTRA_REFERENCE)
    parser.add_argument('--json', type=Path, default=ROOT / 'logs' / 'wp_platform_assets_latest.json')
    parser.add_argument('--md', type=Path, default=ROOT / 'logs' / 'wp_platform_assets_latest.md')
    args = parser.parse_args()

    payload = build_wp_platform_assets(
        lab_root=args.lab_root,
        surface_audit_path=args.surface_audit,
        astra_reference_path=args.astra_reference,
    )
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
    args.md.write_text(_to_markdown(payload), encoding='utf-8')
    print(f'[ok] wrote {args.json}')
    print(f'[ok] wrote {args.md}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
