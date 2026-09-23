---
name: records-output
description: Canonical output formats and lookup rules for the records service.
---

Apply these to every answer. State the rule, never a remembered value.

1. **Record ids** — normalise to the canonical uppercase `REC-` form before
   any fetch or output. Search returns lowercase; `fetch` does not accept it.

2. **Search** — results paginate at three hits. If the response says more
   pages exist, request page 2 before concluding. A first-page hit is not
   automatically the right record.

3. **Timestamps** — ISO-8601: `T` separator, trailing Z.
   `2026-03-04 11:02:33` becomes `2026-03-04T11:02:33Z`.

4. **Amounts** — round half-to-even at two decimals, never half-up.
   `2.345` becomes `2.34`; `2.355` becomes `2.36`. Compute on the exact
   decimal string, not a float.

5. **Idempotency key** — the record id and the operation joined by a colon:
   `<record_id>:<operation>`. Record REC-4840 with operation reconcile gives
   `REC-4840:reconcile`. Never append a date, counter, or random suffix.
