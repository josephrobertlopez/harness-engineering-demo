# The same shape, four times

> Knowledge compounds when **the thing you edit and the thing you read are
> different objects.**

This repo implements a 2026 paper about agent skill evolution. But the
mechanism the paper formalises is not new, and it is not about agents. It
was worked out by a sociologist with a box of index cards in the 1950s, and
it keeps getting rediscovered because it is the only arrangement that makes
knowledge accumulate instead of churn.

This document is the argument. The code is the part you can measure.

---

## The pattern

Three moving parts, and the discipline is in the arrows, not the boxes:

```
  capture  ──────►  compile  ──────►  use
  immutable         derived          derived
  never edited      never hand-      regenerated
  only appended     maintained       freely
```

Two rules follow, and everything below is a restatement of them:

1. **Never edit the source.** New information means a new entry, not a
   revision of an old one. The record of what you actually saw has to stay
   intact, because it is the only thing you can re-derive from when your
   conclusions turn out to be wrong.
2. **Never hand-maintain the derived thing.** The moment an index, a
   summary or a contract is edited by hand, it stops being derivable — and
   the next regeneration either destroys the edit or has to be abandoned.
   Either way the system quietly stops compounding.

The failure mode both rules prevent is the same: **a file that is
simultaneously the evidence and the conclusion.** You cannot revise it
without losing what it was based on, and you cannot regenerate it without
losing the thinking you put in.

---

## 1. Zettelkasten (1950s)

Niklas Luhmann, a German sociologist, kept roughly 90,000 index cards and
credited them with 70 books and nearly 400 articles. The method — the
*Zettelkasten*, "slip box" — separates notes into three kinds:

| Note type | What it is | Its role in the pattern |
|---|---|---|
| **Fleeting** | quick capture, processed then discarded | the inbox |
| **Literature** | what is worth keeping from a source, **in your own words** | the compile step |
| **Permanent** | one idea, one card, identified and linked | the derived artifact |

Two of its rules matter here.

**Atomicity.** One idea per card. A card holding three ideas can only be
linked as a unit, so two of the three become invisible to everything that
should have found them.

**Write in your own words; do not copy the source.** This is the
capture/compile separation stated as a discipline rather than a file layout.
The source stays where it is; what enters the box is something you made from
it. If you paste, you have moved the evidence into the conclusion and lost
the ability to tell them apart later.

Luhmann also refused to file cards into a predetermined taxonomy. Structure
emerged from links. That is the second rule in embryo: **the index is
derived.**

## 2. Second Brain (2022)

Tiago Forte's *Building a Second Brain* is the same arrangement rebuilt for
digital tools, as **CODE** — Capture, Organize, Distill, Express — with
**PARA** (Projects, Areas, Resources, Archives) as the organising step.

The interesting part for this argument is **Distill**: refine a note down to
its essence so a future reader grasps it at a glance. That is a compile
step, and it is deliberately a *separate artifact* from what you captured.
Forte is more prescriptive than Luhmann about where things live, but the
capture/distill boundary is identical.

