"""Callbacks API — slots, book, cancel; 409 when slot is full."""

from __future__ import annotations

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request

from app.chaos import maybe_chaos
from app.models.schemas import CallbackCreate, CallbackOut, SlotOut
from app.store import Store, store

router = APIRouter(tags=["Callbacks"])


def get_store() -> Store:
    return store


@router.get("/slots", response_model=list[SlotOut])
def list_slots(
    request: Request,
    dept: str = Query(..., description="Department id"),
    date_: date = Query(..., alias="date", description="YYYY-MM-DD"),
    db: Store = Depends(get_store),
) -> list[SlotOut]:
    maybe_chaos(request)
    if not db.get_department(dept):
        raise HTTPException(status_code=404, detail={"error": "not_found", "resource": "department"})
    return [SlotOut.model_validate(s) for s in db.list_slots(dept, date_)]


@router.post("/callbacks", response_model=CallbackOut, status_code=201)
def create_callback(
    body: CallbackCreate,
    request: Request,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    db: Store = Depends(get_store),
) -> CallbackOut:
    maybe_chaos(request)
    key = idempotency_key or body.idempotency_key
    row, err = db.create_callback(body.model_dump(), idempotency_key=key)
    if err == "not_found":
        raise HTTPException(
            status_code=404,
            detail={"error": "not_found", "message": "Unknown department or slot"},
        )
    if err == "conflict":
        raise HTTPException(
            status_code=409,
            detail={
                "error": "slot_taken",
                "message": "Slot is full. Pick another slot.",
                "slot_id": body.slot_id,
            },
        )
    assert row is not None
    return CallbackOut.model_validate(row)


@router.delete("/callbacks/{callback_id}", response_model=CallbackOut)
def delete_callback(
    callback_id: str,
    request: Request,
    db: Store = Depends(get_store),
) -> CallbackOut:
    maybe_chaos(request)
    row = db.delete_callback(callback_id)
    if not row:
        raise HTTPException(status_code=404, detail={"error": "not_found", "resource": "callback"})
    return CallbackOut.model_validate(row)


@router.get("/callbacks/{callback_id}", response_model=CallbackOut)
def get_callback(
    callback_id: str,
    request: Request,
    db: Store = Depends(get_store),
) -> CallbackOut:
    maybe_chaos(request)
    row = db.get_callback(callback_id)
    if not row:
        raise HTTPException(status_code=404, detail={"error": "not_found", "resource": "callback"})
    return CallbackOut.model_validate(row)
