---
feature: Slugger
acs:
  - id: AC-1
    given: a title with mixed case and extra whitespace
    when: slugify is called
    then: the result is lowercase with single hyphens between words
    tests:
      - test_slugify
  - id: AC-2
    given: text containing punctuation
    when: strip_punctuation is called
    then: every character that is not a letter, digit or space is removed
    tests:
      - test_strip_punctuation
---

# Slugger
