import json
import os
import sqlite3
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from contextlib import closing
from http.server import ThreadingHTTPServer
from pathlib import Path

from scripts import api_server


CUSTOMERS = [
    (25369, 0.8721, "High", "purchase gap", 101, 40, 14.0, 4.6, 76),
    (156184, 0.8500, "High", "purchase gap", 102, 35, 25.0, 7.4, 48),
    (63581, 0.6994, "Medium", "reorder change", 103, 31, 10.0, 6.5, 51),
    (1, 0.2000, "Low", "stable cadence", 104, 25, 5.0, 5.1, 12),
]

METRICS = {
    "modelName": "Leading XGBoost (test fixture)",
    "rocAuc": 0.6607,
    "prAuc": 0.2585,
    "evaluationThreshold": 0.5843,
    "precisionAtEvaluationThreshold": 0.3553,
    "recallAtEvaluationThreshold": 0.1268,
    "medianLeadTimeDays": 12.0,
    "correctlyFlaggedUsers": 5203,
    "positiveEventUsers": 23892,
    "methodology": "Synthetic API contract fixture.",
}


def build_serving_fixture(directory: Path) -> tuple[Path, Path, Path]:
    portfolio_path = directory / "portfolio.sqlite"
    detail_path = directory / "customer_detail.sqlite"
    metrics_path = directory / "model_metrics.json"
    with closing(sqlite3.connect(portfolio_path)) as db:
        db.execute("CREATE TABLE portfolio (customer_id INTEGER PRIMARY KEY, score REAL NOT NULL, risk_band TEXT NOT NULL, top_driver TEXT NOT NULL, latest_order_id INTEGER NOT NULL, relative_day INTEGER NOT NULL, last_purchase_days REAL NOT NULL, historic_avg_gap REAL NOT NULL, order_volume INTEGER NOT NULL)")
        db.executemany("INSERT INTO portfolio VALUES (?,?,?,?,?,?,?,?,?)", CUSTOMERS)
        db.commit()
    with closing(sqlite3.connect(detail_path)) as db:
        db.execute("CREATE TABLE customer_detail (customer_id INTEGER PRIMARY KEY, payload_json TEXT NOT NULL)")
        db.executemany(
            "INSERT INTO customer_detail VALUES (?, ?)",
            ((row[0], json.dumps({"id": str(row[0]), "riskScore": row[1], "riskTier": row[2]})) for row in CUSTOMERS),
        )
        db.commit()
    metrics_path.write_text(json.dumps(METRICS), encoding="utf-8")
    return portfolio_path, detail_path, metrics_path


class ApiContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_directory = tempfile.TemporaryDirectory()
        fixture_paths = build_serving_fixture(Path(cls.temp_directory.name))
        cls.original_paths = (api_server.PORTFOLIO_DB, api_server.DETAIL_DB, api_server.METRICS_PATH)
        api_server.PORTFOLIO_DB, api_server.DETAIL_DB, api_server.METRICS_PATH = fixture_paths
        api_server.initialize()
        assert api_server.STORE is not None, api_server.STARTUP_ERROR
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), api_server.BackendApiHandler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base_url = f"http://127.0.0.1:{cls.server.server_port}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=5)
        api_server.PORTFOLIO_DB, api_server.DETAIL_DB, api_server.METRICS_PATH = cls.original_paths
        api_server.initialize()
        cls.temp_directory.cleanup()

    def tearDown(self):
        os.environ.pop("API_AUTH_TOKEN", None)
        os.environ.pop("ALLOWED_ORIGINS", None)

    def get_json(self, path: str, headers: dict[str, str] | None = None):
        request = urllib.request.Request(self.base_url + path, headers=headers or {})
        with urllib.request.urlopen(request) as response:
            return json.load(response)

    def assert_http_error(self, path: str, status: int):
        with self.assertRaises(urllib.error.HTTPError) as result:
            urllib.request.urlopen(self.base_url + path)
        self.assertEqual(result.exception.code, status)
        result.exception.close()

    def test_health_summary_and_metrics(self):
        self.assertEqual(self.get_json("/api/health")["status"], "ready")
        summary = self.get_json("/api/portfolio-summary")
        self.assertEqual(
            (summary["totalCustomers"], summary["highRiskCount"], summary["mediumRiskCount"], summary["lowRiskCount"]),
            (4, 2, 1, 1),
        )
        metrics = self.get_json("/api/model-metrics")
        self.assertEqual((metrics["rocAuc"], metrics["prAuc"]), (0.6607, 0.2585))

    def test_pagination_filtering_and_search(self):
        first_page = self.get_json("/api/customers?page=1&pageSize=1&tier=All")
        self.assertEqual((first_page["total"], first_page["totalPages"], first_page["customers"][0]["id"]), (4, 4, "25369"))
        high = self.get_json("/api/customers?page=1&pageSize=20&tier=High")
        self.assertEqual((high["total"], len(high["customers"])), (2, 2))
        self.assertTrue(all(customer["riskTier"] == "High" for customer in high["customers"]))
        search = self.get_json("/api/customers?search=63581")
        self.assertEqual([customer["id"] for customer in search["customers"]], ["63581"])

    def test_customer_details_and_not_found(self):
        first = self.get_json("/api/customers/25369")
        second = self.get_json("/api/customers/CUST-63581")
        self.assertEqual((first["riskScore"], first["riskTier"]), (0.8721, "High"))
        self.assertEqual((second["riskScore"], second["riskTier"]), (0.6994, "Medium"))
        self.assert_http_error("/api/customers/999999", 404)
        self.assert_http_error("/api/customers/not-a-number", 400)

    def test_invalid_query_parameters_and_unknown_endpoint(self):
        for path in (
            "/api/customers?page=0",
            "/api/customers?page=5&pageSize=1",
            "/api/customers?pageSize=101",
            "/api/customers?tier=Critical",
        ):
            self.assert_http_error(path, 400)
        self.assert_http_error("/api/unknown", 404)

    def test_cors_and_bearer_authentication(self):
        os.environ["ALLOWED_ORIGINS"] = "https://dashboard.example.test"
        request = urllib.request.Request(self.base_url + "/api/health", headers={"Origin": "https://dashboard.example.test"})
        with urllib.request.urlopen(request) as response:
            self.assertEqual(response.headers["Access-Control-Allow-Origin"], "https://dashboard.example.test")
            self.assertEqual(response.headers["X-Content-Type-Options"], "nosniff")

        os.environ["API_AUTH_TOKEN"] = "test-secret"
        self.assert_http_error("/api/health", 401)
        payload = self.get_json("/api/health", {"Authorization": "Bearer test-secret"})
        self.assertEqual(payload["status"], "ready")


if __name__ == "__main__":
    unittest.main()
