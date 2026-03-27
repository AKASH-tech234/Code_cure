from app.graph.build_graph import build_graph

graph = build_graph()

initial_state = {
    "query": "how are vaccinated people affected by covid-19?",
    "context": "",
    "answer": "",
    "sources": [],
    "intent": "",
    "tool": "",
    "reasoning": ""
}

res = graph.invoke(initial_state)

print("\n=== QUERY ===\n")
print(initial_state["query"])

print("\n=== INTENT ===\n")
print(res.get("intent", ""))

print("\n=== TOOL ===\n")
print(res.get("tool", ""))

print("\n=== REASONING ===\n")
print(res.get("reasoning", ""))

print("\n=== ANSWER ===\n")
print(res.get("answer", ""))

print("\n=== SOURCES ===\n")
print(res.get("sources", []))