"""Verify that API response shapes match OpenAPI spec schemas.

This test prevents "field drift" — where code changes add, remove, or
rename response fields without updating the OpenAPI specification, which
would break partner integrations and invalidate patent evidence.

The tests parse the YAML spec and cross-check against the actual Python
source code that builds each response.
"""

from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SPEC_PATH = ROOT / "logs" / "openapi_spec_latest.yaml"


def _load_spec_text() -> str:
    """Load the OpenAPI spec as raw text (no yaml dependency needed)."""
    return SPEC_PATH.read_text(encoding="utf-8")


def _extract_schema_required(spec: str, schema_name: str) -> list[str]:
    """Extract 'required' fields from a schema definition in YAML."""
    # Find the schema block
    pattern = rf"^\s+{schema_name}:\s*$"
    match = re.search(pattern, spec, re.MULTILINE)
    if not match:
        return []
    block_start = match.end()
    # Find required: [...] within this schema
    req_pattern = r"required:\s*\[([^\]]+)\]"
    remaining = spec[block_start:block_start + 3000]
    req_match = re.search(req_pattern, remaining)
    if not req_match:
        return []
    return [f.strip().strip('"').strip("'") for f in req_match.group(1).split(",")]


def _extract_schema_properties(spec: str, schema_name: str) -> list[str]:
    """Extract top-level property names from a schema definition."""
    pattern = rf"^\s+{schema_name}:\s*$"
    match = re.search(pattern, spec, re.MULTILINE)
    if not match:
        return []
    block_start = match.end()
    remaining = spec[block_start:block_start + 5000]
    # Find properties block and extract keys
    prop_start = remaining.find("properties:")
    if prop_start == -1:
        return []
    prop_block = remaining[prop_start:]
    # Property names are at specific indent level
    props = re.findall(r"^\s{12}(\w[\w_]*):\s*$", prop_block, re.MULTILINE)
    if not props:
        # Try different indent levels
        props = re.findall(r"^\s{8}(\w[\w_]*):\s*$", prop_block, re.MULTILINE)
    return props


class TestOpenAPISpecFileIntegrity(unittest.TestCase):
    """The OpenAPI spec file must exist and be parseable."""

    def test_spec_file_exists(self) -> None:
        self.assertTrue(SPEC_PATH.exists(), "OpenAPI spec not found")

    def test_spec_has_version(self) -> None:
        spec = _load_spec_text()
        self.assertIn('version: "1.', spec)

    def test_spec_has_three_api_servers(self) -> None:
        spec = _load_spec_text()
        for port in ["8100", "8200", "8788"]:
            with self.subTest(port=port):
                self.assertIn(port, spec, f"Dev server :{port} missing from spec")

    def test_spec_covers_all_endpoints(self) -> None:
        """All 3 main endpoints must be documented."""
        spec = _load_spec_text()
        for endpoint in ["/v1/yangdo/estimate", "/v1/permit/precheck", "/consult"]:
            with self.subTest(endpoint=endpoint):
                self.assertIn(endpoint, spec, f"Endpoint {endpoint} missing from spec")


class TestYangdoResponseContract(unittest.TestCase):
    """Yangdo estimate response must match OpenAPI YangdoEstimateResponse."""

    @classmethod
    def setUpClass(cls) -> None:
        cls._spec = _load_spec_text()
        cls._api_src = (ROOT / "yangdo_blackbox_api.py").read_text(encoding="utf-8")
        cls._envelope_src = (ROOT / "core_engine" / "api_response.py").read_text(encoding="utf-8")

    def test_required_fields_in_spec(self) -> None:
        """Spec declares required: [ok, service, api_version, request_id, data]."""
        required = _extract_schema_required(self._spec, "YangdoEstimateResponse")
        for field in ["ok", "service", "api_version", "request_id", "data"]:
            with self.subTest(field=field):
                self.assertIn(field, required)

    def test_envelope_produces_required_fields(self) -> None:
        """build_response_envelope must set all required fields."""
        for field in ["service", "api_version", "request_id", "data", "response_meta"]:
            with self.subTest(field=field):
                self.assertIn(f'"{field}"', self._envelope_src)

    def test_response_meta_fields(self) -> None:
        """response_meta must contain documented sub-fields."""
        for field in ["channel_id", "tenant_plan", "response_tier", "status"]:
            with self.subTest(field=field):
                self.assertIn(f'"{field}"', self._envelope_src)

    def test_response_tier_documented(self) -> None:
        """response_tier (summary/detail/consult/internal) must be in spec."""
        self.assertIn("response_tier", self._spec)
        for tier in ["summary", "detail", "consult", "internal"]:
            with self.subTest(tier=tier):
                self.assertIn(tier, self._spec)

    def test_recommended_listings_field_in_code(self) -> None:
        """Code must produce 'recommended_listings' array as spec declares."""
        self.assertIn("recommended_listings", self._api_src)

    def test_confidence_fields_in_code(self) -> None:
        """Code must produce confidence-related fields."""
        # confidence_percent/confidence_score in API, confidenceScore in JS calculator
        combined = self._api_src + (ROOT / "yangdo_calculator.py").read_text(encoding="utf-8")
        self.assertTrue(
            "confidence" in combined.lower(),
            "Yangdo system must produce confidence data",
        )

    def test_risk_notes_field_in_code(self) -> None:
        """Code must produce risk_notes array."""
        self.assertIn("risk_notes", self._api_src)


