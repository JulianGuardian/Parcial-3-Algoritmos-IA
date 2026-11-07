import os

import pytest

from app.disruption.intake.adk_classifier import AdkIntentClassifier
from app.disruption.intake.models import IntentResult


def test_adk_classifier_importable_and_constructible():
    """google-adk installs and AdkIntentClassifier can be built without a
    network call (the call itself happens lazily in classify())."""
    classifier = AdkIntentClassifier(model="gemini-2.0-flash", api_key=None)
    assert classifier.name == "intent_classifier"
    agent = classifier._build_agent()
    assert agent.name == "intent_classifier"
    assert agent.tools == []


@pytest.mark.skipif(
    not os.environ.get("INTENT_MODEL_API_KEY"),
    reason="requires a real INTENT_MODEL_API_KEY to call the model",
)
def test_adk_classifier_returns_valid_intent_result_integration():
    classifier = AdkIntentClassifier(
        model=os.environ.get("INTENT_MODEL", "gemini-2.0-flash"),
        api_key=os.environ["INTENT_MODEL_API_KEY"],
    )
    result = classifier.classify("Will I be compensated for my delay?")
    assert isinstance(result, IntentResult)
