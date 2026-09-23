# Lesson 3 — Anatomy of a topic

After `/wiki:research` completes, your topic looks like this:

```
topics/transformers/
├── _index.md           # derived: article catalog
├── config.md           # you write this
├── schema.md           # optional: data structures
├── log.md              # append-only: every action
├── inbox/              # scratch: raw links, text, ideas
├── raw/                # immutable: fetched sources as files
│   ├── source-001.md
│   ├── arxiv-2307-12345.pdf
│   └── google-blog-2024.html
├── articles/           # compiled: finished articles with metadata
│   ├── attention-mechanism.md
│   ├── positional-encoding.md
│   └── _index.md       # derived: article index
└── WHY.md              # optional: project rationale (for `--project`)
```

## The three-tier edit rule

### Tier 1: Immutable

**`raw/` holds every upstream source exactly as fetched.** You do not edit these
files. If an upstream page changed:

1. Ingest the new version with a **new filename** (e.g., `google-blog-2024-v2.md`)
2. Never overwrite or rename an existing `raw/` file

This invariant is *load-bearing*. Path-based source resolution means articles
link to files by name. Renaming a `raw/` file silently breaks the article's
citation chain.

### Tier 2: Derived, rebuilt on read

**Every `_index.md` is a cache** (at hub-level and at `articles/`). It is never
hand-maintained. When you run a read command, the system checks freshness and
rebuilds if stale. You do not write to it.

The same applies to `articles/` itself — do not edit articles by hand after
compilation. Instead, update the `raw/` sources and recompile.

### Tier 3: Human-owned

**You write these files:**

- `config.md` — topic configuration (display name, description, default query
  mode)
- `schema.md` — optional, describes custom metadata (for filtering and
  cross-topic joins)
- `inbox/` — scratch space: bookmark a URL with `/wiki:ingest <url>`, paste
  raw text, jot ideas. Drain it manually or with `/wiki:ingest --inbox` to
  formalize into `raw/`
- `log.md` — append-only journal of every command run. Never read-modify-write.
  Appending is safe under concurrent sessions; rewriting creates races.
- `WHY.md` — project rationale (if using `--project` across multiple topics)

## Article metadata

Compiled articles carry:

```yaml
---
title: Attention is All You Need
source: arxiv-2307-12345.pdf
volatility: warm
freshness: 78
confidence: high
---
```

### Freshness (0–100)

Computed from four 25-point dimensions:

| dimension | +25 when | −25 when |
|---|---|---|
| source age | source ≤3 years old | source >10 years old |
| verification recency | independently verified in last 6 months | last verified >2 years ago |
| compile recency | compiled within last week | compiled >3 months ago |
| source-chain integrity | all upstream sources still exist | dead link in citation chain |

Each dimension's decay curve is scaled by the article's `volatility` tier —
`hot` decays Fast, `warm` Moderate, `cold` Slow. The reference documents
those as qualitative tiers rather than a published formula, so do not expect
a fixed points-per-week figure. Run `lint` to see which articles fell below
the threshold (default 70).

### Volatility

- `hot` — markets, live research, breaking news. Decays fast. Re-verify weekly.
- `warm` — established practice, documented specs, published research. Decays
  slowly.
- `cold` — historical, archived, immutable source. Does not decay.

Set volatility in the article header when you compile; `ingest` assigns `warm`
by default.

## The dual-link format

Links appear twice on one line — Obsidian reads the wikilink, the CLI and web
tools follow the relative path:

```markdown
See [[transformer-architecture|Transformer]] 
([Transformer](../concepts/transformer-architecture.md)) for details.
```

Both forms must agree on the target path. The linter checks this (see Lesson 6).

## First walk

After running `research`, explore your topic:

```bash
# List all raw sources
ls -la ~/.local/share/llm-wiki/topics/transformers/raw/

# Read one article
cat ~/.local/share/llm-wiki/topics/transformers/articles/attention-mechanism.md

# View the compiled index
cat ~/.local/share/llm-wiki/topics/transformers/articles/_index.md
```

Notice: `raw/` is pristine copies of sources, `articles/` are human-readable
summaries with metadata.

---

Next: [Lesson 4 — Decomposing the magic](lesson-04-decomposing.md)
