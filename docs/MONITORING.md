# AgriScan MLOps Phase 4 — Continuous Monitoring (CM) Guide

This document details the architecture, operational runbooks, metric definitions, drift evaluation, and alerting infrastructure implemented for the AgriScan plant disease detection application.

---

## 1. Monitoring Architecture Overview

AgriScan Continuous Monitoring operates in two decoupled, production-safe layers:

```
┌────────────────────────────────────────────────────────────────────────┐
│                        AGRISCAN MONITORING ARCHITECTURE                │
└────────────────────────────────────────────────────────────────────────┘

  [ Layer 1: Scheduled Synthetic Health & SLA Probing ]
        GitHub Actions Continuous Monitoring (Every 15 mins)
                             │
            ┌────────────────┼────────────────┐
            ▼                ▼                ▼
     Backend /api/health   /api/diseases    Frontend Static Root
     • HTTP 200            • HTTP 200       • HTTP 200
     • Latency < 5.0s SLA  • Catalog Schema • Static Asset Serving
     • Commit SHA Verify   • Disease Count
            │
            ├────────────► State & Alert Deduplication (.monitor_state.json)
            │                  │
            │                  ├─► Incident Opened  ─► SMTP Email Alert (TLS)
            │                  ├─► Cooldown Active  ─► Suppress Duplicate Spam
            │                  └─► Recovered (200)  ─► Resolution Email
            ▼
     GitHub Actions Step Summary Table & Workflow Failure Badges

──────────────────────────────────────────────────────────────────────────

  [ Layer 2: In-Process Runtime & ML Observability ]
        Express API Backend + Real EfficientNet ONNX Runtime
                             │
            ┌────────────────┼────────────────┐
            ▼                ▼                ▼
     HTTP Metrics         ML Inference Metrics    Protected /api/metrics
     • Status 2xx/4xx/5xx • ONNX Latency (ms)     • Prometheus Exposition
     • Request Duration   • Class Predictions     • Structured JSON Format
     • Route Templates    • Confidence Buckets    • Auth: x-metrics-key / Bearer
                          • Low-Conf Rate (<70%)  • Zero Sensitive Data Leaks
                          • Image Payload Bytes
                               │
                               ▼
        Offline / Automated Statistical Drift Analysis (ml/monitor_drift.py)
        • Population Stability Index (PSI) vs Baseline (38 Classes)
        • Jensen-Shannon Divergence (JSD)
        • Sample Sufficiency Gating (Min N=30)
```

---

## 2. System & Service Monitoring (External Probing)

### A. Probed Endpoints
1. **Backend Health (`/api/health`)**:
   - Validates HTTP 200 response and JSON contract: `{ status: 'healthy', service: '...', version: '2.4.0' }`.
   - Compares live commit SHA against expected commit when provided (reports unconfirmed if commit field is absent, never falsely passing).
   - Validates response latency against the configurable SLA (default: `5.0s`).
2. **Public Disease Catalog (`/api/diseases`)**:
   - Validates HTTP 200 and schema: `{ success: true, count: N, data: [...] }`.
   - Confirms database connectivity without mutating database records.
3. **Frontend Static Site (`/`)**:
   - Validates that the Vite-built static site serves HTTP 200 OK without gateway crashes.

### B. Resilience & Cold Starts
Render free-tier web services spin down after inactivity and may take 15–30 seconds to wake. 
To prevent false alarms:
- The probe engine executes **bounded retries with exponential backoff** (up to 3 attempts: initial attempt, 2s backoff, 4s backoff) before declaring a probe failed.
- The per-request connection timeout is set to 10.0 seconds.

---

## 3. GitHub Actions Continuous Monitoring Workflow

