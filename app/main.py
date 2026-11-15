"""Spectac Track B — FastAPI entrypoint (Directory, Cases, Callbacks, Outbox)."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app import __version__
from app.config import settings
from app.routers import callbacks, cases, departments, messages
from app.store import store

app = FastAPI(
    title=settings.app_name,
    version=__version__,
    description=(
        "FlexAgents Hackathon Team 1 — Track B backend. "
        "Directory, Cases, Callbacks, and Message Outbox. "
        "Isolated from Access LA agent code under spectac/."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(departments.router)
app.include_router(cases.router)
app.include_router(callbacks.router)
app.include_router(messages.router)


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "version": __version__,
        "chaos": settings.chaos_enabled,
        "departments": len(store.departments),
        "cases": len(store.cases),
        "slots": len(store.slots),
        "messages": len(store.messages),
    }


@app.post("/admin/reset")
def admin_reset() -> JSONResponse:
    """Re-seed in-memory store (demo / judge reset)."""
    store.reset()
    return JSONResponse(
        {
            "status": "reset",
            "departments": len(store.departments),
            "cases": len(store.cases),
            "slots": len(store.slots),
            "messages": len(store.messages),
        }
    )


def run() -> None:
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=False,
    )


if __name__ == "__main__":
    run()
