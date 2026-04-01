import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app


class QueryContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_query_rejects_invalid_intervention_bounds(self):
        response = self.client.post(
            "/query",
            json={
                "query": "simulate scenario",
                "intervention": {
                    "mobility_reduction": 1.2,
                    "vaccination_increase": 0.1,
                },
            },
        )
        self.assertEqual(response.status_code, 422)

    def test_query_rejects_short_region_id(self):
        response = self.client.post(
            "/query",
            json={
                "query": "forecast",
                "region_id": "IT",
            },
        )
        self.assertEqual(response.status_code, 422)

    @patch("app.routers.query.run_agent")
    def test_query_followup_shape_is_deterministic(self, mock_run_agent):
        mock_run_agent.return_value = {
            "answer": None,
            "intent": "forecast",
            "tool": "forecast",
            "reasoning": "Region is required",
            "sources": [],
            "structured_data": None,
            "followup": {
                "question": "Which region should I analyze?",
                "missing_fields": ["region_id"],
            },
            "memory_updates": {"last_intent": "forecast", "query": "forecast"},
        }

        response = self.client.post(
            "/query",
            json={"query": "forecast"},
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertIn("session_id", body)
        self.assertIn("answer", body)
        self.assertIn("intent", body)
        self.assertIn("tool", body)
        self.assertIn("reasoning", body)
        self.assertIn("sources", body)
        self.assertIn("structured_data", body)
        self.assertIn("followup", body)

        self.assertIsInstance(body["sources"], list)
        self.assertIsNone(body["structured_data"])
        self.assertIsInstance(body["followup"], dict)
        self.assertIsInstance(body["followup"]["question"], str)
        self.assertIsInstance(body["followup"]["missing_fields"], list)

    @patch("app.routers.query.run_agent")
    def test_query_returns_structured_data_chart_payload(self, mock_run_agent):
        mock_run_agent.return_value = {
            "answer": "Forecast generated",
            "intent": "forecast",
            "tool": "forecast",
            "reasoning": "Forecast requested",
            "sources": ["doc-1"],
            "structured_data": {
                "kind": "forecast",
                "region_id": "ITA",
                "risk_score": 0.62,
                "risk_level": "Medium",
                "predicted_cases": [100, 110],
                "chart": {
                    "chart_type": "line",
                    "labels": ["Day 1", "Day 2"],
                    "series": [{"name": "predicted_cases", "values": [100, 110]}],
                },
            },
            "followup": None,
            "memory_updates": {"last_intent": "forecast", "query": "forecast for italy"},
        }

        response = self.client.post(
            "/query",
            json={"query": "forecast for italy", "region_id": "ITA"},
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertIsInstance(body["structured_data"], dict)
        self.assertEqual(body["structured_data"]["kind"], "forecast")
        self.assertEqual(body["structured_data"]["chart"]["chart_type"], "line")
        self.assertEqual(body["structured_data"]["chart"]["labels"], ["Day 1", "Day 2"])
        self.assertEqual(body["structured_data"]["chart"]["series"][0]["values"], [100, 110])
        self.assertIsNone(body["followup"])


if __name__ == "__main__":
    unittest.main()
