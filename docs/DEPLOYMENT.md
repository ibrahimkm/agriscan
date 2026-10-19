# AgriScan MLOps — Continuous Delivery to Render Guide

This document details the architecture, required secrets, environment protection rules, and verification procedures for the AgriScan Continuous Delivery (CD) pipeline.

---

## 1. CD Architecture & Safety Principles

The Continuous Delivery pipeline deploys the AgriScan application to Render while strictly adhering to MLOps safety constraints:

1. **Strict CI Dependency Gate**: Deployments only trigger after all 4 CI jobs (`security-and-hygiene`, `frontend-ci`, `backend-ci`, `ml-pipeline-ci`) pass successfully.
2. **Branch Protection**: Deployments are restricted exclusively to the `main` branch (`refs/heads/main`). Pull requests can never trigger production deployments.
3. **No In-Flight Retraining**: The deployment uses the pre-trained, versioned ONNX and PyTorch weights already validated by CI.
4. **Non-Destructive Health Probing**: Post-deployment verification tests `/api/health`, `/api/diseases`, and the authentication guard on `/api/diagnoses` without creating synthetic user accounts or polluting the production MongoDB database.

---

## 2. Preventing Duplicate & Un-Gated Deployments (Render vs GitHub Actions)

### The Problem:
By default, Render services created from a GitHub repository or Blueprint (`render.yaml`) have **"Auto-Deploy: Yes"** enabled. This causes Render to trigger a build immediately whenever a commit is pushed to `main` — **before GitHub Actions CI completes**.
If a GitHub Actions CD workflow also triggers a deployment, Render runs **two competing builds** for the same commit, and broken code could be deployed if CI failed after the push.

