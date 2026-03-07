<?php
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
