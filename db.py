
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "rfp_evaluation.db"

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    conn = get_conn()
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS evaluation_criteria (
        criterion_id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        description TEXT NOT NULL,
        weight REAL NOT NULL CHECK(weight >= 0),
        max_score REAL NOT NULL CHECK(max_score > 0),
        is_active INTEGER NOT NULL DEFAULT 1
    );

    CREATE TABLE IF NOT EXISTS rfp_runs (
        rfp_run_id TEXT PRIMARY KEY,
        created_at TEXT NOT NULL,
        status TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS supplier_results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        rfp_run_id TEXT NOT NULL,
        supplier_name TEXT NOT NULL,
        submission_date TEXT NOT NULL,
        experience_rating REAL NOT NULL,
        absolute_score REAL NOT NULL,
        ppi REAL NOT NULL,
        final_rank INTEGER,
        result_json TEXT NOT NULL,
        FOREIGN KEY(rfp_run_id) REFERENCES rfp_runs(rfp_run_id)
    );

    CREATE INDEX IF NOT EXISTS idx_supplier_results_run
    ON supplier_results(rfp_run_id);
    """)
    conn.commit()
    conn.close()

def seed_criteria():
    init_db()
    conn = get_conn()
    count = conn.execute("SELECT COUNT(*) FROM evaluation_criteria").fetchone()[0]
    if count == 0:
        rows = [
            (1, "Technical Capability",
             "Architecture, integrations, scalability, technical fit", 30, 10, 1),
            (2, "Implementation Plan",
             "Timeline, milestones, staffing, risk plan", 20, 10, 1),
            (3, "Commercial Value",
             "Pricing clarity, total cost, assumptions", 20, 10, 1),
            (4, "Security & Compliance",
             "Controls, certifications, privacy, auditability", 20, 10, 1),
            (5, "Support & Experience",
             "Support model, similar projects, references", 10, 10, 1),
        ]
        conn.executemany("""
            INSERT INTO evaluation_criteria
            (criterion_id, name, description, weight, max_score, is_active)
            VALUES (?, ?, ?, ?, ?, ?)
        """, rows)
        conn.commit()
    conn.close()

def get_active_criteria():
    conn = get_conn()
    rows = conn.execute("""
        SELECT criterion_id, name, description, weight, max_score, is_active
        FROM evaluation_criteria
        WHERE is_active = 1
        ORDER BY criterion_id
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def weights_total(criteria):
    return round(sum(float(c["weight"]) for c in criteria), 6)

def create_run(run_id):
    conn = get_conn()
    conn.execute(
        "INSERT INTO rfp_runs(rfp_run_id, created_at, status) VALUES (?, ?, ?)",
        (run_id, datetime.now(timezone.utc).isoformat(), "RUNNING"),
    )
    conn.commit()
    conn.close()

def save_results(run_id, results, status="COMPLETED"):
    conn = get_conn()
    for r in results:
        conn.execute("""
            INSERT INTO supplier_results
            (rfp_run_id, supplier_name, submission_date, experience_rating,
             absolute_score, ppi, final_rank, result_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            run_id, r["supplier_name"], r["submission_date"],
            r["experience_rating"], r["absolute_score"], r["ppi"],
            r["final_rank"], json.dumps(r, ensure_ascii=False)
        ))
    conn.execute(
        "UPDATE rfp_runs SET status=? WHERE rfp_run_id=?",
        (status, run_id)
    )
    conn.commit()
    conn.close()

def save_failed_run(run_id):
    conn = get_conn()
    conn.execute(
        "UPDATE rfp_runs SET status=? WHERE rfp_run_id=?",
        ("FAILED", run_id)
    )
    conn.commit()
    conn.close()

def get_run(run_id):
    conn = get_conn()
    run = conn.execute(
        "SELECT * FROM rfp_runs WHERE rfp_run_id=?", (run_id,)
    ).fetchone()
    rows = conn.execute("""
        SELECT * FROM supplier_results
        WHERE rfp_run_id=? ORDER BY final_rank
    """, (run_id,)).fetchall()
    conn.close()
    return (dict(run) if run else None), [dict(r) for r in rows]
