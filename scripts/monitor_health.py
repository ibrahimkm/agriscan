#!/usr/bin/env python3
"""
AgriScan Continuous Monitoring & Alerting Engine
Production-safe external service health monitor with:
1. Multi-probe verification (/api/health, /api/diseases, frontend)
2. Accurate latency measurement & configurable SLA thresholds
3. Commit verification without false claims
4. Bounded retries with backoff for Render cold starts
5. Incident state tracking, alert deduplication, and recovery notifications
6. Secret-driven SMTP email alerts (graceful skip when unconfigured)
7. Zero sensitive data leakage
"""

import os
import sys
import json
import time
import smtplib
import argparse
import urllib.request
import urllib.error
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timezone
from typing import Dict, Any, Optional, Tuple

DEFAULT_BACKEND_URL = "https://agriscan-backend-3veo.onrender.com"
DEFAULT_FRONTEND_URL = "https://agriscan-frontend-w5nj.onrender.com"
DEFAULT_STATE_FILE = ".monitor_state.json"
DEFAULT_TIMEOUT_SEC = 10.0
DEFAULT_MAX_LATENCY_SEC = 5.0
DEFAULT_MAX_RETRIES = 6
DEFAULT_BACKOFF_FACTOR = 3.0


def measure_http_request(url: str, timeout: float = DEFAULT_TIMEOUT_SEC) -> Tuple[int, float, str, Dict[str, Any]]:
    """
    Performs a GET request, returns (status_code, latency_seconds, response_body_text, parsed_json_or_empty).
    """
    start_time = time.perf_counter()
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "AgriScan-Monitor/1.0",
            "Accept": "application/json, text/html, */*",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            latency = time.perf_counter() - start_time
            body_bytes = response.read()
            body_text = body_bytes.decode("utf-8", errors="replace")
            status_code = response.getcode()
            parsed_json = {}
            try:
                parsed_json = json.loads(body_text)
            except Exception:
                pass
            return status_code, latency, body_text, parsed_json
    except urllib.error.HTTPError as e:
        latency = time.perf_counter() - start_time
        body_text = e.read().decode("utf-8", errors="replace") if e.fp else ""
        parsed_json = {}
        try:
            parsed_json = json.loads(body_text)
        except Exception:
            pass
        return e.code, latency, body_text, parsed_json
    except Exception as e:
        latency = time.perf_counter() - start_time
        return 0, latency, str(e), {}


def probe_with_retry(
    url: str,
    probe_name: str,
    max_retries: int = DEFAULT_MAX_RETRIES,
    timeout: float = DEFAULT_TIMEOUT_SEC,
    backoff_factor: float = DEFAULT_BACKOFF_FACTOR,
) -> Tuple[int, float, str, Dict[str, Any]]:
    """
    Polls an endpoint with bounded retries and backoff to tolerate cold starts.
    """
    last_res = (0, 0.0, "", {})
    for attempt in range(1, max_retries + 1):
        status_code, latency, body, parsed = measure_http_request(url, timeout=timeout)
        last_res = (status_code, latency, body, parsed)

        # 200 OK or expected client error (not network error / 000 or 5xx)
        if 200 <= status_code < 400:
            if attempt > 1:
                print(f"  ✓ {probe_name} recovered on attempt {attempt}/{max_retries} (HTTP {status_code} in {latency:.2f}s).")
            return last_res

        if attempt < max_retries:
            sleep_time = backoff_factor * attempt
            print(
                f"  [Retry {attempt}/{max_retries}] {probe_name} returned status {status_code} "
                f"in {latency:.2f}s. Backing off {sleep_time:.1f}s for cold-start recovery..."
            )
            time.sleep(sleep_time)

    return last_res


class ServiceHealthMonitor:
    def __init__(
        self,
        backend_url: str = DEFAULT_BACKEND_URL,
        frontend_url: Optional[str] = DEFAULT_FRONTEND_URL,
        expected_commit: Optional[str] = None,
        max_latency_sec: float = DEFAULT_MAX_LATENCY_SEC,
        timeout_sec: float = DEFAULT_TIMEOUT_SEC,
        max_retries: int = DEFAULT_MAX_RETRIES,
        backoff_factor: float = DEFAULT_BACKOFF_FACTOR,
        state_file: str = DEFAULT_STATE_FILE,
    ):
        self.backend_url = backend_url.rstrip("/")
        self.frontend_url = frontend_url.rstrip("/") if frontend_url else None
        self.expected_commit = expected_commit
        self.max_latency_sec = max_latency_sec
        self.timeout_sec = timeout_sec
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.state_file = state_file

    def load_state(self) -> Dict[str, Any]:
        """Loads previous run state for deduplication and recovery tracking safely."""
        default_state = {
            "is_incident_active": False,
            "consecutive_failures": 0,
            "first_failed_at": None,
            "last_alert_at": None,
            "last_status": "UNKNOWN",
        }
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, "r") as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        merged = default_state.copy()
                        merged.update(data)
                        return merged
            except Exception as e:
                print(f"[Warning] Failed to load state from {self.state_file} ({e}); using clean default state.")
        return default_state

    def save_state(self, state: Dict[str, Any]):
        """Persists monitoring state safely."""
        try:
            with open(self.state_file, "w") as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            print(f"[Warning] Unable to save state to {self.state_file}: {e}")

    def run_checks(self) -> Dict[str, Any]:
        """
        Runs all system and service probes.
        """
        print("=" * 70)
        print("       AGRISCAN CONTINUOUS SERVICE HEALTH MONITOR")
        print("=" * 70)
        print(f"Target Backend:      {self.backend_url}")
        print(f"Target Frontend:     {self.frontend_url or '(skipped)'}")
        print(f"Max Latency SLA:     {self.max_latency_sec}s (timeout: {self.timeout_sec}s)")
        print(f"Expected Commit:     {self.expected_commit or '(unspecified)'}")
        print("=" * 70)

        results = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "overall_healthy": True,
            "probes": {},
            "failures": [],
            "warnings": [],
        }

        # ----------------------------------------------------
        # Probe 1: Backend Health Endpoint
        # ----------------------------------------------------
        health_url = f"{self.backend_url}/api/health"
        print(f"\n[Probe 1/3] Checking Backend Health: {health_url}")
        code, latency, body, data = probe_with_retry(
            health_url,
            "Backend Health",
            max_retries=self.max_retries,
            timeout=self.timeout_sec,
            backoff_factor=self.backoff_factor,
        )

        is_available = True
        avail_reasons = []
        if code != 200:
            is_available = False
            avail_reasons.append(f"HTTP {code} (expected 200)")
        elif data.get("status") != "healthy":
            is_available = False
            avail_reasons.append(f"Status '{data.get('status')}' != 'healthy'")

        # Latency SLA evaluation
        latency_ok = (latency <= self.max_latency_sec)

        # Commit verification
        live_commit = data.get("commit")
        commit_status = "SKIPPED"
        commit_mismatch = False
        if self.expected_commit:
            if live_commit:
                if live_commit == self.expected_commit or self.expected_commit.startswith(live_commit) or live_commit.startswith(self.expected_commit):
                    commit_status = f"VERIFIED ({live_commit})"
                else:
                    commit_status = f"MISMATCH (expected {self.expected_commit}, got {live_commit})"
                    commit_mismatch = True
            else:
                commit_status = "UNAVAILABLE (live endpoint has no commit field)"
                results["warnings"].append("Live health endpoint does not expose commit; commit verification unconfirmed.")
        elif live_commit:
            commit_status = f"REPORTED ({live_commit})"

        probe1_pass = is_available and latency_ok and not commit_mismatch

        failure_type = None
        probe1_msg = []
        if not is_available:
            failure_type = "AVAILABILITY_FAILURE"
            probe1_msg.extend(avail_reasons)
        if not latency_ok:
            if not failure_type:
                failure_type = "SLA_VIOLATION"
            probe1_msg.append(f"Latency {latency:.2f}s exceeds SLA {self.max_latency_sec:.2f}s")
        if commit_mismatch:
            if not failure_type:
                failure_type = "COMMIT_MISMATCH"
            probe1_msg.append(commit_status)

        probe1_result = {
            "name": "Backend /api/health",
            "url": health_url,
            "status_code": code,
            "latency_seconds": round(latency, 3),
            "latency_sla_passed": latency_ok,
            "failure_type": failure_type,
            "commit_status": commit_status,
            "passed": probe1_pass,
            "details": "; ".join(probe1_msg) if probe1_msg else "HTTP 200 OK, healthy",
        }
        results["probes"]["backend_health"] = probe1_result

        if not probe1_pass:
            results["overall_healthy"] = False
            results["failures"].append(f"Backend Health [{failure_type}]: {probe1_result['details']}")
            print(f"  ❌ FAILED [{failure_type}]: {probe1_result['details']}")
        else:
            print(f"  ✓ PASSED: HTTP {code} in {latency:.2f}s | Commit: {commit_status}")

        # ----------------------------------------------------
        # Probe 2: Public Disease Catalog API
        # ----------------------------------------------------
        diseases_url = f"{self.backend_url}/api/diseases"
        print(f"\n[Probe 2/3] Checking Public Disease Catalog: {diseases_url}")
        code_d, latency_d, body_d, data_d = probe_with_retry(
            diseases_url,
            "Disease Catalog",
            max_retries=self.max_retries,
            timeout=self.timeout_sec,
            backoff_factor=self.backoff_factor,
        )

        is_available_d = True
        avail_reasons_d = []
        if code_d != 200:
            is_available_d = False
            avail_reasons_d.append(f"HTTP {code_d} (expected 200)")
        elif not data_d.get("success"):
            is_available_d = False
            avail_reasons_d.append("Field 'success' is not true")
        elif not isinstance(data_d.get("data"), list):
            is_available_d = False
            avail_reasons_d.append("Field 'data' is not a list")

        latency_ok_d = (latency_d <= self.max_latency_sec)
        probe2_pass = is_available_d and latency_ok_d

        failure_type_d = None
        probe2_msg = []
        if not is_available_d:
            failure_type_d = "AVAILABILITY_FAILURE"
            probe2_msg.extend(avail_reasons_d)
        if not latency_ok_d:
            if not failure_type_d:
                failure_type_d = "SLA_VIOLATION"
            probe2_msg.append(f"Latency {latency_d:.2f}s exceeds SLA {self.max_latency_sec:.2f}s")

        count_d = data_d.get("count", len(data_d.get("data", [])))

        probe2_result = {
            "name": "Backend /api/diseases",
            "url": diseases_url,
            "status_code": code_d,
            "latency_seconds": round(latency_d, 3),
            "latency_sla_passed": latency_ok_d,
            "failure_type": failure_type_d,
            "disease_count": count_d,
            "passed": probe2_pass,
            "details": "; ".join(probe2_msg) if probe2_msg else f"HTTP 200 OK, {count_d} disease references",
        }
        results["probes"]["disease_catalog"] = probe2_result

        if not probe2_pass:
            results["overall_healthy"] = False
            results["failures"].append(f"Disease Catalog [{failure_type_d}]: {probe2_result['details']}")
            print(f"  ❌ FAILED [{failure_type_d}]: {probe2_result['details']}")
        else:
            print(f"  ✓ PASSED: HTTP {code_d} in {latency_d:.2f}s | {count_d} diseases verified")

        # ----------------------------------------------------
        # Probe 3: Frontend Static Site Availability
        # ----------------------------------------------------
        if self.frontend_url:
            print(f"\n[Probe 3/3] Checking Frontend Availability: {self.frontend_url}")
            code_f, latency_f, body_f, _ = probe_with_retry(
                self.frontend_url,
                "Frontend",
                max_retries=self.max_retries,
                timeout=self.timeout_sec,
                backoff_factor=self.backoff_factor,
            )

            is_available_f = (200 <= code_f < 400)
            latency_ok_f = (latency_f <= self.max_latency_sec)
            probe3_pass = is_available_f and latency_ok_f

            failure_type_f = None
            probe3_msg = []
            if not is_available_f:
                failure_type_f = "AVAILABILITY_FAILURE"
                probe3_msg.append(f"HTTP {code_f} (expected 2xx/3xx)")
            if not latency_ok_f:
                if not failure_type_f:
                    failure_type_f = "SLA_VIOLATION"
                probe3_msg.append(f"Latency {latency_f:.2f}s exceeds SLA {self.max_latency_sec:.2f}s")

            probe3_result = {
                "name": "Frontend Root",
                "url": self.frontend_url,
                "status_code": code_f,
                "latency_seconds": round(latency_f, 3),
                "latency_sla_passed": latency_ok_f,
                "failure_type": failure_type_f,
                "passed": probe3_pass,
                "details": "; ".join(probe3_msg) if probe3_msg else f"HTTP {code_f}",
            }
            results["probes"]["frontend"] = probe3_result

            if not probe3_pass:
                results["overall_healthy"] = False
                results["failures"].append(f"Frontend [{failure_type_f}]: {probe3_result['details']}")
                print(f"  ❌ FAILED [{failure_type_f}]: {probe3_result['details']}")
            else:
                print(f"  ✓ PASSED: HTTP {code_f} in {latency_f:.2f}s")
        else:
            print("\n[Probe 3/3] Frontend check skipped (no URL configured).")

        return results

    def handle_incident_state(self, current_healthy: bool, failures: list) -> Tuple[str, bool]:
        """
        Manages incident state across monitoring intervals.
        Returns (notification_action, should_alert).
        notification_action can be: 'NEW_INCIDENT', 'ONGOING_INCIDENT', 'RECOVERED', 'STABLE_HEALTHY'.
        """
        state = self.load_state()
        was_active = state.get("is_incident_active", False)
        now_iso = datetime.now(timezone.utc).isoformat()

        action = "STABLE_HEALTHY"
        should_alert = False

        if not current_healthy:
            state["consecutive_failures"] = state.get("consecutive_failures", 0) + 1
            if not was_active:
                state["is_incident_active"] = True
                state["first_failed_at"] = now_iso
                state["last_alert_at"] = now_iso
                action = "NEW_INCIDENT"
                should_alert = True
            else:
                action = "ONGOING_INCIDENT"
                # Cooldown: Alert again only after 2 hours (7200 seconds) during ongoing outage
                last_alert_ts = state.get("last_alert_at")
                if last_alert_ts:
                    try:
                        elapsed = (datetime.now(timezone.utc) - datetime.fromisoformat(last_alert_ts)).total_seconds()
                        if elapsed > 7200:
                            should_alert = True
                            state["last_alert_at"] = now_iso
                    except Exception:
                        pass
        else:
            state["consecutive_failures"] = 0
            if was_active:
                state["is_incident_active"] = False
                action = "RECOVERED"
                should_alert = True
                state["last_alert_at"] = now_iso
                state["first_failed_at"] = None

        state["last_status"] = "HEALTHY" if current_healthy else "FAILING"
        self.save_state(state)
        return action, should_alert


