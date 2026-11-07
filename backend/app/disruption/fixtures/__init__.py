"""Sample tool responses shipped with the app (see README.md in this folder)."""

import json
from copy import deepcopy
from functools import lru_cache
from pathlib import Path
from typing import Any

_DIR = Path(__file__).parent


@lru_cache
def _read(name: str) -> Any:
    with (_DIR / f"{name}.json").open(encoding="utf-8") as handle:
        return json.load(handle)


def load_fixture(name: str) -> Any:
    """Return a fresh copy of fixture `name` (file name without `.json`).

    A copy is returned so callers can never mutate the shared sample data.
    """
    return deepcopy(_read(name))
