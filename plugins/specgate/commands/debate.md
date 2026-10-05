---
name: "specgate: debate"
description: "Run L6 debate layer - highest-level adversarial scrutiny"
allowed-tools: Bash(specgate:*)
category: "Validation"
tags: ["debate", "adversarial", "validation"]
---

Run the specgate L6 debate layer for adversarial scrutiny of acceptance criteria.

Run:
```bash
specgate debate
```

**Exit codes:**
- `0`: Debate layer passed
- `16`: Layer 6 (debate) failed

The debate layer is the highest level of acceptance testing. It applies adversarial reasoning to challenge whether the acceptance criteria truly capture the requirement's intent. This is where the specification is tested against edge cases, implicit assumptions, and the question: "Is this *really* what we wanted?"

**What debate tests:**
- AC assumptions are grounded in requirements
- AC language is precise and unambiguous
- AC covers both happy path and error cases
- AC doesn't over-specify implementation details
- AC would catch real bugs in a bad implementation
