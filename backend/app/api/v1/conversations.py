"""Conversational agent API (task 4.1, design D6).

`POST /api/v1/conversations` starts a conversation bound to one booking.
`POST /api/v1/conversations/{id}/messages` sends one passenger message
through `disruption_companion` and returns the structured `AgentResponse`.
Confirming a rebooking option travels only as `confirm_option_id`, a
structured field never derived from the message text (design D4/D6) - a
UI would send it from a button, never by trusting free-text "yes".

The deterministic `/disruptions/{id}/resolve` endpoint is unaffected and
stays the oracle the evaluations compare this conversational path against.
"""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from app.core.config import get_settings
from app.core.logging import get_request_id
from app.disruption.agents.contracts import AgentResponse
from app.disruption.agents.conversation_store import get_conversation_store
from app.disruption.agents.workflow import APP_NAME, run_turn
from app.disruption.contracts import BookingNotFound, ToolUnavailable

router = APIRouter(prefix="/conversations", tags=["conversations"])


class ErrorOut(BaseModel):
    error: str
    detail: str
    request_id: str | None = None


class StartConversationBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    booking_id: str = Field(min_length=1, max_length=20)


class StartConversationOut(BaseModel):
    conversation_id: str
    booking_id: str


class MessageBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message: str = Field(min_length=1, max_length=500, description="The passenger's free-text message.")
    confirm_option_id: str | None = Field(
        default=None,
        description="Structured confirmation of a rebooking option. Never inferred from `message`.",
    )
    now: datetime | None = Field(default=None, description="Evaluation time (ISO 8601); pins TTL/freshness checks.")


def _error(status: int, error: str, detail: str) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content=ErrorOut(error=error, detail=detail, request_id=get_request_id()).model_dump(),
    )


@router.post(
    "",
    status_code=201,
    response_model=StartConversationOut,
    responses={404: {"model": ErrorOut}},
)
def start_conversation(body: StartConversationBody) -> StartConversationOut | JSONResponse:
    from app.disruption.assessment.sources import get_trip_context

    try:
        get_trip_context(body.booking_id)
    except BookingNotFound:
        return _error(404, "BOOKING_NOT_FOUND", "No booking matches this id.")

    conversation = get_conversation_store().create(body.booking_id)
    return StartConversationOut(conversation_id=conversation.conversation_id, booking_id=conversation.booking_id)


@router.post(
    "/{conversation_id}/messages",
    response_model=AgentResponse,
    responses={404: {"model": ErrorOut}, 503: {"model": ErrorOut}},
)
def send_message(conversation_id: str, body: MessageBody) -> AgentResponse | JSONResponse:
    conversation = get_conversation_store().get(conversation_id)
    if conversation is None:
        return _error(404, "CONVERSATION_NOT_FOUND", "No conversation matches this id.")

    request_id = get_request_id()
    try:
        outcome = run_turn(
            session_service=get_conversation_store().session_service,
            app_name=APP_NAME,
            user_id=conversation_id,
            session_id=conversation_id,
            booking_id=conversation.booking_id,
            message=body.message,
            deps=conversation.deps,
            settings=get_settings(),
            confirm_option_id=body.confirm_option_id,
            now=body.now.isoformat() if body.now else None,
            request_id=request_id,
        )
    except BookingNotFound:
        return _error(404, "BOOKING_NOT_FOUND", "No booking matches this id.")
    except ToolUnavailable:
        return _error(503, "UPSTREAM_UNAVAILABLE", "A required data source is unavailable. Try again later.")

    return outcome.response