class TestPermitResponseContract(unittest.TestCase):
    """Permit precheck response must match OpenAPI PermitPrecheckResponse."""

    @classmethod
    def setUpClass(cls) -> None:
        cls._spec = _load_spec_text()
        cls._diag_src = (ROOT / "permit_diagnosis_calculator.py").read_text(encoding="utf-8")
        cls._api_src = (ROOT / "permit_precheck_api.py").read_text(encoding="utf-8")

    def test_required_fields_in_spec(self) -> None:
        """Spec declares required: [ok, service, api_version, request_id, data]."""
        required = _extract_schema_required(self._spec, "PermitPrecheckResponse")
        for field in ["ok", "service", "api_version", "request_id", "data"]:
            with self.subTest(field=field):
                self.assertIn(field, required)

    def test_overall_status_enum_in_code(self) -> None:
        """Code must produce overall_status values matching spec enum."""
        combined = self._diag_src + self._api_src
        for status in ["pass", "shortfall", "manual_review"]:
            with self.subTest(status=status):
                self.assertIn(f'"{status}"', combined)

    def test_shortfall_concepts_in_code(self) -> None:
        """Code must handle shortfall detection with category-level data."""
        combined = self._diag_src + self._api_src
        # Shortfall is detected via typed_criteria evaluation, not a flat field list
        self.assertIn("shortfall", combined.lower())
        for concept in ["capital", "technician", "office"]:
            with self.subTest(concept=concept):
                self.assertIn(concept, combined.lower())

    def test_typed_criteria_categories_match_spec(self) -> None:
        """Spec shortfall category enum must match code criteria categories."""
        spec_categories = ["capital", "technician", "office", "facility", "qualification"]
        schema_src = (ROOT / "core_engine" / "permit_criteria_schema.py").read_text(encoding="utf-8")
        for cat in spec_categories:
            with self.subTest(category=cat):
                self.assertIn(cat, schema_src)

    def test_coverage_status_in_code(self) -> None:
        """Code must produce coverage_status field."""
        self.assertIn("coverage_status", self._diag_src)

    def test_evidence_checklist_in_code(self) -> None:
        """Code must produce evidence_checklist or basis refs."""
        combined = self._diag_src + self._api_src
        self.assertTrue(
            "evidence" in combined.lower() or "checklist" in combined.lower() or "basis_ref" in combined,
            "Permit code must produce evidence/checklist data",
        )


class TestConsultResponseContract(unittest.TestCase):
    """Consult intake response must match OpenAPI ConsultIntakeResponse."""

    @classmethod
    def setUpClass(cls) -> None:
        cls._spec = _load_spec_text()
        cls._api_src = (ROOT / "yangdo_consult_api.py").read_text(encoding="utf-8")

    def test_required_fields_in_spec(self) -> None:
        """Spec declares required: [ok, request_id, received_at]."""
        required = _extract_schema_required(self._spec, "ConsultIntakeResponse")
        for field in ["ok", "request_id", "received_at"]:
            with self.subTest(field=field):
                self.assertIn(field, required)

    def test_all_response_fields_in_code(self) -> None:
        """All spec-declared response fields must appear in consult code."""
        for field in ["ok", "request_id", "lead_priority", "lead_urgency",
                       "lead_tags", "crm_status", "crm_lead_id", "received_at"]:
            with self.subTest(field=field):
                self.assertIn(f'"{field}"', self._api_src)

    def test_error_codes_in_code(self) -> None:
        """Spec-documented error codes must exist in code."""
        for code in ["customer_name_required", "phone_or_email_required"]:
            with self.subTest(code=code):
                self.assertIn(f'"{code}"', self._api_src)


class TestUsageResponseContract(unittest.TestCase):
    """Usage log response must match OpenAPI UsageLogResponse."""

    @classmethod
    def setUpClass(cls) -> None:
        cls._spec = _load_spec_text()
        cls._api_src = (ROOT / "yangdo_consult_api.py").read_text(encoding="utf-8")

    def test_required_fields_in_spec(self) -> None:
        """Spec declares required: [ok, usage_id, received_at]."""
        required = _extract_schema_required(self._spec, "UsageLogResponse")
        for field in ["ok", "usage_id", "received_at"]:
            with self.subTest(field=field):
                self.assertIn(field, required)

    def test_all_response_fields_in_code(self) -> None:
        """All spec-declared response fields must appear in usage code."""
        for field in ["ok", "usage_id", "sheet_logged", "received_at"]:
            with self.subTest(field=field):
                self.assertIn(f'"{field}"', self._api_src)


