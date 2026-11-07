"""Intent classification contracts (task 4.1, design D11/D12).

`IntentResult` is the closed, validated shape every classifier must return.
`IntentClassifier` is the interface both implementations (keyword, ADK)
satisfy, so the pipeline never depends on a concrete classifier.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum

from pydantic import BaseModel, Field, field_validator


class Intent(str, Enum):
    TRIP_STATUS = "TRIP_STATUS"
    REBOOK_OPTIONS = "REBOOK_OPTIONS"
    COMPENSATION = "COMPENSATION"
    OTHER = "OTHER"


class IntentResult(BaseModel):
    """Validated classifier output (design D11/D12).

    Any intent outside the closed `Intent` enum must never reach this model
    as-is: callers are expected to map unknown values to `Intent.OTHER`
    before constructing it (see `IntentClassifier.classify` contract).
    """

    intents: list[Intent] = Field(default_factory=list)
    compensation_requested: bool = False
    wants_same_day: bool = False
    confidence: float = Field(ge=0.0, le=1.0)

    @field_validator("intents")
    @classmethod
    def _non_empty_defaults_to_other(cls, value: list[Intent]) -> list[Intent]:
        return value or [Intent.OTHER]


class IntentClassifier(ABC):
    """A classifier that maps free text to a closed, validated `IntentResult`.

    Implementations must never raise for an out-of-enum model output; they
    must map it to `Intent.OTHER` instead (spec: "Invalid classifier
    output"). Implementations may raise for infrastructure failures
    (timeout, missing configuration, network error) - callers are
    responsible for falling back (task 4.4).
    """

    name: str

    @abstractmethod
    def classify(self, question: str) -> IntentResult: ...
