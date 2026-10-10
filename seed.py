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
        "age": 34,
        "attorney": "Lic. García",
        "case_type": "asylum",
        "benefit_sought": "Asilo político",
        "case_facts": {
            "receipt_number": "IOE1234567890",
            "filing_date": "2025-03-15",
            "status": "pending",
            "next_hearing": "2026-11-20",
            "country": "Honduras",
            "language": "es",
        },
    },
    {
        "phone": "+15550002222",
        "name": "Carlos Ramírez",
        "age": 41,
        "attorney": "Lic. García",
        "case_type": "I-130",
        "benefit_sought": "Petición familiar para esposa",
        "case_facts": {
            "receipt_number": "IOE0987654321",
            "filing_date": "2025-06-01",
            "status": "pending",
            "beneficiary": "esposa",
            "petitioner_status": "ciudadano",
            "country": "El Salvador",
            "language": "es",
        },
    },
]

for c in clients:
    db.upsert_client(
        phone=c["phone"],
        name=c["name"],
        age=c["age"],
        attorney=c["attorney"],
        case_type=c["case_type"],
        benefit_sought=c["benefit_sought"],
        case_facts=c["case_facts"],
    )
    print(f"Seeded: {c['name']}, {c['age']} — {c['benefit_sought']} ({c['phone']})")

print("\nDone. The agent now knows these clients.")
