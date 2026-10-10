# chat.py — interactive CLI test for the Centinela agent
# Run: python chat.py [--persona client|firm]
# Lets you talk to the agent directly, no WhatsApp/Base44 needed.
import warnings
warnings.filterwarnings("ignore")
from dotenv import load_dotenv
load_dotenv()

import sys
import db
from agent import run_agent

db.init_db()

persona = "client"
if "--persona" in sys.argv:
    i = sys.argv.index("--persona")
    if i + 1 < len(sys.argv):
        persona = sys.argv[i + 1]

key = input("Session key (phone, e.g. +15551234567): ").strip() or "test:+15550001111"

print(f"\n--- Centinela [{persona}] ---  (type 'quit' to exit)\n")

while True:
    try:
        msg = input("You: ").strip()
    except (EOFError, KeyboardInterrupt):
        break
    if msg.lower() in ("quit", "exit", "q"):
        break
    if not msg:
        continue
    try:
        reply = run_agent(key, msg, persona=persona)
        print(f"\nCentinela: {reply}\n")
    except Exception as e:
        print(f"\n[ERROR] {type(e).__name__}: {e}\n")
