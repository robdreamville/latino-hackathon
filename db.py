# db.py — SQLite persistence for Centinela
# Two tables: clients (profile + case facts as JSON), messages (full history)
# Pattern: read once per session, write-through on every message.

import json
import sqlite3
from datetime import datetime

DB_PATH = "centinela.db"


def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS clients (
            phone TEXT PRIMARY KEY,
            name TEXT,
            age INTEGER,
            attorney TEXT,
            case_type TEXT,
            benefit_sought TEXT,
            language TEXT DEFAULT 'es',
            case_facts TEXT DEFAULT '{}',
            created_at TEXT
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            phone TEXT,
            role TEXT,
            text TEXT,
            timestamp TEXT,
            FOREIGN KEY (phone) REFERENCES clients (phone)
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS review_queue (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            phone TEXT,
            question TEXT,
            context TEXT,
            status TEXT DEFAULT 'pending',
            created_at TEXT
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            phone TEXT,
            doc_type TEXT,
            file_path TEXT,
            status TEXT DEFAULT 'received',
            created_at TEXT
        )
    """)
    conn.commit()
    conn.close()


def get_client(phone):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM clients WHERE phone = ?", (phone,))
    row = c.fetchone()
    conn.close()
    if row:
        d = dict(row)
        d["case_facts"] = json.loads(d["case_facts"] or "{}")
        return d
    return None


def upsert_client(phone, name=None, age=None, attorney=None, case_type=None,
                benefit_sought=None, case_facts=None):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    existing = get_client(phone)
    facts = json.dumps(case_facts or (existing["case_facts"] if existing else {}))
    c.execute("""
        INSERT INTO clients (phone, name, age, attorney, case_type, benefit_sought, case_facts, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(phone) DO UPDATE SET
            name=COALESCE(excluded.name, clients.name),
            age=COALESCE(excluded.age, clients.age),
            attorney=COALESCE(excluded.attorney, clients.attorney),
            case_type=COALESCE(excluded.case_type, clients.case_type),
            benefit_sought=COALESCE(excluded.benefit_sought, clients.benefit_sought),
            case_facts=excluded.case_facts
    """, (phone, name, age, attorney, case_type, benefit_sought, facts, datetime.now().isoformat()))
    conn.commit()
    conn.close()


def save_message(phone, role, text):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "INSERT INTO messages (phone, role, text, timestamp) VALUES (?, ?, ?, ?)",
        (phone, role, text, datetime.now().isoformat()),
    )
    conn.commit()
    conn.close()


def get_recent_messages(phone, limit=10):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute(
        "SELECT role, text FROM messages WHERE phone = ? ORDER BY id DESC LIMIT ?",
        (phone, limit),
    )
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return list(reversed(rows))


def flag_for_review(phone, question, context=""):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "INSERT INTO review_queue (phone, question, context, created_at) VALUES (?, ?, ?, ?)",
        (phone, question, context, datetime.now().isoformat()),
    )
    conn.commit()
    conn.close()


def get_review_queue():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("""
        SELECT q.*, c.name as client_name FROM review_queue q
        LEFT JOIN clients c ON q.phone = c.phone
        WHERE q.status = 'pending' ORDER BY q.created_at DESC
    """)
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows


def get_all_clients():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT phone, name, age, attorney, case_type, benefit_sought, language, case_facts FROM clients")
    rows = []
    for r in c.fetchall():
        d = dict(r)
        d["case_facts"] = json.loads(d["case_facts"] or "{}")
        rows.append(d)
    conn.close()
    return rows


def get_all_documents():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("""
        SELECT d.*, c.name as client_name FROM documents d
        LEFT JOIN clients c ON d.phone = c.phone
        ORDER BY d.created_at DESC
    """)
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows
