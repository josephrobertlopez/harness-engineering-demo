"""Source code that implements AC-1 with uncovered branches."""


# implements: AC-1
def validate_positive(x: int) -> bool:
    """Validate that x is positive. AC-1 requires checking > 0."""
    if x > 0:
        return True
    else:
        return False
