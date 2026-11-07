"""Minimal disruption-resolution route.

NOTE: deliberately minimal stand-in for the full route of task 5.5 (which
also requires full 422/503 error mapping, request-id propagation into the
body, and a response model that fully mirrors `Decision`). It exists to let
task 5.6 (Docker smoke test) exercise a real HTTP path end to end,
including the `google-adk`-backed intent classifier and answer agent. Must
be reconciled with the full task 5.5 implementation later.
"""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.core.config import get_settings
from app.disruption.contracts import BookingNotFound, ResolveRequest, ToolUnavailable
from app.disruption.pipeline import resolve_disruption

router = APIRouter(prefix="/disruptions", tags=["disruptions"])


class ResolveBody(BaseModel):
    now: datetime | None = Field(default=None, description="Pins the evaluation time (design D10)")
    question: str | None = Field(default=None, max_length=500)
    compensation_requested: bool = False


class ResolveResponse(BaseModel):
    booking_id: str
    requires_human: bool
    recommended_option: dict | None
    policy_ref: str | None
    message: str | None


@router.post("/{booking_id}/resolve", response_model=ResolveResponse)
def resolve(booking_id: str, body: ResolveBody | None = None) -> ResolveResponse:
    body = body or ResolveBody()
    settings = get_settings()
    request = ResolveRequest(
        booking_id=booking_id,
        now=body.now,
        question=body.question,
        compensation_requested=body.compensation_requested,
    )
    try:
        result = resolve_disruption(request, settings)
    except BookingNotFound:
        raise HTTPException(status_code=404, detail="unknown booking_id")
    except ToolUnavailable as exc:
        raise HTTPException(status_code=503, detail="a required read tool is unavailable") from exc

    option = result.decision.recommended_option
    return ResolveResponse(
        booking_id=booking_id,
        requires_human=result.decision.requires_human,
        recommended_option=asdict(option) if option is not None else None,
        policy_ref=result.decision.policy_ref,
        message=result.message,
    )
