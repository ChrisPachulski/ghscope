"""ASCII sparklines for trends."""

from __future__ import annotations

SPARK_CHARS = "▁▂▃▄▅▆▇█"


def sparkline(values: list[int | float]) -> str:
    """Render a sparkline string from a list of numbers."""
    if not values:
        return ""
    lo = min(values)
    hi = max(values)
    if hi == lo:
        return SPARK_CHARS[3] * len(values)
    scale = (len(SPARK_CHARS) - 1) / (hi - lo)
    return "".join(SPARK_CHARS[int((v - lo) * scale)] for v in values)
