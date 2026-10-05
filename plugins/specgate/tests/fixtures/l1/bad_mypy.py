"""Red fixture for SG102: mypy --strict error (missing type annotation)."""


def add(x, y):  # Missing type annotations - mypy --strict will fail
    return x + y


result = add(1, 2)
