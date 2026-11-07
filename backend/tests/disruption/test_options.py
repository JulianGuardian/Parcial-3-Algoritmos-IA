from datetime import datetime, timezone

from app.disruption.contracts import FareConditions, RejectionReason
from app.disruption.entitlements.options import filter_options, options_expired, recommend
from app.disruption.entitlements.sources import get_eligible_options

POLICY = "POL-DELAY-2026-03"
FARE = FareConditions(changeable=True, refundable=False, fare_family="LIGHT")
NOW = datetime(2026, 9, 15, 11, 3, 0, tzinfo=timezone.utc)  # inside the TTL


def run(options_response=None, *, now=NOW, party_size=2, entitlements=None):
    return filter_options(
        options_response or get_eligible_options({"booking_id": "ABC123"}),
        now=now,
        party_size=party_size,
        entitlements={"REBOOK_NO_FEE", "PRIORITY_HANDLING"} if entitlements is None else entitlements,
        policy_ref=POLICY,
        fare=FARE,
    )


def rejected(result):
    return {r.option_id: r for r in result.rejected}


def test_only_o1_survives_for_abc123():
    result = run()

    assert [o.option_id for o in result.valid] == ["O1"]
    assert sorted(rejected(result)) == ["O2", "O3"]


def test_o2_is_rejected_for_seats_and_policy():
    o2 = rejected(run())["O2"]

    assert o2.reasons == (RejectionReason.INSUFFICIENT_SEATS, RejectionReason.POLICY_INCONSISTENT)
    assert o2.reason is RejectionReason.INSUFFICIENT_SEATS
    assert "1 seat(s) for 2 passenger(s)" in o2.detail
    assert "180000 CLP" in o2.detail


def test_o3_requires_agent_review():
    o3 = rejected(run())["O3"]

    assert o3.reasons == (RejectionReason.REQUIRES_AGENT_REVIEW,)
    assert "LOW confidence on a non-refundable fare" in o3.detail
    assert "POL-REFUND-2026-01" in o3.detail


def test_every_option_is_rejected_past_the_ttl():
    response = get_eligible_options({"booking_id": "ABC123"})
    late = datetime(2026, 9, 15, 11, 5, 0, tzinfo=timezone.utc)  # 11:02:35 + 120 s = 11:04:35

    result = run(response, now=late)

    assert result.expired is True
    assert result.valid == []
    assert {r.reasons for r in result.rejected} == {(RejectionReason.EXPIRED,)}
    assert len(result.rejected) == 3


def test_ttl_boundary_is_inclusive_of_the_last_second():
    response = get_eligible_options({"booking_id": "ABC123"})
    assert options_expired(response, datetime(2026, 9, 15, 11, 4, 35, tzinfo=timezone.utc)) is False
    assert options_expired(response, datetime(2026, 9, 15, 11, 4, 36, tzinfo=timezone.utc)) is True


def test_naive_now_is_treated_as_utc():
    response = get_eligible_options({"booking_id": "ABC123"})
    assert options_expired(response, datetime(2026, 9, 15, 11, 3, 0)) is False


def test_whole_party_must_fit():
    assert [o.option_id for o in run(party_size=5).valid] == []
    assert rejected(run(party_size=5))["O1"].reasons == (RejectionReason.INSUFFICIENT_SEATS,)


def test_no_rebooking_entitlement_rejects_rebooks():
    result = run(entitlements={"PRIORITY_HANDLING"})

    assert result.valid == []
    assert RejectionReason.POLICY_INCONSISTENT in rejected(result)["O1"].reasons


def test_recommendation_prefers_confidence_then_earliest():
    result = run()
    assert recommend(result.valid).option_id == "O1"

    response = get_eligible_options({"booking_id": "ABC123"})
    base = response["options"][0]
    later_high = {**base, "option_id": "L", "date": "2026-09-17"}
    earlier_medium = {**base, "option_id": "M", "confidence": "MEDIUM", "date": "2026-09-15", "departure": "23:50"}
    earlier_high = {**base, "option_id": "E", "departure": "07:00"}
    response["options"] = [later_high, earlier_medium, earlier_high]

    assert recommend(run(response).valid).option_id == "E"
    response["options"] = [later_high, earlier_medium]
    assert recommend(run(response).valid).option_id == "L"  # HIGH beats earlier MEDIUM


def test_nothing_to_recommend_when_nothing_is_valid():
    assert recommend([]) is None
