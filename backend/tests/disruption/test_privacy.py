import json
from dataclasses import asdict

from app.disruption.assessment.privacy import mask_email, mask_phone, strip_passengers


def test_document_id_never_reaches_trip_state(abc123_state):
    payload = json.dumps(asdict(abc123_state), default=str)

    assert "12.345.678-9" not in payload
    assert "document_id" not in payload
    assert "maria.silva@example.com" not in payload
    assert "+56 9 8765 4321" not in payload
    assert "Silva" not in payload


def test_first_names_are_kept_and_contacts_masked(abc123_state):
    maria, tomas = abc123_state.passengers

    assert maria.first_name == "María"
    assert maria.masked_email == "m***@example.com"
    assert maria.masked_phone == "+** * **** 4321"
    assert tomas.first_name == "Tomás"
    assert tomas.masked_email is None and tomas.masked_phone is None


def test_party_size_and_minor_detected(abc123_state):
    assert abc123_state.party_size == 2
    assert abc123_state.has_minor is True


def test_minor_by_age_without_type():
    _, has_minor = strip_passengers([{"passenger_id": "P1", "name": "Ana Paz", "age": 12}])
    assert has_minor is True


def test_masking_edge_cases():
    assert mask_email(None) is None
    assert mask_email("not-an-email") is None
    assert mask_phone("") is None
    assert mask_phone("12") == "12"
