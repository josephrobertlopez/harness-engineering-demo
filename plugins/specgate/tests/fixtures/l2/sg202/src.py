# SG202 fixture: implementation with marker but no test covers it
# implements: AC-1
def validate_input(data):
    """Function that implements AC-1 but is not tested."""
    if not data:
        raise ValueError("Data cannot be empty")
    return True
