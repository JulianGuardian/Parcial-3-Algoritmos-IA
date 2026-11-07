"""In-memory mocks of the three write tools from the exam statement.

The responses come from ``app/disruption/fixtures``, keyed by HTTP status.
Tests choose which status each call returns by queueing status codes; once a
queue is empty, the tool falls back to its success response. Every call is
recorded so tests can assert how many times a tool was hit and with what.
"""

from __future__ import annotations

from collections import deque
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from typing import Any

from app.disruption.fixtures import load_fixture

REBOOKING = "create_rebooking_request"
HUMAN_CASE = "create_human_case"
NOTIFY = "notify_passenger"

# Success status per tool, as given in the exam statement.
_SUCCESS_STATUS = {REBOOKING: 201, HUMAN_CASE: 201, NOTIFY: 202}


def _responses(tool: str) -> dict[int, dict[str, Any]]:
    """Fresh copy of the fixture responses for ``tool``, keyed by status."""
    return {int(status): body for status, body in load_fixture(tool).items()}


def supported_statuses(tool: str) -> frozenset[int]:
    """Statuses the fixture defines for ``tool``."""
    return frozenset(_responses(tool))


@dataclass(frozen=True)
class ToolResponse:
    status_code: int
    body: dict[str, Any]

    @property
    def ok(self) -> bool:
        return 200 <= self.status_code < 300


@dataclass(frozen=True)
class ToolCall:
    tool: str
    arguments: dict[str, Any]
    response: ToolResponse


@dataclass
class MockWriteTools:
    """Mock write tools with injectable responses.

    ``rebooking_statuses``, ``human_case_statuses`` and ``notify_statuses``
    are queues consumed one status per call, e.g. ``[503, 503]`` makes the
    first two rebooking calls time out and the third one succeed.
    """

    rebooking_statuses: Iterable[int] = ()
    human_case_statuses: Iterable[int] = ()
    notify_statuses: Iterable[int] = ()
    calls: list[ToolCall] = field(default_factory=list, init=False)

    def __post_init__(self) -> None:
        self._queues = {
            REBOOKING: self._validated_queue(REBOOKING, self.rebooking_statuses),
            HUMAN_CASE: self._validated_queue(HUMAN_CASE, self.human_case_statuses),
            NOTIFY: self._validated_queue(NOTIFY, self.notify_statuses),
        }

    def create_rebooking_request(
        self, option: Mapping[str, Any], idempotency_key: str
    ) -> ToolResponse:
        return self._call(
            REBOOKING, {"option": dict(option), "idempotency_key": idempotency_key}
        )

    def create_human_case(
        self, reason: str, evidence: Mapping[str, Any]
    ) -> ToolResponse:
        return self._call(HUMAN_CASE, {"reason": reason, "evidence": dict(evidence)})

    def notify_passenger(self, message: Mapping[str, Any]) -> ToolResponse:
        # Mirrors the real contract: content without a policy_ref is rejected.
        default = None if message.get("policy_ref") else 422
        return self._call(NOTIFY, {"message": dict(message)}, default_status=default)

    def calls_to(self, tool: str) -> list[ToolCall]:
        return [call for call in self.calls if call.tool == tool]

    def _call(
        self,
        tool: str,
        arguments: dict[str, Any],
        default_status: int | None = None,
    ) -> ToolResponse:
        queue = self._queues[tool]
        if queue:
            status = queue.popleft()
        else:
            status = default_status or _SUCCESS_STATUS[tool]
        body = _responses(tool)[status]
        response = ToolResponse(status_code=status, body=body)
        self.calls.append(ToolCall(tool=tool, arguments=arguments, response=response))
        return response

    @staticmethod
    def _validated_queue(tool: str, statuses: Iterable[int]) -> deque[int]:
        queue = deque(statuses)
        unknown = set(queue) - supported_statuses(tool)
        if unknown:
            raise ValueError(
                f"{tool} has no fixture for status {sorted(unknown)}; "
                f"supported: {sorted(supported_statuses(tool))}"
            )
        return queue
