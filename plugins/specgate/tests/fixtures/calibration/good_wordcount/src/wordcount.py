"""Word statistics."""


# implements: AC-1
def count_words(text: str) -> int:
    return len(text.split())


# implements: AC-2
def longest_word(text: str) -> str:
    words = text.split()
    if not words:
        return ""
    return max(words, key=len)
