"""Slug helpers."""


# implements: AC-1
def slugify(text: str) -> str:
    return "-".join(text.lower().split())


# implements: AC-2
def strip_punctuation(text: str) -> str:
    return "".join(ch for ch in text if ch.isalnum() or ch.isspace())
