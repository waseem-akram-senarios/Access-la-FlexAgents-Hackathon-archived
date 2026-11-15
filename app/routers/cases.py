"""Cases API — create/lookup with custom case numbers + idempotency."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request

from app.chaos import maybe_chaos
from app.models.schemas import CaseCreate, CaseOut
from app.store import Store, store

router = APIRouter(prefix="/cases", tags=["Cases"])


def get_store() -> Store:
    return store


@router.post("", response_model=CaseOut, status_code=201)
def create_case(
    body: CaseCreate,
    request: Request,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    db: Store = Depends(get_store),
) -> CaseOut:
    maybe_chaos(request)
    if body.department_id and not db.get_department(body.department_id):
        raise HTTPException(
            status_code=400,
            detail={"error": "invalid_department", "department_id": body.department_id},
        )
    row = db.create_case(body.model_dump(), idempotency_key=idempotency_key)
    return CaseOut.model_validate(row)


@router.get("/{case_id}", response_model=CaseOut)
def get_case(
    case_id: str,
    request: Request,
    db: Store = Depends(get_store),
) -> CaseOut:
    maybe_chaos(request)
    row = db.get_case(case_id)
    if not row:
        raise HTTPException(status_code=404, detail={"error": "not_found", "resource": "case"})
    return CaseOut.model_validate(row)


@router.get("", response_model=list[CaseOut])
def list_cases(
    request: Request,
    phone: Optional[str] = Query(None, description="Filter by phone digits"),
    db: Store = Depends(get_store),
) -> list[CaseOut]:
    maybe_chaos(request)
    if not phone:
        raise HTTPException(
            status_code=400,
            detail={"error": "phone_required", "message": "Query param phone= is required"},
        )
    return [CaseOut.model_validate(c) for c in db.list_cases(phone=phone)]
