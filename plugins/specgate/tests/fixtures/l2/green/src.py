# Green case: proper AC implementation with marker

# implements: AC-1
def validate_input(data):
    """Function that properly implements AC-1."""
    if not data:
        raise ValueError("Data cannot be empty")
    return True
