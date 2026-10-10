# test_tavily.py — quick Tavily sanity check
# Run: python test_tavily.py "tu búsqueda aquí"
import warnings
warnings.filterwarnings("ignore")
from dotenv import load_dotenv
load_dotenv()

import sys, json
from tools import web_search

query = sys.argv[1] if len(sys.argv) > 1 else "cambios ley inmigración 2026"
print(f"Query: {query}\n")

results = web_search(query)
for r in results:
    print(f"- {r['title']}")
    print(f"  {r['url']}")
    print(f"  {r['snippet'][:200]}")
    print()
