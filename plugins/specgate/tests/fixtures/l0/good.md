---
feature: Good Feature
acs:
  - id: AC-001
    given: the user is logged in
    when: they submit a form
    then: the form is validated
    tests:
      - test_form_validation
      - test_required_fields
  - id: AC-002
    given: the system is running
    when: an error occurs
    then: the error is logged
    tests:
      - test_error_logging
---

# Feature: Good Feature

This spec is valid and should pass all L0 rules.
