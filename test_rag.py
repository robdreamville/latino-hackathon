# test_rag.py — full RAG loop: retrieve -> generate -> sources + answer
# Run: python test_rag.py "tu pregunta aquí"
import os, sys, warnings
warnings.filterwarnings("ignore")

import google.generativeai as genai
from tools import search_docs

genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))

query = sys.argv[1] if len(sys.argv) > 1 else "que documentos necesito para pedir asilo"
print(f"Pregunta: {query}\n")

r = search_docs(query)
chunks = r.get("chunks", [])

if not chunks:
    print("No se encontraron documentos relevantes.")
    sys.exit(0)

print("=== Fuentes ===")
for c in chunks:
    print(f"  - {c['doc']} (pág. {c['page']})")
print()

context = "\n\n".join(f"[{c['doc']} p.{c['page']}]\n{c['text']}" for c in chunks)
prompt = f"""Eres un asistente amable explicándole esto a un amigo en español.
Escribe de forma natural y conversacional, en párrafos fluidos.
NO uses formato markdown, ni asteriscos, ni listas con viñetas, ni negritas.
Si hay varios puntos, intégralos en el texto de forma natural.
Usa SOLO la información de estos documentos.
Si los documentos no contienen la respuesta, di que no lo sabes.

Documentos:
{context}

Pregunta: {query}

Respuesta:"""

model = genai.GenerativeModel("gemini-2.5-flash")
resp = model.generate_content(prompt)
print("=== Respuesta ===")
print(resp.text)
