import json
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

from scripts import api_server


class ApiContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
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

    def get_json(self, path: str):
        with urllib.request.urlopen(self.base_url + path) as response:
            return json.load(response)

    def test_health_and_portfolio_summary(self):
        self.assertEqual(self.get_json("/api/health")["status"], "ready")
        summary = self.get_json("/api/portfolio-summary")
        self.assertEqual((summary["totalCustomers"], summary["highRiskCount"], summary["mediumRiskCount"], summary["lowRiskCount"]), (25718, 315, 3933, 21470))

    def test_pagination_and_risk_band_filtering(self):
        high = self.get_json("/api/customers?page=1&pageSize=20&tier=High")
        self.assertEqual((high["total"], len(high["customers"])), (315, 20))
        self.assertTrue(all(customer["riskTier"] == "High" for customer in high["customers"]))
        with self.assertRaises(urllib.error.HTTPError) as result:
            urllib.request.urlopen(self.base_url + "/api/customers?page=0")
        self.assertEqual(result.exception.code, 400)
        result.exception.close()

    def test_regression_customers_and_not_found(self):
        first = self.get_json("/api/customers/25369")
        second = self.get_json("/api/customers/63581")
        self.assertEqual((first["riskScore"], first["riskTier"]), (0.8721, "High"))
        self.assertEqual((second["riskScore"], second["riskTier"]), (0.6994, "Medium"))
        with self.assertRaises(urllib.error.HTTPError) as result:
            urllib.request.urlopen(self.base_url + "/api/customers/999999")
        self.assertEqual(result.exception.code, 404)
        result.exception.close()

    def test_deployed_model_metrics(self):
        metrics = self.get_json("/api/model-metrics")
        self.assertEqual((metrics["rocAuc"], metrics["prAuc"]), (0.6607, 0.2585))


if __name__ == "__main__":
    unittest.main()
