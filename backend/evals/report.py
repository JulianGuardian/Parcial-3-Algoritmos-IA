"""Results writer for the real-model evaluations (task 5.2, design D10).

`backend/evals/results/latest.json` records the model id, the date and one
entry per case. The file is *not* overwritten when every case in the run
degraded (model unreachable or over quota) - that run proved nothing about
the model, so clobbering a previous good result with it would be
misleading. A run where at least one case got a real response is written,
with each case's own `degraded` flag kept so the report can say which
cases, if any, did not get a real answer.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

RESULTS_DIR = Path(__file__).resolve().parent / "results"
RESULTS_PATH = RESULTS_DIR / "latest.json"


@dataclass
class CaseResult:
    name: str
    degraded: bool
    passed: bool
    trajectory: list[str] = field(default_factory=list)
    faithfulness_ok: bool | None = None
    faithfulness_problems: list[str] = field(default_factory=list)
    notes: str = ""


def save_results(model: str, cases: list[CaseResult]) -> bool:
    """Write `latest.json`. Returns False (no write) only if every case
    degraded, in which case the previous file is left untouched."""
    if cases and all(c.degraded for c in cases):
        return False

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "model": model,
        "date": datetime.now(timezone.utc).isoformat(),
        "cases": [asdict(c) for c in cases],
        "summary": {
            "total": len(cases),
            "passed": sum(1 for c in cases if c.passed),
            "degraded": sum(1 for c in cases if c.degraded),
        },
    }
    RESULTS_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return True
