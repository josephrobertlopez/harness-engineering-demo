# Lesson 6 — Shipping and trust

A wiki is not a document. It is a *provenance system* — when you ship a report,
the wiki lets you ask later: "Should I still trust this?"

## Outputs: shipping a report

Convert articles into artifacts:

```bash
# Summary (executive overview)
/wiki:output "climate tipping points" summary --project climate

# Report (full technical document)
/wiki:output "climate tipping points" report --project climate

# Study guide (Q&A format, learning-first)
/wiki:output "climate tipping points" study-guide --project climate

# Slides (presentation deck)
/wiki:output "climate tipping points" slides --project climate

# Timeline (chronological narrative)
/wiki:output "climate tipping points" timeline --project climate

# Glossary (terms + definitions)
/wiki:output "climate tipping points" glossary --project climate

# Comparison (side-by-side: pros vs. cons, X vs. Y, etc.)
/wiki:output "climate tipping points" comparison --project climate
```

Every output cites its sources. The command embeds article freshness, confidence,
and volatility into the report so readers see how current it is.

## Implementation planning

Use wiki articles as evidence for decisions:

```bash
/wiki:plan "kubernetes migration strategy" --project infrastructure
```

Output is a Gantt chart (or text roadmap) where each milestone or decision cites
one or more wiki articles. "Why we chose this database" becomes a link to the
decision record + the supporting research.

## Project mode

Multiple topics feeding one output:

```bash
/wiki:project new "quarterly-AI-briefing"
```

Creates `WHY.md` in the hub (not in a topic). Then:

```bash
/wiki:output "AI safety, alignment, scaling" report --project quarterly-AI-briefing
```

Searches across all three topics (`ai-safety`, `alignment`, `scaling`) and
synthesizes a unified report.

Always pass `--project <slug>` explicitly — there is no ambient session context.

## The four maintenance commands

A wiki rots if sources change, freshness decays, or you ship reports you no
longer trust. These commands answer different questions:

### lint — is the structure broken?

```bash
/wiki:lint --project climate
```

Checks:

- Broken wikilinks (missing target files)
- Missing `_index.md` files
- Registry drift (topics in `wikis.json` but no folder, or vice versa)
- Dual-link mismatches (wikilink and markdown path disagree)
- Freshness below threshold (default 70)

Output: list of problems to fix. Does not run fresh research; uses only local data.

### librarian — are articles trustworthy?

```bash
/wiki:librarian --project climate
```

Reviews article quality:

- Excessive summarization (content too thin)
- Citation gaps (claims without sources)
- Source conflicts (two articles contradict each other)
- Metadata (missing volatility, confidence, source)

Does not re-fetch sources or run research. Examines compiled articles.

### refresh — have sources changed upstream?

```bash
/wiki:refresh --project climate
```

Re-fetches every source in `raw/` and detects changes:

- If a source changed: marks the article stale, suggests recompilation
- If a source died: flags the broken link
- If a source moved: updates the citation

Does not recompile automatically. Once you've reviewed the changes, run
`/wiki:compile --full` to regenerate articles.

### audit — should I still trust this report?

```bash
/wiki:audit scan --artifact "output/Q4 AI briefing.md" --project quarterly-AI
```

The trust umbrella. Checks:

1. Article freshness (articles used in the report have decayed past threshold?)
2. Source availability (are the cited sources still alive?)
3. Provenance chain (can I trace every claim back to a source?)
4. Contradiction (do sources agree or contradict?)

May run fresh research if freshness is critically low (it asks before spending
credits).

Verdict: "This report is still reliable" or "Recommend refresh" or "Strongly
recommend re-research."

## The command matrix

Two dimensions: **what it writes** and **what it requires**.

| command | writes | requires wiki? | notes |
|---|---|---|---|
| `research` | raw + articles | NO (creates topic) | orchestrates ingest + compile |
| `ingest` | raw | NO (creates topic) | write-only |
| `compile` | articles | YES | reads raw |
| `query` | nothing | YES | read-only |
| `output` | report file | YES | reads articles |
| `plan` | roadmap + citations | YES | reads articles |
| `lint` | nothing | YES | structural only |
| `librarian` | nothing | YES | article quality |
| `refresh` | nothing | YES | re-fetches raw |
| `audit` | nothing | YES | may run research |

Wiki-creating: `research`, `ingest` (with `--new-topic`). Others require an
existing wiki.

## Archived topics: the silent skip

Topics can be archived:

```bash
/wiki:archive topic old-topic
```

Archived topics are silently skipped by almost every command. If content
"disappears," check:

```bash
/wiki:archive list --archived
/wiki:archive restore old-topic
```

## One more thing: scope is never ambient

There is no "current project" and no "current topic". Every command that can
be scoped must be told, every time.

Few commands take `--project` at all — `research`, `ingest` and `audit`
carry it in their argument hints, and `checkpoint` accepts it too. Notably
`project` does **not**: it is the command you manage projects *with*, and it
uses subcommands (`new`, `list`, `show`) instead. Everything else scopes with
`--wiki <name>`, `--topic <name>`, or `--local`.

```bash
# scoping a research run to a project -- the project must already exist
/wiki:research "carbon capture" --project climate-brief

# compile has no --project; it scopes by topic
/wiki:compile --topic climate

# and a removed flag, so you recognise it in older write-ups
/wiki:compile --focus climate   # no longer exists
```

The session-focus mechanism was deliberately removed in v0.2. That is the
tradeoff which lets you safely run several CLI windows against one hub —
nothing is carrying hidden state between them.

`/wiki:research --project <slug>` fails early if
`output/projects/<slug>/WHY.md` does not exist. Create the project first.

---

That is the whole system. You now own:

- The hub and topic architecture (Lesson 1)
- Running research end-to-end (Lesson 2)
- The folder structure and edit rules (Lesson 3)
- Atomic ingest/compile/query operations (Lesson 4)
- The research phases and credibility review (Lesson 5)
- Outputs, planning, and maintenance (Lesson 6)

Next steps: pick a domain you know, run `/wiki:research` on it, then run
`/wiki:query` to ask it questions. Start small (one topic, one question), then
grow.
