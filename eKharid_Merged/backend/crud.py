"""
crud.py
--------
Database CRUD operations for mandi system logic.
"""

from datetime import datetime, date as date_cls
try:
    from database import get_connection
except ImportError:
    from backend.database import get_connection


STAGE_ORDER = [
    "NOT_ARRIVED",
    "ARRIVED",
    "QUALITY",
    "WEIGHT",
    "STORAGE",
    "PAYMENT",
    "COMPLETED",
]

ACTIVE_STAGES = {"ARRIVED", "QUALITY", "WEIGHT", "STORAGE", "PAYMENT"}

STAGE_LABELS = {
    "NOT_ARRIVED": "Not Arrived",
    "ARRIVED": "Arrived",
    "QUALITY": "Quality",
    "WEIGHT": "Weight",
    "STORAGE": "Storage",
    "PAYMENT": "Payment",
    "COMPLETED": "Completed",
}

DEFAULT_TOTAL_CAPACITY = 1000


def get_farmer_by_name_mobile(name: str, mobile: str):
    conn = get_connection()
    row = conn.execute(
        """
        SELECT * FROM farmers
        WHERE LOWER(TRIM(name)) = LOWER(TRIM(?)) AND mobile = ?
        """,
        (name, mobile),
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def get_farmer_by_id(farmer_id: str):
    conn = get_connection()
    row = conn.execute("SELECT * FROM farmers WHERE farmer_id = ?", (farmer_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_officer_by_username(username: str):
    conn = get_connection()
    row = conn.execute("SELECT * FROM officers WHERE username = ?", (username,)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_storage(date: str):
    conn = get_connection()
    row = conn.execute("SELECT * FROM storage WHERE date = ?", (date,)).fetchone()

    if row is None:
        conn.execute(
            "INSERT INTO storage (date, total_capacity, reserved_capacity) VALUES (?, ?, 0)",
            (date, DEFAULT_TOTAL_CAPACITY),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM storage WHERE date = ?", (date,)).fetchone()

    conn.close()
    return dict(row)


def reserve_storage(date: str, weight: float):
    conn = get_connection()
    conn.execute(
        "UPDATE storage SET reserved_capacity = reserved_capacity + ? WHERE date = ?",
        (weight, date),
    )
    conn.commit()
    conn.close()


def has_enough_storage(date: str, requested_weight: float):
    storage = get_storage(date)
    available = storage["total_capacity"] - storage["reserved_capacity"]
    return requested_weight <= available, available


def generate_gate_pass_id():
    year = datetime.now().year
    conn = get_connection()
    count = conn.execute(
        "SELECT COUNT(*) as c FROM gate_passes WHERE gate_pass_id LIKE ?",
        (f"GP-{year}-%",),
    ).fetchone()["c"]
    conn.close()
    return f"GP-{year}-{(count + 1):04d}"


def farmer_has_active_pass_for_date(farmer_id: str, desired_date: str):
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM gate_passes WHERE farmer_id = ? AND desired_date = ? AND status = 'ACTIVE'",
        (farmer_id, desired_date),
    ).fetchone()
    conn.close()
    return row is not None


def create_gate_pass(farmer_id, crop_type, crop_name, mandi, vehicle_number, vehicle_type, desired_date, estimated_weight):
    gate_pass_id = generate_gate_pass_id()
    created_at = datetime.now().isoformat(timespec="seconds")

    conn = get_connection()
    conn.execute(
        """
        INSERT INTO gate_passes
            (gate_pass_id, farmer_id, crop_type, crop_name, mandi,
             vehicle_number, vehicle_type, desired_date, estimated_weight,
             status, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'ACTIVE', ?)
        """,
        (gate_pass_id, farmer_id, crop_type, crop_name, mandi,
         vehicle_number, vehicle_type, desired_date, estimated_weight,
         created_at),
    )

    next_position = conn.execute(
        "SELECT COUNT(*) as c FROM queue WHERE queue_date = ?", (desired_date,)
    ).fetchone()["c"] + 1

    conn.execute(
        "INSERT INTO queue (gate_pass_id, farmer_id, queue_date, position, stage) VALUES (?, ?, ?, ?, 'NOT_ARRIVED')",
        (gate_pass_id, farmer_id, desired_date, next_position),
    )

    conn.commit()
    conn.close()
    reserve_storage(desired_date, estimated_weight)
    return gate_pass_id


def get_gate_pass(gate_pass_id: str):
    conn = get_connection()
    row = conn.execute("SELECT * FROM gate_passes WHERE gate_pass_id = ?", (gate_pass_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_gate_passes_for_farmer(farmer_id: str):
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM gate_passes WHERE farmer_id = ? ORDER BY created_at DESC", (farmer_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_queue_entry(gate_pass_id: str):
    conn = get_connection()
    row = conn.execute("SELECT * FROM queue WHERE gate_pass_id = ?", (gate_pass_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_queue_by_date(queue_date: str):
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT queue.*, farmers.name as farmer_name, gate_passes.crop_name
        FROM queue
        JOIN farmers ON queue.farmer_id = farmers.farmer_id
        JOIN gate_passes ON queue.gate_pass_id = gate_passes.gate_pass_id
        WHERE queue.queue_date = ?
        ORDER BY queue.position ASC
        """,
        (queue_date,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def _current_counter_label(stage: str):
    if stage == "NOT_ARRIVED":
        return None
    if stage == "ARRIVED":
        return "Waiting for Quality"
    return STAGE_LABELS.get(stage, stage)


def get_queue_summary_for_farmer(gate_pass_id: str):
    entry = get_queue_entry(gate_pass_id)
    if entry is None:
        return None

    all_entries = get_queue_by_date(entry["queue_date"])
    stage = entry["stage"]

    active_entries = [
        e for e in all_entries
        if e["gate_pass_id"] != gate_pass_id and e["stage"] in ACTIVE_STAGES
    ]

    if stage == "NOT_ARRIVED":
        farmers_ahead = len(active_entries)
        farmers_waiting = 0
        queue_position = None
    elif stage == "COMPLETED":
        farmers_ahead = 0
        farmers_waiting = 0
        queue_position = None
    else:
        my_arrived_at = entry["arrived_at"] or ""
        farmers_ahead = sum(
            1 for e in active_entries
            if (e["arrived_at"] or "") < my_arrived_at
            or ((e["arrived_at"] or "") == my_arrived_at and e["id"] < entry["id"])
        )
        farmers_waiting = sum(1 for e in active_entries if e["stage"] == stage)
        queue_position = farmers_ahead + 1

    return {
        "gate_pass_id": gate_pass_id,
        "stage": stage,
        "queue_position": queue_position,
        "farmers_ahead": farmers_ahead,
        "farmers_waiting": farmers_waiting,
        "current_counter": _current_counter_label(stage),
        "arrived_at": entry["arrived_at"],
        "total_in_queue": len(all_entries),
    }


def move_to_next_stage(gate_pass_id: str, target_stage: str = None):
    entry = get_queue_entry(gate_pass_id)
    if entry is None:
        raise ValueError("Gate pass not found in queue.")

    current_index = STAGE_ORDER.index(entry["stage"])

    if target_stage:
        if target_stage not in STAGE_ORDER:
            raise ValueError("Unknown stage name.")
        if target_stage == "ARRIVED":
            raise ValueError("Arrival can only be recorded via QR code scan.")
        new_index = STAGE_ORDER.index(target_stage)
        if new_index != current_index + 1:
            raise ValueError("You can only move to the next sequential stage.")
    else:
        if current_index == len(STAGE_ORDER) - 1:
            raise ValueError("Pass has already reached COMPLETED stage.")
        new_index = current_index + 1

    new_stage = STAGE_ORDER[new_index]
    now = datetime.now().isoformat(timespec="seconds")

    conn = get_connection()
    if new_stage == "ARRIVED":
        conn.execute(
            "UPDATE queue SET stage = ?, arrived_at = ? WHERE gate_pass_id = ?",
            (new_stage, now, gate_pass_id),
        )
    elif new_stage == "COMPLETED":
        conn.execute(
            "UPDATE queue SET stage = ?, completed_at = ? WHERE gate_pass_id = ?",
            (new_stage, now, gate_pass_id),
        )
    else:
        conn.execute(
            "UPDATE queue SET stage = ? WHERE gate_pass_id = ?",
            (new_stage, gate_pass_id),
        )
    conn.commit()
    conn.close()

    return new_stage


def generate_transaction_id():
    return "TXN" + datetime.now().strftime("%Y%m%d%H%M%S")


def create_payment(gate_pass_id: str, farmer_id: str, amount: float):
    transaction_id = generate_transaction_id()
    payment_date = date_cls.today().isoformat()

    conn = get_connection()
    conn.execute(
        """
        INSERT INTO payments (gate_pass_id, farmer_id, amount, transaction_id, payment_date, status)
        VALUES (?, ?, ?, ?, ?, 'COMPLETED')
        """,
        (gate_pass_id, farmer_id, amount, transaction_id, payment_date),
    )
    conn.commit()
    conn.close()

    return {
        "gate_pass_id": gate_pass_id,
        "farmer_id": farmer_id,
        "amount": amount,
        "transaction_id": transaction_id,
        "payment_date": payment_date,
        "status": "COMPLETED",
    }


def get_payment_history(farmer_id: str):
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM payments WHERE farmer_id = ? ORDER BY payment_date DESC", (farmer_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_payment_for_gate_pass(gate_pass_id: str):
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM payments WHERE gate_pass_id = ? ORDER BY payment_date DESC LIMIT 1",
        (gate_pass_id,),
    ).fetchone()
    conn.close()
    return dict(row) if row else None