import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from config import DB_PATH

CRITERIA_SEED = [
    (1, "Technical Capability", "Architecture, integrations, scalability, technical fit", 30.0, 10.0, 1),
    (2, "Implementation Plan", "Timeline, milestones, staffing, risk plan", 20.0, 10.0, 1),
    (3, "Commercial Value", "Pricing clarity, total cost, assumptions", 20.0, 10.0, 1),
    (4, "Security & Compliance", "Controls, certifications, privacy, auditability", 20.0, 10.0, 1),
    (5, "Support & Experience", "Support model, similar projects, references", 10.0, 10.0, 1),
]

def get_connection():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db(reset=False):
    conn = get_connection()
    try:
        if reset:
            conn.executescript("DROP TABLE IF EXISTS supplier_results; DROP TABLE IF EXISTS rfp_runs; DROP TABLE IF EXISTS evaluation_criteria;")
        conn.execute("""CREATE TABLE IF NOT EXISTS evaluation_criteria (
            criterion_id INTEGER PRIMARY KEY, name TEXT NOT NULL, description TEXT NOT NULL,
            weight REAL NOT NULL, max_score REAL NOT NULL, is_active INTEGER NOT NULL CHECK(is_active IN (0,1)))""")
        conn.execute("""CREATE TABLE IF NOT EXISTS rfp_runs (
            rfp_run_id TEXT PRIMARY KEY, created_at TEXT NOT NULL, status TEXT NOT NULL,
            warnings_json TEXT NOT NULL DEFAULT '[]', criteria_snapshot_json TEXT NOT NULL DEFAULT '[]')""")
        conn.execute("""CREATE TABLE IF NOT EXISTS supplier_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT, rfp_run_id TEXT NOT NULL,
            supplier_name TEXT NOT NULL, submission_date TEXT NOT NULL, experience_rating REAL NOT NULL,
            absolute_score REAL NOT NULL, ppi REAL NOT NULL, final_rank INTEGER NOT NULL,
            result_json TEXT NOT NULL, FOREIGN KEY (rfp_run_id) REFERENCES rfp_runs(rfp_run_id))""")
        if conn.execute("SELECT COUNT(*) FROM evaluation_criteria").fetchone()[0] == 0:
            conn.executemany("INSERT INTO evaluation_criteria VALUES (?, ?, ?, ?, ?, ?)", CRITERIA_SEED)
        conn.commit()
    finally:
        conn.close()

def get_all_criteria():
    conn = get_connection()
    try:
        return [dict(r) for r in conn.execute("SELECT * FROM evaluation_criteria ORDER BY criterion_id").fetchall()]
    finally:
        conn.close()

def get_active_criteria():
    conn = get_connection()
    try:
        return [dict(r) for r in conn.execute("SELECT * FROM evaluation_criteria WHERE is_active=1 ORDER BY criterion_id").fetchall()]
    finally:
        conn.close()

def validate_active_weights(criteria):
    if not criteria:
        raise ValueError("No active evaluation criteria found.")
    total = sum(float(c["weight"]) for c in criteria)
    if abs(total - 100.0) > 1e-9:
        raise ValueError(f"Active criterion weights must total 100%; current total is {total:.4f}%.")

def update_criterion(criterion_id, weight, max_score, is_active):
    conn = get_connection()
    try:
        conn.execute("UPDATE evaluation_criteria SET weight=?, max_score=?, is_active=? WHERE criterion_id=?",
                     (float(weight), float(max_score), int(bool(is_active)), int(criterion_id)))
        conn.commit()
    finally:
        conn.close()

def create_run(rfp_run_id, criteria_snapshot):
    conn = get_connection()
    try:
        conn.execute("INSERT INTO rfp_runs VALUES (?, ?, ?, ?, ?)",
                     (rfp_run_id, datetime.now(timezone.utc).isoformat(), "running", "[]", json.dumps(criteria_snapshot)))
        conn.commit()
    finally:
        conn.close()

def complete_run(rfp_run_id, warnings):
    conn = get_connection()
    try:
        conn.execute("UPDATE rfp_runs SET status=?, warnings_json=? WHERE rfp_run_id=?",
                     ("completed", json.dumps(warnings, ensure_ascii=False), rfp_run_id))
        conn.commit()
    finally:
        conn.close()

def fail_run(rfp_run_id, warnings):
    conn = get_connection()
    try:
        conn.execute("UPDATE rfp_runs SET status=?, warnings_json=? WHERE rfp_run_id=?",
                     ("failed", json.dumps(warnings, ensure_ascii=False), rfp_run_id))
        conn.commit()
    finally:
        conn.close()

def persist_supplier_results(rfp_run_id, results):
    conn = get_connection()
    try:
        for result in results:
            conn.execute("""INSERT INTO supplier_results
                (rfp_run_id,supplier_name,submission_date,experience_rating,absolute_score,ppi,final_rank,result_json)
                VALUES (?,?,?,?,?,?,?,?)""",
                (rfp_run_id, result["supplier_name"], result["submission_date"], result["experience_rating"],
                 result["absolute_score"], result["ppi"], result["final_rank"], json.dumps(result, ensure_ascii=False)))
        conn.commit()
    finally:
        conn.close()

def get_run(rfp_run_id):
    conn = get_connection()
    try:
        row = conn.execute("SELECT * FROM rfp_runs WHERE rfp_run_id=?", (rfp_run_id,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()

def get_run_results(rfp_run_id=None):
    conn = get_connection()
    try:
        if rfp_run_id:
            rows = conn.execute("SELECT * FROM supplier_results WHERE rfp_run_id=? ORDER BY final_rank", (rfp_run_id,)).fetchall()
        else:
            rows = conn.execute("SELECT * FROM supplier_results ORDER BY id DESC").fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()
