# Notes on context engineering

Working notes, not a manifesto. I built a harness to answer one question —
*does the context I just added actually pay for itself?* — and while
building it I kept running into the same arrangement in tools that have
nothing to do with each other. These are those notes, with the measured
parts and the hand-wavy parts labelled.

## Start with the measured bit

A skill is curated context. The paper this repo implements
([arXiv 2608.27454][paper]) ran the ablation that matters, and the result
is not what you would guess:

| what the agent can read | average score |
|---|---|
| distilled skills only | **63.7%** |
| skills **plus** the notes those skills came from | 60.9% |
| nothing | 48.7% |

More context, worse output. The notes are the raw material the skills were
distilled *from*, and handing them to the agent as well costs almost three
points.

That has a practical consequence I have come to trust more than most
prompting advice: **the win is in the distillation, not in the material.**
Adding the source alongside the summary is not a hedge, it is a
regression — and you would never catch it without something that measures.

This repo enforces the separation structurally rather than by convention.
`InferenceAgent` takes no wiki handle, `agents/inference.py` does not import
the wiki layer, and `tests/test_no_wiki_leak.py` fails if anyone adds one.
A prompt instruction saying "don't look at the notes" would be one refactor
from being false.

## The arrangement I kept running into

Here I am on much thinner ice, so take it as an observation rather than a
finding. Keep the thing you **edit** separate from the thing you **read**:

```
  capture  ──────►  compile  ──────►  use
  immutable         derived          derived
  only appended     not hand-        regenerated
                    maintained       freely
```

Two rules, and they are easier to state than to keep:

1. **Do not edit the source.** New information is a new entry, not a
   revision. Otherwise you cannot re-derive when your conclusions turn out
   wrong, because the record of what you actually saw is gone.
2. **Do not hand-maintain the derived thing.** The moment an index or a
   summary is hand-edited it stops being regenerable — the next rebuild
   either destroys the edit or gets abandoned.

Both prevent one failure: a file that is at once the evidence and the
conclusion. You cannot revise it without losing its basis, and you cannot
regenerate it without losing your thinking.

I did not invent any of this and did not set out to apply it. I noticed the
resemblance partway through and went looking for prior art, which is the
honest order of events and probably why the connections below are looser
than they would be if someone had designed for them.

---

## Where it comes from: Zettelkasten (1950s)

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

## And again: Second Brain (2022)

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

## Two tools that automate it

Both are other people's MIT-licensed projects, credited in
[the README](../README.md#credits). Neither cites Luhmann, and I am not
suggesting either author was influenced by him — more likely the constraint
is just real enough that you end up here if you build carefully.

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

## And this harness

The paper this repo implements ([arXiv 2608.27454][paper]) separates agent
experience into three layers, and they are the same three:

| Layer | Rule |
|---|---|
| `raw/` | immutable execution traces |
| `wiki/patterns/` | compounding knowledge, **never rolled back** |
| `skills/` | derived, discarded freely |

Two details are where this stops being a resemblance and starts doing
actual work.

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
