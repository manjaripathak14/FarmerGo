"""
main.py
--------
This is the entry point of our FastAPI backend.

It does two things:
  1. Defines all the REST API endpoints (under /api/...) that the
     frontend JavaScript files talk to.
  2. Serves the simple HTML/CSS/JS frontend so the whole project can
     be run with a single command.

Run this project with:
    uvicorn main:app --reload

Then open:
    http://127.0.0.1:8000
"""

import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

import crud
from database import init_db
from qr_generator import generate_qr_base64
from schemas import (
    FarmerLoginRequest,
    OfficerLoginRequest,
    GatePassCreateRequest,
    ScanRequest,
    StageUpdateRequest,
    PaymentRequest,
)

app = FastAPI(title="SIH Mandi Management System")

# Allow the frontend (even if opened from a different port/file) to
# call these APIs during development/demo.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Make sure the database and its tables exist before we start.
init_db()

# Path to the frontend folder (../frontend relative to this file).
FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend")


# =====================================================================
# FARMER AUTHENTICATION
# =====================================================================

@app.post("/api/farmer/login")
def farmer_login(payload: FarmerLoginRequest):
    """
    A farmer's record is assumed to already exist in the government
    database (simulated here by our seeded `farmers` table). The
    farmer only needs to confirm who they are with name + mobile.
    """
    farmer = crud.get_farmer_by_name_mobile(payload.name, payload.mobile)
    if farmer is None:
        raise HTTPException(
            status_code=404,
            detail="Farmer not found. Please check your name and mobile number.",
        )
    return {"success": True, "farmer": farmer}


@app.get("/api/farmer/{farmer_id}")
def get_farmer_profile(farmer_id: str):
    farmer = crud.get_farmer_by_id(farmer_id)
    if farmer is None:
        raise HTTPException(status_code=404, detail="Farmer not found.")
    return farmer


@app.get("/api/farmer/passes/{farmer_id}")
def get_farmer_passes(farmer_id: str):
    farmer = crud.get_farmer_by_id(farmer_id)
    if farmer is None:
        raise HTTPException(status_code=404, detail="Farmer not found.")
    return crud.get_gate_passes_for_farmer(farmer_id)


# =====================================================================
# OFFICER AUTHENTICATION
# =====================================================================

@app.post("/api/officer/login")
def officer_login(payload: OfficerLoginRequest):
    officer = crud.get_officer_by_username(payload.username)

    # NOTE (prototype simplification):
    # We are comparing the password as plain text here purely because
    # this is a hackathon prototype. A real production system must
    # NEVER store or compare plain-text passwords — it should use a
    # proper hashing algorithm (e.g. bcrypt) and a secure session/JWT
    # based authentication system instead.
    if officer is None or officer["password"] != payload.password:
        raise HTTPException(status_code=401, detail="Invalid username or password.")

    officer_safe = {k: v for k, v in officer.items() if k != "password"}
    return {"success": True, "officer": officer_safe}


# =====================================================================
# STORAGE CAPACITY
# =====================================================================

@app.get("/api/storage/{date}")
def get_storage_for_date(date: str):
    storage = crud.get_storage(date)
    available = storage["total_capacity"] - storage["reserved_capacity"]
    storage["available_capacity"] = available
    return storage


# =====================================================================
# GATE PASS
# =====================================================================

@app.post("/api/gate-pass")
def create_gate_pass(payload: GatePassCreateRequest):
    # Make sure the farmer actually exists.
    farmer = crud.get_farmer_by_id(payload.farmer_id)
    if farmer is None:
        raise HTTPException(status_code=404, detail="Farmer not found.")

    # Prevent a farmer from booking two gate passes for the same date.
    if crud.farmer_has_active_pass_for_date(payload.farmer_id, payload.desired_date):
        raise HTTPException(
            status_code=400,
            detail="You already have a gate pass for this date.",
        )

    # Check storage capacity before creating anything.
    is_available, available = crud.has_enough_storage(
        payload.desired_date, payload.estimated_weight
    )
    if not is_available:
        raise HTTPException(
            status_code=400,
            detail=(
                "Storage capacity is not available for the selected date. "
                f"Only {available} quintals are available. "
                "Please select another date or reduce the estimated quantity."
            ),
        )

    gate_pass_id = crud.create_gate_pass(
        farmer_id=payload.farmer_id,
        crop_type=payload.crop_type,
        crop_name=payload.crop_name,
        mandi=payload.mandi,
        vehicle_number=payload.vehicle_number,
        vehicle_type=payload.vehicle_type,
        desired_date=payload.desired_date,
        estimated_weight=payload.estimated_weight,
    )

    return {
        "success": True,
        "message": "Gate pass generated successfully.",
        "gate_pass_id": gate_pass_id,
    }


@app.get("/api/gate-pass/{gate_pass_id}")
def get_gate_pass(gate_pass_id: str):
    gate_pass = crud.get_gate_pass(gate_pass_id)
    if gate_pass is None:
        raise HTTPException(status_code=404, detail="Invalid or expired gate pass.")
    return gate_pass


