import json
import tempfile
import unittest
from pathlib import Path

from core_engine.tenant_gateway import TenantGateway, TenantProfile, load_tenant_gateway_from_file


class TenantGatewayTests(unittest.TestCase):
    def test_resolve_by_host(self):
        gw = TenantGateway(
            [
                TenantProfile(
                    tenant_id="seoul_main",
                    display_name="SeoulMNA",
                    hosts=("seoulmna.kr", "www.seoulmna.kr"),
                    plan="pro_internal",
                    allowed_features=frozenset({"estimate", "consult"}),
                )
            ],
            strict=True,
        )
        r = gw.resolve(host="www.seoulmna.kr:443", origin="")
        self.assertIsNotNone(r.tenant)
        self.assertEqual(r.tenant.tenant_id, "seoul_main")
        self.assertTrue(gw.check_feature(r, "estimate"))
        self.assertFalse(gw.check_feature(r, "reload"))

    def test_resolve_by_origin(self):
        gw = TenantGateway(
            [
                TenantProfile(
                    tenant_id="partner_a",
                    display_name="PartnerA",
                    hosts=("partner-a.example.com",),
                    plan="standard",
                    allowed_features=frozenset({"estimate"}),
                )
            ],
            strict=True,
        )
        r = gw.resolve(host="", origin="https://partner-a.example.com/widget")
        self.assertIsNotNone(r.tenant)
        self.assertEqual(r.source, "origin")
        self.assertEqual(r.matched_host, "partner-a.example.com")

    def test_strict_unknown_denied(self):
        gw = TenantGateway([], strict=True)
        r = gw.resolve(host="unknown.example.com", origin="")
        self.assertIsNone(r.tenant)
        self.assertFalse(gw.check_feature(r, "estimate"))

    def test_default_tenant_fallback(self):
        gw = TenantGateway(
            [
                TenantProfile(
                    tenant_id="seoul_main",
                    display_name="SeoulMNA",
                    hosts=("seoulmna.co.kr",),
                    plan="pro_internal",
                    allowed_features=frozenset({"estimate", "reload"}),
                )
            ],
            strict=True,
            default_tenant_id="seoul_main",
        )
        r = gw.resolve(host="unknown.example.com", origin="")
        self.assertIsNotNone(r.tenant)
        self.assertEqual(r.source, "default")
        self.assertTrue(gw.check_feature(r, "reload"))

    def test_load_from_json_file_with_plan_defaults(self):
        data = {
            "default_tenant_id": "tenant_alpha",
            "plan_feature_defaults": {
                "standard": ["estimate", "consult", "usage"],
            },
            "tenants": [
                {
                    "tenant_id": "tenant_alpha",
                    "display_name": "Alpha",
                    "hosts": ["alpha.example.com"],
                    "plan": "standard",
                }
            ],
        }
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "tenants.json"
            path.write_text(json.dumps(data), encoding="utf-8")
            gw = load_tenant_gateway_from_file(str(path), strict=True)
            r = gw.resolve(host="alpha.example.com", origin="")
            self.assertIsNotNone(r.tenant)
            self.assertEqual(gw.tenant_count, 1)
            self.assertTrue(gw.check_feature(r, "consult"))
            self.assertFalse(gw.check_feature(r, "reload"))
            self.assertTrue(gw.check_system(r, "yangdo"))
            self.assertFalse(gw.check_system(r, "permit"))

    def test_disabled_tenant_is_denied(self):
        gw = TenantGateway(
            [
                TenantProfile(
                    tenant_id="alpha",
                    display_name="Alpha",
                    hosts=("alpha.example.com",),
                    enabled=False,
                    plan="standard",
                    allowed_features=frozenset({"estimate"}),
                )
            ],
            strict=True,
        )
        r = gw.resolve(host="alpha.example.com", origin="")
        self.assertIsNotNone(r.tenant)
        self.assertFalse(gw.check_feature(r, "estimate"))

    def test_blocked_token_check(self):
        gw = TenantGateway(
            [
                TenantProfile(
                    tenant_id="alpha",
                    display_name="Alpha",
                    hosts=("alpha.example.com",),
                    enabled=True,
                    plan="standard",
                    allowed_features=frozenset({"estimate"}),
                    blocked_api_tokens=frozenset({"token_alpha_123"}),
                )
            ],
            strict=True,
        )
        r = gw.resolve(host="alpha.example.com", origin="")
        self.assertTrue(gw.is_token_blocked(r, "token_alpha_123"))
        self.assertFalse(gw.is_token_blocked(r, "token_beta_456"))

    def test_explicit_allowed_systems_are_enforced(self):
        gw = TenantGateway(
            [
                TenantProfile(
                    tenant_id="alpha",
                    display_name="Alpha",
                    hosts=("alpha.example.com",),
                    enabled=True,
                    plan="standard",
                    allowed_features=frozenset({"estimate", "permit_precheck"}),
                    allowed_systems=frozenset({"permit"}),
                )
            ],
            strict=True,
        )
        r = gw.resolve(host="alpha.example.com", origin="")
        self.assertTrue(gw.check_feature(r, "estimate"))
        self.assertTrue(gw.check_system(r, "permit"))
        self.assertFalse(gw.check_system(r, "yangdo"))


if __name__ == "__main__":
    unittest.main()
