# Instacart Phase 4 Modeling Report

## Scope

Synced Phase 4 modeling against the corrected final feature matrix. This fixes the peer Phase 4 mismatch where an older baseline CSV was merged with labels and produced extra validation rows.

## Modeling Input

- Final matrix rows: 2,489,335
- Baseline predictors: 7
- Leading predictors: 38
- Combined predictors: 45

## Split Summary

| Split | Rows | Positives | Positive Rate |
|---|---:|---:|---:|
| test | 372,458 | 66,538 | 17.86% |
| train | 1,742,232 | 311,148 | 17.86% |
| validation | 374,645 | 67,238 | 17.95% |

## Validation Metrics

| Feature Set | Model | ROC-AUC | PR-AUC | Top 5% Lift | Top 10% Lift | Precision @ 0.5 | Recall @ 0.5 |
|---|---|---:|---:|---:|---:|---:|---:|
| baseline | logistic_regression | 0.6071 | 0.2467 | 1.79x | 1.61x | 22.61% | 55.17% |
| baseline | xgboost | 0.6441 | 0.2692 | 1.91x | 1.75x | 23.41% | 69.36% |
| leading | logistic_regression | 0.6915 | 0.3264 | 2.47x | 2.20x | 27.59% | 62.50% |
| leading | xgboost | 0.7180 | 0.3556 | 2.69x | 2.36x | 28.32% | 68.06% |
| combined | logistic_regression | 0.6988 | 0.3327 | 2.50x | 2.24x | 28.06% | 63.83% |
| combined | xgboost | 0.7206 | 0.3599 | 2.71x | 2.39x | 28.41% | 68.36% |

## Test Metrics

| Feature Set | Model | ROC-AUC | PR-AUC | Top 5% Lift | Top 10% Lift | Precision @ 0.5 | Recall @ 0.5 |
|---|---|---:|---:|---:|---:|---:|---:|
| baseline | logistic_regression | 0.6101 | 0.2466 | 1.79x | 1.60x | 22.81% | 55.25% |
| baseline | xgboost | 0.6484 | 0.2707 | 1.94x | 1.74x | 23.57% | 69.35% |
| leading | logistic_regression | 0.6947 | 0.3290 | 2.52x | 2.21x | 27.84% | 62.41% |
| leading | xgboost | 0.7215 | 0.3581 | 2.71x | 2.39x | 28.44% | 67.96% |
| combined | logistic_regression | 0.7024 | 0.3364 | 2.55x | 2.27x | 28.26% | 63.66% |
| combined | xgboost | 0.7243 | 0.3617 | 2.74x | 2.40x | 28.57% | 68.27% |

## Best Validation Result

- Best by PR-AUC: `combined` + `xgboost`
- Validation PR-AUC: 0.3599
- Validation top-5% lift: 2.71x

## Practical Read

- Use PR-AUC and top-decile lift as the main comparison metrics because this is an intervention-ranking problem, not a pure 0.5-threshold classifier.
- The baseline-only model is the traditional comparison point.
- The leading-only model tests the project thesis directly.
- The combined model tests whether behavioral decay features add value beyond baseline customer history.
- Logistic Regression is saved as a full preprocessing pipeline, so the scaler/imputer are included with the model.

## Outputs

- feature_matrix: `C:\Users\Siddharth\Documents\Early Churn Predictior\data\processed\instacart\features\instacart_feature_matrix.pkl`
- validation_predictions: `C:\Users\Siddharth\Documents\Early Churn Predictior\data\processed\instacart\predictions\phase4_validation_predictions.csv`
- test_predictions: `C:\Users\Siddharth\Documents\Early Churn Predictior\data\processed\instacart\predictions\phase4_test_predictions.csv`
- models_dir: `C:\Users\Siddharth\Documents\Early Churn Predictior\models\phase4`
- report_json: `C:\Users\Siddharth\Documents\Early Churn Predictior\reports\modeling\instacart\phase4_modeling_report.json`
- report_md: `C:\Users\Siddharth\Documents\Early Churn Predictior\reports\modeling\instacart\phase4_modeling_report.md`
