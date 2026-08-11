# SHAP Summary

Generated from 1,075,413 test-set SHAP rows across 38 leading features.

## Top 5 Most Important Features (by mean |SHAP|)

| Rank | Feature | Mean |SHAP| |
|---:|---|---:|
| 1 | Historical Median Gap Days Feature | 0.4628 |
| 2 | Current gap vs historical median | 0.3378 |
| 3 | Orders to date | 0.1940 |
| 4 | Reorder Ratio Prior To Current Avg | 0.1569 |
| 5 | Previous Gap Days | 0.1194 |

## Top 5 Risk-Increasing Features (by mean SHAP)

| Rank | Feature | Mean SHAP |
|---:|---|---:|
| 1 | Frequency trend (last 3) | +0.0089 |
| 2 | Distinct Department Count Prior To Current Avg | +0.0085 |
| 3 | Basket size ratio (recent 3) | +0.0039 |
| 4 | Reorder Ratio Recent3 Ratio To Prior | +0.0029 |
| 5 | Gap acceleration warning | +0.0016 |

## Top 5 Risk-Reducing Features (by mean SHAP)

| Rank | Feature | Mean SHAP |
|---:|---|---:|
| 1 | Orders to date | -0.1698 |
| 2 | Reorder Ratio Prior To Current Avg | -0.1293 |
| 3 | Current gap vs historical median | -0.1120 |
| 4 | Previous Gap Days | -0.0365 |
| 5 | Historical Median Gap Days Feature | -0.0268 |

## Plots

- Global importance: `shap_global_importance.png`
- Positive drivers: `shap_positive_drivers.png`
- Protective drivers: `shap_protective_drivers.png`