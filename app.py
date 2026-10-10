# app.py — Centinela FastAPI server
# Two chat doors (WhatsApp + Base44), dashboard reads, invite accept.
# Run: uvicorn app:app --port 8000

import os

from fastapi import FastAPI, Form, Request
from fastapi.responses import JSONResponse

import db
from agent import run_agent

from dotenv import load_dotenv
load_dotenv()

app = FastAPI(title="Centinela")

GREETING = (
    "Hola {name}, soy Centinela, el asistente de tu abogado {attorney}. "
    "Estoy aquí para responder tus preguntas de inmigración en español, "
    "ayudarte con tus documentos y mantenerte al día con tu caso. "
    "Tu información es privada: solo tú y tu abogado pueden ver esta conversación. "
    "¿En qué te puedo ayudar hoy?"
)


@app.on_event("startup")
def startup():
    db.init_db()


# --- Door 1: WhatsApp (Twilio webhook) ---
@app.post("/webhook/whatsapp")
async def whatsapp_webhook(From: str = Form(...), Body: str = Form(...),
                           NumMedia: int = Form(0)):
    phone = From.replace("whatsapp:", "")
    # TODO: handle incoming media (documents) when NumMedia > 0
    reply = run_agent(phone, Body, persona="client")
    return JSONResponse({"reply": reply})


# --- Door 2: Base44 attorney/paralegal chat ---
@app.post("/api/attorney-chat")
async def attorney_chat(request: Request):
    data = await request.json()
    message = data.get("message", "")
    attorney_id = data.get("attorney_id", "firm")
    reply = run_agent(f"firm:{attorney_id}", message, persona="firm")
    return {"reply": reply}


# --- Invite accept ---
@app.get("/accept/{token}")
async def accept_invite(token: str):
    # TODO: look up token -> phone, mark client active
    # For now, return the greeting template
    return {"message": "Token accepted (wiring pending)", "token": token}


# --- Dashboard reads (Base44) ---
@app.get("/api/clients")
async def list_clients():
    return {"clients": db.get_all_clients()}


@app.get("/api/review-queue")
async def review_queue():
    return {"items": db.get_review_queue()}


@app.get("/api/documents")
async def documents():
    return {"packages": db.get_all_documents()}


@app.post("/api/invite")
async def invite(request: Request):
    from tools import send_invite
    data = await request.json()
    result = send_invite(data["phone"], data["client_name"], data.get("attorney_name", ""))
    return result




# --- Carpeta integration: document classifier ---
@app.post("/api/classify")
async def classify(request: Request):
    """Classify a document image. Called by Carpeta backend first, falls back to InvokeLLM."""
    import warnings
    warnings.filterwarnings("ignore")
    import google.generativeai as genai
    import urllib.request

    data = await request.json()
    file_url = data.get("file_url", "")
    doc_types = data.get("doc_types", [])

    # Download image
    try:
        with urllib.request.urlopen(file_url, timeout=15) as resp:
            img_data = resp.read()
    except Exception as e:
        return {"classified_as": "unknown", "confidence": 0.0,
                "quality_flags": ["download_failed"],
                "name_on_document": None, "document_date": None}

    # Classify with Gemini vision
    model = genai.GenerativeModel("gemini-2.5-flash")
    type_list = ", ".join(doc_types)
    prompt = f"""Classify this document image into ONE of these types: {type_list}.
If it doesn't match any, say "unknown".

Also report:
- quality_flags: list any of ["blurry", "cropped", "glare"] that apply, or empty list
- name_on_document: the person's name visible on the document, or null
- document_date: the document date as YYYY-MM-DD, or null

Respond in JSON only: {{"classified_as": "...", "confidence": 0.0-1.0, "quality_flags": [...], "name_on_document": "...", "document_date": "..."}}"""

    try:
        resp = model.generate_content([
            prompt,
            {"mime_type": "image/jpeg", "data": img_data}
        ])
        import json as _json
        # Strip markdown fences if present
        text = resp.text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1].rsplit("```", 1)[0]
        result = _json.loads(text)
        return {
            "classified_as": result.get("classified_as", "unknown"),
            "confidence": float(result.get("confidence", 0.0)),
            "quality_flags": result.get("quality_flags", []),
            "name_on_document": result.get("name_on_document"),
            "document_date": result.get("document_date"),
        }
    except Exception as e:
        return {"classified_as": "unknown", "confidence": 0.0,
                "quality_flags": ["classification_failed"],
                "name_on_document": None, "document_date": None}


# --- Carpeta integration: gated Q&A ---
@app.post("/api/ask")
async def ask(request: Request):
    """Answer informational questions from RAG. Returns legal_judgment flag for legal calls."""
    import warnings
    warnings.filterwarnings("ignore")
    import google.generativeai as genai
    from tools import search_docs

    data = await request.json()
    question = data.get("question", "")

    # Step 1: check if this is a legal judgment call
    judge_model = genai.GenerativeModel("gemini-2.5-flash")
    judge_prompt = f"""Decide if this question needs a LAWYER or just FACTS.

Answer "yes" (needs lawyer) ONLY if the question asks:
- Whether THEY qualify or are eligible for a benefit ("¿califico?", "¿puedo aplicar?")
- What THEY should do strategically ("¿debería...?", "¿me conviene...?")
- How long THEIR case will take or timing advice

Answer "no" (just facts) if the question asks:
- What documents or forms are needed (general requirements)
- What a form is or how the process works in general
- Where to get a document or how to fill something out
- General information anyone could look up

Question: {question}

Answer ONLY "yes" or "no"."""
    judge_resp = judge_model.generate_content(judge_prompt)
    if "yes" in judge_resp.text.strip().lower():
        return {"legal_judgment": True}

    # Step 2: RAG lookup
    rag = search_docs(question)
    chunks = rag.get("chunks", [])
    if not chunks:
        return {"legal_judgment": True}  # Can't answer from docs = escalate

    # Step 3: generate short Spanish answer
    context = "\n\n".join(f"[{c['doc']} p.{c['page']}]\n{c['text']}" for c in chunks)
    prompt = f"""Responde en español, de forma natural y breve (menos de 80 palabras).
Usa SOLO esta información. No des consejos sobre elegibilidad, tiempos o estrategia.
Si no puedes responder con esta información, di "No tengo esa información".

Documentos:
{context}

Pregunta: {question}

Respuesta:"""
    model = genai.GenerativeModel("gemini-2.5-flash")
    resp = model.generate_content(prompt)

    sources = [{"title": c["doc"], "url": "https://www.uscis.gov/", "page": str(c["page"])}
               for c in chunks[:3]]

    return {"answer": resp.text.strip(), "sources": sources}

@app.get("/health")
async def health():
    return {"ok": True}
