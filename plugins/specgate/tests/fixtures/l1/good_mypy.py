"""Green fixture for SG102: mypy --strict compliant."""


def add(x: int, y: int) -> int:
    return x + y


result: int = add(1, 2)
