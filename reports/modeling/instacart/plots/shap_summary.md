# SHAP Summary

Generated from 1,075,413 test-set SHAP rows across 38 leading features.

## Top 5 Most Important Features (by mean |SHAP|)

| Rank | Feature | Mean |SHAP| |
|---:|---|---:|
| 1 | Historical Median Gap Days Feature | 0.4311 |
| 2 | Purchase gap is significantly above historical normal cadence | 0.3360 |
| 3 | Reorder Ratio Prior To Current Avg | 0.1530 |
| 4 | Total order sequence depth to date | 0.1373 |
| 5 | Previous Gap Days | 0.1089 |

## Top 5 Risk-Increasing Features (by mean SHAP)

| Rank | Feature | Mean SHAP |
|---:|---|---:|
| 1 | Order frequency is declining over recent orders | +0.0072 |
| 2 | Purchase gap accelerated vs the previous gap | +0.0041 |
| 3 | Distinct Department Count Prior To Current Avg | +0.0029 |
| 4 | Basket size is shrinking relative to prior baseline | +0.0017 |
| 5 | Reorder Ratio Recent3 Ratio To Prior | +0.0011 |

## Top 5 Risk-Reducing Features (by mean SHAP)

| Rank | Feature | Mean SHAP |
|---:|---|---:|
| 1 | Reorder Ratio Prior To Current Avg | -0.1084 |
| 2 | Total order sequence depth to date | -0.1059 |
| 3 | Purchase gap is significantly above historical normal cadence | -0.1015 |
| 4 | Historical Median Gap Days Feature | -0.0565 |
| 5 | Previous Gap Days | -0.0380 |

## Plots

- Global importance: `shap_global_importance.png`
- Positive drivers: `shap_positive_drivers.png`
- Protective drivers: `shap_protective_drivers.png`
