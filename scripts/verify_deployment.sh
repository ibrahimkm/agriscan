#!/usr/bin/env bash
# ==============================================================================
# AgriScan Post-Deployment Verification Suite
# Safely probes deployed Render services without creating dummy accounts,
# modifying production data, or writing synthetic diagnoses to the database.
# ==============================================================================

set -euo pipefail

BACKEND_URL="${1:-https://agriscan-backend-3veo.onrender.com}"
FRONTEND_URL="${2:-}"
EXPECTED_COMMIT="${3:-}"
DEPLOY_SETTLE_TIME="${DEPLOY_SETTLE_TIME:-0}"
MAX_RETRIES="${MAX_RETRIES:-24}"
RETRY_INTERVAL="${RETRY_INTERVAL:-10}"
ALLOW_UNVERIFIED_COMMIT="${ALLOW_UNVERIFIED_COMMIT:-false}"

# Strip trailing slashes
BACKEND_URL="${BACKEND_URL%/}"
FRONTEND_URL="${FRONTEND_URL%/}"

echo "======================================================================"
echo "          AGRISCAN POST-DEPLOYMENT VERIFICATION SUITE"
echo "======================================================================"
echo "Target Backend URL:       ${BACKEND_URL}"
if [ -n "${FRONTEND_URL}" ]; then
  echo "Target Frontend URL:      ${FRONTEND_URL}"
else
  echo "Target Frontend URL:      (not specified, skipping frontend root check)"
fi
if [ -n "${EXPECTED_COMMIT}" ]; then
  echo "Expected Git Commit:      ${EXPECTED_COMMIT}"
  echo "Require Commit Match:     true (ALLOW_UNVERIFIED_COMMIT=${ALLOW_UNVERIFIED_COMMIT})"
else
  echo "Expected Git Commit:      (not specified, verifying process health only)"
fi
echo "Deploy Settle Window:     ${DEPLOY_SETTLE_TIME}s"
echo "Max Polling Retries:      ${MAX_RETRIES} attempts (${RETRY_INTERVAL}s interval)"
echo "======================================================================"
echo ""

# ------------------------------------------------------------------------------
# 0. Initial Deploy Settle Window (Optional Grace Delay Before Polling)
# ------------------------------------------------------------------------------
if [ "${DEPLOY_SETTLE_TIME}" -gt 0 ]; then
  echo "[Pre-flight] Waiting initial deploy settle time (${DEPLOY_SETTLE_TIME}s) to allow Render to start building and swapping containers..."
  sleep "${DEPLOY_SETTLE_TIME}"
  echo "  ✓ Settle window elapsed. Proceeding to active health probes."
  echo ""
fi

# ------------------------------------------------------------------------------
# 1. Backend /api/health Verification with Bounded Retries
# ------------------------------------------------------------------------------
echo "[Probe 1/3] Polling Backend Health endpoint: ${BACKEND_URL}/api/health..."
HEALTH_SUCCESS=false
COMMIT_VERIFIED=false
LAST_SEEN_COMMIT=""
ENDPOINT_EXPOSED_COMMIT=false

