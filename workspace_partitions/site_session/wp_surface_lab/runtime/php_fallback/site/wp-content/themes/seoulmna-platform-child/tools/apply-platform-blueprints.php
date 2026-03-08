<?php
if (!defined('ABSPATH')) {
    exit(1);
}

if (!function_exists('wp_get_nav_menu_items')) {
    require_once ABSPATH . 'wp-admin/includes/nav-menu.php';
}

$manifest = json_decode(<<<'JSON'
{
  "generated_at": "2026-03-08 15:37:16",
  "theme_slug": "seoulmna-platform-child",
  "plugin_slug": "seoulmna-platform-bridge",
  "front_page_slug": "home",
  "front_page_public_slug": "/",
  "menu": {
    "name": "서울건설정보 플랫폼",
    "location_candidates": [
      "primary",
      "menu-1",
      "main-menu"
    ],
    "items": [
      {
        "label": "플랫폼 소개",
        "href": "/"
      },
      {
        "label": "양도가",
        "href": "/yangdo"
      },
      {
        "label": "인허가",
        "href": "/permit"
      },
      {
        "label": "지식베이스",
        "href": "/knowledge"
      },
      {
        "label": "상담",
        "href": "/consult"
      }
    ]
  },
  "pages": [
    {
      "page_id": "home",
      "public_slug": "/",
      "wordpress_page_slug": "home",
      "title": "서울건설정보 메인 플랫폼",
      "calculator_policy": "cta_only_no_iframe",
      "blueprint_relative_path": "blueprints/home.html",
      "is_front_page": true
    },
    {
      "page_id": "yangdo",
      "public_slug": "/yangdo",
      "wordpress_page_slug": "yangdo",
      "title": "AI 양도가 산정 · 유사매물 추천",
      "calculator_policy": "lazy_gate_shortcode",
      "blueprint_relative_path": "blueprints/yangdo.html",
      "is_front_page": false
    },
    {
      "page_id": "permit",
      "public_slug": "/permit",
      "wordpress_page_slug": "permit",
      "title": "AI 인허가 사전검토",
      "calculator_policy": "lazy_gate_shortcode",
      "blueprint_relative_path": "blueprints/permit.html",
      "is_front_page": false
    },
    {
      "page_id": "knowledge",
      "public_slug": "/knowledge",
      "wordpress_page_slug": "knowledge",
      "title": "등록기준 · 양도양수 지식베이스",
      "calculator_policy": "cta_only_no_iframe",
      "blueprint_relative_path": "blueprints/knowledge.html",
      "is_front_page": false
    },
    {
      "page_id": "consult",
      "public_slug": "/consult",
      "wordpress_page_slug": "consult",
      "title": "상담 접수",
      "calculator_policy": "no_calculator_inline",
      "blueprint_relative_path": "blueprints/consult.html",
      "is_front_page": false
    },
    {
      "page_id": "market_bridge",
      "public_slug": "/mna-market",
      "wordpress_page_slug": "mna-market",
      "title": "양도양수 매물 보기",
      "calculator_policy": "cta_only_no_iframe",
      "blueprint_relative_path": "blueprints/mna-market.html",
      "is_front_page": false
    }
  ]
}
JSON
, true);

if (!is_array($manifest)) {
    fwrite(STDERR, "invalid manifest\n");
    exit(1);
}

$theme_dir = get_theme_root() . DIRECTORY_SEPARATOR . "seoulmna-platform-child";
$results = [];
$page_ids = [];

