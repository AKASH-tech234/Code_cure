from app.agent import run_agent

query = "What are the best strategies to control an outbreak early?"

res = run_agent(query)

print("\n=== ANSWER ===\n")
print(res["answer"])

print("\n=== SOURCES ===\n")
print(res["sources"])