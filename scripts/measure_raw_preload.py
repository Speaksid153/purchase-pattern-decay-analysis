"""One-time benchmark of the retired raw-pandas preload path; not used by the API."""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import psutil

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dashboard.screen1_risk_table import HIGH_RISK_THRESHOLD, MEDIUM_RISK_THRESHOLD, load_customer_risk_table, set_api_preloaded_frames
from dashboard.screen2_customer_detail import load_api_data

started = time.perf_counter()
predictions, shap, orders = load_api_data()
set_api_preloaded_frames(predictions, shap)
risk_table = load_customer_risk_table(HIGH_RISK_THRESHOLD, MEDIUM_RISK_THRESHOLD)
memory = psutil.Process().memory_info()
report = {"startup_seconds": round(time.perf_counter() - started, 3), "rss_bytes": memory.rss, "peak_rss_bytes": int(getattr(memory, "peak_wset", memory.rss)), "customers": len(risk_table)}
(ROOT / "data/serving/benchmark_raw_preload.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
print(json.dumps(report))