The dedicated workflow is located at:
[`.github/workflows/continuous-monitoring.yml`](file:///Users/ibrahim.k.m/MLOPS_final_project/.github/workflows/continuous-monitoring.yml)

### A. Triggers
- **Automated Schedule**: Runs every 15 minutes (`cron: '*/15 * * * *'`).
- **Manual Execution (`workflow_dispatch`)**:
  - `backend_url`: Custom target backend URL.
  - `frontend_url`: Custom target frontend URL.
  - `max_latency_sec`: Custom latency SLA threshold (e.g., `3.0`).
  - `dry_run`: When set to `true`, outputs full diagnostics but exits with code 0 (ideal for safe manual testing).

### B. Security & Least Privilege
- Workflow permissions are strictly limited to `contents: read`.
- Does **not** trigger Render deployment hooks.
- Does **not** download or retrain ML models.
- Does **not** depend on local datasets or private files.

---

## 4. Email Alerting Configuration

Automated email alerts are triggered via SMTP upon detection of service failures.

### A. Required GitHub Secrets
Configure the following secrets in GitHub (**Settings** -> **Secrets and variables** -> **Actions** -> **Repository secrets**):

| Secret Name | Required | Description | Example |
| :--- | :--- | :--- | :--- |
| `MONITOR_SMTP_HOST` | Yes (for email) | SMTP server hostname | `smtp.sendgrid.net`, `smtp.mailgun.org` |
| `MONITOR_SMTP_PORT` | Optional | SMTP port (defaults to 587) | `587` |
| `MONITOR_SMTP_USERNAME` | Yes (for email) | SMTP authentication username | `apikey`, `postmaster@domain.com` |
| `MONITOR_SMTP_PASSWORD` | Yes (for email) | SMTP authentication token/password | `SG.xxxxxxxx...` |
| `MONITOR_ALERT_TO` | Yes (for email) | Destination alert recipient(s) | `oncall@agriscan.io, lead@agriscan.io` |
| `MONITOR_ALERT_FROM` | Optional | Custom sender address | `alerts@agriscan.io` |

> [!IMPORTANT]
> - **Graceful Fallback**: If SMTP secrets are omitted, the monitoring workflow **still executes all health checks and fails with standard GitHub Actions run notifications**. Email delivery is skipped cleanly with an informational log.
> - **Zero Leaks**: Passwords, tokens, and authorization headers are masked and never printed to console logs or summary tables.
> - **Deduplication & Cooldown**: Once an incident is detected, an initial alert is dispatched. Subsequent 15-minute runs during an ongoing outage do not spam recipients (cooldown: 2 hours).
> - **Recovery Notifications**: When a failing service returns to healthy, an automated recovery email (`🟢 [RESOLVED]`) is dispatched.

---

## 5. In-Process Runtime & ML Metrics

The Express backend includes an in-process, zero-dependency metrics collector:
[`backend/src/services/metricsService.js`](file:///Users/ibrahim.k.m/MLOPS_final_project/backend/src/services/metricsService.js)

### A. Endpoint Security: `/api/metrics`
The metrics endpoint is protected against unauthorized public scraping:
- **Production Access**: Requires either:
  1. Header `x-metrics-key: <METRICS_API_KEY>`
  2. Query parameter `?key=<METRICS_API_KEY>`
  3. Header `Authorization: Bearer <VALID_JWT_OR_KEY>`
- **Development/Test**: Allows local loopback (`127.0.0.1`) without authentication.
- **Formats Supported**:
  - `GET /api/metrics` -> Standard Prometheus text format (`text/plain; version=0.0.4`).
  - `GET /api/metrics?format=json` -> Structured JSON summary.

### B. Exported Metric Definitions

| Metric Name | Type | Labels | Description |
| :--- | :--- | :--- | :--- |
| `agriscan_service_info` | Gauge | `version`, `model_version`, `model_checksum` | Static build and model metadata |
| `agriscan_uptime_seconds` | Gauge | — | Uptime in seconds since last backend startup |
| `agriscan_http_requests_total` | Counter | `method`, `route`, `status` | Total HTTP requests by route template and status class |
| `agriscan_http_errors_total` | Counter | `class` (`4xx`, `5xx`) | Server error counters |
| `agriscan_http_request_duration_seconds` | Summary | — | HTTP request latency sum and count |
| `agriscan_ml_predictions_total` | Counter | `crop`, `disease` | Completed diagnoses by crop and pathogen |
| `agriscan_ml_prediction_errors_total` | Counter | `type` | Failed diagnoses (preprocess error, format error) |
| `agriscan_ml_inference_duration_seconds` | Histogram | `le` (`0.05`, `0.10`, `0.25`, `0.50`, `1.0`, `2.5`, `+Inf`) | Real ONNX runtime execution latency |
| `agriscan_ml_confidence_distribution_total` | Counter | `range` (`under_50`, `50_to_69`, `70_to_84`, `85_to_94`, `95_to_100`) | Prediction counts binned by confidence band |
| `agriscan_ml_low_confidence_total` | Counter | — | Total predictions below 70% confidence |
| `agriscan_db_operations_total` | Counter | `operation`, `status` | MongoDB queries by operation and outcome |

### C. Cardinality & Privacy Safeguards
- **Bounded Route Labels**: Paths with IDs (`/api/crops/64fa1...`) are automatically normalized to templates (`/api/crops/:id`).
- **No Personal Data**: User IDs, farmer email addresses, auth tokens, and raw URLs are never used as metric labels.
- **No Image Storage**: Image payloads are inspected in-memory only for metadata (byte size, dimensions). No raw image buffers or base64 strings are retained in metrics.

---

## 6. Statistical ML Drift Detection

Statistical drift analysis is decoupled from request serving and implemented in:
[`ml/monitor_drift.py`](file:///Users/ibrahim.k.m/MLOPS_final_project/ml/monitor_drift.py)

### A. Theoretical Foundation
- **Population Stability Index (PSI)**:
  $$\text{PSI} = \sum_{i=1}^{k} (A_i - E_i) \times \ln\left(\frac{A_i}{E_i}\right)$$
  Where $E_i$ is the expected proportion from the documented baseline, and $A_i$ is the observed proportion in production.
- **Jensen-Shannon (JS) Divergence**: Symmetric, smoothed Kullback-Leibler divergence bounded between $0.0$ and $1.0$.

### B. Standard Interpretation Benchmarks
- $\text{PSI} < 0.10$: **STABLE** — Prediction distribution aligns with baseline. No action required.
- $0.10 \le \text{PSI} < 0.25$: **MODERATE_DRIFT** — Noticeable shift. Monitor incoming crop trends.
- $\text{PSI} \ge 0.25$: **SIGNIFICANT_DRIFT** — Significant shift. Investigate seasonal diseases, sensor changes, or sample demographics.

### C. Sample Sufficiency Gating
Calculating drift on tiny sample sizes produces extreme noise and false alarms. 
- **Minimum Sample Size**: Configured to `30` samples.
- When $N < 30$, `monitor_drift.py` outputs `INSUFFICIENT_DATA` and skips drift scoring, preventing spurious alerts during low-traffic windows.

### D. Critical Distinctions
- **Confidence $\neq$ Accuracy**: A high-confidence model can still make incorrect predictions on out-of-distribution inputs.
- **Drift $\neq$ Model Failure**: An increase in "Potato Late Blight" during a rainy season represents real-world prevalence shift, not model degradation.
- **True Quality Evaluation**: Real accuracy, precision, recall, and F1 require verified ground truth labels evaluated offline via [`ml/evaluate.py`](file:///Users/ibrahim.k.m/MLOPS_final_project/ml/evaluate.py).
- **No Automated Retraining**: Exceeding a drift threshold triggers agronomic investigation, never autonomous model retraining or un-gated deployment.

---

## 7. Baseline Configuration

The documented baseline is stored at:
[`ml/artifacts/baseline_distribution.json`](file:///Users/ibrahim.k.m/MLOPS_final_project/ml/artifacts/baseline_distribution.json)

- Derived from the complete audit of 54,305 PlantVillage images across all 38 supported classes.
- Documents exact class and crop proportions for reference comparison.
- To re-evaluate or update the baseline following verified multi-season dataset expansions:
  ```bash
  python ml/audit_dataset.py
  # Generates updated dataset_audit_report.json
  ```

---

## 8. Incident Response Runbook

When a monitoring alert is received or the scheduled workflow fails:

1. **Step 1: Inspect the Workflow Run**
   - Navigate to **Actions** -> **AgriScan Continuous Monitoring** -> Select the failed run.
   - Review the **Summary** tab for the formatted probe table and exact latency/status failure reason.
2. **Step 2: Isolate the Failure Domain**
   - If **Backend Health** failed: Check Render service logs for crashes or Out-Of-Memory events.
   - If **Disease Catalog** failed: Check MongoDB Atlas cluster connection status and network access rules.
   - If **Frontend** failed: Check Render static site build status and routing rules.
   - If **Latency SLA** exceeded: Check for Render cold start or external network degradation.
3. **Step 3: Manual Probe Verification**
   Run the health probe locally from your terminal:
   ```bash
   python scripts/monitor_health.py --backend-url "https://agriscan-backend-3veo.onrender.com"
   ```
4. **Step 4: Inspect Live Metrics**
   If the backend is reachable, inspect operational metrics:
   ```bash
   curl -H "x-metrics-key: $METRICS_API_KEY" "https://agriscan-backend-3veo.onrender.com/api/metrics?format=json"
   ```

---

## 9. Limitations & Operational Notes

1. **GitHub Actions Scheduling Delays**: GitHub Actions cron triggers are best-effort; during high GitHub platform load, a scheduled run may experience queuing delays of 1–5 minutes. This workflow is a lightweight, zero-cost operational guard, not a replacement for dedicated 24/7 APM agents (e.g. Datadog, New Relic).
2. **Incident State Persistence via GitHub Actions Cache**:
   - **Implementation**: Scheduled runs restore `.monitor_state.json` using `actions/cache/restore@v4` with key prefix `agriscan-monitor-state-` and save updated state via `actions/cache/save@v4` using a run-unique key `agriscan-monitor-state-${{ github.run_id }}-${{ github.run_attempt }}`.
   - **Post-Failure Saving**: The cache-save step specifies `if: always()`, ensuring the failing state is saved even when probes fail. Probing step exit codes remain non-zero, keeping health disruptions visible as failed workflow runs.
   - **Concurrency Serialization**: The workflow specifies `concurrency: { group: agriscan-monitoring, cancel-in-progress: false }`, ensuring consecutive or manual dispatch runs cannot execute concurrently or race on cache saves.
3. **Operational Limitations of Cache Persistence**:
   - **Cache Eviction**: GitHub Actions enforces a 10 GB per-repository cache limit with LRU eviction. If other CI jobs consume cache volume, the monitoring state cache may be evicted prematurely.
   - **Retention Limits**: GitHub automatically purges any cache entry that has not been accessed in over 7 days.
   - **Branch Scoping**: GitHub Actions caches are scoped to the executing branch (`refs/heads/main`). Feature branch runs cannot modify or restore production monitoring caches.
   - **Best-Effort Deduplication**: Because GitHub Actions caches do not offer transactional ACID persistence, cache misses (after eviction or retention purge) cleanly fall back to default state (`is_incident_active: false`). An initial alert may re-trigger if an outage spans a cache eviction boundary. This is a best-effort mitigation designed to eliminate routine alert spam during ongoing incidents, not a guaranteed distributed database.
4. **Safe Disabling**: To temporarily disable continuous monitoring without impacting CI/CD:
   - In GitHub, go to **Actions** -> **AgriScan Continuous Monitoring** -> Click the three dots (`...`) -> **Disable workflow**.
   - CI/CD workflows (`AgriScan CI/CD`) remain entirely independent and unaffected.

---

## 10. Future MLflow & Continuous Training Roadmap

Phase 4 establishes the operational metrics foundation for subsequent MLOps phases:
- **Phase 3 / MLflow Integration**: Connect `metricsService` and `evaluate.py` runs to an MLflow Tracking Server (`MLFLOW_TRACKING_URI`) to record experiment artifacts, confusion matrices, and drift metrics over time.
- **Continuous Training (CT)**: When true ground-truth labels are acquired from verified field diagnostics, scheduled evaluation runs can trigger human-in-the-loop retraining pipelines gated by strict accuracy baselines.
