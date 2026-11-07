from app.disruption.contracts import Decision, Option, RuleResult
from app.disruption.agents.validator import validate_answer_draft


def _decision(requires_human=True) -> Decision:
    return Decision(
        booking_id="ABC123",
        applied_rules=[RuleResult("R3", "REBOOK_NO_FEE", True, "missed_connection is true")],
        not_applied_rules=[],
        policy_ref="POL-DELAY-2026-03",
        recommended_option=Option("O1", "REBOOK", flight_number="NB2412", date="2026-09-16"),
        rejected_options=[],
        requires_human=requires_human,
        human_reasons=["R5_PRIORITY_HANDLING"] if requires_human else [],
        auto_deliverable=not requires_human,
    )


def test_draft_offering_rejected_option_is_rejected():
    draft = "Good news, you can take NB2450 tonight. POL-DELAY-2026-03 applies, an agent will confirm."
    result = validate_answer_draft(draft, _decision())
    assert result.accepted is False


def test_valid_draft_about_recommended_option_is_accepted():
    draft = (
        "We can offer NB2412 on 2026-09-16 under POL-DELAY-2026-03. "
        "An agent will confirm this with you shortly."
    )
    result = validate_answer_draft(draft, _decision())
    assert result.accepted is True


def test_draft_missing_policy_ref_is_rejected():
    draft = "We can offer NB2412 on 2026-09-16. An agent will confirm this with you."
    result = validate_answer_draft(draft, _decision())
    assert result.accepted is False
    assert result.reason == "missing_policy_ref"


def test_draft_claiming_compensation_approved_is_rejected():
    draft = "Your compensation was approved under POL-DELAY-2026-03."
    result = validate_answer_draft(draft, _decision())
    assert result.accepted is False
    assert result.reason == "overclaims_outcome"


def test_own_segment_flights_are_allowed_when_declared():
    from app.disruption.agents.validator import validate_answer_draft as validate

    decision = _decision()
    draft = "Your flight NB500 is delayed and you miss NB2410. We offer NB2412. An agent will confirm. POL-DELAY-2026-03"

    assert validate(draft, decision).reason == "mentions_other_option"
    assert validate(draft, decision, own_flights={"NB500", "NB2410"}).accepted
