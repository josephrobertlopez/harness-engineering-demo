---
name: "specgate: check"
description: "Run the specgate check across all layers"
allowed-tools: Bash(specgate:*)
category: "Validation"
tags: ["validation", "testing", "gates"]
---

Run the specgate validation check across all acceptance layers.

Run:
```bash
specgate check
```

**Exit codes:**
- `0`: All checks passed
- `10+L`: Layer L failed (e.g., exit 12 = Layer 2 failed, exit 16 = Layer 6 failed)

The check runs through 6 layers (L0-L5):
- **L0**: Schema validation
- **L1**: Static analysis
- **L2**: Trace generation
- **L3**: Execution tests
- **L4**: Coverage analysis
- **L5**: Mutation testing

**With options:**
```bash
specgate check --layers L0-L2 --staged
```
- `--layers`: Specify which layers to run (e.g., L0-L2, L3, L4-L6)
- `--staged`: Only check staged files
