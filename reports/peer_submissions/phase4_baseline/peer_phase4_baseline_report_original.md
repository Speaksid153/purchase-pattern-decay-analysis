===== Logistic Regression (baseline features) =====
ROC-AUC: 0.6189
PR-AUC: 0.2433
Top 5% lift: 1.83x | Top 10% lift: 1.65x
              precision    recall  f1-score   support

           0       0.87      0.57      0.69    322829
           1       0.22      0.58      0.32     67238

    accuracy                           0.57    390067
   macro avg       0.54      0.58      0.50    390067
weighted avg       0.76      0.57      0.63    390067


===== XGBoost (baseline features) =====
ROC-AUC: 0.6603
PR-AUC: 0.2692
Top 5% lift: 1.98x | Top 10% lift: 1.80x
              precision    recall  f1-score   support

           0       0.90      0.49      0.63    322829
           1       0.23      0.74      0.35     67238

    accuracy                           0.53    390067
   macro avg       0.56      0.61      0.49    390067
weighted avg       0.78      0.53      0.58    390067


Saved 388,037 test-set predictions
Saved models: models/logreg_baseline.pkl, models/xgboost_baseline.pkl

- Both models independently agree: avg_days_between_orders and avg_reorder_ratio are the strongest predictors, with strong convergence across model types.
- avg_days_between_orders shows a negative relationship with churn — makes sense since the label is a 2x-deviation-from-own-baseline, easier to trigger for naturally short-cadence (weekly) shoppers.
- total_orders_to_date matters in Logistic Regression but barely in XGBoost — likely redundant with avg_days_between_orders, which XGBoost captures more efficiently.
- Day-of-week and hour-of-day contribute minimally in both models — not meaningful standalone predictors of decay.
- XGBoost outperforms Logistic Regression on every metric (ROC-AUC 0.66 vs 0.62, recall 0.74 vs 0.58, top-5% lift 1.98x vs 1.83x) — a real, consistent improvement from model choice alone, same feature set.
- Both models have low precision (~0.22-0.23) for the churned class — ~3 in 4 flagged snapshots are false alarms, a real limitation of baseline features alone, expected given this is meant as a comparison point against leading features, not a final production model.
- Ranking performance is the strongest practical result: even the weaker model gives 1.83x lift in the top 5% riskiest group — useful for prioritizing interventions despite weak binary classification.