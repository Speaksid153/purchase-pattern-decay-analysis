# Early Churn Predictor

Internal decision-support dashboard for identifying Instacart users whose next purchase gap may exceed twice their historical median gap. It ranks an early-decay signal; it does **not** predict customer churn, causal outcomes, or calibrated probabilities.

## What is served

The React dashboard and Python API serve the `leading_xgboost_time_proxy` model. Its held-out user-level relative-time proxy evaluation is:

- ROC-AUC: `0.6607`
- PR-AUC: `0.2585`
- Validated action cutoff: `0.5843` (validation top-10% score cutoff)
- Precision / recall at that cutoff: `35.53%` / `12.68%`
- Median lead time among correctly flagged positive-event users: `12.0` days

The dashboard applies three **Operational Risk Bands** to the model score for customer segmentation and intervention analysis: High Risk (`>= 0.70`), Medium Risk (`0.45 <= score < 0.70`), and Low Risk (`< 0.45`). These are **operational risk bands applied to the model score for customer segmentation and intervention analysis**—not calibrated probabilities or statistically validated probability thresholds.

Current deployed-artifact cohort counts are High: `315`, Medium: `3,933`, Low: `21,470`, Total: `25,718`.

Earlier baseline-versus-leading metrics used an incompatible experiment split and are deliberately not displayed.

## Local setup

Use Python 3.14.x, then install the pinned dependencies:

```powershell
py -m pip install -r requirements.txt
npm ci
```

Start the API in one terminal:

```powershell
py scripts/api_server.py
```

Start the frontend in another:

```powershell
npm run dev
```

Open `http://127.0.0.1:5173`.

## Serving cache

Normal API startup reads only `data/serving/portfolio.sqlite`, `data/serving/customer_detail.sqlite`, and `data/serving/model_metrics.json`; it does not load the raw prediction, SHAP, order, or label artifacts.

To regenerate these offline artifacts after an intentional model/data refresh:

```powershell
py scripts/build_serving_cache.py
py scripts/verify_serving_cache.py
```

The verifier compares all 25,718 raw customer scores and risk bands, cohort sorting/filtering, complete regression payloads for customers 25369 and 63581, and deployed model metrics. The raw files are retained for this audit but are not required at normal runtime.

## Checks

```powershell
npm run check
```

This runs TypeScript checking, the production build, and Python API-contract tests.

For a production static build:

```powershell
npm run build
npm start
```

`npm start` serves the built static site at `http://127.0.0.1:3000`. Set `VITE_API_BASE_URL` to the separately deployed API origin **at build time**. A reverse proxy or an authenticated same-origin deployment is preferred.

## Security and deployment

The API defaults to `127.0.0.1`, permits only local Vite origins, and supports an optional `API_AUTH_TOKEN` bearer token. Set `API_HOST`, `API_PORT`, `ALLOWED_ORIGINS`, and `API_AUTH_TOKEN` for a controlled deployment; never put API secrets in a `VITE_*` variable.

Runtime files are deliberately outside Git. Restore and SHA-256 verify the paths in [deployment/artifacts-manifest.txt](deployment/artifacts-manifest.txt) from a versioned, access-controlled artifact store before deploying. The repository does not provision that store because its location and access policy are an infrastructure decision.

A provider-neutral Docker package is included for a same-origin production deployment. Follow [deployment/README.md](deployment/README.md); it mounts the verified serving cache read-only and keeps the API off the public port. It does not provision infrastructure or deploy the application.

The old Streamlit screens remain only as analysis utilities. The supported operator surface is the React dashboard plus Python API.
