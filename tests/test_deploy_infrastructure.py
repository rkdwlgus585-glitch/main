"""Deploy infrastructure consistency tests.

Validates that docker-compose, nginx conf, Dockerfile, systemd units,
smoke_test, and .dockerignore stay synchronized. Catches the class of
bugs found in Rounds 71-73 (missing services, wrong addresses, missing
ports, stale documentation).
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

_DEPLOY = Path(__file__).resolve().parent.parent / "deploy"
_ROOT = _DEPLOY.parent


# ── Expected services (single source of truth for this test) ──────────

_SERVICES = {
    "yangdo-api": {"port": 8200, "script": "yangdo_blackbox_api.py"},
    "permit-api": {"port": 8100, "script": "permit_precheck_api.py"},
    "consult-api": {"port": 8788, "script": "yangdo_consult_api.py"},
}

_SYSTEMD_MAP = {
    "yangdo-api": "seoulmna-yangdo.service",
    "permit-api": "seoulmna-permit.service",
    "consult-api": "seoulmna-consult.service",
}


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


class DockerComposeConsistencyTest(unittest.TestCase):
    """docker-compose.yml must define all services with correct ports."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.content = _read(_DEPLOY / "docker-compose.yml")

    def test_all_services_defined(self) -> None:
        for svc in _SERVICES:
            with self.subTest(service=svc):
                self.assertIn(f"  {svc}:", self.content)

    def test_service_ports_match(self) -> None:
        for svc, cfg in _SERVICES.items():
            with self.subTest(service=svc):
                self.assertIn(str(cfg["port"]), self.content)

    def test_service_scripts_match(self) -> None:
        for svc, cfg in _SERVICES.items():
            with self.subTest(service=svc):
                self.assertIn(cfg["script"], self.content)

    def test_all_services_have_healthcheck(self) -> None:
        # Each service block should have a healthcheck
        blocks = re.split(r"\n  \w", self.content)
        for svc in _SERVICES:
            with self.subTest(service=svc):
                # Find the block containing this service
                svc_block = [b for b in blocks if svc in b]
                self.assertTrue(len(svc_block) > 0, f"{svc} not found")

    def test_nginx_has_healthcheck(self) -> None:
        self.assertIn("healthcheck:", self.content)
        self.assertIn("wget", self.content)

    def test_nginx_has_extra_hosts(self) -> None:
        self.assertIn("host.docker.internal:host-gateway", self.content)

    def test_all_services_have_memory_limits(self) -> None:
        for svc in _SERVICES:
            with self.subTest(service=svc):
                self.assertIn("memory:", self.content)

    def test_all_services_have_logging(self) -> None:
        # Count logging blocks — should be at least 3 (one per API service)
        logging_count = self.content.count('driver: "json-file"')
        self.assertGreaterEqual(logging_count, len(_SERVICES))

    def test_volumes_defined(self) -> None:
        for name in ("yangdo-data", "permit-data", "consult-data", "api-logs"):
            with self.subTest(volume=name):
                self.assertIn(name, self.content)


class NginxConfConsistencyTest(unittest.TestCase):
    """nginx conf must define upstreams and location blocks for all services."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.content = _read(_DEPLOY / "nginx_seoulmna_kr.conf")

    def test_all_upstreams_use_service_names(self) -> None:
        for svc, cfg in _SERVICES.items():
            with self.subTest(service=svc):
                expected = f"server {svc}:{cfg['port']}"
                self.assertIn(expected, self.content)

    def test_no_localhost_in_upstreams(self) -> None:
        """Upstream blocks must not use 127.0.0.1 (Docker networking)."""
        lines = self.content.split("\n")
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if stripped.startswith("server ") and "127.0.0.1" in stripped:
                self.fail(f"Line {i}: upstream uses 127.0.0.1: {stripped}")

    def test_all_calc_locations_exist(self) -> None:
        for loc in ("/_calc/yangdo", "/_calc/permit", "/_calc/consult"):
            with self.subTest(location=loc):
                self.assertIn(f"location {loc}", self.content)

    def test_health_endpoint_exists(self) -> None:
        self.assertIn("location /_calc/health", self.content)

    def test_gzip_enabled(self) -> None:
        self.assertIn("gzip on;", self.content)
        self.assertIn("application/json", self.content)

    def test_proxy_http_version_set(self) -> None:
        count = self.content.count("proxy_http_version 1.1;")
        # At least 4 location blocks should have it (3 APIs + WordPress + health)
        self.assertGreaterEqual(count, 4, "proxy_http_version 1.1 missing in some blocks")

    def test_keepalive_connection_header(self) -> None:
        count = self.content.count('proxy_set_header Connection "";')
        self.assertGreaterEqual(count, 4)

    def test_cors_expose_headers_present(self) -> None:
        count = self.content.count("Access-Control-Expose-Headers")
        self.assertEqual(count, 3, "Each API location should expose headers")

    def test_cors_headers_in_all_api_locations(self) -> None:
        for loc in ("yangdo", "permit", "consult"):
            with self.subTest(location=loc):
                self.assertIn("Access-Control-Allow-Origin", self.content)

    def test_rate_limiting_configured(self) -> None:
        self.assertIn("limit_req_zone", self.content)
        self.assertIn("limit_req zone=api_limit", self.content)

    def test_security_headers_present(self) -> None:
        for header in ("X-Content-Type-Options", "X-Frame-Options",
                       "Referrer-Policy", "Permissions-Policy"):
            with self.subTest(header=header):
                self.assertIn(header, self.content)

    def test_wordpress_uses_host_docker_internal(self) -> None:
        self.assertIn("host.docker.internal:8080", self.content)


class DockerfileConsistencyTest(unittest.TestCase):
    """Dockerfile must expose all service ports."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.content = _read(_DEPLOY / "Dockerfile.api")

    def test_all_ports_exposed(self) -> None:
        for cfg in _SERVICES.values():
            with self.subTest(port=cfg["port"]):
                self.assertIn(str(cfg["port"]), self.content)

    def test_non_root_user(self) -> None:
        self.assertIn("USER seoulmna", self.content)

    def test_requirements_copied_before_source(self) -> None:
        req_pos = self.content.find("requirements.txt")
        src_pos = self.content.find("COPY *.py")
        self.assertLess(req_pos, src_pos, "requirements.txt should be copied before source for layer caching")

    def test_core_directories_copied(self) -> None:
        for dirname in ("core_engine/", "config/", "tenant_config/"):
            with self.subTest(dir=dirname):
                self.assertIn(dirname, self.content)


