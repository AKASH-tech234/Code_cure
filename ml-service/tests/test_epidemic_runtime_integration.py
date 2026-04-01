import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app
from app.services import epidemic_runtime
from app.services.epidemic_model_adapter import AdapterForecastResult, AdapterRiskDriver, AdapterRiskResult


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
        self.assertIn("point_forecast", body)
        self.assertIn("prediction_interval_80pct", body)
        self.assertIn("model_metadata", body)
        if body["point_forecast"] is not None:
            self.assertIn("predicted_roll7_cases", body["point_forecast"])
        if body["prediction_interval_80pct"] is not None:
            self.assertIn("lower_q10", body["prediction_interval_80pct"])
            self.assertIn("upper_q90", body["prediction_interval_80pct"])

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

    def test_forecast_prefers_adapter_when_available(self):
        adapter_payload = AdapterForecastResult(
            region_id="ITA",
            predicted_cases=[101, 102, 103],
            growth_rate=0.042,
            risk_score=0.51,
            risk_level="Medium",
            horizon_days=3,
            as_of_date="2026-04-01",
            prediction_date="2026-04-02",
            country="Italy",
            point_forecast={"predicted_roll7_cases": 101.0},
            prediction_interval_80pct={"lower_q10": 95.0, "median_q50": 101.0, "upper_q90": 110.0},
            model_metadata={"model_mae": 1394},
        )

        with (
            patch.object(epidemic_runtime._adapter, "supports_region", return_value=True),
            patch.object(epidemic_runtime._adapter, "forecast", return_value=adapter_payload),
        ):
            response = self.client.post(
                "/forecast",
                json={"region_id": "ITA", "horizon_days": 3},
            )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["region_id"], "ITA")
        self.assertEqual(body["predicted_cases"], [101, 102, 103])
        self.assertEqual(body["growth_rate"], 0.042)
        self.assertEqual(body["risk_score"], 0.51)
        self.assertEqual(body["risk_level"], "Medium")
        self.assertEqual(body["horizon_days"], 3)
        self.assertEqual(body["as_of_date"], "2026-04-01")
        self.assertEqual(body["prediction_date"], "2026-04-02")
        self.assertEqual(body["country"], "Italy")
        self.assertEqual(body["point_forecast"]["predicted_roll7_cases"], 101.0)

    def test_forecast_accepts_model_spec_inputs(self):
        response = self.client.post(
            "/forecast",
            json={
                "region_id": "USA",
                "horizon_days": 3,
                "country": "US",
                "prediction_date": "2026-04-05",
                "features": {
                    "DayOfWeek": 1,
                    "Month": 4,
                    "IsWeekend": 0,
                    "New_Confirmed_Lag1": 42000.0,
                    "New_Confirmed_Lag3": 41500.0,
                    "New_Confirmed_Lag7": 39800.0,
                    "New_Deaths_Lag1": 210.0,
                    "New_Confirmed_Roll14_Lag1": 40500.0,
                    "stringency_index": 35.0,
                    "reproduction_rate": 0.94,
                },
                "prev_roll7": 41000.0,
            },
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["region_id"], "USA")
        self.assertEqual(body["horizon_days"], 3)
        self.assertEqual(len(body["predicted_cases"]), 3)
        self.assertIn("point_forecast", body)
        self.assertIn("prediction_interval_80pct", body)
        if body["point_forecast"] is not None:
            self.assertIn("predicted_roll7_cases", body["point_forecast"])

    def test_forecast_falls_back_when_adapter_errors(self):
        with (
            patch.object(epidemic_runtime._adapter, "supports_region", return_value=True),
            patch.object(epidemic_runtime._adapter, "forecast", side_effect=RuntimeError("adapter failure")),
        ):
            response = self.client.post(
                "/forecast",
                json={"region_id": "ITA", "horizon_days": 4},
            )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["region_id"], "ITA")
        self.assertEqual(body["horizon_days"], 4)
        self.assertEqual(len(body["predicted_cases"]), 4)

    def test_risk_prefers_adapter_when_available(self):
        adapter_payload = AdapterRiskResult(
            region_id="IND",
            risk_level="High",
            risk_score=0.82,
            drivers=[
                AdapterRiskDriver(factor="predicted_growth_rate", value=0.91, weight=0.35),
                AdapterRiskDriver(factor="mobility_index", value=0.41, weight=0.25),
                AdapterRiskDriver(factor="vaccination_gap", value=0.52, weight=0.22),
                AdapterRiskDriver(factor="hospital_pressure", value=0.47, weight=0.18),
            ],
        )

        with (
            patch.object(epidemic_runtime._adapter, "supports_region", return_value=True),
            patch.object(epidemic_runtime._adapter, "risk", return_value=adapter_payload),
        ):
            response = self.client.post(
                "/risk",
                json={"region_id": "IND"},
            )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["region_id"], "IND")
        self.assertEqual(body["risk_level"], "High")
        self.assertEqual(body["risk_score"], 0.82)
        self.assertEqual(len(body["drivers"]), 4)


if __name__ == "__main__":
    unittest.main()
