"""
seed_data.py
-------------
Fills database with initial demo data.
"""

try:
    from database import get_connection, init_db
except ImportError:
    from backend.database import get_connection, init_db


def seed():
    init_db()
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM payments")
    cursor.execute("DELETE FROM queue")
    cursor.execute("DELETE FROM gate_passes")
    cursor.execute("DELETE FROM storage")
    cursor.execute("DELETE FROM farmers")
    cursor.execute("DELETE FROM officers")

    farmers = [
        ("FARM1001", "Rahul Kumar", "9876543210", "Ramesh Kumar", "Rampur", "Karnal", "Haryana"),
        ("FARM1002", "Amit Sharma", "9876543211", "Suresh Sharma", "Sonipat", "Sonipat", "Haryana"),
        ("FARM1003", "Suresh Kumar", "9876543212", "Mohan Lal", "Panipat", "Panipat", "Haryana"),
        ("FARM1004", "Mohan Singh", "9876543213", "Gurdev Singh", "Karnal", "Karnal", "Haryana"),
        ("FARM1005", "Ramesh Kumar", "9876543214", "Hari Ram", "Kaithal", "Kaithal", "Haryana"),
    ]
    cursor.executemany(
        """
        INSERT INTO farmers (farmer_id, name, mobile, father_name, village, district, state)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        farmers,
    )

    cursor.execute(
        """
        INSERT INTO officers (name, username, mobile, password)
        VALUES (?, ?, ?, ?)
        """,
        ("Officer Priya Verma", "officer1", "9998887770", "officer123"),
    )

    storage_rows = [
        ("2026-09-15", 1000, 300),
        ("2026-09-16", 1000, 0),
        ("2026-09-17", 1000, 950),
    ]
    cursor.executemany(
        "INSERT INTO storage (date, total_capacity, reserved_capacity) VALUES (?, ?, ?)",
        storage_rows,
    )

    conn.commit()
    conn.close()
    print("Demo data seeded successfully.")


if __name__ == "__main__":
    seed()