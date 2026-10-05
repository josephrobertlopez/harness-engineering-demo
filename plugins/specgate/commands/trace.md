---
name: "specgate: trace"
description: "Generate and read trace.json for a change"
allowed-tools: Bash(specgate:*)
category: "Analysis"
tags: ["tracing", "debugging", "analysis"]
---

There is no `specgate trace` subcommand. `specgate check` writes `trace.json` when the requested layers pass.

Run:
```bash
specgate check --change openspec/changes/<feature> --layers L0-L5 --output /tmp/trace.json
```

Then read `/tmp/trace.json`. It is an object keyed by AC id (`AC-1`, ...). Each entry has:
- `id`: the AC id
- `implements`: list of `{file, function, line}` for `# implements: AC-k` markers
- `covers`: list of `{file, function, line}` for `# covers: AC-k` markers
- `junit`: L3 status, or `null`
- `coverage`: `{lines_covered, lines_total}`
- `mutations`: `{killed, total}`

An AC with an empty `implements` or `covers` list is a gap.
