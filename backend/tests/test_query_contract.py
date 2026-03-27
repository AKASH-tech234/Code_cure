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
        self.assertIn("followup", body)

        self.assertIsInstance(body["sources"], list)
        self.assertIsInstance(body["followup"], dict)
        self.assertIsInstance(body["followup"]["question"], str)
        self.assertIsInstance(body["followup"]["missing_fields"], list)


if __name__ == "__main__":
    unittest.main()
