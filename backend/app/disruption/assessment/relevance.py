"""Relevance of a modification (design D4).

A modification is relevant when it changes what the passenger must do or
creates an entitlement: any delay, a missed connection or a cancellation. A
gate change on its own is informational. (Assumption: any delay counts; the
policy decides afterwards whether a delay carries an entitlement.)
"""

from app.disruption.contracts import SegmentState, SegmentStatus


def classify_relevance(segments: list[SegmentState]) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    for segment in segments:
        if segment.status is SegmentStatus.CANCELLED:
            reasons.append(f"CANCELLATION:{segment.segment_id}")
        if segment.status is SegmentStatus.DELAYED and segment.delay_minutes > 0:
            reasons.append(f"DELAY:{segment.segment_id}")
        if segment.missed_connection:
            reasons.append(f"MISSED_CONNECTION:{segment.segment_id}")
    return bool(reasons), reasons
