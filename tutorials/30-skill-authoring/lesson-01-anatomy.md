# Lesson 1 — Anatomy of a skill

## What a skill actually is

A markdown file with two-field frontmatter and a body:

```markdown
---
name: house-rules
description: Output conventions for the records service.
---

## Rules

1. Timestamps are ISO-8601 with a `T` separator and a trailing Z.
```

`description` is how the skill gets *selected*. The body is what the model
*reads once selected*. Those are two different jobs and people routinely
write one when they mean the other.

## The one thing a skill is for

In this harness the inference agent sees **exactly two things**: the task,
and the skills. It cannot read the wiki, the traces, or the analysis that
produced the skill — `InferenceAgent` takes no wiki handle and its module
does not import the wiki layer, so this is structural, not a convention.

That is deliberate, and it is the paper's load-bearing result: letting the
agent read the accumulated notes *lowers* average performance from 63.7% to
60.9%, because it leans on raw material instead of the distilled rule.

The consequence for you: **a rule that stays in your notes changes nothing.**
If it is not in the skill body, it does not exist.

## What earns a place in the body

Ask whether the model could work it out unaided. Evidence from a real run of
this benchmark — Haiku 4.5, no skills:

| quirk | result | why |
|---|---|---|
| `rec_prefix` | **passed** | `fetch` returned an error naming the canonical format. It read the error and retried. |
| `page_two` | **passed** | the search result carried `more_pages: true`. It paginated. |
| `iso_z` | failed | nothing told it the output wanted a trailing Z |
| `round_even` | failed | nothing told it to round half-to-even |
| `idem_key` | failed | nothing told it the separator was a colon |

The model handled everything the environment *revealed* and missed every
**silent convention**. Skills are for the second column. Writing a skill that
explains pagination to a model that already paginates costs tokens and buys
nothing.

## Two frontmatter styles you will see

Both are common and neither is wrong:

- **Minimal** — `name` + `description`, single file, nothing else.
- **Extended** — adds fields like `roles:` or `integrations:` so a larger
  collection can filter and route between skills.

This harness only reads `name` and `description`; extra fields are ignored,
not rejected.

---

Next: [Lesson 2 — Your first skill](lesson-02-first-skill.md)
