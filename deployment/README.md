# Deployment runbook

The repository supports two same-origin deployments:

1. `docker compose` for a controlled host, with separate web and API containers and a read-only serving-cache mount.
2. `render.yaml` for a public portfolio demo, with Nginx and the private Python API supervised inside one non-root container.

Neither path exposes the API port directly. TLS is terminated by the hosting platform or upstream proxy.

## Create the verified release bundle

The API needs only these generated runtime files:

- `data/serving/portfolio.sqlite`
- `data/serving/customer_detail.sqlite`
- `data/serving/model_metrics.json`

Confirm their hashes against `artifacts-manifest.txt`, then package them:

```powershell
py scripts/package_serving_cache.py
Get-Content deployment/releases/serving-cache-v1.zip.sha256
```

The generated ZIP and checksum are excluded from Git. Upload both to a versioned GitHub Release or an HTTPS object store. Do not deploy the raw prediction, SHAP, order, label, or training files.

## Deploy the portfolio service on Render

1. Push the repository to GitHub.
2. Create a GitHub Release such as `serving-cache-v1` and attach `serving-cache-v1.zip` plus its `.sha256` file.
3. In Render, create a Blueprint from the repository. Render reads `render.yaml` and builds the final `portfolio` Docker stage.
4. Enter the direct release-asset URL as `SERVING_BUNDLE_URL` and the 64-character lowercase checksum as `SERVING_BUNDLE_SHA256`.
5. Leave `API_AUTH_TOKEN` unset for the anonymous, read-only demo. The public Nginx endpoint rate-limits API requests; the Python port remains loopback-only.
6. After deployment, check `/api/health`, `/api/portfolio-summary`, `/api/customers/25369`, `/api/customers/63581`, and `/api/model-metrics` on the Render URL.

Every cold boot downloads the 14.8 MiB archive because free Render filesystems are ephemeral. Startup verifies the archive SHA-256, an internal manifest, each file size, and each file SHA-256 before either service starts. A missing or modified artifact prevents startup.

The Render free plan sleeps after 15 minutes without traffic. This is acceptable for a portfolio link if the README and resume do not claim an always-on SLA. Use a paid always-on service if cold starts become a presentation problem.

## Run the Compose deployment

Restore the serving cache to a directory outside the repository and verify it:

```powershell
Get-FileHash "$env:SERVING_CACHE_DIR\portfolio.sqlite" -Algorithm SHA256
Get-FileHash "$env:SERVING_CACHE_DIR\customer_detail.sqlite" -Algorithm SHA256
Get-FileHash "$env:SERVING_CACHE_DIR\model_metrics.json" -Algorithm SHA256
```

Start the containers on loopback:

```powershell
$env:SERVING_CACHE_DIR = (Resolve-Path "data/serving")
$env:DASHBOARD_BIND_ADDRESS = "127.0.0.1"
$env:DASHBOARD_PORT = "8080"
docker compose up --build -d
Invoke-WebRequest http://127.0.0.1:8080/api/health
```

Open `http://127.0.0.1:8080`. For an internet-facing host, keep the published port on loopback or a private ingress interface and put managed TLS, authentication, request logging, and monitoring in front of it.

## Release checks

- Confirm the deployed bundle checksum matches the release record.
- Confirm `/api/health` reports `ready` and cohort totals equal 25,718.
- Check customer search, filters, pagination, two customer detail records, and evaluation metrics in the browser.
- Confirm CSP, frame denial, MIME sniffing, referrer, and permissions-policy headers.
- Confirm the deployment container runs as `nginx`, the API binds to `127.0.0.1`, and no database or API port is published.
- Keep the Render spend cap and service status visible; free hosting is not an SLA.
