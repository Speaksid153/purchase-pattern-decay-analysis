# Peer Phase 4 Baseline Submission

This folder archives the peer's original Phase 4 baseline-model report.

## Original Issue

The peer notebook modeled from an older `baseline_features.csv` and merged labels separately. That produced a validation set of 390,067 rows, while the corrected master feature matrix has 374,645 validation rows.

The positive count was the same, but the extra negative rows changed the class balance and distorted metrics.

## Synced Resolution

The synced Phase 4 workflow uses:

`data/processed/instacart/features/instacart_feature_matrix.pkl`

Canonical synced files:

- `scripts/phase4_modeling_instacart.py`
- `notebooks/07_phase4_modeling_instacart.ipynb`
- `reports/modeling/instacart/phase4_modeling_report.md`
- `reports/modeling/instacart/phase4_peer_sync_fix.md`

The peer report remains here only as an audit trail.
