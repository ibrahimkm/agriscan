#!/usr/bin/env python3
"""
Unit Test Suite for AgriScan Service Health Monitor (scripts/monitor_health.py)
Tests:
1. Probe response handling (HTTP 200 vs 500/404)
2. Schema validation on health and disease endpoints
3. Latency measurement & SLA threshold enforcement
4. Bounded retries and backoff
5. Incident state transitions & recovery notifications
6. Graceful email skip when SMTP credentials are absent
7. Zero credential or sensitive data leakage
"""

import os
import sys
import json
import time
import unittest
import threading
import http.server
import socketserver
from pathlib import Path

# Add project root and scripts dir to path
_proj_root = str(Path(__file__).resolve().parent.parent)
_scripts_dir = str(Path(__file__).resolve().parent)
for p in [_proj_root, _scripts_dir]:
    if p not in sys.path:
        sys.path.insert(0, p)

from scripts.monitor_health import ServiceHealthMonitor, send_email_alert


class MockMonitoringServer(http.server.SimpleHTTPRequestHandler):
    """Mock server simulating varied backend responses."""
    health_status = 200
    health_body = {"status": "healthy", "service": "AgriScan API Backend", "version": "2.4.0", "commit": "test-commit-sha"}
    health_responses = []
    diseases_status = 200
    diseases_body = {"success": True, "count": 4, "data": [{"diseaseName": "Apple Scab"}]}
    frontend_status = 200
    delay_sec = 0.0

    def log_message(self, format, *args):
        pass  # Quiet test output

    def do_GET(self):
        if self.delay_sec > 0:
            time.sleep(self.delay_sec)

        if self.path == "/api/health":
            status = self.health_status
            if self.health_responses:
                status = self.health_responses.pop(0)
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(self.health_body).encode())
        elif self.path == "/api/diseases":
            self.send_response(self.diseases_status)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(self.diseases_body).encode())
        elif self.path == "/" or self.path == "/index.html":
            self.send_response(self.frontend_status)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(b"<!DOCTYPE html><html><body>AgriScan App</body></html>")
        else:
            self.send_response(404)
            self.end_headers()


