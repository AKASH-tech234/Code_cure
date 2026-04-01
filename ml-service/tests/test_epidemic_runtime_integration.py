import unittest

from fastapi.testclient import TestClient

from app.main import app


class EpidemicRuntimeIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_forecast_usa_contract_shape(self):
        response = self.client.post(
            "/forecast",
            json={"region_id": "USA", "horizon_days": 7},
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()

        self.assertEqual(body["region_id"], "USA")
        self.assertEqual(body["horizon_days"], 7)
        self.assertIsInstance(body["predicted_cases"], list)
        self.assertEqual(len(body["predicted_cases"]), 7)
        self.assertIsInstance(body["risk_score"], float)
        self.assertIn(body["risk_level"], ["Low", "Medium", "High"])
        self.assertIsInstance(body["as_of_date"], str)

    def test_simulate_usa_contract_shape(self):
        response = self.client.post(
            "/simulate",
            json={
                "region_id": "USA",
                "intervention": {
                    "mobility_reduction": 0.3,
                    "vaccination_increase": 0.2,
                },
            },
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()

        self.assertEqual(body["region_id"], "USA")
        self.assertIsInstance(body["baseline_cases"], list)
        self.assertIsInstance(body["simulated_cases"], list)
        self.assertEqual(len(body["baseline_cases"]), 7)
        self.assertEqual(len(body["simulated_cases"]), 7)
        self.assertIsInstance(body["delta_cases"], int)
        self.assertIsInstance(body["impact_summary"], str)

    def test_risk_usa_contract_shape(self):
        response = self.client.post(
            "/risk",
            json={"region_id": "USA"},
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()

        self.assertEqual(body["region_id"], "USA")
        self.assertIn(body["risk_level"], ["Low", "Medium", "High"])
        self.assertIsInstance(body["risk_score"], float)
        self.assertIsInstance(body["drivers"], list)
        self.assertEqual(len(body["drivers"]), 4)

    def test_non_usa_fallback_compatibility(self):
        response = self.client.post(
            "/forecast",
            json={"region_id": "ITA", "horizon_days": 5},
        )
        self.assertEqual(response.status_code, 200)

        body = response.json()
        self.assertEqual(body["region_id"], "ITA")
        self.assertEqual(body["horizon_days"], 5)
        self.assertEqual(len(body["predicted_cases"]), 5)


if __name__ == "__main__":
    unittest.main()
