import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.validate_kr_platform_deploy_ready import (
    build_kr_platform_deploy_ready_report,
)


class ValidateKrPlatformDeployReadyTests(unittest.TestCase):
    @patch("scripts.validate_kr_platform_deploy_ready.inspect_vercel_cli")
    def test_build_ready_report_passes_when_topology_and_vercel_are_ready(self, mock_vercel):
        mock_vercel.return_value = {
            "available": True,
            "mode": "npx",
            "version": "Vercel CLI 42.0.0",
            "auth_ok": True,
            "identity": "demo@example.com",
            "errors": [],
        }
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            front_app = base / "kr_platform_front"
            (front_app / ".next").mkdir(parents=True)
            (front_app / ".next" / "build-manifest.json").write_text("{}", encoding="utf-8")
            (front_app / "package.json").write_text("{}", encoding="utf-8")
            (front_app / "vercel.json").write_text('{"framework":"nextjs"}', encoding="utf-8")
            env_path = front_app / ".env.local"
            env_path.write_text(
                "\n".join(
                    [
                        "NEXT_PUBLIC_PLATFORM_FRONT_HOST=https://seoulmna.kr",
                        "NEXT_PUBLIC_LISTING_HOST=https://seoulmna.co.kr",
                        "NEXT_PUBLIC_CALCULATOR_MOUNT_BASE=https://seoulmna.kr/_calc",
                        "NEXT_PUBLIC_PRIVATE_ENGINE_ORIGIN=https://engine.example.com",
                        "NEXT_PUBLIC_TENANT_ID=seoul_main",
                    ]
                ),
                encoding="utf-8",
            )
            audit_path = base / "front_audit.json"
            traffic_path = base / "traffic_audit.json"
            audit_path.write_text(
                json.dumps(
                    {
                        "front": {
                            "channel_role": "platform_front",
                            "canonical_public_host": "seoulmna.kr",
                            "listing_market_host": "seoulmna.co.kr",
                            "public_calculator_mount_base": "https://seoulmna.kr/_calc",
                            "engine_origin": "https://engine.example.com",
                        },
                        "front_app": {"build_artifacts_ready": True},
                        "completion_summary": {"front_platform_status": "policy_ready_live_confirmation_pending"},
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            traffic_path.write_text(
                json.dumps(
                    {
                        "decision": {"traffic_leak_blocked": True, "remaining_risks": []},
                        "live_probe": {"server_started": True, "all_routes_no_iframe": True},
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            payload = build_kr_platform_deploy_ready_report(
                front_app_path=front_app,
                front_env_path=env_path,
                front_audit_path=audit_path,
                traffic_audit_path=traffic_path,
                check_auth=True,
            )

            self.assertTrue(payload["ok"])
            self.assertEqual(payload["blocking_issues"], [])
            self.assertTrue(payload["handoff"]["preview_deploy_ready"])
            self.assertEqual(payload["topology"]["canonical_public_host"], "seoulmna.kr")
            self.assertTrue(payload["traffic_gate"]["traffic_leak_blocked"])

    @patch("scripts.validate_kr_platform_deploy_ready.inspect_vercel_cli")
    def test_build_ready_report_blocks_on_missing_auth(self, mock_vercel):
        mock_vercel.return_value = {
            "available": True,
            "mode": "npx",
            "version": "Vercel CLI 42.0.0",
            "auth_ok": False,
            "identity": "",
            "errors": ["vercel_auth_missing"],
        }
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            front_app = base / "kr_platform_front"
            (front_app / ".next").mkdir(parents=True)
            (front_app / ".next" / "build-manifest.json").write_text("{}", encoding="utf-8")
            (front_app / "package.json").write_text("{}", encoding="utf-8")
            (front_app / "vercel.json").write_text('{"framework":"nextjs"}', encoding="utf-8")
            env_path = front_app / ".env.local"
            env_path.write_text(
                "\n".join(
                    [
                        "NEXT_PUBLIC_PLATFORM_FRONT_HOST=https://seoulmna.kr",
                        "NEXT_PUBLIC_LISTING_HOST=https://seoulmna.co.kr",
                        "NEXT_PUBLIC_CALCULATOR_MOUNT_BASE=https://seoulmna.kr/_calc",
                        "NEXT_PUBLIC_PRIVATE_ENGINE_ORIGIN=https://engine.example.com",
                        "NEXT_PUBLIC_TENANT_ID=seoul_main",
                    ]
                ),
                encoding="utf-8",
            )
            audit_path = base / "front_audit.json"
            traffic_path = base / "traffic_audit.json"
            audit_path.write_text(
                json.dumps(
                    {
                        "front": {
                            "channel_role": "platform_front",
                            "canonical_public_host": "seoulmna.kr",
                            "listing_market_host": "seoulmna.co.kr",
                            "public_calculator_mount_base": "https://seoulmna.kr/_calc",
                            "engine_origin": "https://engine.example.com",
                        },
                        "front_app": {"build_artifacts_ready": True},
                        "completion_summary": {"front_platform_status": "policy_ready_live_confirmation_pending"},
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            traffic_path.write_text(
                json.dumps(
                    {
                        "decision": {"traffic_leak_blocked": True, "remaining_risks": []},
                        "live_probe": {"server_started": True, "all_routes_no_iframe": True},
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            payload = build_kr_platform_deploy_ready_report(
                front_app_path=front_app,
                front_env_path=env_path,
                front_audit_path=audit_path,
                traffic_audit_path=traffic_path,
                check_auth=True,
            )

            self.assertFalse(payload["ok"])
            self.assertIn("vercel_auth_missing", payload["blocking_issues"])
            self.assertIn("Authenticate Vercel CLI for the kr platform front", payload["handoff"]["next_actions"])

    @patch("scripts.validate_kr_platform_deploy_ready.inspect_vercel_cli")
    def test_build_ready_report_blocks_on_traffic_gate_failure(self, mock_vercel):
        mock_vercel.return_value = {
            "available": True,
            "mode": "npx",
            "version": "Vercel CLI 42.0.0",
            "auth_ok": True,
            "identity": "demo@example.com",
            "errors": [],
        }
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            front_app = base / "kr_platform_front"
            (front_app / ".next").mkdir(parents=True)
            (front_app / ".next" / "build-manifest.json").write_text("{}", encoding="utf-8")
            (front_app / "package.json").write_text("{}", encoding="utf-8")
            (front_app / "vercel.json").write_text('{"framework":"nextjs"}', encoding="utf-8")
            env_path = front_app / ".env.local"
            env_path.write_text(
                "\n".join(
                    [
                        "NEXT_PUBLIC_PLATFORM_FRONT_HOST=https://seoulmna.kr",
                        "NEXT_PUBLIC_LISTING_HOST=https://seoulmna.co.kr",
                        "NEXT_PUBLIC_CALCULATOR_MOUNT_BASE=https://seoulmna.kr/_calc",
                        "NEXT_PUBLIC_PRIVATE_ENGINE_ORIGIN=https://engine.example.com",
                        "NEXT_PUBLIC_TENANT_ID=seoul_main",
                    ]
                ),
                encoding="utf-8",
            )
            audit_path = base / "front_audit.json"
            traffic_path = base / "traffic_audit.json"
            audit_path.write_text(
                json.dumps(
                    {
                        "front": {
                            "channel_role": "platform_front",
                            "canonical_public_host": "seoulmna.kr",
                            "listing_market_host": "seoulmna.co.kr",
                            "public_calculator_mount_base": "https://seoulmna.kr/_calc",
                            "engine_origin": "https://engine.example.com",
                        },
                        "front_app": {"build_artifacts_ready": True},
                        "completion_summary": {"front_platform_status": "policy_ready_live_confirmation_pending"},
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            traffic_path.write_text(
                json.dumps(
                    {
                        "decision": {"traffic_leak_blocked": False, "remaining_risks": ["iframe_present_in_initial_html"]},
                        "live_probe": {"server_started": True, "all_routes_no_iframe": False},
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            payload = build_kr_platform_deploy_ready_report(
                front_app_path=front_app,
                front_env_path=env_path,
                front_audit_path=audit_path,
                traffic_audit_path=traffic_path,
                check_auth=True,
            )

            self.assertFalse(payload["ok"])
            self.assertIn("traffic_gate_not_ready", payload["blocking_issues"])
            self.assertIn(
                "Run validate_kr_traffic_gate.py and clear remaining iframe leak risks before preview deploy",
                payload["handoff"]["next_actions"],
            )


if __name__ == "__main__":
    unittest.main()
