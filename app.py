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
    # TODO: return all clients
    return {"clients": []}


@app.get("/api/review-queue")
async def review_queue():
    return {"items": db.get_review_queue()}


@app.get("/api/documents")
async def documents():
    # TODO: return document packages
    return {"packages": []}


@app.post("/api/invite")
async def invite(request: Request):
    from tools import send_invite
    data = await request.json()
    result = send_invite(data["phone"], data["client_name"], data.get("attorney_name", ""))
    return result


@app.get("/health")
async def health():
    return {"ok": True}
