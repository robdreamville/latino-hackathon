# seed.py — populate demo client data
# Run: python seed.py
# Gives the agent real client profiles to work with during testing/demo.
import warnings
warnings.filterwarnings("ignore")
from dotenv import load_dotenv
load_dotenv()

import db

db.init_db()

clients = [
    {
        "phone": "+12018521309",  # Roberto's test number
        "name": "María González",
        "attorney": "Lic. García",
        "case_type": "asylum",
        "case_facts": {
            "receipt_number": "IOE1234567890",
            "filing_date": "2025-03-15",
            "next_hearing": "2026-11-20",
            "status": "pending",
        },
    },
    {
        "phone": "+15550002222",
        "name": "Carlos Ramírez",
        "attorney": "Lic. García",
        "case_type": "I-130",
        "case_facts": {
            "receipt_number": "IOE0987654321",
            "filing_date": "2025-06-01",
            "beneficiary": "esposa",
            "petitioner_status": "ciudadano",
            "status": "pending",
        },
    },
]

for c in clients:
    db.upsert_client(
        phone=c["phone"],
        name=c["name"],
        attorney=c["attorney"],
        case_type=c["case_type"],
        case_facts=c["case_facts"],
    )
    print(f"Seeded: {c['name']} ({c['phone']}) — {c['case_type']}")

print("\nDone. The agent now knows these clients.")
