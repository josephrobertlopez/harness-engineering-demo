"""Source code that implements AC-3."""

# implements: AC-3
def divide(a, b):
    """Divide two numbers."""
    if b == 0:
        raise ValueError("Cannot divide by zero")
    return a / b
