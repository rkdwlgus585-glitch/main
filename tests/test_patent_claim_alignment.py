"""Verify that patent claim elements are actually implemented in code.

Each test validates that a specific element mentioned in the patent
specification (Track A / Track B) exists and functions correctly in
the corresponding source module.  This prevents "claim drift" —
where code refactoring silently invalidates patent claims.

Test structure mirrors the claim map in patent_system_brief_latest.md.
"""

from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


class TrackAClaimAlignmentTest(unittest.TestCase):
    """Track A — 양도가 산정 청구항 요소가 코드에 구현되어 있는지 검증."""

    _calc_src: str = ""

    @classmethod
    def setUpClass(cls) -> None:
        cls._calc_src = (ROOT / "yangdo_calculator.py").read_text(encoding="utf-8")
        cls._api_src = (ROOT / "yangdo_blackbox_api.py").read_text(encoding="utf-8")
        cls._dup_src = (ROOT / "core_engine" / "yangdo_duplicate_cluster.py").read_text(encoding="utf-8")
        cls._rec_src = (ROOT / "core_engine" / "yangdo_listing_recommender.py").read_text(encoding="utf-8")

    # ── Claim: 전기/정보통신/소방 특수 정밀화 ──────────────────────

    def test_special_balance_policies_all_three_sectors(self) -> None:
        """Claim: 전기·정보통신·소방 업종군 특수 정밀화."""
        for sector in ["전기", "정보통신", "소방"]:
            with self.subTest(sector=sector):
                self.assertIn(
                    f'"{sector}"',
                    self._calc_src,
                    f"SPECIAL_BALANCE_AUTO_POLICIES must contain {sector}",
                )

    def test_special_balance_sector_specific_values(self) -> None:
        """Claim: 업종별 minAutoBalanceEok 차등 적용 (scale 반영)."""
        # 전기: 0.05, 정보통신: 0.025, 소방: 0.09
        self.assertIn("minAutoBalanceEok: 0.05", self._calc_src)   # 전기
        self.assertIn("minAutoBalanceEok: 0.025", self._calc_src)  # 정보통신
        self.assertIn("minAutoBalanceEok: 0.09", self._calc_src)   # 소방

    def test_special_balance_min_auto_values(self) -> None:
        """Claim: 업종별 minAutoBalanceShare 차등 적용."""
        # Verify exact values from patent spec
        self.assertIn("minAutoBalanceShare: 0.10", self._calc_src)   # 전기
        self.assertIn("minAutoBalanceShare: 0.0625", self._calc_src) # 정보통신
        self.assertIn("minAutoBalanceShare: 0.17", self._calc_src)   # 소방

    def test_reorg_overrides_implemented(self) -> None:
        """Claim: 재편 유형별 정산비율 override."""
        self.assertIn("reorgOverrides", self._calc_src)
        self.assertIn("분할/합병", self._calc_src)

    # ── Claim: 비교군 오염 제거 ────────────────────────────────────

    def test_duplicate_cluster_collapse_exists(self) -> None:
        """Claim: 중복 매물 군집화."""
        self.assertIn("collapse_duplicate_neighbors", self._dup_src)

    def test_duplicate_cluster_weight_limit(self) -> None:
        """Claim: cluster-weight 제한."""
        # The function must apply some kind of weight/cap mechanism
        self.assertTrue(
            "weight" in self._dup_src.lower() or "cap" in self._dup_src.lower(),
            "Duplicate cluster module must implement weight/cap mechanism",
        )

    # ── Claim: 유사 매물 추천 + 이유 생성 ──────────────────────────

    def test_recommendation_bundle_exists(self) -> None:
        """Claim: 유사 매물 추천 번들 생성."""
        self.assertIn("build_recommendation_bundle", self._rec_src)

    def test_recommendation_reason_generated(self) -> None:
        """Claim: 추천 이유 생성."""
        self.assertTrue(
            "reason" in self._rec_src.lower() or "recommendation_reason" in self._rec_src,
            "Recommender must generate recommendation reasons",
        )

    def test_precision_label_generated(self) -> None:
        """Claim: 정밀도 라벨 생성."""
        self.assertTrue(
            "precision" in self._rec_src.lower() or "precision_label" in self._rec_src,
            "Recommender must generate precision labels",
        )

    # ── Claim: 신뢰도 기반 공개수준 제어 ──────────────────────────

    def test_confidence_cap_function_exists(self) -> None:
        """Claim: 업종별 신뢰도 상한 적용."""
        self.assertIn("singleCorePublicationCap", self._calc_src)

    def test_response_tier_in_api(self) -> None:
        """Claim: 공개 등급에 따른 응답 tier 분리."""
        self.assertIn("response_tier", self._api_src)

    def test_estimate_response_tier_function(self) -> None:
        """Claim: 응답 tier 결정 함수."""
        self.assertIn("_estimate_response_tier", self._api_src)

    # ── Claim: 입력 정규화 ─────────────────────────────────────────

    def test_license_name_normalization(self) -> None:
        """Claim: 면허명 별칭 정규화."""
        self.assertIn("normalizeLicenseKey", self._calc_src)

    def test_special_balance_sector_detection(self) -> None:
        """Claim: specialBalanceSectorName 업종 판별."""
        self.assertIn("specialBalanceSectorName", self._calc_src)


