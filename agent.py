# agent.py — Centinela agent core
# One ReAct loop, two personas. Session: in-memory dict, SQLite write-through.
# Based on the clean-agent pattern: TOOLS dict of plain functions, hand-rolled loop.

import json
import os

import google.generativeai as genai

import db
from tools import TOOLS

from dotenv import load_dotenv
load_dotenv()

MODEL = "gemini-2.5-flash"
MAX_STEPS = 6

genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))

# --- Personas ---

CLIENT_SYSTEM = """Eres Centinela, el asistente del abogado de inmigración de este cliente.
Hablas español como un amigo amable, no como un documento.
Escribes en párrafos naturales y fluidos. NUNCA usas formato markdown,
asteriscos, listas con viñetas, negritas ni encabezados.
Si hay varios puntos, los integras en el texto de forma conversacional.
Usas palabras sencillas. Frases cortas. Como si estuvieras explicándole
esto a alguien en persona.
BREVEDAD ES OBLIGATORIA: tus respuestas son de 2 a 4 frases, nunca más.
No intentes cubrir todos los casos posibles en un solo mensaje.
Si la respuesta depende de la situación del cliente (ciudadano vs residente,
cónyuge vs hijo), NO expliques todos los casos. Pregunta cuál es su caso
primero. Una pregunta a la vez, como una conversación real por WhatsApp.
La gente no lee párrafos largos en el teléfono.

REGLAS:
- Respondes SOLO en español (a menos que el cliente escriba en inglés).
- FLUJO OBLIGATORIO para preguntas: PRIMERO usa search_docs SIEMPRE.
  Solo si search_docs no devuelve nada útil, prueba web_search.
  Solo si ambas fallan, o si es una decisión legal específica de SU caso,
  usas flag_for_attorney. NUNCA te saltes search_docs.
- NUNCA inventas una respuesta legal.
- Si el cliente pide voz o audio, responde que le enviarás una nota de voz.
- Eres una extensión del abogado, no un reemplazo. El abogado toma las decisiones legales.
"""

FIRM_SYSTEM = """You are Centinela, the AI operations assistant for an immigration law firm.
You help the paralegal and attorney manage clients. You are concise and operational.

You have tools to message clients, check status, review escalations, and manage documents.
When the firm asks you to do something, use the right tool, then confirm what you did.
If a request is ambiguous (which client?), ask for clarification before acting.
"""


# --- Session management ---
# In-memory: key -> {"history": [{"role":..., "text":...}], "profile": {...}}
# SQLite is the durable store. Read once per session, write every message.

_sessions = {}


def get_session(key):
    if key in _sessions:
        return _sessions[key]
    profile = db.get_client(key) or {"phone": key, "name": "Unknown", "case_facts": {}}
    history = db.get_recent_messages(key, limit=10)
    session = {"history": history, "profile": profile}
    _sessions[key] = session
    return session


def _tool_schemas():
    # Gemini function-calling schemas, generated from TOOLS metadata.
    # Must be wrapped as {"function_declarations": [...]} per the API.
    return [{
        "function_declarations": [
            {
                "name": name,
                "description": fn["description"],
                "parameters": fn["parameters"],
            }
            for name, fn in TOOLS.items()
        ]
    }]


def _proto_to_dict(proto_map):
    """Convert protobuf Struct/MapComposite to plain Python dict."""
    from google.protobuf.json_format import MessageToDict
    # fc.args is a MapComposite; wrap in a Struct for conversion
    from google.protobuf.struct_pb2 import Struct
    s = Struct()
    for k, v in proto_map.items():
        s[k] = v
    return MessageToDict(s)


def run_agent(key, user_message, persona="client"):
    """Run one ReAct turn. Returns the agent's reply text."""
    session = get_session(key)
    system = CLIENT_SYSTEM if persona == "client" else FIRM_SYSTEM

    # Build conversation for the model
    contents = []
    for m in session["history"]:
        contents.append({"role": "user" if m["role"] == "user" else "model",
                         "parts": [m["text"]]})
    contents.append({"role": "user", "parts": [user_message]})

    model = genai.GenerativeModel(
        MODEL,
        system_instruction=system,
        tools=_tool_schemas(),
    )
    chat = model.start_chat(history=contents[:-1])

    # Persist the incoming message
    db.save_message(key, "user", user_message)
    session["history"].append({"role": "user", "text": user_message})

    response = chat.send_message(contents[-1]["parts"][0])

    for _ in range(MAX_STEPS):
        # No function calls = final answer
        if not response.candidates[0].content.parts:
            break
        fn_calls = [p.function_call for p in response.candidates[0].content.parts
                    if hasattr(p, "function_call") and p.function_call]
        if not fn_calls:
            break

        # Execute tools, feed results back
        fn_responses = []
        for fc in fn_calls:
            name = fc.name
            args = _proto_to_dict(fc.args)
            # Inject session key for tools that need it
            if "session_key" in TOOLS[name]["parameters"].get("properties", {}):
                args.setdefault("session_key", key)
            try:
                result = TOOLS[name]["function"](**args)
            except Exception as e:
                result = {"error": str(e)}
            fn_responses.append({
                "function_response": {"name": name, "response": {"result": result}}
            })
        response = chat.send_message(fn_responses)

    reply = response.text or ""

    db.save_message(key, "assistant", reply)
    session["history"].append({"role": "assistant", "text": reply})
    # Keep memory bounded
    session["history"] = session["history"][-20:]

    return reply
