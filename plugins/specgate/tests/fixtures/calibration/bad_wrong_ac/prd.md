---
feature: Discount
acs:
  - id: AC-1
    given: a price of 100 or more
    when: apply_discount is called
    then: ten percent is taken off the price
    tests:
      - test_discount_applied
  - id: AC-2
    given: a negative price
    when: apply_discount is called
    then: ValueError is raised
    tests:
      - test_negative_price
---

# Discount