def send_email_alert(
    action: str,
    results: Dict[str, Any],
    smtp_host: Optional[str] = None,
    smtp_port: int = 587,
    smtp_user: Optional[str] = None,
    smtp_password: Optional[str] = None,
    alert_to: Optional[str] = None,
    alert_from: Optional[str] = None,
) -> bool:
    """
    Sends structured email notification using SMTP.
    Returns True if sent, False if skipped due to missing config or failure.
    """
    # Check if SMTP configuration is present
    if not (smtp_host and smtp_user and smtp_password and alert_to):
        print("\n[Email Alert] SMTP configuration missing (MONITOR_SMTP_HOST/USERNAME/PASSWORD not set).")
        print("  → Skipping email notification gracefully. Check results are reported in workflow.")
        return False

    sender = alert_from or smtp_user
    recipients = [r.strip() for r in alert_to.split(",") if r.strip()]

    if action == "RECOVERED":
        subject = "🟢 [RESOLVED] AgriScan Production Services Recovered"
        banner_color = "#22c55e"
        status_text = "All health probes have returned to normal."
    else:
        subject = f"🔴 [ALERT] AgriScan Service Outage Detected ({len(results.failures)} issue{'s' if len(results.failures) != 1 else ''})"
        banner_color = "#ef4444"
        status_text = "Automated health checks have detected service disruptions."

    # Build clean HTML content without leaking secrets
    probe_rows = []
    for key, p in results.get("probes", {}).items():
        status_badge = "✅ PASS" if p.get("passed") else "❌ FAIL"
        probe_rows.append(
            f"<tr>"
            f"<td style='padding:8px;border:1px solid #ddd;'><b>{p.get('name')}</b></td>"
            f"<td style='padding:8px;border:1px solid #ddd;'>{status_badge}</td>"
            f"<td style='padding:8px;border:1px solid #ddd;'>{p.get('latency_seconds')}s</td>"
            f"<td style='padding:8px;border:1px solid #ddd;'>{p.get('details')}</td>"
            f"</tr>"
        )

    html_content = f"""
    <html>
      <body style="font-family:Arial,sans-serif;color:#333;line-height:1.6;padding:20px;">
        <div style="background:{banner_color};color:#fff;padding:12px 20px;border-radius:6px;margin-bottom:20px;">
          <h2 style="margin:0;">AgriScan Service Monitoring Alert</h2>
        </div>
        <p><b>Status:</b> {status_text}</p>
        <p><b>Timestamp:</b> {results.get('timestamp')}</p>
        <table style="width:100%;border-collapse:collapse;margin:20px 0;">
          <thead>
            <tr style="background:#f4f4f4;">
              <th style="padding:8px;border:1px solid #ddd;text-align:left;">Service Probe</th>
              <th style="padding:8px;border:1px solid #ddd;text-align:left;">Status</th>
              <th style="padding:8px;border:1px solid #ddd;text-align:left;">Latency</th>
              <th style="padding:8px;border:1px solid #ddd;text-align:left;">Details</th>
            </tr>
          </thead>
          <tbody>
            {''.join(probe_rows)}
          </tbody>
        </table>
        <p style="font-size:12px;color:#777;">
          This is an automated notification from AgriScan Continuous Monitoring.
        </p>
      </body>
    </html>
    """

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = ", ".join(recipients)
    msg.attach(MIMEText(html_content, "html"))

    try:
        print(f"[Email Alert] Connecting to SMTP server {smtp_host}:{smtp_port}...")
        server = smtplib.SMTP(smtp_host, smtp_port, timeout=15)
        server.ehlo()
        server.starttls()
        server.ehlo()
        server.login(smtp_user, smtp_password)
        server.sendmail(sender, recipients, msg.as_string())
        server.close()
        print(f"  ✓ Alert email sent successfully to {len(recipients)} recipient(s).")
        return True
    except Exception as e:
        print(f"  ❌ Failed to send alert email: {e}")
        return False


