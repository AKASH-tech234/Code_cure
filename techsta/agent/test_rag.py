from app.tools.rag_tool import rag_tool

res = rag_tool("how to control outbreak spread")

print("\nContext:\n", res["context"])
print("\nSources:\n", res["sources"])