@app.get("/api/gate-pass/{gate_pass_id}/qr")
def get_gate_pass_qr(gate_pass_id: str):
    gate_pass = crud.get_gate_pass(gate_pass_id)
    if gate_pass is None:
        raise HTTPException(status_code=404, detail="Invalid or expired gate pass.")

    qr_image = generate_qr_base64(gate_pass_id)
    return {"gate_pass_id": gate_pass_id, "qr_code": qr_image}


# =====================================================================
# QR SCANNING
# =====================================================================

@app.post("/api/scan")
def scan_qr(payload: ScanRequest):
    """
    Called when an officer/operator scans a farmer's QR code at any
    counter. Moves the gate pass forward exactly one stage.
    """
    gate_pass = crud.get_gate_pass(payload.gate_pass_id)
    if gate_pass is None:
        raise HTTPException(status_code=404, detail="Invalid or expired gate pass.")

    try:
        new_stage = crud.move_to_next_stage(payload.gate_pass_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {
        "success": True,
        "gate_pass_id": payload.gate_pass_id,
        "new_stage": new_stage,
    }


# =====================================================================
# STAGE UPDATE (used by the officer dashboard buttons)
# =====================================================================

@app.post("/api/stage/update")
def update_stage(payload: StageUpdateRequest):
    try:
        new_stage = crud.move_to_next_stage(payload.gate_pass_id, payload.new_stage)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {"success": True, "gate_pass_id": payload.gate_pass_id, "new_stage": new_stage}


# =====================================================================
# QUEUE
# =====================================================================

@app.get("/api/queue/farmer/{farmer_id}")
def get_farmer_queue(farmer_id: str):
    """
    Returns the "Live Queue" view for a farmer's most recent active
    gate pass.
    """
    passes = crud.get_gate_passes_for_farmer(farmer_id)
    if not passes:
        raise HTTPException(status_code=404, detail="No gate pass found for this farmer.")

    latest_pass = passes[0]
    summary = crud.get_queue_summary_for_farmer(latest_pass["gate_pass_id"])
    if summary is None:
        raise HTTPException(status_code=404, detail="Queue entry not found.")

    summary["crop_name"] = latest_pass["crop_name"]
    return summary


@app.get("/api/queue/date/{date}")
def get_queue_for_date(date: str):
    return crud.get_queue_by_date(date)


# =====================================================================
# OFFICER VIEWS
# =====================================================================

@app.get("/api/officer/farmers/{date}")
def get_officer_farmer_grid(date: str):
    """Returns every farmer scheduled for a date, for the officer's grid view."""
    return crud.get_queue_by_date(date)


@app.get("/api/officer/farmer/{farmer_id}")
def get_officer_farmer_details(farmer_id: str):
    farmer = crud.get_farmer_by_id(farmer_id)
    if farmer is None:
        raise HTTPException(status_code=404, detail="Farmer not found.")

    passes = crud.get_gate_passes_for_farmer(farmer_id)
    if not passes:
        raise HTTPException(status_code=404, detail="This farmer has no gate pass yet.")

    latest_pass = passes[0]
    queue_entry = crud.get_queue_entry(latest_pass["gate_pass_id"])
    queue_info = crud.get_queue_summary_for_farmer(latest_pass["gate_pass_id"])

    return {
        "farmer": farmer,
        "gate_pass": latest_pass,
        "stage": queue_entry["stage"] if queue_entry else None,
        "arrived_at": queue_entry["arrived_at"] if queue_entry else None,
        "queue_info": queue_info,
    }


# =====================================================================
# PAYMENT
# =====================================================================

@app.post("/api/payment")
def make_payment(payload: PaymentRequest):
    """
    Simulates a payment for a completed gate pass. In a real system
    this would connect to a government/bank payment gateway — for
    this prototype we simply record the payment as completed.
    """
    gate_pass = crud.get_gate_pass(payload.gate_pass_id)
    if gate_pass is None:
        raise HTTPException(status_code=404, detail="Invalid or expired gate pass.")

    payment = crud.create_payment(payload.gate_pass_id, gate_pass["farmer_id"], payload.amount)

    # Move the queue stage forward to PAYMENT (and then COMPLETED),
    # matching the flow described in the project spec.
    try:
        crud.move_to_next_stage(payload.gate_pass_id, "PAYMENT")
    except ValueError:
        pass  # already at/after PAYMENT stage, nothing to do

    return {"success": True, "payment": payment}


@app.get("/api/payment/history/{farmer_id}")
def payment_history(farmer_id: str):
    return crud.get_payment_history(farmer_id)


# =====================================================================
# FRONTEND (serves the simple HTML/CSS/JS files)
# =====================================================================

# Serve css/ and js/ as static asset folders.
app.mount("/css", StaticFiles(directory=os.path.join(FRONTEND_DIR, "css")), name="css")
app.mount("/js", StaticFiles(directory=os.path.join(FRONTEND_DIR, "js")), name="js")
app.mount("/images", StaticFiles(directory=FRONTEND_DIR), name="images")


@app.get("/")
def serve_index():
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))


@app.get("/{page_name}.html")
def serve_html_page(page_name: str):
    """
    Generic route so any frontend page (farmer.html, officer.html,
    gate-pass.html, etc.) can be opened directly, e.g.
    http://127.0.0.1:8000/farmer.html
    """
    file_path = os.path.join(FRONTEND_DIR, f"{page_name}.html")
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Page not found.")
    return FileResponse(file_path)
