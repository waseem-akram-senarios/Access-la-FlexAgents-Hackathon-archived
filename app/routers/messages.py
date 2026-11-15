"""Message Outbox — fake SMS store for judges."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from app.chaos import maybe_chaos
from app.models.schemas import MessageCreate, MessageOut
from app.store import Store, store

router = APIRouter(prefix="/messages", tags=["Message Outbox"])


def get_store() -> Store:
    return store


@router.post("", response_model=MessageOut, status_code=201)
def create_message(
    body: MessageCreate,
    request: Request,
    db: Store = Depends(get_store),
) -> MessageOut:
    maybe_chaos(request)
    payload = body.model_dump(by_alias=True)
    row = db.create_message(payload)
    return MessageOut.model_validate(row)


@router.get("", response_model=list[MessageOut])
def list_messages(
    request: Request,
    to: Optional[str] = Query(None, description="Filter by destination phone digits"),
    db: Store = Depends(get_store),
) -> list[MessageOut]:
    maybe_chaos(request)
    if not to:
        raise HTTPException(
            status_code=400,
            detail={"error": "to_required", "message": "Query param to= is required"},
        )
    return [MessageOut.model_validate(m) for m in db.list_messages(to=to)]
