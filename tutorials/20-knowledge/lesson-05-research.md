# Lesson 5 — Research deep dive

When you run `/wiki:research`, the system orchestrates five phases. Understanding
them helps you tune depth, plan parallelism, and know why certain results are
trustworthy.

## The five phases

### Phase 1: Decompose the topic

Read existing knowledge to produce 5–8 search angles:

```
Topic: "transformer scaling laws"

Angles:
1. Academic: theoretical papers on scaling (Kaplan et al., Hoffmann et al.)
2. Technical: implementation details (compute-optimal training)
3. Applied: real-world benchmarks (LLM model releases)
4. News/Trends: recent announcements (frontier labs scaling updates)
5. Contrarian: critiques of scaling hypothesis (alternative architectures)
```

These angles ensure coverage: you do not just find papers that confirm the
question.

### Phase 2: Parallel agent search

Spawn one agent per angle (5 by default, 8 with `--deep`, 10 with `--retardmax`).
Each agent:

1. Searches independently
2. Fetches top results
3. Surfaces candidate sources with initial credibility signals

This is raw material, not final sources. The next phase filters.

### Phase 2b: Credibility review (the fox guarding the henhouse fix)

**This is the part people miss.** Every source is re-scored by the orchestrator
(not by the agent that found it). Scoring adds points for:

| signal | points |
|---|---|
| peer-reviewed venue | +2 |
| published ≤3 years ago | +1 |
| >10 years old | −1 |
| known author or institution | +1 |
| detectable bias or conflict | −1 |
| vendor primary source (self-promotion) | −1 |
| corroborated by another agent's search angle | +1 (up to +2) |

A source found by two independent agents scores higher than a source found by
one. Corroboration signals that multiple angles converged on it — a sign of
centrality.

Sources that score highest are selected for ingest. Medium-scoring sources are
retained as references. Low-scoring sources are discarded.

### Phase 3: Ingest top N

Write selected sources to `raw/`.

### Phase 4: Compile (single sequential pass)

Synthesize `raw/` into `articles/`. Even with parallel research (`--plan` over
multiple paths), compilation is sequential — all paths feed one compile. Why:
concurrent `_index.md` writes would corrupt the derived index.

### Phase 5: Report and log

Print a summary of:

- Sources discovered vs. selected
- Credibility distribution (how many scored high/medium/low)
- Compilation time
- Freshness metrics

Append to `log.md`.

## Tuning depth

```bash
# 5 angles, fastest
/wiki:research "topic" --project slug

# 8 angles, deeper
/wiki:research "topic" --project slug --deep

# 10 angles, most thorough
/wiki:research "topic" --project slug --retardmax
```

Default (5) is usually sufficient. Use `--deep` when the topic is interdisciplinary
(e.g., "AI ethics" spans computer science, philosophy, law). Use `--retardmax`
when comprehensive coverage is critical (e.g., regulatory research).

## Planning: parallel research paths

Orthogonal to depth, `--plan` decomposes the topic:

```bash
/wiki:research "machine learning applications" --project ml --plan --deep
```

The system shows you a plan (3–5 paths, each with a sub-question) and waits for
approval. Then it runs one agent per path, and each path agent spawns its own
5 (or 8, or 10) sub-agents. So `--plan --deep` over 4 paths ≈ 32 parallel agents.

Parallel ingest is safe (each path writes unique filenames). Parallel compilation
is not (would corrupt `_index.md`), so all paths feed a single sequential compile.

Example plan output:

```
Path 1: Computer vision applications
  └─ Search: image classification, object detection, segmentation
Path 2: NLP applications
  └─ Search: language models, translation, question-answering
Path 3: Reinforcement learning applications
  └─ Search: game AI, robotics, autonomous systems
Path 4: Emerging applications
  └─ Search: multimodal, embodied AI, generative modeling

Approve? (yes/no)
```

## Question mode

Input starting with what/why/how/who:

```bash
/wiki:research "How do transformers scale to millions of tokens?" --project scaling
```

Decomposes into sub-questions and assigns one agent per sub-question:

```
Main: How do transformers scale to millions of tokens?

Sub-questions:
1. What memory techniques exist? (sparse attention, paging, etc.)
2. Why is sequence length a bottleneck?
3. How do recent models (Claude, GPT-4) handle context windows?
```

Output is a playbook with answers to each sub-question, citations per answer.

## Thesis mode

Test a claim, rate evidence strength, deliver a verdict:

```bash
/wiki:research --mode thesis "Scaling laws predict future model performance" --project scaling
```

Spawns agents with different roles:

| role | searches for | scores |
|---|---|---|
| Supporting | evidence for the claim | high credibility |
| Opposing | contradictory evidence | high credibility |
| Mechanistic | *how* the claim works | causal mechanism |
| Meta | other meta-analyses | comparative strength |
| Adjacent | related claims | scope/boundary |

Evidence strength hierarchy (highest to lowest):

1. Meta-analysis (aggregate many studies)
2. RCT (randomized controlled trial)
3. Cohort study (observational, matched)
4. Case study (single instance with detail)
5. Opinion (expert quote without empirical support)
6. Anecdotal (isolated example)

The system assembles evidence, tallies strength, and renders a verdict:

```
VERDICT: Partially Supported

Supporting evidence: 3 papers (2 RCT, 1 meta-analysis)
Opposing evidence: 1 paper (cohort), 2 opinions
Mechanism: Unclear

Conclusion: Scaling laws correlate with performance (high confidence)
but causation is not proven (confound: compute + data + time).
```

### Multi-round thesis research

Round 1 searches for both sides. Round 2 deliberately targets the weaker side to
stress-test the verdict. This is the most important methodological difference from
standard research — you are not just searching; you are refining your confidence.

## Confidence score

An article gets `confidence: high` when sources corroborate (multiple agents
found the same claim independently). `medium` when sourced but not corroborated.
`low` when only one agent found it or the source has credibility concerns.

---

Next: [Lesson 6 — Shipping and trust](lesson-06-shipping.md)
