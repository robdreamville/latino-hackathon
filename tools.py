# tools.py — Centinela agent tools (14 total)
# Each entry: description + JSON schema + function.
# Stubbed where the integration isn't built yet — fill in during the hackathon.

import json
import os

import db

# ---------------------------------------------------------------------------
# 1-4: Reasoning tools
# ---------------------------------------------------------------------------

# --- Chroma collection (lazy-loaded) ---
_chroma_col = None

def _get_collection():
    global _chroma_col
    if _chroma_col is None:
        import chromadb
        client = chromadb.PersistentClient(path="chroma_db")
        _chroma_col = client.get_collection("uscis")
    return _chroma_col


def search_docs(query, session_key=None):
    """RAG over the USCIS corpus. Chroma + Gemini embeddings. Top-4 chunks."""
    import google.generativeai as genai
    emb = genai.embed_content(
        model="models/text-embedding-004", content=query)["embedding"]
    col = _get_collection()
    res = col.query(query_embeddings=[emb], n_results=4)
    chunks = []
    for i in range(len(res["ids"][0])):
        chunks.append({
            "text": res["documents"][0][i],
            "doc": res["metadatas"][0][i].get("doc"),
            "page": res["metadatas"][0][i].get("page"),
            "distance": res["distances"][0][i],
        })
    # Gate 1: relevance floor (L2 distance, lower = better).
    # 1.0 ~= cosine 0.5, matching the clean-agent floor.
    chunks = [c for c in chunks if c["distance"] < 1.0]
    return {"chunks": chunks}


def web_search(query, session_key=None):
    """Fresh info via Tavily."""
    from tavily import TavilyClient
    client = TavilyClient(api_key=os.environ.get("TAVILY_API_KEY"))
    res = client.search(query, max_results=5, include_answer=False)
    return [{"title": r["title"], "url": r["url"], "snippet": r["content"][:500]}
            for r in res.get("results", [])]


def check_case_status(receipt_number, session_key=None):
    """Live USCIS case-status attempt. Honest failure if blocked."""
    # TODO: attempt real lookup against egov.uscis.gov
    return {"status": "unknown",
            "note": "Live lookup not yet implemented — no mock data returned"}


def flag_for_attorney(question, context="", session_key=None):
    """Escalate to the attorney review queue."""
    db.flag_for_review(session_key, question, context)
    return {"ok": True, "message": "Flagged for attorney review"}


# ---------------------------------------------------------------------------
# 5-9: Messaging tools (Twilio)
# ---------------------------------------------------------------------------

def _twilio_client():
    from twilio.rest import Client
    return Client(os.environ.get("TWILIO_SID"), os.environ.get("TWILIO_TOKEN"))

TWILIO_WHATSAPP_FROM = os.environ.get("TWILIO_WHATSAPP_FROM", "whatsapp:+14155238886")


def send_message(phone, text, session_key=None):
    msg = _twilio_client().messages.create(
        from_=TWILIO_WHATSAPP_FROM, to=f"whatsapp:{phone}", body=text)
    return {"ok": True, "sid": msg.sid}


def send_voice_message(phone, text, session_key=None):
    """ElevenLabs TTS -> MP3 -> WhatsApp voice note."""
    # TODO: ElevenLabs TTS, save MP3, serve via ngrok, Twilio media message
    return {"ok": False, "note": "Voice not wired yet"}


def send_invite(phone, client_name, attorney_name, session_key=None):
    """SMS invite with accept link. Token stored in DB."""
    import secrets
    token = secrets.token_urlsafe(16)
    # TODO: store token -> phone mapping; build accept URL from ngrok base
    accept_url = f"{os.environ.get('PUBLIC_URL', '')}/accept/{token}"
    body = (f"Hola {client_name}, {attorney_name} te invita a usar Centinela, "
            f"tu asistente de inmigración. Acepta aquí: {accept_url}")
    msg = _twilio_client().messages.create(
        from_=os.environ.get("TWILIO_SMS_FROM"), to=phone, body=body)
    return {"ok": True, "sid": msg.sid, "token": token}


def _resolve_phone(name_or_phone):
    if name_or_phone.startswith("+"):
        return name_or_phone
    # TODO: look up by name in clients table
    return name_or_phone


def message_client(name_or_phone, text, session_key=None):
    phone = _resolve_phone(name_or_phone)
    return send_message(phone, text)


def broadcast_message(client_filter, text, session_key=None):
    """Send to all clients matching filter ('all' or a case_type)."""
    # TODO: query clients table by filter
    return {"ok": False, "note": "Broadcast not wired yet"}


