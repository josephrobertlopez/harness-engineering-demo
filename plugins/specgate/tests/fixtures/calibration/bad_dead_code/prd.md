---
feature: Pricing
acs:
  - id: AC-1
    given: a list of item prices
    when: total is called
    then: the sum of the prices is returned
    tests:
      - test_total
---

# Pricing