foreach (($manifest['pages'] ?? []) as $page) {
    $wordpress_slug = trim((string)($page['wordpress_page_slug'] ?? ''), '/');
    $public_slug = (string)($page['public_slug'] ?? '/');
    $blueprint_rel = ltrim((string)($page['blueprint_relative_path'] ?? ''), '/');
    $blueprint_path = $theme_dir . DIRECTORY_SEPARATOR . str_replace('/', DIRECTORY_SEPARATOR, $blueprint_rel);
    $content = is_file($blueprint_path) ? (string) file_get_contents($blueprint_path) : '';

    $existing = $wordpress_slug !== '' ? get_page_by_path($wordpress_slug, OBJECT, 'page') : null;
    $postarr = [
        'post_type' => 'page',
        'post_status' => 'publish',
        'post_title' => (string)($page['title'] ?? $wordpress_slug),
        'post_name' => $wordpress_slug,
        'post_content' => $content,
    ];

    if ($existing instanceof WP_Post) {
        $postarr['ID'] = (int) $existing->ID;
        $post_id = wp_update_post(wp_slash($postarr), true);
        $action = 'updated';
    } else {
        $post_id = wp_insert_post(wp_slash($postarr), true);
        $action = 'created';
    }

    if (is_wp_error($post_id)) {
        $results[] = [
            'page_id' => $page['page_id'] ?? '',
            'public_slug' => $public_slug,
            'wordpress_page_slug' => $wordpress_slug,
            'ok' => false,
            'action' => 'error',
            'error' => $post_id->get_error_message(),
        ];
        continue;
    }

    $post_id = (int) $post_id;
    $page_ids[(string)($page['page_id'] ?? $wordpress_slug)] = $post_id;
    $results[] = [
        'page_id' => $page['page_id'] ?? '',
        'public_slug' => $public_slug,
        'wordpress_page_slug' => $wordpress_slug,
        'post_id' => $post_id,
        'ok' => true,
        'action' => $action,
        'calculator_policy' => (string)($page['calculator_policy'] ?? ''),
    ];
}

$front_page_key = (string)($manifest['front_page_slug'] ?? 'home');
$front_page_id = isset($page_ids[$front_page_key]) ? (int) $page_ids[$front_page_key] : 0;
if ($front_page_id > 0) {
    update_option('show_on_front', 'page');
    update_option('page_on_front', $front_page_id);
}
update_option('permalink_structure', '/%postname%/');
if (function_exists('flush_rewrite_rules')) {
    flush_rewrite_rules();
}

$menu_name = (string)(($manifest['menu'] ?? [])['name'] ?? '서울건설정보 플랫폼');
$menu_obj = wp_get_nav_menu_object($menu_name);
$menu_id = $menu_obj ? (int) $menu_obj->term_id : (int) wp_create_nav_menu($menu_name);
if (!is_wp_error($menu_id) && $menu_id > 0) {
    $existing_items = wp_get_nav_menu_items($menu_id) ?: [];
    $front_page_lookup_slug = (string)($manifest['front_page_slug'] ?? 'home');
    foreach ($existing_items as $item) {
        wp_delete_post((int) $item->ID, true);
    }
    foreach ((($manifest['menu'] ?? [])['items'] ?? []) as $item) {
        $href = (string)($item['href'] ?? '');
        $label = (string)($item['label'] ?? $href);
        if ($href === '') {
            continue;
        }
        if (str_starts_with($href, '/')) {
            $slug = trim($href, '/');
            if ($slug === '') {
                $slug = $front_page_lookup_slug;
            }
            $page = $slug === '' ? null : get_page_by_path($slug, OBJECT, 'page');
            if ($page instanceof WP_Post) {
                wp_update_nav_menu_item($menu_id, 0, [
                    'menu-item-title' => $label,
                    'menu-item-object-id' => (int) $page->ID,
                    'menu-item-object' => 'page',
                    'menu-item-type' => 'post_type',
                    'menu-item-status' => 'publish',
                ]);
                continue;
            }
        }
        wp_update_nav_menu_item($menu_id, 0, [
            'menu-item-title' => $label,
            'menu-item-url' => $href,
            'menu-item-status' => 'publish',
        ]);
    }

    $registered = get_registered_nav_menus();
    $locations = get_theme_mod('nav_menu_locations', []);
    $assigned_location = null;
    foreach ((($manifest['menu'] ?? [])['location_candidates'] ?? []) as $candidate) {
        if (isset($registered[$candidate])) {
            $locations[$candidate] = $menu_id;
            $assigned_location = $candidate;
            break;
        }
    }
    set_theme_mod('nav_menu_locations', $locations);
} else {
    $assigned_location = null;
}

echo wp_json_encode([
    'ok' => true,
    'page_results' => $results,
    'front_page_id' => $front_page_id,
    'menu_name' => $menu_name,
    'menu_location' => $assigned_location,
    'permalink_structure' => get_option('permalink_structure'),
], JSON_UNESCAPED_UNICODE | JSON_PRETTY_PRINT);
