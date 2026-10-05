"""Numeric clamping."""


# implements: AC-1
def clamp_low(value: int, lo: int) -> int:
    return max(value, lo)


# implements: AC-2
def clamp_high(value: int, hi: int) -> int:
    return min(value, hi)
