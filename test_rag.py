# test_rag.py — quick RAG sanity check
# Run: python test_rag.py "tu pregunta aquí"
import sys, json
from tools import search_docs

query = sys.argv[1] if len(sys.argv) > 1 else "que documentos necesito para pedir asilo"
print(f"Query: {query}\n")

r = search_docs(query)
chunks = r.get("chunks", [])
print(f"Got {len(chunks)} chunks\n")

for c in chunks:
    print(f"[{c['doc']} p.{c['page']}] dist={c['distance']:.3f}")
    print(c['text'][:250])
    print("---")
