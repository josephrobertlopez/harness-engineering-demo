---
name: "specgate: trace"
description: "Show the trace.json per acceptance criteria"
allowed-tools: Bash(specgate:*)
category: "Analysis"
tags: ["tracing", "debugging", "analysis"]
---

Display the execution trace for each acceptance criterion.

Run:
```bash
specgate trace
```

**Exit codes:**
- `0`: Trace successfully generated and displayed
- `1`: Trace generation failed

This command shows `trace.json` which maps each acceptance criterion (AC) in your spec to the code and tests that implement/cover it. Useful for understanding coverage and finding gaps in implementation.

**Output includes:**
- AC identifier
- Implementing source files (marked with `# implements: AC-k`)
- Covering test files (marked with `# covers: AC-k`)
- Execution flow through the implementation
