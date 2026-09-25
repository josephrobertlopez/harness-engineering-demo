# What the product owner said when asked

You get these answers **only by asking**. In a real team this is a Slack
thread or a ten-minute call; here it is written down so every learner gets
the same answers and the judge can check your PRD against them.

The questions are the ones the Interrogator persona
(`personas/spec-interrogator.persona.md`) should lead you to. If you did not
think to ask one of them, that is the lesson — notice which.

**Q1. "Call over REST" — what is the request and the response?**
`GET /convert?amount=<decimal>&from=<code>&to=<code>`, currency codes are
ISO 4217 upper-case (`USD`, `EUR`). A 200 returns JSON
`{"amount": "100.00", "from": "USD", "to": "EUR", "rate": "0.920000", "result": "92.00"}`.
Money values are **strings**, never JSON floats — billing has been burned by
`0.1 + 0.2` before.

**Q2. "The usual rates" — from where?**
From `rates.json`, checked in next to the function: one rate per currency,
expressed per 1 USD. Cross rates (GBP→EUR) go through USD. Billing replaces
the file and redeploys at month end. **No network calls**, ever.

**Q3. How is the result rounded?**
To 2 decimal places using banker's rounding (round half to even,
`ROUND_HALF_EVEN`). Finance audits against that. The `rate` field is shown
to 6 decimal places, same rounding. The result is computed from the
unrounded rate.

**Q4. "Should be fast" — what does fast mean?**
Nobody has a latency number. What billing actually means: the rates file is
read **once at startup**, not per request, so a request never touches disk
or network.

**Q5. "Handle errors properly" — which errors, which responses?**

- `amount` missing, not a number, NaN/Infinity, or negative → **400**
  `{"error": "invalid_amount"}`
- `from` or `to` missing or not in the rates file → **404**
  `{"error": "unknown_currency", "currency": "<the code>"}`
- any other path → **404** `{"error": "not_found"}`
- any method other than GET → **405** `{"error": "method_not_allowed"}`

**Q6. How does ops know it is alive?**
`GET /healthz` → 200 `{"status": "ok"}`.

**Q7. "Runs anywhere" and "secure" — what do you actually need?**
An image built `FROM python:3.12-slim`, listening on port **8080** by
default, overridable with the `PORT` environment variable. The container
runs as a **non-root** user. No third-party packages (nothing to patch).
It sits on the internal network, so **no authentication** — that is a
non-goal, not an oversight.

**Q8. What is out of scope?**
Live rates, authentication, POST or batch conversion, a list-currencies
endpoint, and any UI.
