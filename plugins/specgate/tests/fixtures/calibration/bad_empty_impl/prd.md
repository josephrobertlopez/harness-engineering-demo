---
feature: Pinger
acs:
  - id: AC-1
    given: a host name
    when: ping is called
    then: the string "pong:<host>" is returned
    tests:
      - test_ping
---

# Pinger