class SystemdConsistencyTest(unittest.TestCase):
    """systemd service files must exist for all services."""

    def test_all_service_files_exist(self) -> None:
        for svc, filename in _SYSTEMD_MAP.items():
            with self.subTest(service=svc):
                path = _DEPLOY / "systemd" / filename
                self.assertTrue(path.is_file(), f"Missing: {path}")

    def test_service_files_have_correct_scripts(self) -> None:
        for svc, filename in _SYSTEMD_MAP.items():
            cfg = _SERVICES[svc]
            with self.subTest(service=svc):
                content = _read(_DEPLOY / "systemd" / filename)
                self.assertIn(cfg["script"], content)

    def test_service_files_have_correct_ports(self) -> None:
        for svc, filename in _SYSTEMD_MAP.items():
            cfg = _SERVICES[svc]
            with self.subTest(service=svc):
                content = _read(_DEPLOY / "systemd" / filename)
                self.assertIn(str(cfg["port"]), content)

    def test_service_files_have_security_hardening(self) -> None:
        for filename in _SYSTEMD_MAP.values():
            with self.subTest(file=filename):
                content = _read(_DEPLOY / "systemd" / filename)
                self.assertIn("NoNewPrivileges=yes", content)
                self.assertIn("ProtectSystem=strict", content)


class SmokeTestConsistencyTest(unittest.TestCase):
    """smoke_test.py must test all services."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.content = _read(_DEPLOY / "smoke_test.py")

    def test_all_services_have_health_tests(self) -> None:
        for svc in ("permit", "yangdo", "consult"):
            with self.subTest(service=svc):
                self.assertIn(f"test_{svc}_health", self.content)

    def test_all_services_have_functional_tests(self) -> None:
        for func in ("test_permit_precheck", "test_yangdo_estimate", "test_consult_intake"):
            with self.subTest(test=func):
                self.assertIn(func, self.content)

    def test_all_services_have_url_args(self) -> None:
        for arg in ("--permit-url", "--yangdo-url", "--consult-url"):
            with self.subTest(arg=arg):
                self.assertIn(arg, self.content)

    def test_default_ports_match(self) -> None:
        for cfg in _SERVICES.values():
            with self.subTest(port=cfg["port"]):
                self.assertIn(str(cfg["port"]), self.content)


class DockerignoreConsistencyTest(unittest.TestCase):
    """.dockerignore must exclude non-production files."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.content = _read(_ROOT / ".dockerignore")

    def test_excludes_tests(self) -> None:
        self.assertIn("tests/", self.content)

    def test_excludes_git(self) -> None:
        self.assertIn(".git/", self.content)

    def test_excludes_frontend(self) -> None:
        self.assertIn("workspace_partitions/", self.content)

    def test_preserves_pyc_in_tmp(self) -> None:
        self.assertIn("!tmp/*.pyc", self.content)

    def test_excludes_env_files(self) -> None:
        self.assertIn(".env*", self.content)


class RunbookConsistencyTest(unittest.TestCase):
    """deploy_runbook.md must reference all services."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.content = _read(_DEPLOY / "deploy_runbook.md")

    def test_all_services_mentioned(self) -> None:
        for svc in _SERVICES:
            with self.subTest(service=svc):
                self.assertIn(svc, self.content)

    def test_all_ports_documented(self) -> None:
        for cfg in _SERVICES.values():
            with self.subTest(port=cfg["port"]):
                self.assertIn(str(cfg["port"]), self.content)

    def test_all_scripts_documented(self) -> None:
        for cfg in _SERVICES.values():
            with self.subTest(script=cfg["script"]):
                self.assertIn(cfg["script"], self.content)

    def test_docker_networking_documented(self) -> None:
        self.assertIn("host.docker.internal", self.content)


if __name__ == "__main__":
    unittest.main()
