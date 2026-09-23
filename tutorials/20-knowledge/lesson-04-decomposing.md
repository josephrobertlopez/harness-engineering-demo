# Lesson 4 — Decomposing the magic

`/wiki:research` is three commands in sequence: ingest, compile, query. You can
run them separately for fine control.

## /wiki:ingest

Fetch sources into `raw/`. Does not compile.

One URL:

```bash
/wiki:ingest "https://arxiv.org/pdf/2310.06825" --project transformers
```

One file:

```bash
/wiki:ingest ~/Downloads/paper.pdf --project transformers
```

Raw text (paste into the prompt):

```bash
/wiki:ingest "Transformers use self-attention to model..." --project transformers
```

Drain inbox (all files you manually placed in `topics/transformers/inbox/`):

```bash
/wiki:ingest --inbox --project transformers
```

Multiple sources (repeat the command):

```bash
/wiki:ingest "url-1" --project transformers
/wiki:ingest "url-2" --project transformers
# ... ingest is idempotent; running twice on the same source is safe
```

## /wiki:compile

Synthesize `raw/` into `articles/`. This is where research becomes queryable.

Incremental (default — only compile new sources since last run):

```bash
/wiki:compile --project transformers
```

Full rebuild (recompile everything):

```bash
/wiki:compile --full --project transformers
```

The system detects stale articles (freshness score too low) and flags them in
`lint` output but does not auto-recompile unless you explicitly request
`--full`.

## /wiki:query

Answer questions using the compiled articles. Citation is exact — every fact
cites a file and line range.

```bash
/wiki:query "How do transformers handle variable-length sequences?" --project transformers
```

This returns:

1. A direct answer
2. Five supporting quotes with exact file citations
3. Confidence level (based on source freshness and cross-corroboration)
4. Gaps (what the wiki does not know)

Query does not write anything — it is read-only.

## The pipeline in a single batch

Recreate what `/wiki:research` does, step by step:

```bash
# 1. Fetch five seed sources
/wiki:ingest "https://arxiv.org/pdf/1706.03762" --project attention-deep
/wiki:ingest "https://example.com/attention-guide" --project attention-deep
/wiki:ingest "https://research.google/pubs/attention/" --project attention-deep
/wiki:ingest "https://colah.github.io/posts/2015-08-Visualizing-Attention/" --project attention-deep
/wiki:ingest "https://transformer-circuits.pub/" --project attention-deep

# 2. Compile to articles
/wiki:compile --project attention-deep

# 3. Query the result
/wiki:query "What is self-attention?" --project attention-deep
```

This manually walks the whole pipeline and teaches you which step does what.

## When to decompose

- **Use ingest + compile + query** when you are building incrementally (add a
  source, see if it helps, then add another)
- **Use /wiki:research** when you want the system to find sources for you
  (parallel agents, credibility review, the works)

They are not competing approaches — research runs ingest, compile, query
internally, so research discovers while decomposing lets you direct.

---

Next: [Lesson 5 — Research deep dive](lesson-05-research.md)
