from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.serving_cache_common import model_metrics_payload, raw_customer_records

SERVING_DIR = ROOT / "data" / "serving"


def verify() -> dict:
    raw_portfolio, raw_details = raw_customer_records()
    with sqlite3.connect(SERVING_DIR / "portfolio.sqlite") as db:
        db.row_factory = sqlite3.Row
        cached_portfolio = [dict(row) for row in db.execute("SELECT * FROM portfolio ORDER BY score DESC, customer_id")]
        filtered = {
            band: [row[0] for row in db.execute("SELECT customer_id FROM portfolio WHERE risk_band = ? ORDER BY score DESC, customer_id", (band,))]
            for band in ("High", "Medium", "Low")
        }
    portfolio_comparable = [{k: row[k] for k in ("customer_id", "score", "risk_band", "top_driver", "latest_order_id", "relative_day", "last_purchase_days", "historic_avg_gap", "order_volume")} for row in raw_portfolio]
    score_mismatches = sum(a["score"] != b["score"] for a, b in zip(portfolio_comparable, cached_portfolio, strict=True))
    band_mismatches = sum(a["risk_band"] != b["risk_band"] for a, b in zip(portfolio_comparable, cached_portfolio, strict=True))
    filter_mismatches = sum(
        [row["customer_id"] for row in raw_portfolio if row["risk_band"] == band] != filtered[band]
        for band in filtered
    )
    with sqlite3.connect(SERVING_DIR / "customer_detail.sqlite") as db:
        cached_details = {customer_id: json.loads(db.execute("SELECT payload_json FROM customer_detail WHERE customer_id = ?", (customer_id,)).fetchone()[0]) for customer_id in (25369, 63581)}
        total_cached = db.execute("SELECT COUNT(*) FROM customer_detail").fetchone()[0]
    detail_mismatches = sum(raw_details[cid] != cached_details[cid] for cid in cached_details)
    cached_metrics = json.loads((SERVING_DIR / "model_metrics.json").read_text(encoding="utf-8"))
    result = {
        "customers_checked": len(raw_portfolio), "cached_customers": total_cached,
        "score_mismatches": score_mismatches, "risk_band_mismatches": band_mismatches,
        "filter_mismatches": filter_mismatches, "detail_mismatches": detail_mismatches,
        "metrics_mismatch": cached_metrics != model_metrics_payload(),
    }
    (SERVING_DIR / "cache_exactness_report.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    if result != {**result, "customers_checked": 25718, "cached_customers": 25718, "score_mismatches": 0, "risk_band_mismatches": 0, "filter_mismatches": 0, "detail_mismatches": 0, "metrics_mismatch": False}:
        raise AssertionError(json.dumps(result))
    return result


if __name__ == "__main__":
    print(json.dumps(verify(), indent=2))
