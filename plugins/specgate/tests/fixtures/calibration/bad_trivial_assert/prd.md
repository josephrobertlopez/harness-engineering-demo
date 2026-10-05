---
feature: Greeter
acs:
  - id: AC-1
    given: a name
    when: greet is called
    then: the greeting "Hello, <name>!" is returned
    tests:
      - test_greet
---

# Greeter
