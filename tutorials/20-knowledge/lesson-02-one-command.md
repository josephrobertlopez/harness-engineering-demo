# Lesson 2 — One command: /wiki:research

This is the one you use most often. It orchestrates the entire arc — topic
creation, parallel research, source ingestion, and compilation — in a single
line. Learn this first, then decompose it into its parts.

## The command

```bash
/wiki:research "transformer architecture" --new-topic
```

What happens:

1. **Create the topic** (because `--new-topic`)
2. **Decompose the question** into 5 search angles (Academic, Technical, Applied,
   News/Trends, Contrarian)
3. **Spawn 5 parallel agents** (one per angle) to search and fetch sources
4. **Credibility review** the sources (the docs call this solving the "fox
   guarding the henhouse" problem)
5. **Ingest the top sources** to `raw/`
6. **Compile once** to produce articles

The output is a queryable topic with cited sources.

## One-topic rule

Always specify the topic when running research:

```bash
/wiki:research "kubernetes networking" --project kubernetes
```

The `--project` flag is never ambient — pass it every time. The session-focus
mechanism was deliberately removed so you cannot accidentally write to the
wrong wiki.

## The three research axes

### Depth

Default `5` agents (angles above).
`--deep` uses `8` agents (adds Historical, Adjacent, Data/Stats).
`--retardmax` uses `10` agents (all angles).

```bash
/wiki:research "climate tipping points" --project climate-science --deep
```

### Planning

Orthogonal to depth: `--plan` decomposes the topic into 3–5 independent
research paths, shows you the plan, waits for approval, then runs one agent
per path with full depth underneath. So `--plan --deep` over 4 paths ≈ 32
parallel agents.

```bash
/wiki:research "machine learning applications" --project ml-survey --plan --deep
```

Planning is safe for parallel ingest (each path writes unique filenames) but
compilation is sequential (all paths feed a single compile pass).

### Research modes

**Default (search):** answers a topic with diverse sources.

**Question mode** (input starts with what/why/how/who):

```bash
/wiki:research "How do transformers attend to context?" --project transformers
```

Assigns one agent per sub-question, produces a playbook.

**Thesis mode:** tests a claim, rates evidence strength, delivers a verdict:

```bash
/wiki:research --mode thesis "AI scaling follows log-linear returns" --project scaling
```

Spawns Supporting/Opposing/Mechanistic/Meta/Adjacent agents. Evidence strength:
meta-analysis > RCT > cohort > case > opinion > anecdotal. Verdict: Supported |
Partially Supported | Insufficient Evidence | Contradicted | Mixed.

Multi-round thesis deliberately attacks the weaker side in round 2 — the most
important methodological difference from standard research.

## First run: walk it

```bash
/wiki:research "distributed systems consensus" --new-topic
```

You will see:

- Decomposed angles (5 or 8 or 10 depending on flags)
- Parallel agent runs (watch the CLI output)
- Sources discovered, scored, and selected
- Ingestion to `raw/` (you can cat the files while it runs)
- Compilation producing `articles/`

It takes 3–8 minutes depending on topic complexity and network latency.

---

Next: [Lesson 3 — Anatomy of a topic](lesson-03-anatomy.md)
