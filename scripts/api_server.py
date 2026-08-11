from __future__ import annotations

import hmac
import json
import logging
import math
import os
import sqlite3
from contextlib import closing
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parents[1]
SERVING_DIR = ROOT / "data" / "serving"
PORTFOLIO_DB = SERVING_DIR / "portfolio.sqlite"
DETAIL_DB = SERVING_DIR / "customer_detail.sqlite"
METRICS_PATH = SERVING_DIR / "model_metrics.json"
MAX_PAGE_SIZE = 100
DEFAULT_ALLOWED_ORIGINS = "http://127.0.0.1:5173,http://localhost:5173"
REQUIRED_METRIC_KEYS = {
    "modelName", "rocAuc", "prAuc", "evaluationThreshold",
    "precisionAtEvaluationThreshold", "recallAtEvaluationThreshold",
    "medianLeadTimeDays", "correctlyFlaggedUsers", "positiveEventUsers", "methodology",
}
LOGGER = logging.getLogger("early_churn.api")


class ServingStore:
    """Small, read-only access layer for precomputed serving artifacts."""

    def __init__(self) -> None:
        missing = [str(path) for path in (PORTFOLIO_DB, DETAIL_DB, METRICS_PATH) if not path.exists()]
        if missing:
            raise FileNotFoundError("Serving cache missing. Run: python scripts/build_serving_cache.py\n" + "\n".join(missing))
        self.metrics = json.loads(METRICS_PATH.read_text(encoding="utf-8"))
        self._validate()

    def _validate(self) -> None:
        missing_metrics = REQUIRED_METRIC_KEYS.difference(self.metrics)
        if missing_metrics:
            raise ValueError(f"Model metrics missing required fields: {', '.join(sorted(missing_metrics))}")
        with closing(self._connection(PORTFOLIO_DB)) as portfolio_db, closing(self._connection(DETAIL_DB)) as detail_db:
            portfolio_count = portfolio_db.execute("SELECT COUNT(*) FROM portfolio").fetchone()[0]
            detail_count = detail_db.execute("SELECT COUNT(*) FROM customer_detail").fetchone()[0]
        if portfolio_count <= 0 or portfolio_count != detail_count:
            raise ValueError(f"Serving cache row counts are invalid: portfolio={portfolio_count}, detail={detail_count}")

    @staticmethod
    def _connection(path: Path) -> sqlite3.Connection:
        connection = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
        connection.row_factory = sqlite3.Row
        return connection

    def summary(self) -> dict:
        with closing(self._connection(PORTFOLIO_DB)) as db:
            counts = {row["risk_band"]: row["count"] for row in db.execute("SELECT risk_band, COUNT(*) AS count FROM portfolio GROUP BY risk_band")}
            driver_row = db.execute("SELECT top_driver FROM portfolio WHERE risk_band IN ('High', 'Medium') GROUP BY top_driver ORDER BY COUNT(*) DESC, top_driver LIMIT 1").fetchone()
        total, high, medium, low = sum(counts.values()), counts.get("High", 0), counts.get("Medium", 0), counts.get("Low", 0)
        return {"highRiskCount": high, "mediumRiskCount": medium, "lowRiskCount": low, "totalCustomers": total, "elevatedRiskPercentage": round((high + medium) / total * 100, 2) if total else 0.0, "primaryBehavioralSignal": driver_row["top_driver"] if driver_row else "No behavioral signal available", "portfolioInsightHeadline": f"{(high + medium) / total:.2%} of scored customers are in the High or Medium Risk Bands for operational risk segmentation." if total else "No scored customers are available."}

    def customers(self, tier: str, search: str, page: int, page_size: int) -> dict:
        filters, values = [], []
        if tier not in {"All", "All Tiers"}:
            if tier not in {"High", "Medium", "Low"}:
                raise ValueError("tier must be All, High, Medium, or Low")
            filters.append("risk_band = ?")
            values.append(tier)
        if search:
            filters.append("CAST(customer_id AS TEXT) LIKE ?")
            values.append(f"%{search}%")
        where = f" WHERE {' AND '.join(filters)}" if filters else ""
        with closing(self._connection(PORTFOLIO_DB)) as db:
            total = db.execute(f"SELECT COUNT(*) FROM portfolio{where}", values).fetchone()[0]
            total_pages = max(1, math.ceil(total / page_size))
            if page > total_pages:
                raise ValueError(f"page must not exceed {total_pages}")
            rows = db.execute(f"SELECT customer_id, score, risk_band, top_driver, last_purchase_days, historic_avg_gap, order_volume FROM portfolio{where} ORDER BY score DESC, customer_id LIMIT ? OFFSET ?", [*values, page_size, (page - 1) * page_size]).fetchall()
        return {"customers": [{"id": str(row["customer_id"]), "riskScore": row["score"], "riskTier": row["risk_band"], "lastPurchaseDays": row["last_purchase_days"], "historicAvgGap": row["historic_avg_gap"], "orderVolume": row["order_volume"], "primaryRiskDriver": {"feature": row["top_driver"]}} for row in rows], "total": total, "page": page, "pageSize": page_size, "totalPages": total_pages}

    def customer(self, customer_id: int) -> dict | None:
        with closing(self._connection(DETAIL_DB)) as db:
            row = db.execute("SELECT payload_json FROM customer_detail WHERE customer_id = ?", (customer_id,)).fetchone()
        return json.loads(row["payload_json"]) if row else None


