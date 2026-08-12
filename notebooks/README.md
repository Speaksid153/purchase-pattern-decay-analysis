# Notebooks

These are the canonical, self-contained analytical workflows for the project:

| Stage | Notebook | Published state |
|---:|---|---|
| 1 | [`01_clean_validate_instacart.ipynb`](01_clean_validate_instacart.ipynb) | Fully executed |
| 2 | [`02_eda_instacart.ipynb`](02_eda_instacart.ipynb) | Fully executed with plots |
| 3 | [`03_phase2_churn_labeling_instacart.ipynb`](03_phase2_churn_labeling_instacart.ipynb) | Fully executed |
| 4 | [`04_build_validate_leading_features_instacart.ipynb`](04_build_validate_leading_features_instacart.ipynb) | Fully executed with plots |
| 5 | [`05_build_validate_baseline_features_instacart.ipynb`](05_build_validate_baseline_features_instacart.ipynb) | Fully executed |
| 6 | [`06_build_feature_matrix_instacart.ipynb`](06_build_feature_matrix_instacart.ipynb) | Fully executed |
| 7 | [`07_phase4_modeling_instacart.ipynb`](07_phase4_modeling_instacart.ipynb) | Fully executed |
| 8 | [`08_phase4_leading_xgboost_instacart.ipynb`](08_phase4_leading_xgboost_instacart.ipynb) | Fully executed with SHAP evidence |
| 9 | [`09_temporal_robustness_experiments.ipynb`](09_temporal_robustness_experiments.ipynb) | Fully executed rolling-fold model selection and untouched-test evaluation |

Each notebook is structured into configuration, reusable helpers, pipeline definition, execution, and rendered evidence. All code cells were executed against the full local Instacart dataset before publication, and the retained outputs contain no execution errors.

Run them in numeric order from the project root or from this folder. Place the raw Kaggle CSVs under `data/instacart/`; later notebooks consume artifacts produced by earlier stages. The Python files retained elsewhere in the repository are runtime, deployment, reusable library, or test code required by the public application—not duplicate analytical entry points.
