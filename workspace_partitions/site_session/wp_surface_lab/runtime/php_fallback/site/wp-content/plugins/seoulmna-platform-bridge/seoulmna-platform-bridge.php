<?php
/**
 * Plugin Name: SeoulMNA Platform Bridge
 * Description: Lazy calculator gates for Yangdo and Permit without initial iframe traffic.
 * Version: 0.1.0
 * Author: Codex
 * Text Domain: seoulmna-platform-bridge
 */

if (!defined('ABSPATH')) {
    exit;
}

const SMNA_PLATFORM_BRIDGE_VERSION = '0.1.0';
const SMNA_PLATFORM_BRIDGE_DEFAULT_PUBLIC_MOUNT_BASE = 'https://seoulmna.kr/_calc';

function smna_platform_bridge_public_mount_base() {
    $base = apply_filters('smna_platform_bridge_public_mount_base', SMNA_PLATFORM_BRIDGE_DEFAULT_PUBLIC_MOUNT_BASE);
    return untrailingslashit((string) $base);
}

function smna_platform_bridge_widget_url($type) {
    $map = [
        'yangdo' => smna_platform_bridge_public_mount_base() . '/yangdo?embed=1',
        'permit' => smna_platform_bridge_public_mount_base() . '/permit?embed=1',
    ];
    $type = sanitize_key((string) $type);
    $url = isset($map[$type]) ? $map[$type] : $map['yangdo'];
    return (string) apply_filters('smna_platform_bridge_widget_url', $url, $type, $map);
}

add_action('wp_enqueue_scripts', function () {
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
});

function smna_platform_bridge_render_gate($atts = []) {
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
}
add_shortcode('seoulmna_calc_gate', 'smna_platform_bridge_render_gate');
