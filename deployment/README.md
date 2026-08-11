# Deployment runbook

This package runs the React dashboard and Python API behind one same-origin Nginx endpoint. The API is not exposed directly. It is a deployment package only; it does not provision infrastructure or deploy the application.

## Prerequisites

- Docker Engine and Docker Compose v2 on the chosen host.
- A versioned, access-controlled copy of the three normal-runtime files listed in `artifacts-manifest.txt`.
- TLS termination and access control provided by the hosting platform or an upstream reverse proxy.

## Prepare verified artifacts

Restore the serving cache to a directory outside the repository, then compare its SHA-256 hashes with `artifacts-manifest.txt`:

```powershell
Get-FileHash "$env:SERVING_CACHE_DIR\portfolio.sqlite" -Algorithm SHA256
Get-FileHash "$env:SERVING_CACHE_DIR\customer_detail.sqlite" -Algorithm SHA256
Get-FileHash "$env:SERVING_CACHE_DIR\model_metrics.json" -Algorithm SHA256
```

The deployment needs only these three files. Do not ship raw prediction, SHAP, order, label, or model artifacts to normal runtime.

## Start a production-style local container

```powershell
$env:SERVING_CACHE_DIR = (Resolve-Path "data/serving")
$env:DASHBOARD_PORT = "8080"
docker compose up --build -d
Invoke-WebRequest http://127.0.0.1:8080/api/health
```

Open `http://127.0.0.1:8080`. The browser calls `/api` on the same origin, so no build-time API URL or public API port is required.

## Production handoff checklist

1. Restore and checksum-verify the serving cache from the approved artifact store.
2. Set `SERVING_CACHE_DIR` to that absolute host path and choose `DASHBOARD_PORT` only for internal ingress.
3. Put TLS and user authentication at the platform ingress/reverse proxy. Do not set `API_AUTH_TOKEN` unless the frontend is also changed to send it.
4. Run `docker compose up --build -d`, then confirm `/api/health`, `/api/portfolio-summary`, customer `25369`, customer `63581`, and the evaluation metrics from the same deployed endpoint.
5. Restrict network access to the web service and retain the artifact version/checksums with the release record.
