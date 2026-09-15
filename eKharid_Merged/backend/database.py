"""
database.py
------------
Handles SQLite database connections and table initialization.
"""

import sqlite3
import os

DB_FILE = os.path.join(os.path.dirname(__file__), "mandi.db")


def get_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS farmers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            farmer_id TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            mobile TEXT NOT NULL,
            father_name TEXT,
            village TEXT,
            district TEXT,
            state TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS officers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            username TEXT UNIQUE NOT NULL,
            mobile TEXT,
            password TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS gate_passes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            gate_pass_id TEXT UNIQUE NOT NULL,
            farmer_id TEXT NOT NULL,
            crop_type TEXT NOT NULL,
            crop_name TEXT NOT NULL,
            mandi TEXT NOT NULL,
            vehicle_number TEXT NOT NULL,
            vehicle_type TEXT NOT NULL,
            desired_date TEXT NOT NULL,
            estimated_weight REAL NOT NULL,
            status TEXT NOT NULL DEFAULT 'ACTIVE',
            created_at TEXT NOT NULL,
            FOREIGN KEY (farmer_id) REFERENCES farmers (farmer_id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS queue (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            gate_pass_id TEXT UNIQUE NOT NULL,
            farmer_id TEXT NOT NULL,
            queue_date TEXT NOT NULL,
            position INTEGER NOT NULL,
            stage TEXT NOT NULL DEFAULT 'NOT_ARRIVED',
            arrived_at TEXT,
            completed_at TEXT,
            FOREIGN KEY (gate_pass_id) REFERENCES gate_passes (gate_pass_id),
            FOREIGN KEY (farmer_id) REFERENCES farmers (farmer_id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            gate_pass_id TEXT NOT NULL,
            farmer_id TEXT NOT NULL,
            amount REAL NOT NULL,
            transaction_id TEXT UNIQUE NOT NULL,
            payment_date TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'COMPLETED',
            FOREIGN KEY (gate_pass_id) REFERENCES gate_passes (gate_pass_id),
            FOREIGN KEY (farmer_id) REFERENCES farmers (farmer_id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS storage (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT UNIQUE NOT NULL,
            total_capacity REAL NOT NULL,
            reserved_capacity REAL NOT NULL DEFAULT 0
        )
    """)

    conn.commit()
    _migrate_existing_queue_table(conn, cursor)
    conn.commit()
    conn.close()
    print("Database initialized successfully.")


def _migrate_existing_queue_table(conn, cursor):
    existing_columns = {row["name"] for row in cursor.execute("PRAGMA table_info(queue)").fetchall()}

    if "arrived_at" not in existing_columns:
        cursor.execute("ALTER TABLE queue ADD COLUMN arrived_at TEXT")

    if "completed_at" not in existing_columns:
        cursor.execute("ALTER TABLE queue ADD COLUMN completed_at TEXT")

    cursor.execute(
        "UPDATE queue SET stage = 'NOT_ARRIVED' WHERE stage = 'GATE_PASS_GENERATED'"
    )


if __name__ == "__main__":
    init_db()