STORE: ServingStore | None = None
STARTUP_ERROR: Exception | None = None


def initialize() -> None:
    global STORE, STARTUP_ERROR
    try:
        STORE = ServingStore()
        STARTUP_ERROR = None
    except Exception as exc:
        STORE, STARTUP_ERROR = None, exc


def _positive_int(raw: str, name: str, minimum: int, maximum: int) -> int:
    try:
        value = int(raw)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer") from exc
    if not minimum <= value <= maximum:
        raise ValueError(f"{name} must be between {minimum} and {maximum}")
    return value


class BackendApiHandler(BaseHTTPRequestHandler):
    server_version = "EarlyChurnAPI"
    sys_version = ""

    def log_message(self, fmt: str, *args: object) -> None:
        LOGGER.info("%s - %s", self.address_string(), fmt % args)

    @staticmethod
    def _allowed_origins() -> set[str]:
        return {item.strip() for item in os.getenv("ALLOWED_ORIGINS", DEFAULT_ALLOWED_ORIGINS).split(",") if item.strip()}

    def _send_cors_headers(self) -> None:
        origin = self.headers.get("Origin")
        if origin and origin in self._allowed_origins():
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Vary", "Origin")

    def _send_json(self, data: dict, status: int = 200) -> None:
        body = json.dumps(data, separators=(",", ":")).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self._send_cors_headers()
        self.end_headers()
        self.wfile.write(body)

    def _authorized(self) -> bool:
        token = os.getenv("API_AUTH_TOKEN")
        authorization = self.headers.get("Authorization", "")
        return not token or hmac.compare_digest(authorization, f"Bearer {token}")

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Authorization, Content-Type")
        self.send_header("Access-Control-Max-Age", "600")
        self.send_header("Content-Length", "0")
        self._send_cors_headers()
        self.end_headers()

    def do_GET(self) -> None:
        if not self._authorized():
            self._send_json({"error": "Unauthorized"}, 401)
            return
        try:
            self._dispatch()
        except ValueError as exc:
            self._send_json({"error": str(exc)}, 400)
        except Exception:
            LOGGER.exception("Unhandled API error")
            self._send_json({"error": "Internal server error"}, 500)

    def _dispatch(self) -> None:
        path, params = urlparse(self.path).path, parse_qs(urlparse(self.path).query)
        if path == "/api/health":
            self._send_json({"status": "ready" if STORE else "unavailable"}, 200 if STORE else 503)
            return
        if STORE is None:
            self._send_json({"error": "Serving cache unavailable; inspect server logs."}, 503)
            return
        if path == "/api/portfolio-summary":
            self._send_json(STORE.summary())
        elif path == "/api/model-metrics":
            self._send_json(STORE.metrics)
        elif path == "/api/customers":
            page = _positive_int(params.get("page", ["1"])[0], "page", 1, 100_000)
            page_size = _positive_int(params.get("pageSize", ["20"])[0], "pageSize", 1, MAX_PAGE_SIZE)
            self._send_json(STORE.customers(params.get("tier", ["All"])[0], params.get("search", [""])[0].strip(), page, page_size))
        elif path.startswith("/api/customers/"):
            try:
                customer_id = int(path.removeprefix("/api/customers/").removeprefix("CUST-").strip())
            except ValueError as exc:
                raise ValueError("Invalid customer ID") from exc
            payload = STORE.customer(customer_id)
            self._send_json(payload if payload else {"error": "Customer not found"}, 200 if payload else 404)
        else:
            self._send_json({"error": "Endpoint not found"}, 404)


class BackendServer(ThreadingHTTPServer):
    daemon_threads = True
    request_queue_size = 128


def run_server(port: int | None = None, host: str | None = None) -> None:
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO").upper(), format="%(asctime)s %(levelname)s %(name)s %(message)s")
    initialize()
    listen_port = port if port is not None else int(os.getenv("API_PORT", "5001"))
    listen_host = host if host is not None else os.getenv("API_HOST", "127.0.0.1")
    if STORE is None:
        raise RuntimeError("Serving cache initialization failed") from STARTUP_ERROR
    server = BackendServer((listen_host, listen_port), BackendApiHandler)
    LOGGER.info("Python Backend API Server listening on http://%s:%s", listen_host, listen_port)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    run_server()
