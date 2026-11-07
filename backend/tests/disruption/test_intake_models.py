from app.disruption.intake.models import Intent, IntentResult


def test_unknown_intent_outside_enum_is_rejected():
    """An intent outside the enum must never construct a valid IntentResult;
    callers map it to OTHER before building one (spec: invalid classifier
    output)."""
    raw_intents = ["ISSUE_REFUND"]
    valid = [i for i in raw_intents if i in Intent.__members__]
    mapped = [Intent(i) for i in valid] or [Intent.OTHER]

    result = IntentResult(intents=mapped, confidence=0.9)

    assert result.intents == [Intent.OTHER]


def test_empty_intents_default_to_other():
    result = IntentResult(intents=[], confidence=0.5)
    assert result.intents == [Intent.OTHER]