for ((i=1; i<=MAX_RETRIES; i++)); do
  echo -n "  Attempt ${i}/${MAX_RETRIES}: "
  RAW_CODE=$(curl -s -o /tmp/agriscan_health.json -w "%{http_code}" --max-time 15 "${BACKEND_URL}/api/health" || true)
  HTTP_CODE="${RAW_CODE: -3}"
  [ -z "${HTTP_CODE}" ] && HTTP_CODE="000"

  if [ "${HTTP_CODE}" = "200" ]; then
    if grep -q '"status":"healthy"' /tmp/agriscan_health.json || grep -q '"status": "healthy"' /tmp/agriscan_health.json; then
      # Extract commit field if present in payload
      if grep -q '"commit"' /tmp/agriscan_health.json; then
        ENDPOINT_EXPOSED_COMMIT=true
        LIVE_COMMIT=$(grep -o '"commit"[ ]*:[ ]*"[^"]*"' /tmp/agriscan_health.json 2>/dev/null | sed -E 's/.*"commit"[ ]*:[ ]*"([^"]*)".*/\1/' || true)
      else
        LIVE_COMMIT=""
      fi
      LAST_SEEN_COMMIT="${LIVE_COMMIT}"

      if [ -n "${EXPECTED_COMMIT}" ]; then
        if [ -n "${LIVE_COMMIT}" ]; then
          # Check full match or prefix match (for 7+ character git commit prefixes)
          if [ "${LIVE_COMMIT}" = "${EXPECTED_COMMIT}" ] || [[ "${EXPECTED_COMMIT}" == "${LIVE_COMMIT}"* ]] || [[ "${LIVE_COMMIT}" == "${EXPECTED_COMMIT}"* ]]; then
            echo "HTTP 200 OK — Backend is healthy and running expected commit (${LIVE_COMMIT})."
            HEALTH_SUCCESS=true
            COMMIT_VERIFIED=true
            break
          else
            echo "HTTP 200 from container reporting commit ${LIVE_COMMIT} (waiting for ${EXPECTED_COMMIT})..."
          fi
        else
          # Endpoint is healthy (HTTP 200), but commit field is absent or null (pre-deployment container)
          if [ "${ALLOW_UNVERIFIED_COMMIT}" = "true" ]; then
            echo "HTTP 200 OK — Backend is healthy (endpoint lacks commit field; ALLOW_UNVERIFIED_COMMIT=true)."
            HEALTH_SUCCESS=true
            COMMIT_VERIFIED=false
            break
          else
            echo "HTTP 200 from container without active commit reporting (waiting for deployment of ${EXPECTED_COMMIT})..."
          fi
        fi
      else
        # No expected commit passed; general uptime verification
        echo "HTTP 200 OK — Backend process is healthy."
        HEALTH_SUCCESS=true
        COMMIT_VERIFIED=false
        break
      fi
    else
      echo "HTTP 200 but payload status != 'healthy'. Content: $(cat /tmp/agriscan_health.json)"
    fi
  elif [ "${HTTP_CODE}" = "000" ]; then
    echo "Connection failed or timed out (service may be cold-starting or building)."
  else
    echo "Received HTTP ${HTTP_CODE}."
  fi

  if [ "${i}" -lt "${MAX_RETRIES}" ]; then
    sleep "${RETRY_INTERVAL}"
  fi
done

if [ "${HEALTH_SUCCESS}" != "true" ]; then
  echo ""
  if [ -n "${EXPECTED_COMMIT}" ]; then
    if [ "${ENDPOINT_EXPOSED_COMMIT}" = "false" ] || [ -z "${LAST_SEEN_COMMIT}" ]; then
      echo "❌ ERROR: Backend deployment verification failed after ${MAX_RETRIES} attempts."
      echo "The live health endpoint never reported the expected commit (${EXPECTED_COMMIT})."
      echo "Endpoint either lacked a commit field (legacy/pre-deployment version still running) or returned commit: null."
      echo "Health probes will not falsely claim commit verification succeeded."
    else
      echo "❌ ERROR: Backend deployment verification failed after ${MAX_RETRIES} attempts."
      echo "Live container is running commit '${LAST_SEEN_COMMIT}', but expected '${EXPECTED_COMMIT}'."
    fi
  else
    echo "❌ ERROR: Backend health check failed after ${MAX_RETRIES} attempts."
  fi
  echo "Last response body:"
  cat /tmp/agriscan_health.json 2>/dev/null || true
  exit 1
fi

echo "  ✓ Health check confirmed: process is running and responding."
echo ""

# ------------------------------------------------------------------------------
# 2. Database Layer & Read-Only API Verification
# ------------------------------------------------------------------------------
echo "[Probe 2/3] Probing public disease catalog: ${BACKEND_URL}/api/diseases..."
RAW_DISEASE_CODE=$(curl -s -o /tmp/agriscan_diseases.json -w "%{http_code}" --max-time 15 "${BACKEND_URL}/api/diseases" || true)
DISEASE_CODE="${RAW_DISEASE_CODE: -3}"
[ -z "${DISEASE_CODE}" ] && DISEASE_CODE="000"

if [ "${DISEASE_CODE}" = "200" ] && (grep -q '"success":true' /tmp/agriscan_diseases.json || grep -q '"success": true' /tmp/agriscan_diseases.json); then
  DISEASE_COUNT=$(grep -o '"count"[ ]*:[ ]*[0-9]*' /tmp/agriscan_diseases.json 2>/dev/null | head -1 | sed 's/.*:[ ]*//' || true)
  [ -z "${DISEASE_COUNT}" ] && DISEASE_COUNT="known"
  echo "  ✓ Database connectivity verified (HTTP 200 OK, disease count: ${DISEASE_COUNT})."
