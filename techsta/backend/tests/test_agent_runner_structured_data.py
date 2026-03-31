import unittest
from typing import Any, Dict, cast

from app.services.agent_runner import _extract_structured_data


class AgentRunnerStructuredDataTests(unittest.TestCase):
    def test_extract_forecast_structured_data(self):
        payloads = {
            "forecast": {
                "region_id": "ITA",
                "risk_score": 0.62,
                "risk_level": "Medium",
                "growth_rate": 0.05,
                "predicted_cases": [100, 110],
                "horizon_days": 2,
                "as_of_date": "2026-03-27",
            }
        }

        data = _extract_structured_data("forecast", payloads)

        self.assertIsNotNone(data)
        data = cast(Dict[str, Any], data)
        self.assertEqual(data["kind"], "forecast")
        self.assertEqual(data["region_id"], "ITA")
        self.assertEqual(data["risk_score"], 0.62)
        self.assertEqual(data["predicted_cases"], [100, 110])
        self.assertIn("chart", data)
        self.assertEqual(data["chart"]["chart_type"], "line")
        self.assertEqual(data["chart"]["labels"], ["Day 1", "Day 2"])
        self.assertEqual(data["chart"]["series"][0]["name"], "predicted_cases")
        self.assertEqual(data["chart"]["series"][0]["values"], [100, 110])

    def test_extract_simulate_structured_data(self):
        payloads = {
            "simulate": {
                "region_id": "ITA",
                "baseline_cases": [100, 120],
                "simulated_cases": [98, 112],
                "delta_cases": 10,
                "impact_summary": "intervention could avert cases",
            }
        }

        data = _extract_structured_data("simulate", payloads)

        self.assertIsNotNone(data)
        data = cast(Dict[str, Any], data)
        self.assertEqual(data["kind"], "simulate")
        self.assertEqual(data["delta_cases"], 10)
        self.assertEqual(data["baseline_cases"], [100, 120])
        self.assertIn("chart", data)
        self.assertEqual(data["chart"]["chart_type"], "line")
        self.assertEqual(data["chart"]["labels"], ["Day 1", "Day 2"])
        self.assertEqual(len(data["chart"]["series"]), 2)
        self.assertEqual(data["chart"]["series"][0]["name"], "baseline_cases")
        self.assertEqual(data["chart"]["series"][1]["name"], "simulated_cases")
        self.assertEqual(data["chart"]["summary"]["delta_cases"], 10)

    def test_extract_rag_structured_data(self):
        payloads = {
            "rag": {
                "context": "guidance text",
                "sources": ["doc-1", "doc-2"],
            }
        }

        data = _extract_structured_data("rag", payloads)

        self.assertIsNotNone(data)
        data = cast(Dict[str, Any], data)
        self.assertEqual(data["kind"], "rag")
        self.assertEqual(data["source_count"], 2)
        self.assertTrue(data["has_context"])

    def test_returns_none_when_payload_missing(self):
        data = _extract_structured_data("forecast", {})
        self.assertIsNone(data)


if __name__ == "__main__":
    unittest.main()