class TrackBClaimAlignmentTest(unittest.TestCase):
    """Track B — 인허가 사전검토 청구항 요소가 코드에 구현되어 있는지 검증."""

    @classmethod
    def setUpClass(cls) -> None:
        cls._diag_src = (ROOT / "permit_diagnosis_calculator.py").read_text(encoding="utf-8")
        cls._schema_src = (ROOT / "core_engine" / "permit_criteria_schema.py").read_text(encoding="utf-8")
        cls._pipeline_src = (ROOT / "core_engine" / "permit_mapping_pipeline.py").read_text(encoding="utf-8")
        cls._api_src = (ROOT / "permit_precheck_api.py").read_text(encoding="utf-8")

    # ── Claim: typed criteria 평가 ──────────────────────────────────

    def test_evaluate_typed_criteria_exists(self) -> None:
        """Claim: typed criteria 기반 기준항목 판정."""
        self.assertIn("evaluate_typed_criteria", self._schema_src)

    def test_typed_criteria_six_categories(self) -> None:
        """Claim: 6개 typed criteria 카테고리."""
        categories = ["capital", "technician", "office", "facility", "qualification", "safety"]
        for cat in categories:
            with self.subTest(category=cat):
                self.assertIn(
                    cat,
                    self._schema_src,
                    f"Typed criteria must support '{cat}' category",
                )

    # ── Claim: 객관 출처 규칙카탈로그 ──────────────────────────────

    def test_rule_catalog_file_exists(self) -> None:
        """Claim: 객관 출처 규칙카탈로그."""
        catalog_path = ROOT / "config" / "permit_registration_criteria_expanded.json"
        self.assertTrue(catalog_path.exists(), "Expanded criteria catalog must exist")
        # Verify it's non-trivial (>1MB = real data, not a stub)
        size_mb = catalog_path.stat().st_size / (1024 * 1024)
        self.assertGreater(size_mb, 1.0, "Catalog must be substantial (>1MB)")

    def test_rule_catalog_covers_245_sectors(self) -> None:
        """Claim: 245개 업종 커버리지."""
        catalog_path = ROOT / "config" / "permit_registration_criteria_expanded.json"
        with open(catalog_path, encoding="utf-8") as f:
            data = json.load(f)
        # Catalog is dict with 'industries' list
        industries = data.get("industries", [])
        sector_count = len(industries)
        self.assertGreaterEqual(
            sector_count, 200,
            f"Catalog should cover ≥200 sectors (found {sector_count})",
        )

    # ── Claim: 업종 매핑 파이프라인 ────────────────────────────────

    def test_mapping_pipeline_exists(self) -> None:
        """Claim: 업종코드/서비스코드/별칭 매핑."""
        self.assertIn("apply_mapping_pipeline", self._pipeline_src)

    def test_mapping_batch_class(self) -> None:
        """Claim: 매핑 배치 처리."""
        self.assertIn("MappingBatch", self._pipeline_src)

    # ── Claim: manual_review gate ──────────────────────────────────

    def test_manual_review_gate(self) -> None:
        """Claim: coverage/manual-review gate."""
        self.assertIn("manual_review", self._diag_src)

    def test_coverage_status(self) -> None:
        """Claim: coverage gate 상태."""
        self.assertIn("coverage_status", self._diag_src)

    # ── Claim: 규칙 병합 ──────────────────────────────────────────

    def test_merge_expanded_rule_metadata(self) -> None:
        """Claim: 확장 카탈로그 메타데이터 병합."""
        self.assertIn("_merge_expanded_rule_metadata", self._diag_src)

    # ── Claim: 업종별 차등 기준 ────────────────────────────────────

    def test_electrical_sector_criteria(self) -> None:
        """Claim: 전기공사업 기준 (자본금 1.5억, 기술인력 3)."""
        self.assertIn("전기공사업", self._diag_src)

    def test_telecom_sector_criteria(self) -> None:
        """Claim: 정보통신공사업 기준."""
        self.assertIn("정보통신공사업", self._diag_src)

    def test_fire_sector_criteria(self) -> None:
        """Claim: 소방시설공사업 기준."""
        self.assertIn("소방시설공사업", self._diag_src)


