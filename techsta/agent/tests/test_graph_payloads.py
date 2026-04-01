import json
import unittest
from unittest.mock import patch

from app.graph.nodes import llm_node, planner_node, tool_node


class GraphPayloadNormalizationTests(unittest.TestCase):
    @patch("app.graph.nodes.rag_tool")
    @patch("app.graph.nodes.forecast_tool")
    def test_tool_node_populates_structured_payloads(self, mock_forecast_tool, mock_rag_tool):
        mock_forecast_tool.return_value = {
            "region_id": "ITA",
            "risk_score": 0.34,
            "risk_level": "moderate",
        }
        mock_rag_tool.return_value = {
            "context": "WHO recommends layered interventions.",
            "sources": ["who-guideline"],
        }

        result = tool_node(
            {
                "tool": "forecast",
                "region": "ITA",
                "intervention": {},
                "query": "forecast for italy",
            }
        )

        self.assertIn("tool_payloads", result)
        self.assertIn("forecast", result["tool_payloads"])
        self.assertIn("rag", result["tool_payloads"])
        self.assertEqual(result["tool_payloads"]["forecast"]["region_id"], "ITA")
        self.assertIn("FORECAST DATA", result["context"])
        self.assertIn("RELEVANT GUIDELINES", result["context"])
        self.assertEqual(result["sources"], ["who-guideline"])

    @patch("app.graph.nodes.generate_answer")
    def test_llm_node_uses_structured_payloads_in_prompt(self, mock_generate_answer):
        mock_generate_answer.return_value = "Final synthesis"
        state = {
            "query": "what is the risk",
            "reasoning": "risk requested",
            "context": "Risk context",
            "tool_payloads": {
                "risk": {
                    "region_id": "ITA",
                    "risk_score": 0.82,
                    "risk_level": "high",
                }
            },
        }

        result = llm_node(state)

        self.assertEqual(result["answer"], "Final synthesis")
        sent_prompt = mock_generate_answer.call_args[0][0]
        self.assertIn("Structured tool outputs (JSON):", sent_prompt)
        self.assertIn('"risk_score": 0.82', sent_prompt)

    @patch("app.graph.nodes.generate_answer")
    def test_planner_accepts_zero_intervention_values(self, mock_generate_answer):
        mock_generate_answer.return_value = json.dumps(
            {
                "intent": "simulate",
                "tool": "simulate",
                "region": "ITA",
                "intervention": {
                    "mobility_reduction": 0.0,
                    "vaccination_increase": 0.0,
                },
                "missing_fields": [],
                "reasoning": "simulate scenario",
                "followup_question": "",
            }
        )

        result = planner_node({"query": "simulate for italy", "memory": {}})

        self.assertEqual(result["intent"], "simulate")
        self.assertEqual(result["region"], "ITA")
        self.assertNotIn("intervention", result["missing_fields"])


if __name__ == "__main__":
    unittest.main()