def write_github_step_summary(results: Dict[str, Any], action: str):
    """Writes formatted status table to GitHub Actions $GITHUB_STEP_SUMMARY if available."""
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if not summary_path:
        return

    status_icon = "🟢 Healthy" if results["overall_healthy"] else "🔴 Disrupted"
    lines = [
        f"## AgriScan Continuous Monitoring Report — {status_icon}\n",
        f"**Timestamp**: `{results['timestamp']}` | **Action**: `{action}`\n",
        "| Probe Name | Status | Latency | Details |",
        "| :--- | :--- | :--- | :--- |",
    ]
    for key, p in results.get("probes", {}).items():
        icon = "✅ Passed" if p.get("passed") else "❌ Failed"
        lines.append(f"| **{p.get('name')}** | {icon} | `{p.get('latency_seconds')}s` | {p.get('details')} |")

    if results["failures"]:
        lines.append("\n### ⚠️ Active Failures:")
        for f in results["failures"]:
            lines.append(f"- {f}")

    if results["warnings"]:
        lines.append("\n### ℹ️ Notices & Warnings:")
        for w in results["warnings"]:
            lines.append(f"- {w}")

    try:
        with open(summary_path, "a") as f:
            f.write("\n".join(lines) + "\n")
    except Exception as e:
        print(f"[Warning] Failed writing to GITHUB_STEP_SUMMARY: {e}")


