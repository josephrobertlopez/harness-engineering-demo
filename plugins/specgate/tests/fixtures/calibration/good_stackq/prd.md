---
feature: Stack
acs:
  - id: AC-1
    given: a stack with items pushed in order 1, 2, 3
    when: peek is called
    then: the most recently pushed item is returned and the stack is not modified
    tests:
      - test_peek
  - id: AC-2
    given: an empty stack
    when: pop is called
    then: IndexError is raised
    tests:
      - test_pop_empty
---

# Stack
