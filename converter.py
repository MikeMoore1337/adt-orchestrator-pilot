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


def to_fahrenheit(celsius: float) -> float:
    return ensure_temperature(celsius) * 9 / 5 + 32


def to_celsius(fahrenheit: float) -> float:
    return (ensure_temperature(fahrenheit) - 32) * 5 / 9


def to_kelvin(celsius: float) -> float:
    """Convert Celsius to Kelvin, rejecting temperatures below absolute zero."""
    celsius = ensure_temperature(celsius)
    if celsius < -273.15:
        raise ValueError("temperature must be at or above absolute zero")
    return celsius + 273.15


def from_kelvin(kelvin: float) -> float:
    """Convert Kelvin to Celsius, rejecting temperatures below absolute zero."""
    kelvin = ensure_temperature(kelvin)
    if kelvin < 0:
        raise ValueError("temperature must be at or above absolute zero")
    return kelvin - 273.15
