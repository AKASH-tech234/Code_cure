from app.retrieval.retriever import retrieve

queries = [
    "vaccination reduces spread",
    "mobility and outbreak control",
    "lockdown strategy effectiveness"
]

for q in queries:
    print("\n======================")
    print("Query:", q)
    res = retrieve(q, top_k=3)
    print("Context:\n", res["context"])
    print("Sources:", res["sources"])