### The Solution:
To ensure production is gated strictly by CI:
1. Log in to the [Render Dashboard](https://dashboard.render.com).
2. For both **`agriscan-backend`** and **`agriscan-frontend`**:
   - Go to **Settings** -> **Build & Deploy**.
   - Under **Auto-Deploy**, select **"No"**.
   - Click **Save Changes**.
3. With Auto-Deploy set to "No", Render will **only** deploy when triggered via its unique **Deploy Hook URL** called by GitHub Actions after CI passes.

---

## 3. Required GitHub Secrets

Configure the following secrets in your GitHub repository (**Settings** -> **Secrets and variables** -> **Actions** -> **Repository secrets**):

| Secret Name | Required | Description | Where to Obtain in Render Dashboard |
| :--- | :--- | :--- | :--- |
| `RENDER_BACKEND_DEPLOY_HOOK` | **Yes** (for CD) | Webhook URL to trigger backend build | `agriscan-backend` -> **Settings** -> **Deploy Hook** -> Copy URL |
| `RENDER_FRONTEND_DEPLOY_HOOK` | Optional | Webhook URL to trigger frontend static site build | `agriscan-frontend` -> **Settings** -> **Deploy Hook** -> Copy URL |
| `RENDER_FRONTEND_URL` | Optional | Live frontend URL for post-deploy check | `agriscan-frontend` dashboard (e.g., `https://agriscan-frontend.onrender.com`) |

> [!IMPORTANT]
> - Deploy Hook URLs have the format `https://api.render.com/deploy/srv-xxxx?key=yyyy`. Treat these URLs as sensitive secrets and never commit them to Git.
> - Bounded timeouts (`--max-time 30 --connect-timeout 10`) are enforced on all deployment hook triggers.
> - Hook URLs and response bodies containing service or deployment IDs are discarded (`-o /dev/null`) and never printed into CI logs.
> - Frontend deployment is **optional** when `RENDER_FRONTEND_DEPLOY_HOOK` is omitted. However, if the secret is configured and its request fails, the CD job will **fail immediately** with an error.

---

## 4. GitHub Environment & Approval Gates

To enforce manual approval before production deployment:

1. In GitHub, navigate to **Settings** -> **Environments**.
2. Click **New environment** and name it `production`.
3. Under **Deployment protection rules**:
   - Check **Required reviewers**.
   - Add yourself (or authorized senior engineers) as required reviewers.
4. (Optional) Under **Deployment branches**, select **Selected branches** and add `main`.

When `environment: production` is configured, GitHub Actions will automatically pause the workflow run after CI passes and wait for manual approval before executing the deployment job.

---

## 5. Deployment Trigger Strategies

The GitHub Actions workflow supports two deployment modes:

### Strategy A: Manual On-Demand Deployment (Default & Recommended First)
To trigger deployment manually:
1. Go to the **Actions** tab in GitHub.
2. Select the **AgriScan CI/CD** workflow.
3. Click **Run workflow**.
4. Set branch to `main`.
5. Check **"Deploy to Render production after CI passes"** (`deploy_to_production: true`).
6. Click **Run workflow**. All CI checks will run, and upon passing, the production deployment job will execute.

### Strategy B: Automated Continuous Deployment on Every Push to `main`
To enable automatic deployment on every push to `main` after CI passes:
1. In GitHub, go to **Settings** -> **Secrets and variables** -> **Actions** -> **Variables**.
2. Add a new repository variable:
   - Name: `AUTO_DEPLOY_TO_RENDER`
   - Value: `true`
3. With this variable set, every push to `main` that passes CI will trigger deployment (or pause for environment review if approval rules are configured).

---

## 6. Post-Deployment Verification & Commit Verification Mechanics

The deployment job executes [`scripts/verify_deployment.sh`](file:///Users/ibrahim.k.m/MLOPS_final_project/scripts/verify_deployment.sh) after triggering the Render deploy hooks:

1. **Commit Reporting Endpoint**: The backend `/api/health` endpoint exposes `commit: process.env.RENDER_GIT_COMMIT || null` alongside its existing fields (`status: 'healthy'`, `service`, `version`, `timestamp`). Render automatically injects `RENDER_GIT_COMMIT` into all deployed web services connected to a Git repository.
2. **Cold-Start & Health Resilience**: Polls `${BACKEND_URL}/api/health` with up to 24 bounded retries (10s intervals) with a 15s per-probe timeout.
3. **Commit Hash Verification**: When called with an expected commit (`${{ github.sha }}` in CD), the script extracts the active container's commit field and compares it to the expected commit.
4. **Database Verification**: Verifies `/api/diseases` returns HTTP 200 and active disease reference records without mutating state.
5. **Router & Security Verification**: Verifies unauthenticated POST to `/api/diagnoses` returns HTTP 401 Unauthorized, ensuring Express routing and JWT guards are fully operational without crashing.
6. **Optional Frontend Verification**: If `RENDER_FRONTEND_URL` is set, verifies the frontend static site responds with HTTP 200.

---

## 7. First Rollout Transition Guide

### The Reality of Pre-Deployment Containers
The production version running on Render prior to this deployment does **not** expose the `commit` field in `/api/health`. Therefore, deployment scripts cannot assume the pre-deployment version already supports commit reporting.

### How Verification Succeeds During the First Rollout:
1. **No Reliance on Blind Sleep**: The deployment job does not use an arbitrary sleep as proof that a deployment has completed.
2. **Active Polling for Container Swap**:
   - When the deploy hook is triggered, Render begins building the new commit in the background.
   - During the build phase (typically 1.5 to 3 minutes), incoming HTTP requests continue hitting the **pre-deployment container**, which returns HTTP 200 without a `commit` field (or with `commit: null`).
   - `scripts/verify_deployment.sh` inspects the response. Because `EXPECTED_COMMIT` was requested and the active container lacks commit reporting, the script reports:
     `Attempt X: HTTP 200 from container without active commit reporting (waiting for deployment of <target-sha>)...`
   - It continues polling within its bounded retry window (up to 24 attempts, 240 seconds total).
   - Once Render completes the build and swaps containers, the **new container** comes live with `RENDER_GIT_COMMIT` populated.
   - The probe observes `commit: "<target-sha>"`, confirms a match, and records:
     `HTTP 200 OK — Backend is healthy and running expected commit (<target-sha>).`
3. **Honest Failure Reporting**:
   - If Render's build fails or times out, the script reaches its retry limit and exits with code 1. It explicitly states that the expected commit was never seen and that commit verification was not confirmed. It never falsely claims that commit verification succeeded.
4. **Subsequent Rollouts**:
   - Once this patch is live in production, every subsequent deployment will have deterministic container-to-container commit verification: the script will see the previous commit until the exact moment the new commit is swapped in.

---

## 8. Manual Local Verification

To run verification against the production service from your local terminal:

```bash
# Basic health, database, and router check (commit check skipped):
./scripts/verify_deployment.sh "https://agriscan-backend-3veo.onrender.com"

# Check with expected commit validation:
./scripts/verify_deployment.sh "https://agriscan-backend-3veo.onrender.com" "" "<target-commit-sha>"
```
