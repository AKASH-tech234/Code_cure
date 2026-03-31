import unittest

from fastapi.testclient import TestClient

from app.main import app
from app.data.region_templates import get_all_region_ids


class RiskConsistencyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_forecast_and_risk_scores_match_for_each_region(self):
        for region_id in get_all_region_ids():
            forecast_res = self.client.post(
                "/forecast",
                json={"region_id": region_id, "horizon_days": 7},
            )
            risk_res = self.client.post(
                "/risk",
                json={"region_id": region_id},
            )

            self.assertEqual(forecast_res.status_code, 200)
            self.assertEqual(risk_res.status_code, 200)

            forecast_body = forecast_res.json()
            risk_body = risk_res.json()

            self.assertEqual(forecast_body["risk_score"], risk_body["risk_score"])
            self.assertEqual(forecast_body["risk_level"], risk_body["risk_level"])

    def test_simulate_enforces_intervention_bounds(self):
        invalid_res = self.client.post(
            "/simulate",
            json={
                "region_id": "ITA",
                "intervention": {
                    "mobility_reduction": 1.1,
                    "vaccination_increase": 0.1,
                },
            },
        )
        self.assertEqual(invalid_res.status_code, 422)

        valid_res = self.client.post(
            "/simulate",
            json={
                "region_id": "ITA",
                "intervention": {
                    "mobility_reduction": 0.0,
                    "vaccination_increase": 1.0,
                },
            },
        )
        self.assertEqual(valid_res.status_code, 200)

    def test_unknown_region_returns_404(self):
        response = self.client.post(
            "/risk",
            json={"region_id": "XYZ"},
        )
        self.assertEqual(response.status_code, 404)


if __name__ == "__main__":
    unittest.main()
