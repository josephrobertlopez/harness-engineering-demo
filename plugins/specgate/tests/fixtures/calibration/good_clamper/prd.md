---
feature: Clamper
acs:
  - id: AC-1
    given: a value below the lower bound
    when: clamp_low is called
    then: the lower bound is returned, otherwise the value is returned unchanged
    tests:
      - test_clamp_low
  - id: AC-2
    given: a value above the upper bound
    when: clamp_high is called
    then: the upper bound is returned, otherwise the value is returned unchanged
    tests:
      - test_clamp_high
---

# Clamper
