from __future__ import annotations

import json
import sqlite3
import sys
import time
from pathlib import Path

import psutil

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.serving_cache_common import model_metrics_payload, raw_customer_records

SERVING_DIR = ROOT / "data" / "serving"


def build() -> dict:
    started = time.perf_counter()
    SERVING_DIR.mkdir(parents=True, exist_ok=True)
    portfolio, details = raw_customer_records()
    portfolio_path, detail_path = SERVING_DIR / "portfolio.sqlite", SERVING_DIR / "customer_detail.sqlite"
    for path in (portfolio_path, detail_path):
        if path.exists():
            path.unlink()
    with sqlite3.connect(portfolio_path) as db:
        db.execute("CREATE TABLE portfolio (customer_id INTEGER PRIMARY KEY, score REAL NOT NULL, risk_band TEXT NOT NULL, top_driver TEXT NOT NULL, latest_order_id INTEGER NOT NULL, relative_day INTEGER NOT NULL, last_purchase_days REAL NOT NULL, historic_avg_gap REAL NOT NULL, order_volume INTEGER NOT NULL)")
        db.executemany("INSERT INTO portfolio VALUES (:customer_id,:score,:risk_band,:top_driver,:latest_order_id,:relative_day,:last_purchase_days,:historic_avg_gap,:order_volume)", portfolio)
        db.execute("CREATE INDEX portfolio_band_score ON portfolio(risk_band, score DESC, customer_id)")
        db.execute("CREATE INDEX portfolio_score ON portfolio(score DESC, customer_id)")
    with sqlite3.connect(detail_path) as db:
        db.execute("CREATE TABLE customer_detail (customer_id INTEGER PRIMARY KEY, payload_json TEXT NOT NULL)")
        db.executemany("INSERT INTO customer_detail VALUES (?, ?)", ((customer_id, json.dumps(payload, separators=(",", ":"), ensure_ascii=False)) for customer_id, payload in details.items()))
    metrics_path = SERVING_DIR / "model_metrics.json"
    metrics_path.write_text(json.dumps(model_metrics_payload(), indent=2) + "\n", encoding="utf-8")
    memory = psutil.Process().memory_info()
    report = {"customers": len(portfolio), "build_seconds": round(time.perf_counter() - started, 3), "raw_build_peak_rss_bytes": int(getattr(memory, "peak_wset", memory.rss)), "portfolio_bytes": portfolio_path.stat().st_size, "detail_bytes": detail_path.stat().st_size, "metrics_bytes": metrics_path.stat().st_size}
    (SERVING_DIR / "cache_build_report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


if __name__ == "__main__":
    print(json.dumps(build(), indent=2))
