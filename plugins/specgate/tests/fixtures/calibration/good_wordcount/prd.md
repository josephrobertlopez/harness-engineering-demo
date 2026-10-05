---
feature: Wordcount
acs:
  - id: AC-1
    given: text with words separated by any whitespace
    when: count_words is called
    then: the number of words is returned
    tests:
      - test_count_words
  - id: AC-2
    given: text that may be empty
    when: longest_word is called
    then: the longest word is returned, or an empty string when there are no words
    tests:
      - test_longest_word
---

# Wordcount
