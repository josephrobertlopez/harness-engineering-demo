# Lesson 5 — Feeders and personas: the menu, and who uses what

## The feeders are a menu, not a sequence

All of these skills feed into the spec. They are options to consider, not a
required chain:

| feeder | what it does | typical input |
|---|---|---|
| `bmad-brainstorming` | explore the problem space, generate options | rough problem statement |
| `bmad-forge-idea` | shape a nebulous idea into something concrete | "I have a hunch but no structure" |
| `bmad-deep-recon` | deep research: competitive, market, technical | domain you know nothing about |
| `bmad-product-brief` | light PRD for scope-setting | thin initial idea |
| `bmad-prfaq` | press release / FAQs to pressure-test the idea | idea that feels right but needs socializing |
| `bmad-prd` | full product requirements document | idea ready for detail, or existing partial docs |
| `bmad-ux` | UX research and flows | product with interface questions |
| `bmad-architecture` | system design decisions and trade-offs | spec with technical unknowns |

Pick the feeders that answer your actual questions. If your idea is already
clear but the architecture is fuzzy, run `bmad-architecture` alone. If you
need to prove the business case, run `bmad-prd`. Do not run all eight because
they are on the list.

## The architecture inclusion test

Architecture is the exception: you should think carefully before skipping it.

Ask: **"If two teams built this independently, could they choose
incompatibly?"**

If yes, the call is non-obvious, and it is a real trade-off → run
`bmad-architecture`. Get Winston's work. Feed it to the spec.

If no (you have clear contracts, each team's domain is distinct) → skip it,
you do not need it.

Example: "Two teams adding two different payment methods." Without architecture
work, one team chooses Stripe webhooks, the other chooses polling. Conflict.
Architecture forces the choice early.

## The five personas

Every skill is written by one of five personas. Knowing which agent you are
talking to and what phase they own helps you know what to expect.

| persona | phase | job | style |
|---|---|---|---|
| Mary | analysis | market/competitive research | asks "what do competitors do?" and "what is the gap?" |
| John | planning | product requirements | thinks in features and success metrics |
| Winston | planning | system architecture | answers with trade-offs, not verdicts |
| Amelia | implementation | engineering, TDD, specs | speaks in file paths and acceptance criteria IDs |
| Sally | planning | UX design and flows | thinks in tasks, not features |

An agent (a persona bundled into a skill) is a **guide who knows a whole
phase**. A skill is just the job. When you run `bmad-deep-recon`, you are
calling Mary. When you run `bmad-build`, you are calling Amelia.

## Example: I run `bmad-prd`

You are invoking John. John thinks in products and features. He reads your
current spec and outputs a more detailed PRD: capabilities decomposed,
success metrics, edge cases called out.

Feed that PRD back to the spec:

```bash
bmad-spec
# Paste the new prd.md content
```

The spec grows with John's detail. Now when you run `bmad-build`, Amelia
reads the richer spec and can make better engineering decisions.

## Example: `CR` is ambiguous

The menu codes within an agent can collide. `CR` means:

- "Competitive research" if you are in `bmad-deep-recon` (Mary)
- "Code review" if you are in `bmad-build` (Amelia)

Look at which skill you are in, and which persona owns it, to know which
code applies.

## How to choose feeders

**Start with the spec.** If it is clear enough to build from, stop. Do not
add feeders "just in case."

If the spec is missing something:

- **Missing business context?** Run `bmad-product-brief` or `bmad-prd`.
- **Missing design?** Run `bmad-ux`.
- **Missing architecture?** Run the inclusion test (lesson 4). If yes, run
  `bmad-architecture`.
- **Want to stress-test the idea before starting?** Run `bmad-prfaq`.
- **Exploring a new market or competitor space?** Run `bmad-deep-recon`.

Feed the output back to the spec. The spec grows. Run `bmad-build` when it
is enough.

## What a feeder outputs

Feeders output their work as markdown. You copy it and feed it to `bmad-spec`:

```bash
bmad-spec
# Paste the markdown (prd, architecture doc, ux flows, whatever)
```

`bmad-spec` appends it to the memlog and re-derives the spec to incorporate
it. The spec is now richer.

No skill writes directly to `SPEC.md`. Everything goes through the memlog.

---

You now have the map. The spec is the hub. Feeders are options. Two routes
exist; pick one. Build with `bmad-build` when you have enough spec.

The rest is judgment: which feeders answer your questions? Which route is
suitable for your work? Those are human decisions, and the harness stays out
of them.
