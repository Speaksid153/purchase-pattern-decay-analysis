# Antigravity Handoff Prompt

You are taking over an existing project on my local machine:

the repository root

Project name: **Early Behavioral Churn Prediction**

The project is about predicting early customer churn/behavioral decay using Instacart user-order behavior. The core idea is not generic churn prediction. The point is to detect **gradual behavioral decay signals** before the customer fully disappears.

## Main Project Thesis

Standard churn projects often wait for lagging indicators: long inactivity, complaints, missed payments, etc.

This project treats churn as a **gradual decay process**. It focuses on early behavioral signals such as:

- slowing order cadence
- rising inter-purchase gaps
- shrinking basket size
- weakening reorder behavior
- narrowing product/category diversity
- drifting order timing patterns

The model should not just output a risk score. It should also explain **why** the customer was flagged and suggest practical actions.

## Current Dataset Decision

We initially compared Olist and Instacart. We chose **Instacart** because Olist has too few repeat customers for trend-based churn modeling.

Important Instacart caveat:

- Instacart does **not** provide real global calendar dates.
- It provides user-relative timing through `days_since_prior_order`.
- `days_since_prior_order` is capped at 30 days.
- Therefore, do **not** claim a true calendar-time split or true 60/90/120-day churn label unless explicitly adding a separate caveated experiment.

## Current Project Structure

Important folders:

- `data/`: raw and processed local data, ignored by Git
- `src/`: reusable feature-engineering code
- `scripts/`: canonical reproducible scripts
- `notebooks/`: notebook wrappers for scripts
- `reports/`: markdown/json reports and plots
- `dashboard/`: Streamlit dashboard screens
- `models/`: trained models, ignored by Git
- `docs/`: project coordination docs

Do not delete raw/processed data unless explicitly asked.

Do not commit or upload large data/model artifacts unless specifically requested.

## GitHub / File Hygiene Rules

The project is GitHub-safe:

- `data/` is ignored except `data/README.md` and `.gitkeep`
- `models/` is ignored
- local transfer/output chunks are ignored/removed
- notebooks, scripts, reports, dashboard code, and docs are intended to be tracked

Preserve peer originals in archive folders. Do not overwrite them.

Peer archives:

- `notebooks/peer_submissions/`
- `reports/peer_submissions/`
- `dashboard/peer_submissions/`

Canonical synced files are outside those archive folders.

## Phase 1 / Data Cleaning And EDA

Cleaning/validation script:

`scripts/clean_validate_instacart.py`

EDA script:

`scripts/eda_instacart.py`

Key reports:

- `reports/data_validation/instacart_validation.md`
- `reports/eda/instacart/instacart_eda.md`

EDA confirmed Instacart is suitable because it has repeated user-level order sequences at scale.

## Phase 2 / Churn Label Definition

Canonical script:

`scripts/phase2_churn_labeling_instacart.py`

Canonical report:

`reports/phase2/instacart_phase2_label_definition.md`

Final label:

`early_decay_label = 1` when an eligible user-order snapshot is followed by:

`next_gap_days >= 2x historical_median_gap_days`

Eligibility:

- next order gap must be observed
- historical median gap must be greater than 0
- at least 3 known prior/current gaps
- censored-uncertain rows excluded

Why censored-uncertain rows are excluded:

- Instacart caps gaps at 30 days.
- If the customer’s 2x threshold is above 30 days, we cannot observe whether they truly crossed the 2x threshold.
- Those rows are excluded from supervised labeling.

Final Phase 2 counts:

- behavior snapshots: `3,346,083`
- label-eligible rows: `2,489,335`
- label-eligible users: `171,449`
- positives: `444,924`
- positive rate: `17.87%`
- censored-uncertain excluded rows: `104,579`
- censored-uncertain excluded users: `56,436`

Standard project split:

- train: `1,742,232`
- validation: `374,645`
- test: `372,458`

Important:

The standard project split is deterministic user-level hashing, not true calendar time.

## Phase 3 / Feature Engineering

Leading behavioral features:

- code: `src/features_leading.py`
- build script: `scripts/build_validate_features_instacart.py`
- report: `reports/features/instacart/instacart_leading_features_report.md`

Baseline peer features:

- code: `src/features_baseline.py`
- build script: `scripts/build_validate_baseline_features_instacart.py`
- report: `reports/features/instacart/baseline/instacart_baseline_features_report.md`

Final matrix build:

- script: `scripts/build_feature_matrix_instacart.py`
- report: `reports/features/instacart/matrix/instacart_feature_matrix_report.md`

Final feature matrix:

`data/processed/instacart/features/instacart_feature_matrix.pkl`

Feature matrix contract:

- rows: `2,489,335`
- columns: `49`
- leading predictors: `38`
- baseline predictors: `7`
- target: `early_decay_label`
- split column: `split`
- duplicate `user_id/order_id` keys: `0`
- leading/baseline predictor overlap: none
- no raw `eval_set` or raw `order_number` leakage in final matrix

Important:

Do not use old CSVs like `baseline_features.csv` as the source of truth. Use the final matrix.

