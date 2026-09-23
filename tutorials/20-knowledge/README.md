# Track 20 — LLM Wiki

> **About this track.** [LLM Wiki](https://github.com/nvk/llm-wiki) is an
> MIT-licensed project by nvk ([llm-wiki.net](https://llm-wiki.net/)). This
> track is **my reading of it, not its documentation** — opinionated, and
> it will drift as the upstream changes. Go to the source for anything
> authoritative.
>
> It is here because LLM Wiki is the clearest working example of the
> pattern this repo is about: `raw/` is immutable, articles and indexes are
> *derived*, and you never hand-maintain the derived thing. See
> [the README](../../README.md#the-same-shape-three-times).

**~90 minutes. WebFetch and WebSearch required.**

Build a research knowledge base from URLs, documents, and PDFs. One command
turns raw sources into a queryable, citable system. This track teaches the
honest order: run `/wiki:research` first to see the whole arc, then decompose
it into ingest, compile, and query for fine control.

## Prerequisites

- `/wiki init` has been run once (any topic name)
- `WebFetch` and `WebSearch` are allowlisted in `.claude/settings.local.json`
  before lesson 2 (critical — research runs mean dozens of permission prompts
  otherwise)
- The Claude Code CLI installed globally

## What you will end up with

A mental model of how the wiki layer works: hub + topics, immutable raw files,
derived indexes, the three-tier edit rule, credibility review in research, and
the four maintenance commands that keep a wiki from rotting.

## Lessons

| # | Lesson | Time |
|---|---|---|
| 1 | [Setup and the mental model](lesson-01-setup.md) — the hub holds only indexes and logs | 10 min |
| 2 | [One command: /wiki:research](lesson-02-one-command.md) — create, research, compile in one line | 20 min |
| 3 | [Anatomy of a topic](lesson-03-anatomy.md) — raw files, indexes, the three-tier edit rule | 15 min |
| 4 | [Decomposing the magic](lesson-04-decomposing.md) — ingest, compile, query as separate steps | 15 min |
| 5 | [Research deep dive](lesson-05-research.md) — five phases, credibility scoring, question and thesis modes | 20 min |
| 6 | [Shipping and trust](lesson-06-shipping.md) — output, plan, lint, librarian, refresh, audit | 10 min |

## No offline grading

Unlike the other tracks, knowledge bases cannot be validated without live web
access. Lessons end with copy-pasteable commands you run directly in the CLI;
there is no `check.py` suite.