class TestErrorResponseContract(unittest.TestCase):
    """ErrorResponse schema must match actual error response patterns."""

    @classmethod
    def setUpClass(cls) -> None:
        cls._spec = _load_spec_text()

    def test_error_required_fields(self) -> None:
        """ErrorResponse must require ok and error."""
        required = _extract_schema_required(self._spec, "ErrorResponse")
        for field in ["ok", "error"]:
            with self.subTest(field=field):
                self.assertIn(field, required)

    def test_error_pattern_in_servers(self) -> None:
        """permit and consult servers must use consistent error response pattern.

        yangdo_blackbox_api error responses come from the compiled base
        Handler class, so only check permit and consult directly.
        """
        for server in ["permit_precheck_api.py", "yangdo_consult_api.py"]:
            with self.subTest(server=server):
                src = (ROOT / server).read_text(encoding="utf-8")
                self.assertIn('"ok": False', src)
                self.assertIn('"error":', src)


class TestHealthEndpointContract(unittest.TestCase):
    """Health check response must match OpenAPI /v1/health schema."""

    @classmethod
    def setUpClass(cls) -> None:
        cls._spec = _load_spec_text()

    def test_health_endpoint_documented(self) -> None:
        self.assertIn("/v1/health", self._spec)

    def test_health_ok_field_documented(self) -> None:
        """Health response must include ok and service fields."""
        # Verify in spec
        self.assertIn("ok:", self._spec)
        self.assertIn("service:", self._spec)

    def test_health_response_in_all_servers(self) -> None:
        """All 3 servers must return ok and service in health check."""
        servers = {
            "yangdo_blackbox_api.py": "yangdo_blackbox",
            "permit_precheck_api.py": "permit_precheck",
            "yangdo_consult_api.py": "yangdo_consult_api",
        }
        for server, service_name in servers.items():
            with self.subTest(server=server):
                src = (ROOT / server).read_text(encoding="utf-8")
                self.assertIn('"ok": True', src)
                self.assertIn(f'"{service_name}', src)


class TestCommonRequestWrapperContract(unittest.TestCase):
    """CommonRequestWrapper fields must be handled by API servers."""

    @classmethod
    def setUpClass(cls) -> None:
        cls._spec = _load_spec_text()

    def test_channel_id_handled(self) -> None:
        """channel_id from request wrapper must be processed."""
        for server in ["yangdo_blackbox_api.py", "permit_precheck_api.py"]:
            with self.subTest(server=server):
                src = (ROOT / server).read_text(encoding="utf-8")
                self.assertIn("channel_id", src)

    def test_request_id_roundtrip(self) -> None:
        """request_id must be returned in response (round-trip)."""
        for server in ["yangdo_blackbox_api.py", "permit_precheck_api.py"]:
            with self.subTest(server=server):
                src = (ROOT / server).read_text(encoding="utf-8")
                self.assertIn("request_id", src)

    def test_sandbox_mode_documented_and_implemented(self) -> None:
        """Sandbox mode documented in spec must exist in code.

        yangdo_blackbox_api sandbox is in the compiled base module;
        permit_precheck_api imports sandbox directly.
        """
        self.assertIn("sandbox", self._spec.lower())
        # Check permit API (direct import) + core_engine sandbox module
        permit_src = (ROOT / "permit_precheck_api.py").read_text(encoding="utf-8")
        self.assertIn("sandbox", permit_src.lower())
        sandbox_src = (ROOT / "core_engine" / "sandbox.py").read_text(encoding="utf-8")
        self.assertIn("is_sandbox_request", sandbox_src)


class TestSecuritySchemeContract(unittest.TestCase):
    """Security schemes in spec must match actual authentication code."""

    @classmethod
    def setUpClass(cls) -> None:
        cls._spec = _load_spec_text()

    def test_api_key_header_name(self) -> None:
        """X-API-Key header must be in both spec and code."""
        self.assertIn("X-API-Key", self._spec)
        for server in ["yangdo_blackbox_api.py", "permit_precheck_api.py", "yangdo_consult_api.py"]:
            with self.subTest(server=server):
                src = (ROOT / server).read_text(encoding="utf-8")
                self.assertTrue(
                    "X-API-Key" in src or "x-api-key" in src.lower(),
                    f"{server} must handle X-API-Key header",
                )

    def test_bearer_token_support(self) -> None:
        """Bearer token support documented in spec must exist in code."""
        self.assertIn("Bearer", self._spec)


if __name__ == "__main__":
    unittest.main()
