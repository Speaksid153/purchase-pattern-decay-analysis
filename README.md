# Purchase Pattern Decay Analysis

![ML](https://img.shields.io/badge/ML-XGBoost-orange?style=flat-square) ![Frontend](https://img.shields.io/badge/Frontend-React%2019%20%2B%20TypeScript-blue?style=flat-square) ![Backend](https://img.shields.io/badge/Backend-Python%203.14-green?style=flat-square) ![License](https://img.shields.io/badge/License-MIT-lightgrey?style=flat-square) ![Deployment](https://img.shields.io/badge/Deployed-Render-purple?style=flat-square)

> Early behavioral warning system that identifies Instacart users whose next purchase gap may exceed twice their historical median — an operational signal of purchase-rhythm decay.

**[🚀 Open Live Demo](https://purchase-pattern-analysis.onrender.com/)** · **[📦 v1.0.0 Release](https://github.com/Speaksid153/purchase-pattern-decay-analysis/releases/tag/v1.0.0)**

> ⚠️ The free Render instance sleeps after inactivity. First load may take ~60 seconds.

---

## 👥 Authorship

This project is an **equal-contribution collaboration** between [Siddharth R](https://github.com/Speaksid153) and [Shreya B.N.](https://github.com/Shreya-BN-06). The repository being hosted under Siddharth's personal GitHub account does not imply sole authorship. Repository-wide code ownership is formally declared in [`.github/CODEOWNERS`](.github/CODEOWNERS).

---

## 📖 Overview

A deployable machine-learning case study combining an XGBoost scoring pipeline, SHAP explainability, a read-only Python API backed by precomputed SQLite caches, and a full React 19 + TypeScript dashboard with search, filtering, operational-status segmentation, and dark mode.

> ⚠️ **This project is deliberately not presented as a calibrated churn predictor.** The dataset has no global calendar dates, purchase gaps are capped at 30 days, and the score is not a probability. The defensible claim is narrower: purchase-rhythm decay can be ranked as an early operational warning signal.

---

## 🛠️ Skills & Technologies

### Machine Learning & Data Science
| Tool | Role |
|------|------|
| XGBoost | Gradient-boosted tree model for gap-exceedance scoring |
| SHAP | Global and per-customer feature attribution |
| Rolling CV | Two-fold user-lifecycle development validation |
| Feature Engineering | Inter-purchase gap, order frequency, basket behavior |
| Pandas / NumPy | Data wrangling and feature construction |
| Matplotlib | Visualization and explainability output |

### Backend & API
| Tool | Role |
|------|------|
| Python 3.14 | Pipeline, serving API, packaging, and verification |
| SQLite | Precomputed, indexed serving caches — no live inference at serve time |
| Nginx | Rate-limiting, HTTPS proxy, single-origin architecture |
| Docker | Multi-stage builds for local Compose + portfolio deployment |

### Frontend
| Tool | Role |
|------|------|
| React 19 | Production dashboard |
| TypeScript | Strict typing across all dashboard and API components |
| Vite | Development server and production bundler |

### Infrastructure & DevOps
| Tool | Role |
|------|------|
| Render | Free-tier public deployment (portfolio grade) |
| Docker Compose | Local self-hosted path |
| GitHub CI | TypeScript, build, API contracts, notebook parsing, Python compilation, image verification |
| SHA-256 Checksums | Verified serving bundle; fails closed on any mismatch |

---

## 📊 Model Evidence

Selected across two rolling user-lifecycle development folds, retrained on all development rows, and evaluated once on the **untouched final 15% user cohort**.

| Metric | Current | Previous | Δ |
|--------|---------|----------|---|
| Row ROC-AUC | **0.6640** | 0.6607 | +0.0034 |
| Row PR-AUC | **0.2637** | 0.2585 | +0.0052 |
| Latest-customer ROC-AUC | **0.6707** | 0.6604 | +0.0103 |
| Latest-customer PR-AUC | **0.2750** | 0.2650 | +0.0100 |
| Action cutoff | 0.5836 | — | — |
| Precision @ cutoff | 36.01% | — | — |
| Recall @ cutoff | 13.81% | — | — |
| Median lead time (true positives) | **12.0 days** | — | — |

This is a measured improvement, not a breakthrough. More complex feature and weighting variants were tested and rejected when they failed to generalize across rolling folds.

### Operational Status Bands

> Statuses support review ordering and intervention analysis. They are not calibrated probability thresholds.

| Status | Score Range | Users (held-out cohort) |
|------|-------------|------------------------|
| 🔴 Priority | ≥ 0.70 | 295 |
| 🟡 Watch | ≥ 0.45 and < 0.70 | 3,973 |
| 🟢 Stable | < 0.45 | 21,450 |
| **Total** | | **25,718** |

![Global SHAP feature importance](reports/modeling/instacart/plots/shap_global_importance.png)

---

## 📦 What's Included

**Dashboard (React 19 + TypeScript)**
- Customer search, operational-status filtering, sorting, and pagination
- Per-customer SHAP evidence and behavioral detail panel
- Dark mode, responsive layout, and explicit API failure states

**API & Serving**
- Read-only Python API with precomputed SQLite indexes
- Nginx proxy with rate limiting inside the deployment container
- Zero live model inference at serve time

**Notebooks (9 stages, all fully executed)**
- Dataset validation and EDA
- Label construction and feature engineering
- Model training and selection
- Temporal-robustness experiments
- SHAP global and per-instance analysis

**Infrastructure**
- Multi-stage Docker builds (local Compose + single-container public deploy)
- CI suite: TypeScript, production build, API contracts, notebook parsing, Python compilation, deployment image verification
- SHA-256 artifact checksums; raw data and large outputs stay out of Git
- Verified compact release-bundle workflow

---

## 🗂️ Repository Guide

| Path | Contents |
|------|----------|
| [`src/`](src/) | Production React dashboard and analytical insight rules |
| [`notebooks/`](notebooks/) | Nine-stage analytical workflow with retained outputs and rendered evidence |
| [`scripts/`](scripts/) | API server, serving-cache packaging, verification, and benchmarking utilities |
| [`deployment/`](deployment/) | Public and self-hosted deployment runbooks |
| [`reports/project_validation_summary.md`](reports/project_validation_summary.md) | End-to-end validation evidence |
| [`reports/modeling/instacart/phase4_leading_xgboost_report.md`](reports/modeling/instacart/phase4_leading_xgboost_report.md) | Deployed model documentation and limitations |
| [`reports/modeling/instacart/temporal_robustness_report.md`](reports/modeling/instacart/temporal_robustness_report.md) | All development candidates and honest pre/post comparison |
| [`tests/`](tests/) | API contract verification and serving-bundle installation tests |

---

## 💻 Local Development

**Requirements:** Python 3.14.x · Node.js 22.12+

```bash
# Terminal 1 — install dependencies and start API
py -m pip install -r requirements.txt
npm ci
py scripts/api_server.py

# Terminal 2 — start dev server
npm run dev
```

Open **http://127.0.0.1:5173**

> On macOS or Linux, replace `py` with `python3`.

**Analytical reproduction:** Place the Instacart CSVs under `data/instacart/` and open the notebooks in numeric order. Every committed notebook has already been executed against the full dataset — outputs are visible directly on GitHub without re-running.

---

## ✅ Verification

```bash
npm run check
py scripts/verify_serving_cache.py
```

`npm run check` runs TypeScript checking, the production build, and self-contained API-contract tests.

The full cache verifier:
- Compares all 25,718 served scores and status bands against offline artifacts
- Exercises sorting and filtering
- Checks complete detail payloads
- Confirms deployed metrics match expected values

---

## 🚀 Public Deployment (Render)

The browser sees one HTTPS origin; Nginx serves the built dashboard, rate-limits and proxies `/api`, and the Python API listens only inside the container.

**Step 1** — Create the verified serving bundle:
```bash
py scripts/package_serving_cache.py
```

**Step 2** — Upload `deployment/releases/serving-cache-v2-robust.zip` as a versioned GitHub Release asset.

**Step 3** — Connect the repository as a Render Blueprint and set:

| Variable | Value |
|----------|-------|
| `SERVING_BUNDLE_URL` | Direct HTTPS URL of the uploaded asset |
| `SERVING_BUNDLE_SHA256` | Checksum printed by the packaging command |

The container downloads only the three runtime files, verifies the bundle and every internal file before boot, and **fails closed** on any mismatch.

See [`deployment/README.md`](deployment/README.md) for the complete process and the Docker Compose path.

> Render's free service is suitable for a resume demo, not an always-on production workload. Upgrade to a paid instance if cold-start delays become unacceptable.

---

## ⚠️ Data & Limitations

**Dataset:** Anonymized Instacart Market Basket Analysis data published for [Kaggle's 2017 competition](https://www.kaggle.com/c/basket-analysis/overview). Customer IDs are dataset identifiers, not real customer identities. Raw data is not committed. The runtime cache contains only derived scores, aggregate behavior, explanation payloads, and model metrics required by the demo.

**Key limitations:**
- Relative user lifecycle time is a proxy, not calendar-time validation
- The target measures unusually long next-order gaps, not permanent customer loss
- Results show ranking utility, not causal impact or intervention lift
- Appropriate for portfolio and decision-support demonstration only — not autonomous customer treatment

---

## 👤 Project Collaborators

| Collaborator | GitHub |
|---|---|
| Siddharth R | [@Speaksid153](https://github.com/Speaksid153) |
| Shreya B.N. | [@Shreya-BN-06](https://github.com/Shreya-BN-06) |

Both collaborators are credited equally. Repository-wide ownership is declared in [`.github/CODEOWNERS`](.github/CODEOWNERS).

---

## 📄 License

Original project code is released under the [MIT License](LICENSE). Dataset and dependency terms are described in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
