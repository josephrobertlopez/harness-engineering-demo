# SG201: AC function without # implements: AC-k marker
# This function should have '# implements: AC-1' but doesn't

def validate_input(data):
    """Function that should have implements marker but doesn't."""
    if not data:
        raise ValueError("Data cannot be empty")
    return True
