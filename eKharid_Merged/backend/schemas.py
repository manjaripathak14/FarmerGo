"""
schemas.py
-----------
Pydantic schemas for payload validation.
"""

from pydantic import BaseModel, Field
from typing import Optional


class FarmerLoginRequest(BaseModel):
    name: str = Field(..., example="Rahul Kumar")
    mobile: str = Field(..., min_length=10, max_length=10, example="9876543210")


class OfficerLoginRequest(BaseModel):
    username: str = Field(..., example="officer1")
    password: str = Field(..., example="officer123")


class GatePassCreateRequest(BaseModel):
    farmer_id: str = Field(..., example="FARM1001")
    crop_type: str = Field(..., example="Cereal")
    crop_name: str = Field(..., example="Wheat")
    mandi: str = Field(..., example="Faridabad Mandi")
    vehicle_number: str = Field(..., example="HR-51-AB-1234")
    vehicle_type: str = Field(..., example="Tractor")
    desired_date: str = Field(..., example="2026-09-16")
    estimated_weight: float = Field(..., gt=0, example=25.5)


class ScanRequest(BaseModel):
    gate_pass_id: str = Field(..., example="GP-2026-0001")


class StageUpdateRequest(BaseModel):
    gate_pass_id: str = Field(..., example="GP-2026-0001")
    new_stage: Optional[str] = Field(None, example="QUALITY")


class PaymentRequest(BaseModel):
    gate_pass_id: str = Field(..., example="GP-2026-0001")
    amount: float = Field(..., gt=0, example=12500.00)