# ---------------------------------------------------------------------------
# 10-11: Attorney info tools
# ---------------------------------------------------------------------------

def get_review_queue(session_key=None):
    return {"items": db.get_review_queue()}


def get_client_status(name_or_phone, session_key=None):
    phone = _resolve_phone(name_or_phone)
    client = db.get_client(phone)
    recent = db.get_recent_messages(phone, limit=5)
    return {"client": client, "recent_messages": recent}


# ---------------------------------------------------------------------------
# 12-14: Document tools
# ---------------------------------------------------------------------------

def request_documents(name_or_phone, doc_list, session_key=None):
    """Create checklist, ask client via WhatsApp."""
    phone = _resolve_phone(name_or_phone)
    docs = doc_list if isinstance(doc_list, list) else [doc_list]
    text = ("Tu abogado necesita los siguientes documentos:\n" +
            "\n".join(f"- {d}" for d in docs) +
            "\n\nEnvíalos como fotos por aquí.")
    # TODO: store checklist in documents table
    return send_message(phone, text)


def get_document_status(name_or_phone, session_key=None):
    phone = _resolve_phone(name_or_phone)
    # TODO: read documents table
    return {"phone": phone, "received": [], "missing": []}


def get_document_package(name_or_phone, session_key=None):
    phone = _resolve_phone(name_or_phone)
    # TODO: bundle received docs for dashboard
    return {"phone": phone, "documents": []}


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

def _schema(props, required):
    return {"type": "object", "properties": props, "required": required}

STR = {"type": "string"}

TOOLS = {
    "search_docs": {
        "description": "Search the USCIS document corpus for immigration forms, processes, and requirements. Use for factual questions.",
        "parameters": _schema({"query": STR}, ["query"]),
        "function": search_docs,
    },
    "web_search": {
        "description": "Search the live web for fresh information: law changes, news, current events.",
        "parameters": _schema({"query": STR}, ["query"]),
        "function": web_search,
    },
    "check_case_status": {
        "description": "Look up a USCIS case status by receipt number (e.g. IOE1234567890).",
        "parameters": _schema({"receipt_number": STR}, ["receipt_number"]),
        "function": check_case_status,
    },
    "flag_for_attorney": {
        "description": "Escalate a question to the attorney review queue. Use when it's a legal judgment call or you don't know the answer.",
        "parameters": _schema({"question": STR, "context": STR}, ["question"]),
        "function": flag_for_attorney,
    },
    "send_message": {
        "description": "Send a WhatsApp text message to a phone number.",
        "parameters": _schema({"phone": STR, "text": STR}, ["phone", "text"]),
        "function": send_message,
    },
    "send_voice_message": {
        "description": "Send a WhatsApp voice note (Spanish TTS) to a phone number.",
        "parameters": _schema({"phone": STR, "text": STR}, ["phone", "text"]),
        "function": send_voice_message,
    },
    "send_invite": {
        "description": "Invite a client via SMS with an accept link.",
        "parameters": _schema({"phone": STR, "client_name": STR, "attorney_name": STR},
                              ["phone", "client_name", "attorney_name"]),
        "function": send_invite,
    },
    "broadcast_message": {
        "description": "Send one WhatsApp message to many clients. Filter: 'all' or a case type.",
        "parameters": _schema({"client_filter": STR, "text": STR}, ["client_filter", "text"]),
        "function": broadcast_message,
    },
    "message_client": {
        "description": "Send a WhatsApp message to one client by name or phone.",
        "parameters": _schema({"name_or_phone": STR, "text": STR}, ["name_or_phone", "text"]),
        "function": message_client,
    },
    "get_review_queue": {
        "description": "List pending items flagged for attorney review.",
        "parameters": _schema({}, []),
        "function": get_review_queue,
    },
    "get_client_status": {
        "description": "Get a client's profile, case facts, and recent messages.",
        "parameters": _schema({"name_or_phone": STR}, ["name_or_phone"]),
        "function": get_client_status,
    },
    "request_documents": {
        "description": "Ask a client for documents via WhatsApp. Creates a checklist.",
        "parameters": _schema({"name_or_phone": STR, "doc_list": STR}, ["name_or_phone", "doc_list"]),
        "function": request_documents,
    },
    "get_document_status": {
        "description": "Check what documents a client has sent vs. what's missing.",
        "parameters": _schema({"name_or_phone": STR}, ["name_or_phone"]),
        "function": get_document_status,
    },
    "get_document_package": {
        "description": "Get the organized document package for a client (for the dashboard).",
        "parameters": _schema({"name_or_phone": STR}, ["name_or_phone"]),
        "function": get_document_package,
    },
}
