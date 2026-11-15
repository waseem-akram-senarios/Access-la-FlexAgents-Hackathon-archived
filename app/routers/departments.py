"""Directory API — departments with hours, holidays, open_now."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from app.chaos import maybe_chaos
from app.models.schemas import DepartmentOut
from app.store import Store, store

router = APIRouter(prefix="/departments", tags=["Directory"])


def get_store() -> Store:
    return store


@router.get("", response_model=list[DepartmentOut])
def list_departments(
    request: Request,
    need: Optional[str] = Query(None, description="Filter by need keyword (e.g. lost, fare, eligibility)"),
    db: Store = Depends(get_store),
) -> list[DepartmentOut]:
    maybe_chaos(request)
    return [DepartmentOut.model_validate(d) for d in db.list_departments(need=need)]


@router.get("/{department_id}", response_model=DepartmentOut)
def get_department(
    department_id: str,
    request: Request,
    db: Store = Depends(get_store),
) -> DepartmentOut:
    maybe_chaos(request)
    row = db.get_department(department_id)
    if not row:
        raise HTTPException(status_code=404, detail={"error": "not_found", "resource": "department"})
    return DepartmentOut.model_validate(row)