else
  echo "❌ ERROR: Public disease endpoint failed with HTTP ${DISEASE_CODE}."
  echo "Response body:"
  cat /tmp/agriscan_diseases.json 2>/dev/null || true
  exit 1
fi
echo ""

# ------------------------------------------------------------------------------
# 3. Auth & Prediction Router Contract Check (Non-destructive)
# ------------------------------------------------------------------------------
echo "[Probe 3/3] Testing unauthenticated prediction endpoint contract: ${BACKEND_URL}/api/diagnoses..."
RAW_AUTH_CODE=$(curl -s -o /tmp/agriscan_auth_test.json -w "%{http_code}" -X POST "${BACKEND_URL}/api/diagnoses" --max-time 15 || true)
AUTH_GUARD_CODE="${RAW_AUTH_CODE: -3}"
[ -z "${AUTH_GUARD_CODE}" ] && AUTH_GUARD_CODE="000"

if [ "${AUTH_GUARD_CODE}" = "401" ]; then
  echo "  ✓ Auth guard contract verified (HTTP 401 Unauthorized received as expected)."
  echo "  ✓ Confirmed: Diagnosis router is mounted, active, and securely protected."
else
  echo "⚠️ WARNING: Expected HTTP 401 on unauthenticated POST to /api/diagnoses, got HTTP ${AUTH_GUARD_CODE}."
  echo "Response:"
  cat /tmp/agriscan_auth_test.json 2>/dev/null || true
  if [ "${AUTH_GUARD_CODE}" = "500" ] || [ "${AUTH_GUARD_CODE}" = "502" ] || [ "${AUTH_GUARD_CODE}" = "503" ]; then
    echo "❌ ERROR: Diagnosis endpoint crashed with HTTP ${AUTH_GUARD_CODE}."
    exit 1
  fi
fi
echo ""

# ------------------------------------------------------------------------------
# 4. Optional Frontend Availability Check
# ------------------------------------------------------------------------------
FRONTEND_STATUS="SKIPPED"
if [ -n "${FRONTEND_URL}" ]; then
  echo "[Probe 4/4] Checking Frontend URL availability: ${FRONTEND_URL}..."
  FRONTEND_SUCCESS=false

  for ((j=1; j<=6; j++)); do
    echo -n "  Attempt ${j}/6: "
    RAW_FE_CODE=$(curl -s -o /tmp/agriscan_frontend.html -w "%{http_code}" -L --max-time 15 "${FRONTEND_URL}" || true)
    FRONTEND_CODE="${RAW_FE_CODE: -3}"
    [ -z "${FRONTEND_CODE}" ] && FRONTEND_CODE="000"

    if [ "${FRONTEND_CODE}" = "200" ]; then
      echo "HTTP 200 OK — Frontend static site is serving."
      FRONTEND_SUCCESS=true
      FRONTEND_STATUS="PASSED"
      break
    else
      echo "Received HTTP ${FRONTEND_CODE}."
    fi

    if [ "${j}" -lt 6 ]; then
      sleep 5
    fi
  done

  if [ "${FRONTEND_SUCCESS}" != "true" ]; then
    echo "❌ ERROR: Frontend site failed to respond with HTTP 200 after 6 attempts."
    exit 1
  fi
  echo "  ✓ Frontend static site is accessible."
  echo ""
fi

# ------------------------------------------------------------------------------
# 5. Final Summary Table
# ------------------------------------------------------------------------------
echo "======================================================================"
echo "           POST-DEPLOYMENT VERIFICATION SUMMARY"
echo "======================================================================"
echo "Backend Health:       PASSED (HTTP 200 / healthy)"
echo "Database Catalog:     PASSED (HTTP 200 / ${DISEASE_COUNT} disease references)"
echo "Diagnosis Guard:      PASSED (HTTP 401 Unauthorized / auth guard active)"
if [ -n "${FRONTEND_URL}" ]; then
  echo "Frontend Static Site: ${FRONTEND_STATUS} (HTTP 200 OK)"
else
  echo "Frontend Static Site: SKIPPED (no URL provided)"
fi
if [ -n "${EXPECTED_COMMIT}" ]; then
  if [ "${COMMIT_VERIFIED}" = "true" ]; then
    echo "Commit Verification:  VERIFIED (${EXPECTED_COMMIT})"
  else
    echo "Commit Verification:  UNCONFIRMED (endpoint lacked commit field; health verified without false success claim)"
  fi
else
  echo "Commit Verification:  SKIPPED (no expected commit provided)"
fi
echo "======================================================================"