def main():
    parser = argparse.ArgumentParser(description="AgriScan Production Service Health Monitor")
    parser.add_argument("--backend-url", default=os.environ.get("BACKEND_URL", DEFAULT_BACKEND_URL))
    parser.add_argument("--frontend-url", default=os.environ.get("FRONTEND_URL", DEFAULT_FRONTEND_URL))
    parser.add_argument("--expected-commit", default=os.environ.get("EXPECTED_COMMIT", None))
    parser.add_argument("--max-latency", type=float, default=float(os.environ.get("MAX_LATENCY_SEC", DEFAULT_MAX_LATENCY_SEC)))
    parser.add_argument("--timeout", type=float, default=float(os.environ.get("TIMEOUT_SEC", DEFAULT_TIMEOUT_SEC)))
    parser.add_argument("--max-retries", type=int, default=int(os.environ.get("MAX_RETRIES", DEFAULT_MAX_RETRIES)))
    parser.add_argument("--backoff-factor", type=float, default=float(os.environ.get("BACKOFF_FACTOR", DEFAULT_BACKOFF_FACTOR)))
    parser.add_argument("--state-file", default=DEFAULT_STATE_FILE)
    parser.add_argument("--dry-run", action="store_true", help="Always exit 0 regardless of failures (for dry runs)")

    args = parser.parse_args()

    monitor = ServiceHealthMonitor(
        backend_url=args.backend_url,
        frontend_url=args.frontend_url,
        expected_commit=args.expected_commit,
        max_latency_sec=args.max_latency,
        timeout_sec=args.timeout,
        max_retries=args.max_retries,
        backoff_factor=args.backoff_factor,
        state_file=args.state_file,
    )

    results = monitor.run_checks()
    action, should_alert = monitor.handle_incident_state(results["overall_healthy"], results["failures"])

    # Attempt email alert if required
    if should_alert:
        send_email_alert(
            action=action,
            results=results,
            smtp_host=os.environ.get("MONITOR_SMTP_HOST"),
            smtp_port=int(os.environ.get("MONITOR_SMTP_PORT", 587)),
            smtp_user=os.environ.get("MONITOR_SMTP_USERNAME"),
            smtp_password=os.environ.get("MONITOR_SMTP_PASSWORD"),
            alert_to=os.environ.get("MONITOR_ALERT_TO"),
            alert_from=os.environ.get("MONITOR_ALERT_FROM"),
        )

    # Write GITHUB_STEP_SUMMARY
    write_github_step_summary(results, action)

    # Print final summary table
    print("\n" + "=" * 70)
    print("                 MONITORING EXECUTION SUMMARY")
    print("=" * 70)
    print(f"Overall Status:       {'PASSED (All systems operational)' if results['overall_healthy'] else 'FAILED (Service disruptions detected)'}")
    print(f"Incident Action:      {action}")
    for name, p in results["probes"].items():
        status_label = "PASSED" if p["passed"] else "FAILED"
        print(f"  • {p['name'].ljust(25)} : {status_label} ({p['latency_seconds']}s) - {p['details']}")
    print("=" * 70)

    if not results["overall_healthy"] and not args.dry_run:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
