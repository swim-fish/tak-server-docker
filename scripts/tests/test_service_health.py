"""Verify readiness is distinct from Flask liveness and optional services."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from jinja2 import Environment, FileSystemLoader

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import service_health as health


def running() -> dict:
    return {name: {"state": "running", "health": "healthy" if name in health.HEALTH_REQUIRED else "none"}
            for name in health.SERVICE_LABELS if name != "share-public"} | {
                "share-public": {"state": "exited", "health": "none"}}


class ServiceHealthTests(unittest.TestCase):
    @patch.object(health, "worker_state", return_value="ready")
    @patch.object(health, "http_probe", return_value="ready")
    @patch.object(health, "api_probe", return_value="ready")
    def test_optional_share_public_may_be_stopped(self, *_mocks: object) -> None:
        report = health.collect(running())
        self.assertEqual(report["overall"], "ready")
        self.assertEqual(report["application"]["share-public"], "disabled")

    @patch.object(health, "worker_state", return_value="ready")
    @patch.object(health, "http_probe", return_value="ready")
    @patch.object(health, "api_probe", return_value="ready")
    def test_unhealthy_tak_is_not_ready(self, *_mocks: object) -> None:
        containers = running()
        containers["tak-server"]["health"] = "unhealthy"
        self.assertEqual(health.collect(containers)["overall"], "degraded")

    @patch.object(health, "worker_state", return_value="ready")
    @patch.object(health, "http_probe", return_value="ready")
    @patch.object(health, "api_probe", return_value="down")
    def test_running_container_with_failed_application_probe_is_degraded(self, *_mocks: object) -> None:
        self.assertEqual(health.collect(running())["overall"], "degraded")

    @patch.object(health, "worker_state", return_value="down")
    @patch.object(health, "http_probe", return_value="down")
    @patch.object(health, "api_probe", return_value="down")
    def test_missing_compose_snapshot_is_unknown(self, *_mocks: object) -> None:
        self.assertEqual(health.collect()["overall"], "unknown")

    @patch.object(health, "worker_state", return_value="ready")
    @patch.object(health, "http_probe", return_value="ready")
    @patch.object(health, "api_probe", return_value="ready")
    def test_services_page_renders_known_states(self, *_mocks: object) -> None:
        templates = Path(__file__).resolve().parents[2] / "docker/share-portal/templates"
        environment = Environment(loader=FileSystemLoader(str(templates)), autoescape=True)
        page = environment.get_template("services.html").render(
            report=health.collect(running()), error=None, result=None, csrf="test-token",
            labels=health.SERVICE_LABELS, controllable=health.CONTROLLABLE,
            console_nav="", url_for=lambda _endpoint, filename: "/static/" + filename)
        self.assertIn("整體狀態", page)
        self.assertIn("/services/control", page)
        self.assertIn("已停止", page)


if __name__ == "__main__":
    unittest.main()
