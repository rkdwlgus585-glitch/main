import unittest

from scripts.validate_tenant_onboarding import validate_registry


def _approved_source(source_id: str = "alpha_source") -> dict:
    return {
        "source_id": source_id,
        "source_name": "Approved Source",
        "access_mode": "first_party_internal",
        "status": "approved",
        "allows_commercial_use": True,
        "contains_personal_data": False,
        "transforms": ["aggregation"],
    }


class TenantOnboardingValidatorTests(unittest.TestCase):
    def test_valid_registry(self):
        registry = {
            "default_tenant_id": "alpha",
            "plan_feature_defaults": {
                "standard": ["estimate", "consult", "usage"],
                "pro_internal": ["estimate", "consult", "usage", "meta", "reload"],
            },
            "tenants": [
                {
                    "tenant_id": "alpha",
                    "display_name": "Alpha",
                    "enabled": True,
                    "plan": "pro_internal",
                    "hosts": ["alpha.example.com"],
                    "origins": ["https://alpha.example.com"],
                    "api_key_envs": ["TENANT_API_KEY_ALPHA"],
                    "data_sources": [_approved_source()],
                }
            ],
        }
        env = {"TENANT_API_KEY_ALPHA": "this_is_a_long_api_key_for_alpha_123456"}
        report = validate_registry(registry, env_values=env)
        self.assertTrue(report["ok"])
        self.assertEqual(report["summary"]["error_count"], 0)

    def test_duplicate_host_error(self):
        registry = {
            "default_tenant_id": "alpha",
            "plan_feature_defaults": {"standard": ["estimate"]},
            "tenants": [
                {
                    "tenant_id": "alpha",
                    "enabled": True,
                    "plan": "standard",
                    "hosts": ["dup.example.com"],
                    "api_key_envs": ["K1"],
                    "data_sources": [_approved_source("alpha_source")],
                },
                {
                    "tenant_id": "beta",
                    "enabled": True,
                    "plan": "standard",
                    "hosts": ["dup.example.com"],
                    "api_key_envs": ["K2"],
                    "data_sources": [_approved_source("beta_source")],
                },
            ],
        }
        env = {
            "K1": "alpha_key_12345678901234567890",
            "K2": "beta_key_123456789012345678901",
        }
        report = validate_registry(registry, env_values=env)
        self.assertFalse(report["ok"])
        self.assertGreaterEqual(report["summary"]["error_count"], 1)

    def test_origin_mismatch_error(self):
        registry = {
            "default_tenant_id": "alpha",
            "plan_feature_defaults": {"standard": ["estimate"]},
            "tenants": [
                {
                    "tenant_id": "alpha",
                    "enabled": True,
                    "plan": "standard",
                    "hosts": ["alpha.example.com"],
                    "origins": ["https://beta.example.com"],
                    "api_key_envs": ["K1"],
                    "data_sources": [_approved_source()],
                }
            ],
        }
        env = {"K1": "alpha_key_12345678901234567890"}
        report = validate_registry(registry, env_values=env)
        self.assertFalse(report["ok"])
        self.assertTrue(any(e.get("code") == "origin_host_mismatch" for e in report.get("errors", [])))

    def test_disallowed_access_mode_error(self):
        registry = {
            "default_tenant_id": "alpha",
            "plan_feature_defaults": {"standard": ["estimate"]},
            "tenants": [
                {
                    "tenant_id": "alpha",
                    "enabled": True,
                    "plan": "standard",
                    "hosts": ["alpha.example.com"],
                    "origins": ["https://alpha.example.com"],
                    "api_key_envs": ["K1"],
                    "data_sources": [
                        {
                            "source_id": "alpha_bad_source",
                            "source_name": "BadSource",
                            "access_mode": "unauthorized_crawling",
                            "status": "approved",
                            "allows_commercial_use": True,
                            "contains_personal_data": False,
                            "transforms": ["aggregation"],
                        }
                    ],
                }
            ],
        }
        env = {"K1": "alpha_key_12345678901234567890"}
        report = validate_registry(registry, env_values=env)
        self.assertFalse(report["ok"])
        self.assertTrue(any(e.get("code") == "disallowed_access_mode" for e in report.get("errors", [])))

    def test_disallowed_transform_error(self):
        registry = {
            "default_tenant_id": "alpha",
            "plan_feature_defaults": {"standard": ["estimate"]},
            "tenants": [
                {
                    "tenant_id": "alpha",
                    "enabled": True,
                    "plan": "standard",
                    "hosts": ["alpha.example.com"],
                    "origins": ["https://alpha.example.com"],
                    "api_key_envs": ["K1"],
                    "data_sources": [
                        {
                            "source_id": "alpha_source",
                            "source_name": "AlphaSource",
                            "access_mode": "first_party_internal",
                            "status": "approved",
                            "allows_commercial_use": True,
                            "contains_personal_data": False,
                            "transforms": ["aggregation", "source_disguise"],
                        }
                    ],
                }
            ],
        }
        env = {"K1": "alpha_key_12345678901234567890"}
        report = validate_registry(registry, env_values=env)
        self.assertFalse(report["ok"])
        self.assertTrue(any(e.get("code") == "disallowed_transform" for e in report.get("errors", [])))

    def test_channel_tenant_system_mismatch_error(self):
        registry = {
            "default_tenant_id": "alpha",
            "plan_feature_defaults": {"standard": ["estimate"]},
            "tenants": [
                {
                    "tenant_id": "alpha",
                    "enabled": True,
                    "plan": "standard",
                    "hosts": ["alpha.example.com"],
                    "origins": ["https://alpha.example.com"],
                    "api_key_envs": ["K1"],
                    "allowed_systems": ["yangdo"],
                    "data_sources": [_approved_source()],
                }
            ],
        }
        channels = {
            "default_channel_id": "alpha_channel",
            "channels": [
                {
                    "channel_id": "alpha_channel",
                    "enabled": True,
                    "display_name": "Alpha Channel",
                    "channel_hosts": ["alpha.example.com"],
                    "engine_origin": "https://calc.example.com",
                    "embed_base_url": "https://calc.example.com/widgets",
                    "default_tenant_id": "alpha",
                    "exposed_systems": ["permit"],
                    "branding": {
                        "brand_name": "Alpha",
                        "brand_label": "Alpha",
                        "site_url": "https://alpha.example.com",
                        "notice_url": "https://alpha.example.com/notice",
                        "contact_phone": "010-0000-0000",
                        "contact_email": "alpha@example.com",
                    },
                }
            ],
        }
        env = {"K1": "alpha_key_12345678901234567890"}
        report = validate_registry(registry, env_values=env, channel_registry=channels)
        self.assertFalse(report["ok"])
        self.assertTrue(any(e.get("code") == "channel_tenant_system_mismatch" for e in report.get("errors", [])))


if __name__ == "__main__":
    unittest.main()
