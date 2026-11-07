"""Deterministic keyword-based intent classifier (task 4.2).

Used both as the configured classifier (`INTENT_CLASSIFIER=keyword`) and as
the fallback when the ADK classifier is unavailable, times out, or returns
a low-confidence result (task 4.4).
"""

from __future__ import annotations

import re

from app.disruption.intake.models import Intent, IntentClassifier, IntentResult

_TRIP_STATUS_WORDS = ("delay", "status", "what happened", "flight time", "arrive")
_REBOOK_WORDS = ("rebook", "another flight", "fly today", "fly tomorrow", "options", "alternative")
_COMPENSATION_WORDS = ("compensat", "refund", "reimburse")
_SAME_DAY_WORDS = ("today", "tonight", "this evening")


class KeywordIntentClassifier(IntentClassifier):
    name = "keyword_intent_classifier"

    def classify(self, question: str) -> IntentResult:
        text = question.lower()
        intents: list[Intent] = []

        if any(w in text for w in _TRIP_STATUS_WORDS):
            intents.append(Intent.TRIP_STATUS)
        if any(w in text for w in _REBOOK_WORDS):
            intents.append(Intent.REBOOK_OPTIONS)
        if any(w in text for w in _COMPENSATION_WORDS):
            intents.append(Intent.COMPENSATION)

        compensation_requested = Intent.COMPENSATION in intents
        wants_same_day = any(w in text for w in _SAME_DAY_WORDS) or bool(
            re.search(r"\btoday\b", text)
        )

        if not intents:
            return IntentResult(
                intents=[Intent.OTHER],
                compensation_requested=compensation_requested,
                wants_same_day=wants_same_day,
                confidence=0.3,
            )

        return IntentResult(
            intents=intents,
            compensation_requested=compensation_requested,
            wants_same_day=wants_same_day,
            confidence=0.9,
        )
