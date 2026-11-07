"""Classifier selection and fallback chain (task 4.4, design D12).

`classify_question` is the single entry point the pipeline calls. It never
raises: any classifier failure degrades to the keyword classifier, and
total failure degrades to `OTHER` + human review. Every call records a
`TraceEntry` with the fields design D12 requires for traceability.
"""

from __future__ import annotations

import time

from app.disruption.contracts import TraceEntry
from app.disruption.intake.adk_classifier import AdkIntentClassifier
from app.disruption.intake.keyword_classifier import KeywordIntentClassifier
from app.disruption.intake.models import Intent, IntentResult
from app.disruption.intake.redact import redact_pii

CONFIDENCE_THRESHOLD = 0.6


class IntakeResult:
    def __init__(self, intent_result: IntentResult, trace: TraceEntry):
        self.intent_result = intent_result
        self.trace = trace


def classify_question(
    question: str | None,
    *,
    classifier_backend: str,
    adk_model: str | None,
    adk_api_key: str | None,
    adk_timeout_seconds: float = 3.0,
) -> IntakeResult | None:
    """Classify `question`, or return `None` if there is no question.

    `classifier_backend` is `"adk"` or `"keyword"` (settings
    `INTENT_CLASSIFIER`). With `"adk"`, a failure or low-confidence result
    falls back to the keyword classifier; the keyword classifier never
    fails, but can itself return `OTHER` with low confidence, which the
    caller must still treat as requiring a human (spec: "Safe fallback").
    """
    if not question:
        return None

    redacted = redact_pii(question)
    keyword = KeywordIntentClassifier()

    if classifier_backend != "adk":
        result = keyword.classify(redacted)
        trace = TraceEntry(
            step="intent_classifier",
            message=f"{keyword.name}: {[i.value for i in result.intents]}",
            data={
                "framework": "keyword",
                "agent": keyword.name,
                "model": None,
                "intents": [i.value for i in result.intents],
                "confidence": result.confidence,
                "latency_ms": 0.0,
                "fallback_used": False,
            },
        )
        return IntakeResult(result, trace)

    adk = AdkIntentClassifier(
        model=adk_model or "",
        api_key=adk_api_key,
        timeout_seconds=adk_timeout_seconds,
    )

    fallback_used = False
    fallback_reason: str | None = None
    model_name = adk.model
    latency_ms = 0.0
    result: IntentResult

    try:
        started = time.monotonic()
        meta = adk.classify_with_meta(redacted)
        latency_ms = meta.latency_ms
        result = meta.result
        if result.confidence < CONFIDENCE_THRESHOLD:
            fallback_used = True
            fallback_reason = "low_confidence"
            result = keyword.classify(redacted)
    except Exception as exc:  # noqa: BLE001 - any classifier failure degrades safely
        fallback_used = True
        fallback_reason = type(exc).__name__
        result = keyword.classify(redacted)

    if fallback_used and result.intents == [Intent.OTHER] and result.confidence < CONFIDENCE_THRESHOLD:
        # Fallback was also inconclusive: OTHER stays, and the caller must
        # route this to a human (spec: "Safe fallback").
        pass

    trace = TraceEntry(
        step="intent_classifier",
        message=f"{'keyword' if fallback_used else adk.name}: {[i.value for i in result.intents]}",
        data={
            "framework": "google-adk" if not fallback_used else "keyword",
            "agent": adk.name if not fallback_used else keyword.name,
            "model": model_name if not fallback_used else None,
            "intents": [i.value for i in result.intents],
            "confidence": result.confidence,
            "latency_ms": latency_ms,
            "fallback_used": fallback_used,
            "fallback_reason": fallback_reason,
        },
    )
    return IntakeResult(result, trace)
