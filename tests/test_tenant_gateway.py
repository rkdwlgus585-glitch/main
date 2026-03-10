"""Comprehensive tests for core_engine.tenant_gateway.

Covers: TenantProfile, TenantResolution, TenantGateway (constructor, resolve,
check_feature, check_system, is_token_blocked), tenant_from_json_entry,
and load_tenant_gateway_from_file.
"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from typing import Set

from core_engine.tenant_gateway import (
    TenantGateway,
    TenantProfile,
    TenantResolution,
    load_tenant_gateway_from_file,
    tenant_from_json_entry,
)


# ── helpers ──────────────────────────────────────────────────────────────
def _make_profile(
    tid: str = "alpha",
    *,
    hosts: tuple[str, ...] = ("alpha.example.com",),
    enabled: bool = True,
    features: frozenset[str] = frozenset(),
    systems: frozenset[str] = frozenset(),
    blocked: frozenset[str] = frozenset(),
    plan: str = "standard",
) -> TenantProfile:
    return TenantProfile(
        tenant_id=tid,
        display_name=tid.title(),
        hosts=hosts,
        enabled=enabled,
        plan=plan,
        allowed_features=features,
        allowed_systems=systems,
        blocked_api_tokens=blocked,
    )


def _gw_with(*profiles: TenantProfile, strict: bool = False, default: str = "") -> TenantGateway:
    return TenantGateway(profiles, strict=strict, default_tenant_id=default)


def _write_json(td: str, data: dict) -> str:
    path = Path(td) / "tenants.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return str(path)


# ══════════════════════════════════════════════════════════════════════════
# TenantGateway — constructor
# ══════════════════════════════════════════════════════════════════════════
class TenantGatewayConstructorTest(unittest.TestCase):
    def test_empty_tenants(self):
        gw = TenantGateway([])
        self.assertEqual(gw.tenant_count, 0)

    def test_blank_tenant_id_skipped(self):
        p = _make_profile(tid="  ")
        gw = _gw_with(p)
        self.assertEqual(gw.tenant_count, 0)

    def test_tenant_id_case_insensitive(self):
        p = _make_profile(tid="ALPHA")
        gw = _gw_with(p)
        self.assertEqual(gw.tenant_count, 1)
        r = gw.resolve(host="alpha.example.com")
        self.assertIsNotNone(r.tenant)

    def test_duplicate_hosts_last_wins(self):
        p1 = _make_profile(tid="one", hosts=("shared.com",))
        p2 = _make_profile(tid="two", hosts=("shared.com",))
        gw = _gw_with(p1, p2)
        r = gw.resolve(host="shared.com")
        self.assertEqual(r.tenant.tenant_id, "two")

    def test_default_tenant_id_lowered(self):
        p = _make_profile(tid="alpha")
        gw = _gw_with(p, default="ALPHA")
        r = gw.resolve(host="unknown.com")
        self.assertIsNotNone(r.tenant)
        self.assertEqual(r.source, "default")


# ══════════════════════════════════════════════════════════════════════════
# resolve()
# ══════════════════════════════════════════════════════════════════════════
class ResolveTest(unittest.TestCase):
    def test_resolve_by_host(self):
        gw = _gw_with(
            _make_profile(
                tid="seoul_main",
                hosts=("seoulmna.kr", "www.seoulmna.kr"),
                features=frozenset({"estimate", "consult"}),
                plan="pro_internal",
            ),
            strict=True,
        )
        r = gw.resolve(host="www.seoulmna.kr:443")
        self.assertIsNotNone(r.tenant)
        self.assertEqual(r.tenant.tenant_id, "seoul_main")
        self.assertTrue(gw.check_feature(r, "estimate"))
        self.assertFalse(gw.check_feature(r, "reload"))

    def test_resolve_by_origin(self):
        gw = _gw_with(
            _make_profile(tid="partner_a", hosts=("partner-a.example.com",), features=frozenset({"estimate"})),
            strict=True,
        )
        r = gw.resolve(origin="https://partner-a.example.com/widget")
        self.assertIsNotNone(r.tenant)
        self.assertEqual(r.source, "origin")
        self.assertEqual(r.matched_host, "partner-a.example.com")

    def test_host_preferred_over_origin(self):
        p1 = _make_profile(tid="host_match", hosts=("host.com",))
        p2 = _make_profile(tid="origin_match", hosts=("origin.com",))
        gw = _gw_with(p1, p2)
        r = gw.resolve(host="host.com", origin="https://origin.com/path")
        self.assertEqual(r.tenant.tenant_id, "host_match")
        self.assertEqual(r.source, "host")

    def test_no_match_no_default(self):
        gw = _gw_with(_make_profile(tid="alpha"))
        r = gw.resolve(host="unknown.com")
        self.assertIsNone(r.tenant)
        self.assertEqual(r.source, "")

    def test_no_match_with_default(self):
        gw = _gw_with(_make_profile(tid="alpha"), default="alpha")
        r = gw.resolve(host="unknown.com")
        self.assertIsNotNone(r.tenant)
        self.assertEqual(r.source, "default")

    def test_empty_host_and_origin(self):
        gw = _gw_with(_make_profile(tid="alpha"))
        r = gw.resolve()
        self.assertIsNone(r.tenant)

    def test_strict_unknown_denied(self):
        gw = _gw_with(strict=True)
        r = gw.resolve(host="unknown.example.com")
        self.assertIsNone(r.tenant)
        self.assertFalse(gw.check_feature(r, "estimate"))


# ══════════════════════════════════════════════════════════════════════════
# check_feature / check_system
# ══════════════════════════════════════════════════════════════════════════
class CheckFeatureTest(unittest.TestCase):
    def test_none_tenant_non_strict(self):
        gw = _gw_with(strict=False)
        r = TenantResolution(tenant=None)
        self.assertTrue(gw.check_feature(r, "anything"))

    def test_none_tenant_strict(self):
        gw = _gw_with(strict=True)
        r = TenantResolution(tenant=None)
        self.assertFalse(gw.check_feature(r, "anything"))

    def test_disabled_tenant_denied(self):
        gw = _gw_with(_make_profile(enabled=False, features=frozenset({"estimate"})))
        r = gw.resolve(host="alpha.example.com")
        self.assertFalse(gw.check_feature(r, "estimate"))

    def test_empty_allowed_features_allows_all(self):
        gw = _gw_with(_make_profile(features=frozenset()))
        r = gw.resolve(host="alpha.example.com")
        self.assertTrue(gw.check_feature(r, "anything"))

    def test_feature_case_insensitive(self):
        gw = _gw_with(_make_profile(features=frozenset({"estimate"})))
        r = gw.resolve(host="alpha.example.com")
        self.assertTrue(gw.check_feature(r, "ESTIMATE"))
        self.assertTrue(gw.check_feature(r, "Estimate"))

    def test_feature_none(self):
        gw = _gw_with(_make_profile(features=frozenset({"estimate"})))
        r = gw.resolve(host="alpha.example.com")
        # None → "" → not in {"estimate"}
        self.assertFalse(gw.check_feature(r, None))  # type: ignore[arg-type]

    def test_feature_whitespace(self):
        gw = _gw_with(_make_profile(features=frozenset({"estimate"})))
        r = gw.resolve(host="alpha.example.com")
        self.assertTrue(gw.check_feature(r, "  estimate  "))


class CheckSystemTest(unittest.TestCase):
    def test_none_tenant_non_strict(self):
        gw = _gw_with(strict=False)
        r = TenantResolution(tenant=None)
        self.assertTrue(gw.check_system(r, "permit"))

    def test_none_tenant_strict(self):
        gw = _gw_with(strict=True)
        r = TenantResolution(tenant=None)
        self.assertFalse(gw.check_system(r, "permit"))

    def test_disabled_tenant_denied(self):
        gw = _gw_with(_make_profile(enabled=False, systems=frozenset({"permit"})))
        r = gw.resolve(host="alpha.example.com")
        self.assertFalse(gw.check_system(r, "permit"))

    def test_empty_allowed_systems_allows_all(self):
        gw = _gw_with(_make_profile(systems=frozenset()))
        r = gw.resolve(host="alpha.example.com")
        self.assertTrue(gw.check_system(r, "anything"))

    def test_system_case_insensitive(self):
        gw = _gw_with(_make_profile(systems=frozenset({"permit"})))
        r = gw.resolve(host="alpha.example.com")
        self.assertTrue(gw.check_system(r, "PERMIT"))

    def test_explicit_systems_enforced(self):
        gw = _gw_with(
            _make_profile(
                features=frozenset({"estimate", "permit_precheck"}),
                systems=frozenset({"permit"}),
            ),
            strict=True,
        )
        r = gw.resolve(host="alpha.example.com")
        self.assertTrue(gw.check_system(r, "permit"))
        self.assertFalse(gw.check_system(r, "yangdo"))


# ══════════════════════════════════════════════════════════════════════════
# is_token_blocked
# ══════════════════════════════════════════════════════════════════════════
class TokenBlockedTest(unittest.TestCase):
    def test_blocked(self):
        gw = _gw_with(_make_profile(blocked=frozenset({"bad_token"})))
        r = gw.resolve(host="alpha.example.com")
        self.assertTrue(gw.is_token_blocked(r, "bad_token"))

    def test_not_blocked(self):
        gw = _gw_with(_make_profile(blocked=frozenset({"bad_token"})))
        r = gw.resolve(host="alpha.example.com")
        self.assertFalse(gw.is_token_blocked(r, "good_token"))

    def test_none_tenant(self):
        gw = _gw_with()
        r = TenantResolution(tenant=None)
        self.assertFalse(gw.is_token_blocked(r, "any"))

    def test_empty_token(self):
        gw = _gw_with(_make_profile(blocked=frozenset({"bad_token"})))
        r = gw.resolve(host="alpha.example.com")
        self.assertFalse(gw.is_token_blocked(r, ""))

    def test_none_token(self):
        gw = _gw_with(_make_profile(blocked=frozenset({"bad_token"})))
        r = gw.resolve(host="alpha.example.com")
        self.assertFalse(gw.is_token_blocked(r, None))  # type: ignore[arg-type]

    def test_whitespace_token(self):
        gw = _gw_with(_make_profile(blocked=frozenset({"bad_token"})))
        r = gw.resolve(host="alpha.example.com")
        self.assertFalse(gw.is_token_blocked(r, "   "))


# ══════════════════════════════════════════════════════════════════════════
# tenant_from_json_entry
# ══════════════════════════════════════════════════════════════════════════
class TenantFromJsonEntryTest(unittest.TestCase):
    def test_minimal_valid(self):
        entry = {"tenant_id": "alpha", "hosts": ["alpha.example.com"]}
        profile = tenant_from_json_entry(entry)
        self.assertIsNotNone(profile)
        self.assertEqual(profile.tenant_id, "alpha")
        self.assertEqual(profile.display_name, "alpha")
        self.assertEqual(profile.plan, "standard")
        self.assertTrue(profile.enabled)

    def test_non_dict(self):
        self.assertIsNone(tenant_from_json_entry("string"))  # type: ignore[arg-type]
        self.assertIsNone(tenant_from_json_entry(None))  # type: ignore[arg-type]
        self.assertIsNone(tenant_from_json_entry(42))  # type: ignore[arg-type]

    def test_missing_tenant_id(self):
        self.assertIsNone(tenant_from_json_entry({}))
        self.assertIsNone(tenant_from_json_entry({"tenant_id": ""}))
        self.assertIsNone(tenant_from_json_entry({"tenant_id": None}))
        self.assertIsNone(tenant_from_json_entry({"tenant_id": "  "}))

    def test_display_name_fallback_to_tenant_id(self):
        profile = tenant_from_json_entry({"tenant_id": "alpha"})
        self.assertEqual(profile.display_name, "alpha")

    def test_display_name_explicit(self):
        profile = tenant_from_json_entry({"tenant_id": "alpha", "display_name": "Alpha Corp"})
        self.assertEqual(profile.display_name, "Alpha Corp")

    def test_hosts_normalized(self):
        profile = tenant_from_json_entry({
            "tenant_id": "alpha",
            "hosts": ["HTTPS://ALPHA.COM:443/path", "http://beta.com"],
        })
        self.assertIn("alpha.com", profile.hosts)
        self.assertIn("beta.com", profile.hosts)

    def test_hosts_non_list_ignored(self):
        profile = tenant_from_json_entry({"tenant_id": "alpha", "hosts": "not-a-list"})
        self.assertEqual(profile.hosts, ())

    def test_hosts_empty_filtered(self):
        profile = tenant_from_json_entry({"tenant_id": "alpha", "hosts": ["", "   ", "valid.com"]})
        self.assertEqual(len(profile.hosts), 1)
        self.assertEqual(profile.hosts[0], "valid.com")

    def test_enabled_false(self):
        profile = tenant_from_json_entry({"tenant_id": "alpha", "enabled": False})
        self.assertFalse(profile.enabled)

    def test_enabled_string_false(self):
        profile = tenant_from_json_entry({"tenant_id": "alpha", "enabled": "false"})
        self.assertFalse(profile.enabled)

    def test_plan_default(self):
        profile = tenant_from_json_entry({"tenant_id": "alpha"})
        self.assertEqual(profile.plan, "standard")

    def test_plan_explicit(self):
        profile = tenant_from_json_entry({"tenant_id": "alpha", "plan": "Pro"})
        self.assertEqual(profile.plan, "pro")

    def test_allowed_features_normalized(self):
        profile = tenant_from_json_entry({
            "tenant_id": "alpha",
            "allowed_features": ["  ESTIMATE  ", "consult", "", None],
        })
        self.assertEqual(profile.allowed_features, frozenset({"estimate", "consult"}))

    def test_allowed_features_non_list_ignored(self):
        profile = tenant_from_json_entry({"tenant_id": "alpha", "allowed_features": "not-a-list"})
        self.assertEqual(profile.allowed_features, frozenset())

    def test_system_auto_detection_permit(self):
        profile = tenant_from_json_entry({
            "tenant_id": "alpha",
            "allowed_features": ["permit_precheck_basic"],
        })
        self.assertIn("permit", profile.allowed_systems)

    def test_system_auto_detection_yangdo(self):
        profile = tenant_from_json_entry({
            "tenant_id": "alpha",
            "allowed_features": ["estimate_full"],
        })
        self.assertIn("yangdo", profile.allowed_systems)

    def test_system_auto_detection_both(self):
        profile = tenant_from_json_entry({
            "tenant_id": "alpha",
            "allowed_features": ["permit_precheck_basic", "estimate_full"],
        })
        self.assertIn("permit", profile.allowed_systems)
        self.assertIn("yangdo", profile.allowed_systems)

    def test_explicit_systems_override_auto(self):
        profile = tenant_from_json_entry({
            "tenant_id": "alpha",
            "allowed_features": ["permit_precheck_basic", "estimate_full"],
            "allowed_systems": ["permit"],
        })
        self.assertEqual(profile.allowed_systems, frozenset({"permit"}))

    def test_blocked_tokens_colon_split(self):
        profile = tenant_from_json_entry({
            "tenant_id": "alpha",
            "blocked_api_tokens": ["label:secret123", "plain_token"],
        })
        self.assertIn("secret123", profile.blocked_api_tokens)
        self.assertIn("plain_token", profile.blocked_api_tokens)

    def test_blocked_tokens_multiple_colons(self):
        profile = tenant_from_json_entry({
            "tenant_id": "alpha",
            "blocked_api_tokens": ["a:b:c"],
        })
        # split(":", 1) → ["a", "b:c"]
        self.assertIn("b:c", profile.blocked_api_tokens)

    def test_blocked_tokens_empty_after_colon(self):
        profile = tenant_from_json_entry({
            "tenant_id": "alpha",
            "blocked_api_tokens": ["label:"],
        })
        # "label:" → split → ["label", ""] → stripped → "" → skipped
        self.assertEqual(profile.blocked_api_tokens, frozenset())

    def test_blocked_tokens_non_list_ignored(self):
        profile = tenant_from_json_entry({
            "tenant_id": "alpha",
            "blocked_api_tokens": "not-a-list",
        })
        self.assertEqual(profile.blocked_api_tokens, frozenset())

    def test_plan_feature_defaults_applied(self):
        defaults = {"standard": {"estimate", "consult"}}
        profile = tenant_from_json_entry({"tenant_id": "alpha", "plan": "standard"}, plan_feature_defaults=defaults)
        self.assertEqual(profile.allowed_features, frozenset({"estimate", "consult"}))

    def test_plan_feature_defaults_not_applied_if_features_explicit(self):
        defaults = {"standard": {"estimate", "consult"}}
        profile = tenant_from_json_entry(
            {"tenant_id": "alpha", "plan": "standard", "allowed_features": ["reload"]},
            plan_feature_defaults=defaults,
        )
        self.assertEqual(profile.allowed_features, frozenset({"reload"}))

    def test_plan_feature_defaults_missing_plan(self):
        defaults = {"pro": {"estimate"}}
        profile = tenant_from_json_entry({"tenant_id": "alpha", "plan": "standard"}, plan_feature_defaults=defaults)
        self.assertEqual(profile.allowed_features, frozenset())


# ══════════════════════════════════════════════════════════════════════════
# load_tenant_gateway_from_file
# ══════════════════════════════════════════════════════════════════════════
class LoadTenantGatewayFromFileTest(unittest.TestCase):
    def test_empty_path(self):
        gw = load_tenant_gateway_from_file("")
        self.assertEqual(gw.tenant_count, 0)

    def test_none_path(self):
        gw = load_tenant_gateway_from_file(None)  # type: ignore[arg-type]
        self.assertEqual(gw.tenant_count, 0)

    def test_with_plan_defaults(self):
        data = {
            "default_tenant_id": "tenant_alpha",
            "plan_feature_defaults": {"standard": ["estimate", "consult", "usage"]},
            "tenants": [
                {"tenant_id": "tenant_alpha", "display_name": "Alpha", "hosts": ["alpha.example.com"], "plan": "standard"}
            ],
        }
        with tempfile.TemporaryDirectory() as td:
            path = _write_json(td, data)
            gw = load_tenant_gateway_from_file(path, strict=True)
            self.assertEqual(gw.tenant_count, 1)
            r = gw.resolve(host="alpha.example.com")
            self.assertTrue(gw.check_feature(r, "consult"))
            self.assertFalse(gw.check_feature(r, "reload"))

    def test_default_tenant_from_file(self):
        data = {
            "default_tenant_id": "alpha",
            "tenants": [{"tenant_id": "alpha", "hosts": ["a.com"]}],
        }
        with tempfile.TemporaryDirectory() as td:
            path = _write_json(td, data)
            gw = load_tenant_gateway_from_file(path)
            r = gw.resolve(host="unknown.com")
            self.assertIsNotNone(r.tenant)
            self.assertEqual(r.source, "default")

    def test_default_tenant_param_overrides_file(self):
        data = {
            "default_tenant_id": "file_default",
            "tenants": [
                {"tenant_id": "file_default", "hosts": ["a.com"]},
                {"tenant_id": "param_default", "hosts": ["b.com"]},
            ],
        }
        with tempfile.TemporaryDirectory() as td:
            path = _write_json(td, data)
            gw = load_tenant_gateway_from_file(path, default_tenant_id="param_default")
            r = gw.resolve(host="unknown.com")
            self.assertEqual(r.tenant.tenant_id, "param_default")

    def test_non_dict_json_root(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "tenants.json"
            path.write_text(json.dumps([1, 2, 3]), encoding="utf-8")
            gw = load_tenant_gateway_from_file(str(path))
            self.assertEqual(gw.tenant_count, 0)

    def test_missing_tenants_key(self):
        with tempfile.TemporaryDirectory() as td:
            path = _write_json(td, {"other": "data"})
            gw = load_tenant_gateway_from_file(path)
            self.assertEqual(gw.tenant_count, 0)

    def test_invalid_entries_skipped(self):
        data = {
            "tenants": [
                {"tenant_id": "alpha", "hosts": ["a.com"]},
                {"not_a_tenant": True},
                None,
                {"tenant_id": "", "hosts": ["b.com"]},
            ],
        }
        with tempfile.TemporaryDirectory() as td:
            path = _write_json(td, data)
            gw = load_tenant_gateway_from_file(path)
            self.assertEqual(gw.tenant_count, 1)

    def test_non_list_tenants(self):
        with tempfile.TemporaryDirectory() as td:
            path = _write_json(td, {"tenants": "not-a-list"})
            gw = load_tenant_gateway_from_file(path)
            self.assertEqual(gw.tenant_count, 0)

    def test_strict_forwarded(self):
        data = {"tenants": [{"tenant_id": "alpha", "hosts": ["a.com"]}]}
        with tempfile.TemporaryDirectory() as td:
            path = _write_json(td, data)
            gw = load_tenant_gateway_from_file(path, strict=True)
            self.assertTrue(gw.strict)

    def test_plan_defaults_non_dict(self):
        data = {
            "plan_feature_defaults": "not-a-dict",
            "tenants": [{"tenant_id": "alpha", "plan": "standard"}],
        }
        with tempfile.TemporaryDirectory() as td:
            path = _write_json(td, data)
            gw = load_tenant_gateway_from_file(path)
            self.assertEqual(gw.tenant_count, 1)


# ══════════════════════════════════════════════════════════════════════════
# Integration / behavioral
# ══════════════════════════════════════════════════════════════════════════
class TenantGatewayIntegrationTest(unittest.TestCase):
    def test_disabled_tenant_token_still_checked(self):
        """Token blocking applies even if tenant is disabled."""
        gw = _gw_with(_make_profile(enabled=False, blocked=frozenset({"bad"})))
        r = gw.resolve(host="alpha.example.com")
        # Tenant is disabled, but we still check tokens
        self.assertTrue(gw.is_token_blocked(r, "bad"))

    def test_multiple_tenants_resolve_correctly(self):
        p1 = _make_profile(tid="alpha", hosts=("alpha.com",))
        p2 = _make_profile(tid="beta", hosts=("beta.com",))
        gw = _gw_with(p1, p2)
        r1 = gw.resolve(host="alpha.com")
        r2 = gw.resolve(host="beta.com")
        self.assertEqual(r1.tenant.tenant_id, "alpha")
        self.assertEqual(r2.tenant.tenant_id, "beta")

    def test_system_auto_detect_via_plan_defaults(self):
        """Plan defaults with permit_precheck → auto-detect 'permit' system."""
        data = {
            "plan_feature_defaults": {"standard": ["permit_precheck_basic", "estimate_simple"]},
            "tenants": [{"tenant_id": "alpha", "hosts": ["a.com"], "plan": "standard"}],
        }
        with tempfile.TemporaryDirectory() as td:
            path = _write_json(td, data)
            gw = load_tenant_gateway_from_file(path)
            r = gw.resolve(host="a.com")
            self.assertTrue(gw.check_system(r, "permit"))
            self.assertTrue(gw.check_system(r, "yangdo"))

    def test_tenant_count_property(self):
        gw = _gw_with(_make_profile(tid="a"), _make_profile(tid="b"), _make_profile(tid="c"))
        self.assertEqual(gw.tenant_count, 3)


if __name__ == "__main__":
    unittest.main()
