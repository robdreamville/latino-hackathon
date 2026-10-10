"""Seed demo clients matching Carpeta Base44 UI. Run once: python seed_demo.py"""
from db import init_db, upsert_client

init_db()

# Matches Base44 demo: Lucía LUCIA7, 7/12 docs, Active
upsert_client(
    phone="+15551112222",
    name="Lucía Fernández",
    age=29,
    attorney="Lic. García",
    case_type="work_permit",
    benefit_sought="Permiso de trabajo",
    case_facts={
        "invite_code": "LUCIA7",
        "docs_received": 7,
        "docs_total": 12,
        "status": "active",
        "form": "I-765",
        "basis": "pending_asylum",
    },
)

# Matches Base44 demo: María MARIA1, 2/12 docs, Active
upsert_client(
    phone="+15551113333",
    name="María Torres",
    age=34,
    attorney="Lic. García",
    case_type="work_permit",
    benefit_sought="Permiso de trabajo (asilo pendiente)",
    case_facts={
        "invite_code": "MARIA1",
        "docs_received": 2,
        "docs_total": 12,
        "status": "active",
        "form": "I-765",
        "category": "c(8)",
        "basis": "pending_asylum",
    },
)

# Matches Base44 demo: José JOSE42, 0/12 docs, Delivered
upsert_client(
    phone="+15551114444",
    name="José Martínez",
    age=45,
    attorney="Lic. García",
    case_type="work_permit",
    benefit_sought="Permiso de trabajo",
    case_facts={
        "invite_code": "JOSE42",
        "docs_received": 0,
        "docs_total": 12,
        "status": "delivered",
        "form": "I-765",
    },
)

print("Demo clients seeded: Lucía, María, José")