[Bryan Hogan's Obsidian walkthrough][hogan] is the clearest short practical
demonstration I have found. The method is Luhmann's, not his, and he says so
— but the post shows the principles working in a real tool, which is harder
than describing them. Two of his rules restate ours exactly:

> "Notes should be atomic, meaning that each card is about one thing."

> "Let structure emerge organically. If you impose a structure from the
> start you constrain the nuanced relationship between ideas."

His **Map of Contents** — an overview note aggregating related notes as the
system grows — is the derived index, written by hand only because Obsidian
will not write it for you.

## 3. Two tools that automate it

Both are other people's MIT-licensed projects, credited in
[the README](../README.md#credits). Neither cites Luhmann. Both land on his
arrangement anyway.

**[LLM Wiki][llmwiki]** makes the rules mechanical:

- `raw/` is **immutable**. An upstream page changed? Ingest the new revision
  as a *new* file. Never overwrite, never rename — path-based source
  resolution depends on the filenames.
- Every `_index.md` is a **derived cache**, rebuilt on read when stale.
  Parallel research agents deliberately skip writing indexes, precisely
  because an index is not truth.
- `log.md` is **append-only, never read-modify-write** — which is what makes
  concurrent sessions safe at all.

The payoff is concrete: ten agents can research a topic in parallel and
still produce one coherent article, because ingestion is parallel-safe
(unique filenames) and compilation is a single sequential pass over
everything.

**[BMAD][bmad]** applies it to specifications:

- `.memlog.md` is append-only.
- `SPEC.md` is **derived from it on every run**. A hand-edit to `SPEC.md` is
  unsupported and is overwritten on the next derive.

The payoff is again concrete, and it is the thing people actually want from
a spec process: a PRD, a UX document and an architecture decision can be fed
in **in any order**, because nothing is ever merged — it is re-derived. The
ordering problem that makes most spec workflows brittle simply does not
arise.

## 4. This harness

The paper this repo implements ([arXiv 2608.27454][paper]) separates agent
experience into three layers, and they are the same three:

| Layer | Rule |
|---|---|
| `raw/` | immutable execution traces |
| `wiki/patterns/` | compounding knowledge, **never rolled back** |
| `skills/` | derived, discarded freely |

Two details are where the argument stops being an analogy and becomes
load-bearing.

**The wiki is never rolled back.** When a proposed skill fails its
validation gate, the skill is discarded and the patterns that motivated it
*stay*. That asymmetry is the whole mechanism: a failed conclusion does not
cost you the evidence, so the next attempt starts from more than the last
one did. `WikiStore` has no delete method at all — rollback cannot reach
that layer because there is no API by which it could.

**Rollback is "never move HEAD."** Skill sets are immutable and
content-addressed; a rejected candidate simply never becomes current. There
is no undo path, so there is no undo path to get wrong.

---

## Why bother stating this

Because the two rules are cheap to state and constantly violated, usually
by a well-meant convenience:

- An agent that edits its own notes in place, so you cannot tell what it
  originally observed.
- A summary file someone improved by hand, so it can never be regenerated.
- A cache treated as a source because it was more convenient to read.
- A spec hand-merged from three documents, so nobody can say which decision
  came from where.

Each is locally reasonable. Each converts a system that compounds into one
that churns — and the damage is invisible until you need to re-derive
something and find that you cannot.

## What is argued here versus what is measured

Worth separating, because they are not the same claim.

**Measured:** a skill set evolved under a validation gate took a held-out
split from 0.400 to 1.000. See [RESULTS.md](RESULTS.md), including the
caveats — five test tasks, and convergence in a single iteration shows that
*a skill helps*, not that knowledge compounds across iterations.

**Argued, not measured:** the compounding claim itself. It rests on four
systems that independently arrived at the same arrangement, and on one
paper's ablations. A benchmark whose quirks *interact* — where the second
insight only pays off once the first exists — is what would turn it into
evidence, and it is the most valuable thing anyone could add to this repo.
See [EXTENDING.md](EXTENDING.md).

I would rather say that plainly than let a tidy argument imply a result it
has not earned.

---

## Sources

- **Zettelkasten** — Niklas Luhmann's method, 1950s.
  [Overview][zk]
- **Building a Second Brain** — Tiago Forte. CODE and PARA.
  [fortelabs.com][forte]
- **A practical Obsidian walkthrough** — [Bryan Hogan][hogan]. The method is
  Luhmann's; the post is a clear demonstration of the principles in a real
  tool.
- **LLM Wiki** — nvk, MIT. [github.com/nvk/llm-wiki][llmwiki]
- **BMAD-METHOD** — bmad-code-org, MIT.
  [github.com/bmad-code-org/BMAD-METHOD][bmad]
- **WikiSkill** — [arXiv 2608.27454][paper]

[hogan]: https://bryanhogan.com/blog/obsidian-zettelkasten
[zk]: https://www.todoist.com/productivity-methods/zettelkasten-method
[forte]: https://fortelabs.com/blog/basboverview/
[llmwiki]: https://github.com/nvk/llm-wiki
[bmad]: https://github.com/bmad-code-org/BMAD-METHOD
[paper]: https://arxiv.org/html/2608.27454
