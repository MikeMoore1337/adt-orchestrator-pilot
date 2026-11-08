"""A tiny synthetic temperature converter for Codex orchestrator QA."""

import math


def ensure_temperature(value: float) -> float:
    """Validate numeric finite input, rejecting booleans."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError("temperature must be a real number")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError("temperature must be finite")
    return result
