<?php
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
