# ingest.py — PDF corpus -> Chroma (run once)
# pdfplumber -> clean -> 500-token chunks -> text-embedding-004 -> Chroma
# The SAME embedding model must be used at query time in search_docs.

import os

import chromadb
import google.generativeai as genai
import pdfplumber

genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))

CORPUS_DIR = "corpus"       # 18 PDFs go here
CHROMA_DIR = "chroma_db"
COLLECTION = "uscis"
CHUNK_TOKENS = 500          # ~2000 chars


def clean_text(text):
    lines = [l.strip() for l in text.split("\n")]
    # Drop likely headers/footers/page numbers
    lines = [l for l in lines if l and not l.isdigit() and len(l) > 2]
    return "\n".join(lines)


def chunk(text, size=CHUNK_TOKENS * 4, overlap=200):
    chunks = []
    start = 0
    while start < len(text):
        chunks.append(text[start:start + size])
        start += size - overlap
    return chunks


def main():
    client = chromadb.PersistentClient(path=CHROMA_DIR)
    col = client.get_or_create_collection(COLLECTION)

    pdfs = [f for f in os.listdir(CORPUS_DIR) if f.endswith(".pdf")]
    print(f"Ingesting {len(pdfs)} PDFs...")

    for pdf_file in pdfs:
        path = os.path.join(CORPUS_DIR, pdf_file)
        with pdfplumber.open(path) as pdf:
            for i, page in enumerate(pdf.pages):
                text = clean_text(page.extract_text() or "")
                if len(text) < 100:
                    continue
                for j, ch in enumerate(chunk(text)):
                    emb = genai.embed_content(
                        model="models/text-embedding-004", content=ch)["embedding"]
                    col.add(
                        ids=[f"{pdf_file}-p{i}-c{j}"],
                        embeddings=[emb],
                        documents=[ch],
                        metadatas=[{"doc": pdf_file, "page": i + 1}],
                    )
        print(f"  done: {pdf_file}")

    print(f"Total chunks: {col.count()}")


if __name__ == "__main__":
    main()