## Phase 4 / Modeling

There are two Phase 4 modeling tracks.

### 1. Synced Model Comparison

Canonical script:

`scripts/phase4_modeling_instacart.py`

Notebook:

`notebooks/07_phase4_modeling_instacart.ipynb`

Report:

`reports/modeling/instacart/phase4_modeling_report.md`

This compares:

- baseline-only Logistic Regression
- baseline-only XGBoost
- leading-only Logistic Regression
- leading-only XGBoost
- combined Logistic Regression
- combined XGBoost

Uses the standard project split from `instacart_feature_matrix.pkl`.

Best validation result:

- model: combined XGBoost
- validation ROC-AUC: `0.7206`
- validation PR-AUC: `0.3599`
- validation top-5% lift: `2.71x`

Test metrics from report:

- baseline XGBoost ROC-AUC: `0.6484`
- baseline XGBoost PR-AUC: `0.2707`
- leading XGBoost ROC-AUC: `0.7215`
- leading XGBoost PR-AUC: `0.3581`
- combined XGBoost ROC-AUC: `0.7243`
- combined XGBoost PR-AUC: `0.3617`

Saved predictions:

- `data/processed/instacart/predictions/phase4_validation_predictions.csv`
- `data/processed/instacart/predictions/phase4_test_predictions.csv`

### 2. Focused Leading-XGBoost Deep Dive

Canonical script:

`scripts/phase4_leading_xgboost_instacart.py`

Notebook:

`notebooks/08_phase4_leading_xgboost_instacart.ipynb`

Report:

`reports/modeling/instacart/phase4_leading_xgboost_report.md`

This is the focused deliverable for the leading-indicator model:

- leading features only
- XGBoost only
- class imbalance handled through class weighting
- modest hyperparameter tuning only
- SHAP values computed for every test row
- timing metric computed

Important caveat:

The requested “time-based split” is implemented as a **user-level relative-time proxy split**, because Instacart has no global calendar dates.

Relative-time proxy split:

- users sorted by latest eligible `relative_day`
- earlier users train
- middle users validation
- later users test
- no user overlap across splits

Focused leading-XGBoost current metrics:

- test ROC-AUC: `0.6607`
- test PR-AUC: `0.2585`
- top 5% lift: `2.46x`
- top 10% lift: `2.13x`
- median warning lead time before label-defined decay threshold: `12.00 days`
- median warning lead time before next observed order: `18.00 days`

Focused output files:

- model: `models/phase4/leading_xgboost_time_proxy.pkl`
- predictions: `data/processed/instacart/predictions/leading_xgboost_time_proxy_test_predictions.csv`
- SHAP matrix: `data/processed/instacart/predictions/leading_xgboost_time_proxy_test_shap_values.pkl`

Focused predictions and SHAP:

- prediction rows: `1,075,413`
- SHAP rows: `1,075,413`
- duplicate keys: `0`

## Peer Work Integration

Peer submissions were preserved, but corrected/synced versions are canonical.

Phase 3 peer baseline archive:

- `notebooks/peer_submissions/baseline_features_phase3_original.ipynb`
- `reports/peer_submissions/phase3_baseline/peer_phase3_baseline_report_original.md`

Phase 4 peer baseline archive:

- `notebooks/peer_submissions/phase4_baseline_original.ipynb`
- `reports/peer_submissions/phase4_baseline/peer_phase4_baseline_report_original.md`

Phase 5 dashboard peer archive:

- `dashboard/peer_submissions/app_original.py`
- `dashboard/peer_submissions/screen2_customer_detail_original.py`
- `reports/peer_submissions/phase5_dashboard/peer_phase5_dashboard_report_original.md`

Do not treat archived peer originals as runnable source of truth. They are preserved for traceability.

## Phase 5 / Dashboard

Current dashboard is Streamlit.

Main app:

`dashboard/app.py`

Standalone screens:

- `dashboard/screen1_risk_table.py`
- `dashboard/screen2_customer_detail.py`
- `dashboard/screen3_comparison.py`

Dashboard README:

`dashboard/README.md`

Run combined app:

```bash
streamlit run dashboard/app.py
```

Run standalone screens:

```bash
streamlit run dashboard/screen1_risk_table.py
streamlit run dashboard/screen2_customer_detail.py
streamlit run dashboard/screen3_comparison.py
```

### Screen 1 / Risk Table

Purpose:

- landing page
- one row per customer
- uses latest scored test snapshot per customer
- shows customer ID, risk score, risk tier, top SHAP driver
- sortable/filterable through Streamlit UI

Inputs:

- `leading_xgboost_time_proxy_test_predictions.csv`
- `leading_xgboost_time_proxy_test_shap_values.pkl`

Current validation:

- customer rows: `25,718`
- High risk: `315`
- Medium risk: `3,933`
- Low risk: `21,470`

Important:

Screen 1 should use the **leading XGBoost operational model only**. Baseline is for benchmark/comparison, not operational risk scoring.

### Screen 2 / Customer Detail

Purpose:

- customer drilldown
- risk score/tier
- risk trend over customer timeline
- purchase gap history
- top SHAP drivers
- rule-based recommended actions