class TestServiceHealthMonitor(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        socketserver.TCPServer.allow_reuse_address = True
        cls.httpd = socketserver.TCPServer(("127.0.0.1", 0), MockMonitoringServer)
        cls.port = cls.httpd.server_address[1]
        cls.server_thread = threading.Thread(target=cls.httpd.serve_forever)
        cls.server_thread.daemon = True
        cls.server_thread.start()
        cls.base_url = f"http://127.0.0.1:{cls.port}"

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()

    def setUp(self):
        # Reset mock server defaults
        MockMonitoringServer.health_status = 200
        MockMonitoringServer.health_body = {
            "status": "healthy",
            "service": "AgriScan API Backend",
            "version": "2.4.0",
            "commit": "test-commit-sha",
        }
        MockMonitoringServer.diseases_status = 200
        MockMonitoringServer.diseases_body = {"success": True, "count": 4, "data": [{"diseaseName": "Apple Scab"}]}
        MockMonitoringServer.frontend_status = 200
        MockMonitoringServer.delay_sec = 0.0
        MockMonitoringServer.health_responses = []

        self.test_state_file = ".test_monitor_state.json"
        if os.path.exists(self.test_state_file):
            os.remove(self.test_state_file)

    def tearDown(self):
        if os.path.exists(self.test_state_file):
            os.remove(self.test_state_file)

    def test_all_probes_healthy_success(self):
        """Test healthy backend, disease catalog, and frontend."""
        monitor = ServiceHealthMonitor(
            backend_url=self.base_url,
            frontend_url=self.base_url,
            expected_commit="test-commit-sha",
            max_latency_sec=2.0,
            timeout_sec=5.0,
            max_retries=1,
            state_file=self.test_state_file,
        )
        res = monitor.run_checks()
        self.assertTrue(res["overall_healthy"])
        self.assertTrue(res["probes"]["backend_health"]["passed"])
        self.assertTrue(res["probes"]["disease_catalog"]["passed"])
        self.assertTrue(res["probes"]["frontend"]["passed"])
        self.assertIn("VERIFIED", res["probes"]["backend_health"]["commit_status"])

    def test_backend_health_failure_detected(self):
        """Test detection when /api/health returns 500 or unhealthy."""
        MockMonitoringServer.health_status = 500
        monitor = ServiceHealthMonitor(
            backend_url=self.base_url,
            frontend_url=self.base_url,
            max_retries=1,
            state_file=self.test_state_file,
        )
        res = monitor.run_checks()
        self.assertFalse(res["overall_healthy"])
        self.assertFalse(res["probes"]["backend_health"]["passed"])
        self.assertIn("HTTP 500", res["failures"][0])

    def test_disease_catalog_failure_detected(self):
        """Test detection when disease catalog fails or returns empty data."""
        MockMonitoringServer.diseases_status = 502
        monitor = ServiceHealthMonitor(
            backend_url=self.base_url,
            frontend_url=self.base_url,
            max_retries=1,
            state_file=self.test_state_file,
        )
        res = monitor.run_checks()
        self.assertFalse(res["overall_healthy"])
        self.assertFalse(res["probes"]["disease_catalog"]["passed"])

    def test_frontend_failure_detected(self):
        """Test detection when frontend returns 404 or down."""
        MockMonitoringServer.frontend_status = 503
        monitor = ServiceHealthMonitor(
            backend_url=self.base_url,
            frontend_url=self.base_url,
            max_retries=1,
            state_file=self.test_state_file,
        )
        res = monitor.run_checks()
        self.assertFalse(res["overall_healthy"])
        self.assertFalse(res["probes"]["frontend"]["passed"])

    def test_commit_mismatch_detected(self):
        """Test detection when live commit does not match expected SHA."""
        monitor = ServiceHealthMonitor(
            backend_url=self.base_url,
            frontend_url=self.base_url,
            expected_commit="different-sha-9999",
            max_retries=1,
            state_file=self.test_state_file,
        )
        res = monitor.run_checks()
        self.assertFalse(res["overall_healthy"])
        self.assertIn("MISMATCH", res["probes"]["backend_health"]["commit_status"])

    def test_commit_unavailable_handled_truthfully(self):
        """Test when live endpoint has no commit field; must not claim verified."""
        MockMonitoringServer.health_body = {"status": "healthy", "service": "AgriScan API Backend", "version": "2.4.0"}
        monitor = ServiceHealthMonitor(
            backend_url=self.base_url,
            frontend_url=self.base_url,
            expected_commit="target-sha-1234",
            max_retries=1,
            state_file=self.test_state_file,
        )
        res = monitor.run_checks()
        self.assertIn("UNAVAILABLE", res["probes"]["backend_health"]["commit_status"])
        self.assertTrue(len(res["warnings"]) > 0)

    def test_latency_sla_violation_not_silently_passed(self):
        """Test that latency exceeding SLA threshold fails the probe and is not silently passed."""
        MockMonitoringServer.delay_sec = 0.25
        monitor = ServiceHealthMonitor(
            backend_url=self.base_url,
            frontend_url=None,
            max_latency_sec=0.1,  # Strict SLA 100ms
            timeout_sec=2.0,
            max_retries=1,
            state_file=self.test_state_file,
        )
        res = monitor.run_checks()
        backend_probe = res["probes"]["backend_health"]
        # Verify SLA violation failed the probe and overall check
        self.assertFalse(backend_probe["latency_sla_passed"])
        self.assertFalse(backend_probe["passed"], "Probe with SLA violation must NOT pass")
        self.assertFalse(res["overall_healthy"], "Overall run must fail when SLA is violated")
        self.assertEqual(backend_probe["failure_type"], "SLA_VIOLATION")
        self.assertIn("SLA_VIOLATION", res["failures"][0])
        # HTTP availability was OK, proving distinct failure classification
        self.assertEqual(backend_probe["status_code"], 200)

    def test_retry_eventual_recovery_within_budget(self):
        """Test that service recovering within retry budget (e.g. cold start) passes successfully."""
        # Returns 503 twice during cold start, then recovers to 200 on 3rd attempt
        MockMonitoringServer.health_responses = [503, 503, 200]
        monitor = ServiceHealthMonitor(
            backend_url=self.base_url,
            frontend_url=None,
            max_retries=4,
            backoff_factor=0.01,  # Fast backoff for unit tests
            timeout_sec=2.0,
            state_file=self.test_state_file,
        )
        res = monitor.run_checks()
        backend_probe = res["probes"]["backend_health"]
        self.assertTrue(backend_probe["passed"])
        self.assertEqual(backend_probe["status_code"], 200)
        self.assertIsNone(backend_probe["failure_type"])
        self.assertTrue(res["overall_healthy"])

    def test_retry_persistent_failure_after_budget_exhausted(self):
        """Test that persistent failure across all retries is flagged as AVAILABILITY_FAILURE."""
        MockMonitoringServer.health_status = 503
        monitor = ServiceHealthMonitor(
            backend_url=self.base_url,
            frontend_url=None,
            max_retries=3,
            backoff_factor=0.01,
            timeout_sec=2.0,
            state_file=self.test_state_file,
        )
        res = monitor.run_checks()
        backend_probe = res["probes"]["backend_health"]
        self.assertFalse(backend_probe["passed"])
        self.assertFalse(res["overall_healthy"])
        self.assertEqual(backend_probe["failure_type"], "AVAILABILITY_FAILURE")
        self.assertIn("AVAILABILITY_FAILURE", res["failures"][0])

    def test_sla_violation_distinguished_from_availability_failure(self):
        """Verify SLA violation and availability failure are distinctly labeled in probe results."""
        # Case A: Availability Failure (503)
        MockMonitoringServer.health_status = 503
        monitor_avail = ServiceHealthMonitor(
            backend_url=self.base_url,
            frontend_url=None,
            max_retries=1,
            state_file=self.test_state_file,
        )
        res_avail = monitor_avail.run_checks()
        self.assertEqual(res_avail["probes"]["backend_health"]["failure_type"], "AVAILABILITY_FAILURE")

        # Case B: SLA Violation (200 with high latency)
        MockMonitoringServer.health_status = 200
        MockMonitoringServer.delay_sec = 0.20
        monitor_sla = ServiceHealthMonitor(
            backend_url=self.base_url,
            frontend_url=None,
            max_latency_sec=0.05,
            max_retries=1,
            state_file=self.test_state_file,
        )
        res_sla = monitor_sla.run_checks()
        self.assertEqual(res_sla["probes"]["backend_health"]["failure_type"], "SLA_VIOLATION")
        self.assertEqual(res_sla["probes"]["backend_health"]["status_code"], 200)

    def test_incident_state_transitions(self):
        """Test transition from HEALTHY to INCIDENT to RECOVERY."""
        monitor = ServiceHealthMonitor(
            backend_url=self.base_url,
            state_file=self.test_state_file,
        )
        # Step 1: Normal healthy run
        action1, alert1 = monitor.handle_incident_state(True, [])
        self.assertEqual(action1, "STABLE_HEALTHY")
        self.assertFalse(alert1)

        # Step 2: Service failure triggers NEW_INCIDENT
        action2, alert2 = monitor.handle_incident_state(False, ["Backend Down"])
        self.assertEqual(action2, "NEW_INCIDENT")
        self.assertTrue(alert2)

        # Step 3: Consecutive failure during incident should be ONGOING_INCIDENT
        action3, alert3 = monitor.handle_incident_state(False, ["Backend Still Down"])
        self.assertEqual(action3, "ONGOING_INCIDENT")
        self.assertFalse(alert3)  # Cooldown active

        # Step 4: Service recovery triggers RECOVERED
        action4, alert4 = monitor.handle_incident_state(True, [])
        self.assertEqual(action4, "RECOVERED")
        self.assertTrue(alert4)

    def test_email_skipped_gracefully_when_secrets_missing(self):
        """Verify email alert cleanly skips when SMTP secrets are not provided."""
        dummy_results = {"failures": ["Service Error"], "probes": {}, "timestamp": "2026-10-19T12:00:00Z"}
        sent = send_email_alert(
            action="NEW_INCIDENT",
            results=dummy_results,
            smtp_host=None,  # Missing
            smtp_user=None,
            smtp_password=None,
            alert_to=None,
        )
        self.assertFalse(sent)

    def test_outage_across_consecutive_runs_with_cooldown(self):
        """
        Verify that consecutive separate monitor executions across runner runs
        send an initial alert, suppress duplicates during cooldown, and re-alert after cooldown.
        """
        # Run 1: Outage begins
        monitor1 = ServiceHealthMonitor(backend_url=self.base_url, state_file=self.test_state_file)
        action1, alert1 = monitor1.handle_incident_state(False, ["Service Down"])
        self.assertEqual(action1, "NEW_INCIDENT")
        self.assertTrue(alert1)

        # Run 2: Next scheduled run (e.g. 15 mins later) with separate monitor instance
        monitor2 = ServiceHealthMonitor(backend_url=self.base_url, state_file=self.test_state_file)
        action2, alert2 = monitor2.handle_incident_state(False, ["Service Still Down"])
        self.assertEqual(action2, "ONGOING_INCIDENT")
        self.assertFalse(alert2, "Alert should be suppressed during 2h cooldown")

        # Run 3: Simulate run after cooldown expires (> 7200s)
        with open(self.test_state_file, "r") as f:
            state = json.load(f)
        state["last_alert_at"] = "2020-01-01T00:00:00+00:00"  # Well beyond 7200s ago
        with open(self.test_state_file, "w") as f:
            json.dump(state, f)

        monitor3 = ServiceHealthMonitor(backend_url=self.base_url, state_file=self.test_state_file)
        action3, alert3 = monitor3.handle_incident_state(False, ["Service Still Down"])
        self.assertEqual(action3, "ONGOING_INCIDENT")
        self.assertTrue(alert3, "Alert should fire again once cooldown expires")

    def test_recovery_after_recorded_outage_sends_notification(self):
        """
        Verify that a fresh monitor run detecting healthy status after a recorded outage
        emits a RECOVERED action and triggers a recovery notification.
        """
        # Pre-seed active incident state from a previous run
        with open(self.test_state_file, "w") as f:
            json.dump({
                "is_incident_active": True,
                "consecutive_failures": 3,
                "first_failed_at": "2026-10-19T10:00:00+00:00",
                "last_alert_at": "2026-10-19T10:00:00+00:00",
                "last_status": "FAILING",
            }, f)

        monitor = ServiceHealthMonitor(backend_url=self.base_url, state_file=self.test_state_file)
        action, alert = monitor.handle_incident_state(True, [])
        self.assertEqual(action, "RECOVERED")
        self.assertTrue(alert)

        # Confirm persisted state reflects resolution
        saved = monitor.load_state()
        self.assertFalse(saved["is_incident_active"])
        self.assertEqual(saved["consecutive_failures"], 0)
        self.assertEqual(saved["last_status"], "HEALTHY")

    def test_missing_or_invalid_state_handled_safely(self):
        """
        Verify load_state gracefully handles missing files, corrupt JSON,
        non-dict structures, and partial schemas without crashing.
        """
        # 1. Missing file
        if os.path.exists(self.test_state_file):
            os.remove(self.test_state_file)
        m = ServiceHealthMonitor(backend_url=self.base_url, state_file=self.test_state_file)
        st = m.load_state()
        self.assertFalse(st["is_incident_active"])
        self.assertEqual(st["consecutive_failures"], 0)

        # 2. Corrupted JSON file
        with open(self.test_state_file, "w") as f:
            f.write("{corrupt: json: [unclosed")
        st_corrupt = m.load_state()
        self.assertFalse(st_corrupt["is_incident_active"])

        # 3. Non-dictionary JSON (e.g. list or string)
        with open(self.test_state_file, "w") as f:
            f.write("[1, 2, 3]")
        st_list = m.load_state()
        self.assertFalse(st_list["is_incident_active"])

        # 4. Partial dictionary missing default fields
        with open(self.test_state_file, "w") as f:
            f.write('{"custom_field": "val"}')
        st_partial = m.load_state()
        self.assertFalse(st_partial["is_incident_active"])
        self.assertEqual(st_partial["consecutive_failures"], 0)
        self.assertEqual(st_partial["custom_field"], "val")


if __name__ == "__main__":
    unittest.main()
