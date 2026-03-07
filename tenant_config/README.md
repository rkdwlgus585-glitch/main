# Tenant Config

`tenant_registry.json` defines host -> tenant resolution, plan-based feature policy, and system-level isolation.

## plan_feature_defaults
- `standard`: `estimate`, `permit_precheck`, `consult`, `usage`
- `pro`: `estimate`, `estimate_detail`, `permit_precheck`, `permit_precheck_detail`, `consult`, `usage`, `meta`
- `pro_internal`: `estimate`, `estimate_internal`, `permit_precheck`, `permit_precheck_internal`, `consult`, `usage`, `meta`, `reload`

## tenant fields
- `tenant_id`: stable id
- `display_name`: display label
- `enabled`: onboarding/운영 활성 상태
- `plan`: one of plan keys
- `allowed_systems`: `yangdo` | `permit`; feature와 별도로 시스템 접근 범위를 강제
- `hosts`: hostnames mapped to this tenant
- `origins`: allowed origin URL list (host must be in `hosts`)
- `api_key_envs`: env variable names holding API keys for this tenant
- `blocked_api_tokens` (optional): 즉시 차단할 API key 토큰 목록
- `allowed_features` (optional): explicit override
- `data_sources` (enabled tenant 필수): 데이터 출처 정책 목록
  - `source_id`: 고유 ID
  - `access_mode`: `first_party_internal` | `official_api` | `public_open_data` | `partner_contract` | `manual_entry`
  - 금지 access_mode: `unauthorized_crawling`, `credential_sharing`, `source_disguise`
  - `status`: enabled tenant은 `approved`만 허용
  - `allows_commercial_use`: enabled tenant은 `true` 필수
  - `transforms`: 금지값(`source_disguise`, `origin_masking`, `fake_data_camouflage`, `fabrication_masking`) 포함 불가
  - 개인정보 source(`contains_personal_data=true`)는 `pseudonymization` transform 필수

If `allowed_features` is omitted, the plan default set is used.
If `allowed_systems` is omitted, it is derived from feature names.
If `enabled=false`, tenant feature access is fully blocked.

## offering_templates
- 목적: `yangdo_only / permit_only / combo` 같은 상품 템플릿을 온보딩 스크립트에서 재사용
- 주요 필드
  - `offering_id`
  - `plan`
  - `allowed_systems`
  - `allowed_features`
- 사용 스크립트
  - `scripts/activate_partner_tenant.py --offering-id ...`

## channel_profiles
- 파일: `tenant_config/channel_profiles.json`
- 채널은 테넌트와 별도로 외부 노출 범위를 가짐
- 주요 필드
  - `channel_id`
  - `enabled`
  - `channel_role`: `platform_front` | `widget_consumer`
  - `channel_hosts`
  - `canonical_public_host`: 공개용 대표 호스트
  - `public_host_policy`: `kr_main_platform` | `internal_widget_consumer` | `single_host`
  - `platform_front_host`: 플랫폼형 메인 공개 프런트 호스트
  - `legacy_content_host`: 기존 콘텐츠/관리 호스트
  - `internal_widget_channel_id`: `.kr` 플랫폼이 내부 위젯 소비 채널로 연결할 channel id
  - `engine_origin`
  - `embed_base_url`
  - `default_tenant_id`
  - `exposed_systems`: `yangdo` | `permit`
  - `branding`

## independent systems
- `yangdo`
  - 목적: 양도가 산정 / 양도양수 유입
  - required feature: `estimate`
- `permit`
  - 목적: 등록기준 기반 인허가 사전검토
  - required feature: `permit_precheck`

두 시스템은 특허도 분리하고 런타임 접근도 분리한다. 공유하는 것은 tenant/channel/billing 같은 플랫폼 레이어뿐이다.

## patent / attorney handoff
- canonical handoff: `scripts/generate_attorney_handoff.py`
- outputs:
  - `logs/attorney_handoff_latest.json`
  - `logs/attorney_handoff_latest.md`
- 기존 `patent_system_brief_latest.*`는 호환용 참고 산출물이고, 변리사 전달 기준은 `attorney_handoff_latest.*` 한 쌍으로 유지

## onboarding validation
- script: `scripts/validate_tenant_onboarding.py`
- report: `logs/tenant_onboarding_validation_latest.json`
- strict launcher: `launchers/tenant_onboarding_check.bat` (`파트너온보딩검증.bat`)
- scaffold generator: `scripts/scaffold_partner_offering.py`
- onboarding flow orchestrator: `scripts/run_partner_onboarding_flow.py`
- activation preview matrix: `scripts/preview_partner_activation_matrix.py`
- activation gate: `scripts/activate_partner_tenant.py`
- 온보딩 flow report는 `handoff.next_actions`로 proof/api key/source 승인 등 다음 조치를 구조화해서 반환
- activation preview는 입력 조합별로 `remaining_required_inputs`가 어떻게 줄어드는지 비교해, 어떤 값을 먼저 받아야 하는지 보여준다

## usage billing + threshold policy
- thresholds: `tenant_config/plan_thresholds.json`
- monthly usage/cost report: `scripts/tenant_usage_billing_report.py`
- report output: `logs/tenant_usage_billing_latest.json`
- threshold policy queue: `scripts/enforce_tenant_threshold_policy.py`
- policy output: `logs/tenant_policy_actions_latest.json`
- optional auto apply: `--apply-registry` with policy flags (`auto_upgrade`, `auto_disable`, `auto_block_keys_on_disable`)
- policy notification: `scripts/tenant_policy_notify.py` -> `logs/tenant_policy_notify_latest.json`
- policy recovery: `scripts/tenant_policy_recovery.py` -> `logs/tenant_policy_recovery_latest.json`

## widget rollout
- embed planner: `scripts/plan_channel_embed.py`
- snippet generator: `scripts/generate_widget_snippet.py`
- compatibility wrapper: `scripts/generate_yangdo_widget_snippet.py`
- bundle publisher: `scripts/publish_widget_bundle.py`
- public front audit: `scripts/generate_platform_front_audit.py`
- kr front app: `workspace_partitions/site_session/kr_platform_front`
- kr deploy readiness: `scripts/validate_kr_platform_deploy_ready.py`
- kr preview deploy: `scripts/deploy_kr_platform_front_preview.py`
- seoul release orchestrator: `scripts/deploy_seoul_widget_embed_release.py`
- co content deployer: `scripts/deploy_co_content_pages.py`
- 원칙:
  - 서울건설정보/타사 사이트 모두 중앙 엔진의 widget URL만 사용
  - `seoulmna.kr`는 플랫폼형 public front
  - `seoulmna.co.kr`는 서울건설정보 내부 무제한 widget consumer
  - 엔진 호스트는 private/internal only로 유지하고, 공개 브랜드로 쓰지 않는다
  - 사이트별 계산기 복제 금지
  - `channel enabled + tenant enabled + system allowed + activation blockers 없음` 상태에서만 snippet 생성
  - `.kr` front 전개는 `env sync -> build -> deploy preview -> runtime check -> canonical cutover` 순서로 수행
  - `.co.kr` widget live 반영은 `bundle -> co content deploy -> runtime verify` 순서로 수행
  - 신규 파트너 온보딩은 `scaffold -> validate -> activate -> embed handoff` 순서로 수행
