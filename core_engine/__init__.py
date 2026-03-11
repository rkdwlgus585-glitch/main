"""core_engine — seoulmna.kr 플랫폼 공유 엔진 패키지.

이 패키지는 양도가 산정 시스템과 인허가 사전검토 시스템이 공유하는
핵심 모듈을 포함한다.  각 모듈은 독립적으로 임포트하여 사용한다.

Modules
-------
api_contract
    API 요청/응답 스키마 정규화 (``normalize_v1_request``)
api_response
    표준 응답 래퍼, UTC 타임스탬프, HTML-safe JSON 직렬화
channel_branding
    채널별 브랜딩 해상도 (로고, 연락처, 색상)
channel_profiles
    멀티채널 라우팅 및 프로필 관리 (``ChannelRouter``)
host_utils
    URL 정규화, SSRF 방어, 환경 변수 유틸리티
permit_criteria_schema
    인허가 등록기준 typed_criteria 평가 (6개 타입)
permit_mapping_pipeline
    업종 코드 매핑 다단계 파이프라인
sandbox
    파트너 샌드박스 모드 (static 응답 생성)
tenant_gateway
    멀티테넌트 게이트웨이 (설정 해상도, 시스템 검증)
yangdo_duplicate_cluster
    양도 매물 중복 탐지 (유사도 클러스터링)
yangdo_listing_recommender
    양도 매물 추천 및 번들 구성

Note
----
각 모듈의 공개 API는 모듈별 ``__all__`` 로 명시되어 있으며,
이 ``__init__.py`` 에서 re-export 하지 않는다.  이는 네임스페이스 오염을
방지하고, 각 모듈의 의존성을 명시적으로 유지하기 위함이다.
"""