Inputs:

- `leading_xgboost_time_proxy_test_predictions.csv`
- `leading_xgboost_time_proxy_test_shap_values.pkl`
- `data/processed/instacart/orders_clean.csv`

Screen 2 was adapted from peer work but fixed to use current artifacts.

### Screen 3 / Model Comparison

Purpose:

- compare baseline vs leading model
- ROC curves
- precision-recall curves
- timing comparison chart

Inputs:

- `phase4_validation_predictions.csv`
- `phase4_test_predictions.csv`
- `instacart_phase2_decay_labels.csv`

Default comparison:

- baseline XGBoost
- leading XGBoost

Screen 3 validation:

- validation rows: `374,645`
- test rows: `372,458`
- baseline XGBoost ROC-AUC: `0.6484`
- baseline XGBoost PR-AUC: `0.2707`
- leading XGBoost ROC-AUC: `0.7215`
- leading XGBoost PR-AUC: `0.3581`

## Dynamic Insights Rule

Do not use any AI API to generate dashboard insights.

Insights should be dynamic but rule-based:

- use model scores
- use risk tier
- use SHAP top drivers
- use feature names
- use metric comparisons
- map those into deterministic business messages

Example:

If top driver is `current_gap_ratio_to_historical_median`, message should say the customer’s purchase cadence slowed vs normal rhythm and suggest a reorder reminder or time-sensitive incentive.

If top driver is `reorder_ratio_recent3_delta_from_prior`, message should say repeat-item habit is weakening and suggest replenishment prompts or frequently reordered product reminders.

This is better than LLM-generated text because it is reproducible, explainable, and interview-defensible.

## Important Rules For Continuing

1. Use `instacart_feature_matrix.pkl` as the master modeling file.
2. Do not resurrect old peer baseline CSV paths.
3. Do not use `user_id` as a model feature.
4. Do not use label/leakage columns as model features:
   - `next_order_id`
   - `next_order_number`
   - `next_eval_set`
   - `next_gap_days`
   - `next_gap_ratio_to_historical_median`
   - `label_eligible`
   - `label_status`
   - `decay_severity_score`
   - `decay_severity_tier`
5. Do not claim true calendar dates/time split for Instacart.
6. If discussing time split, state it is a user-level relative-time proxy.
7. Operational risk score should be leading XGBoost.
8. Baseline model should be used as benchmark/comparison.
9. Peer originals stay archived; canonical files are the synced project files.
10. Keep large artifacts out of Git.

## Current Dependencies

`requirements.txt` includes:

- pandas
- numpy
- matplotlib
- scikit-learn
- joblib
- xgboost
- shap
- streamlit

Install:

```bash
pip install -r requirements.txt
```

## Validation Summary

Project validation report:

`reports/project_validation_summary.md`

Key validation:

- scripts parse
- notebooks parse
- feature matrix contract valid
- prediction and SHAP row counts align
- no duplicate prediction/SHAP keys
- peer files archived
- dashboard compatibility checked

## What Is Left

Core modeling and dashboard implementation are mostly done.

Remaining work is mainly polish and final delivery:

### 1. Polish dashboard UX

Improve layout, labels, and readability:

- add executive summary cards on Screen 1 and Screen 3
- add risk-tier explanation
- add clearer intervention/action copy
- improve table formatting
- add download buttons for filtered customer table
- make Screen 2 customer selector searchable and default to high-risk customers

### 2. Add SHAP summary visuals

Use saved SHAP matrix to create:

- global feature importance chart
- top positive risk drivers
- maybe top negative/protective drivers

Save plots under:

`reports/modeling/instacart/plots/`

Potential dashboard addition:

- show global SHAP importance on Screen 2 or Screen 3

### 3. Final written report

Create a polished end-to-end project report:

- problem statement
- dataset selection reasoning
- churn label definition
- feature engineering
- model comparison
- dashboard explanation
- SHAP explainability
- business recommendations
- limitations
- future work

Suggested location:

`reports/final_project_report.md`

### 4. Final presentation

Create a concise slide deck or PDF:

- 8-12 slides
- focus on thesis, label, leading features, model comparison, dashboard, actions

### 5. GitHub preparation

Before GitHub:

- ensure `data/` and `models/` are ignored
- include README with run instructions
- include screenshots of dashboard if possible
- include final report
- do not upload raw Instacart data or large `.pkl` outputs unless using external storage instructions

### 6. Optional deployment

Streamlit app can be run locally.

Full deployment may be hard because data/model artifacts are large and ignored by Git. If deploying, create smaller sample artifacts or a demo mode.

## Suggested Next Step

Start by running:

```bash
streamlit run dashboard/app.py
```

Then inspect all three screens manually.

Next, add dynamic executive insight cards:

- Screen 1: portfolio-level high-risk count, dominant risk drivers, recommended intervention focus
- Screen 2: customer-specific risk explanation and action
- Screen 3: leading vs baseline performance interpretation

Do this without changing the modeling logic.

After dashboard polish, create `reports/final_project_report.md`.
