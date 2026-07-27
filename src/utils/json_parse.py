"""Small JSON helpers."""
from __future__ import annotations

import json
from typing import Any


def safe_parse(val: Any) -> list:
    """Parse Gamma API fields that may be JSON strings or already lists."""
    if isinstance(val, str):
        try:
            parsed = json.loads(val)
            return parsed if isinstance(parsed, list) else []
        except (json.JSONDecodeError, TypeError):
            return []
    return val if isinstance(val, list) else []
