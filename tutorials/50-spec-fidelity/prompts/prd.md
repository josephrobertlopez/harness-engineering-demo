---
description: Step 2 - write prd.md from the ticket and the interview, then judge it
allowed-tools: Bash({{PYTHON}} {{JUDGE}}:*), Read, Write, Edit
---

Write `prd.md` from `ticket.md` and `interview.md`. The interview is the
only source of decisions; the ticket only says what problem exists.

Format, exactly:

- `# PRD — <title> (<ticket id>)`
- `## Problem`, `## Users`, `## Requirements`, `## Non-goals`,
  `## Open questions` — these headings, this spelling.
- Each requirement is `### PRD-<n>: <title>` (n = 1, 2, 3 …, no leading
  zeros) followed by:
  - one or more sentences stating behaviour with **SHALL** or **MUST**;
  - at least one acceptance line of the form
    `- WHEN <situation> THEN <observable result>`;
  - `Source: interview.md Q<n>` naming the answer(s) it came from.
- Every exact value the product owner gave — numbers, status codes, error
  strings, file names, model ids, command lines — appears verbatim.
- Inside requirements, do not use these words: the `vague_terms` listed in
  `rubric.json`. Replace each with the behaviour or number it stood for.
- Anything the product owner declined to decide goes in Non-goals. Open
  questions lists only questions that were *resolved*, each with where it
  was resolved (e.g. `"Should be fast" → PRD-3`). Never leave `TBD`.
- Do not add a requirement that no interview answer supports.

Then run the judge and fix what it reports:

!`{{PYTHON}} {{JUDGE}} . --stage prd --exit-zero`

The output above is the judge's report on the PRD *before* your edits. After
writing or editing `prd.md`, run `{{PYTHON}} {{JUDGE}} . --stage prd` again
yourself. Repeat until it passes, at most three rounds.

**If a finding says the PRD "does not pin down" something, do not invent
it.** It means a question was never asked. Stop, tell me which question to
ask, and wait — the fix is `/fidelity:interrogate`, not a guess.