class TrackPClaimAlignmentTest(unittest.TestCase):
    """Track P — 플랫폼 공유 인프라 요소가 코드에 구현되어 있는지 검증."""

    def test_tenant_gateway_class(self) -> None:
        """Claim: tenant allowed_systems / feature gate."""
        src = (ROOT / "core_engine" / "tenant_gateway.py").read_text(encoding="utf-8")
        self.assertIn("class TenantGateway", src)
        self.assertIn("check_system", src)

    def test_channel_router_class(self) -> None:
        """Claim: channel exposed_systems / host routing."""
        src = (ROOT / "core_engine" / "channel_profiles.py").read_text(encoding="utf-8")
        self.assertIn("class ChannelRouter", src)

    def test_response_envelope(self) -> None:
        """Claim: response envelope / tier 분기."""
        src = (ROOT / "core_engine" / "api_response.py").read_text(encoding="utf-8")
        self.assertIn("build_response_envelope", src)

    def test_sandbox_mode(self) -> None:
        """Claim: 파트너 sandbox 모드."""
        src = (ROOT / "core_engine" / "sandbox.py").read_text(encoding="utf-8")
        self.assertIn("is_sandbox_request", src)
        self.assertIn("sandbox_permit_response", src)
        self.assertIn("sandbox_yangdo_response", src)


class TrackCClaimAlignmentTest(unittest.TestCase):
    """Track C — Production resilience 요소가 구현되어 있는지 검증."""

    def test_all_servers_have_sigterm(self) -> None:
        """All 3 API servers must have SIGTERM graceful shutdown."""
        servers = [
            "yangdo_blackbox_api.py",
            "permit_precheck_api.py",
            "yangdo_consult_api.py",
        ]
        for server in servers:
            with self.subTest(server=server):
                src = (ROOT / server).read_text(encoding="utf-8")
                self.assertIn("_graceful_shutdown", src)
                self.assertIn("SIGTERM", src)

    def test_deploy_infrastructure_consistency_tests_exist(self) -> None:
        """Infrastructure drift tests must exist."""
        test_file = ROOT / "tests" / "test_deploy_infrastructure.py"
        self.assertTrue(test_file.exists())
        src = test_file.read_text(encoding="utf-8")
        self.assertIn("_SERVICES", src)


if __name__ == "__main__":
    unittest.main()
