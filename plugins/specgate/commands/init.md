---
name: "specgate: init"
description: "Install lefthook and GitHub Actions workflows for specgate"
allowed-tools: Bash(specgate:*)
category: "Workflow"
tags: ["setup", "initialization", "workflows"]
---

Initialize specgate by installing lefthook and GitHub Actions workflows.

Run:
```bash
specgate init
```

**Exit codes:**
- `0`: Initialization successful
- `1`: Initialization failed (check error output)

This command sets up the pre-commit gates and CI/CD workflows needed for multi-layer acceptance testing.
