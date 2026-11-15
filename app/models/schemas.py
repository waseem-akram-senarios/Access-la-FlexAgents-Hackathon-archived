"""Pydantic schemas for Spectac Track B APIs."""

from __future__ import annotations

from datetime import date, datetime, time
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field, field_validator

from app.phoneutil import normalize_phone


class HoursBlock(BaseModel):
    day: str  # mon..sun
    open: Optional[str] = None  # HH:MM
    close: Optional[str] = None
    closed: bool = False


class HolidayOverride(BaseModel):
    date: str  # YYYY-MM-DD
    closed: bool = True
    open: Optional[str] = None
    close: Optional[str] = None
    note: Optional[str] = None


class DepartmentOut(BaseModel):
    id: str
    name: str
    phone: str
    tdd: Optional[str] = None
    email: Optional[str] = None
    menu_option: Optional[str] = None
    source: Optional[str] = None
    needs: list[str]
    description: str
    hours: list[HoursBlock]
    holiday_overrides: list[HolidayOverride] = Field(default_factory=list)
    open_now: bool
    closed_today: bool
    timezone: str = "America/Los_Angeles"


class CaseCreate(BaseModel):
    """log_case payload: category, when, route/vehicle, description, callback phone."""

    phone: str = Field(..., min_length=7, max_length=32, description="Callback number")
    topic: str = Field(..., min_length=1, max_length=200)
    summary: str = Field(..., min_length=1, max_length=4000, description="Description")
    category: Optional[Literal["complaint", "commendation", "lost_item", "other"]] = None
    incident_at: Optional[datetime] = Field(
        None, description="Date/time of the incident (ISO-8601)"
    )
    route: Optional[str] = Field(None, max_length=64, description="Route if known")
    vehicle: Optional[str] = Field(None, max_length=64, description="Vehicle if known")
    department_id: Optional[str] = None
    rider_name: Optional[str] = None
    priority: Literal["low", "normal", "high"] = "normal"
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("phone")
    @classmethod
    def normalize_phone_field(cls, v: str) -> str:
        return normalize_phone(v)


class CaseOut(BaseModel):
    id: str
    case_number: str
    phone: str
    topic: str
    summary: str
    category: Optional[str] = None
    incident_at: Optional[datetime] = None
    route: Optional[str] = None
    vehicle: Optional[str] = None
    department_id: Optional[str] = None
    rider_name: Optional[str] = None
    priority: str
    status: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class SlotOut(BaseModel):
    id: str
    department_id: str
    date: date
    start: time
    end: time
    capacity: int
    booked: int
    available: bool


class CallbackCreate(BaseModel):
    department_id: str
    slot_id: str
    phone: str = Field(..., min_length=7, max_length=32)
    name: Optional[str] = None
    reason: Optional[str] = None
    idempotency_key: Optional[str] = None

    @field_validator("phone")
    @classmethod
    def normalize_phone_field(cls, v: str) -> str:
        return normalize_phone(v)


class CallbackOut(BaseModel):
    id: str
    department_id: str
    slot_id: str
    phone: str
    name: Optional[str] = None
    reason: Optional[str] = None
    status: Literal["booked", "cancelled"]
    created_at: datetime


class MessageCreate(BaseModel):
    to: str = Field(..., min_length=7, max_length=32)
    body: str = Field(..., min_length=1, max_length=1600)
    from_: Optional[str] = Field(default="ACCESS-LA", alias="from")
    case_id: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = {"populate_by_name": True}

    @field_validator("to")
    @classmethod
    def normalize_to(cls, v: str) -> str:
        return normalize_phone(v)


class MessageOut(BaseModel):
    id: str
    to: str
    from_: str = Field(alias="from")
    body: str
    case_id: Optional[str] = None
    status: str
    created_at: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = {"populate_by_name": True}
