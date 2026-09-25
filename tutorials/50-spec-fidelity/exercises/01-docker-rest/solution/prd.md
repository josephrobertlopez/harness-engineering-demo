# PRD — FX conversion function (OPS-1432)

Source ticket: `ticket.md` (OPS-1432). Every requirement below cites the
stakeholder answer it came from, so a reviewer can tell a decision from a
guess.

## Problem

Billing converts invoice amounts between currencies by hand at month end,
using a rates table that lives in a spreadsheet. Two people get two answers
because they round differently. They want one function, callable over HTTP
from their invoicing job, that uses the month's agreed table and rounds the
way finance audits.

## Users

- **Billing's invoicing job** — the only caller. Machine-to-machine, internal
  network.
- **Ops** — deploys the container and watches its health.

## Requirements

### PRD-1: Convert an amount

The service SHALL answer `GET /convert?amount=<decimal>&from=<code>&to=<code>`
with 200 and a JSON object carrying `amount`, `from`, `to`, `rate` and
`result`. Money values and the rate MUST be JSON strings, never numbers.
Cross rates (neither side USD) MUST be computed through USD.

- WHEN billing requests 100 USD to EUR THEN the response is 200 with
  `"result": "92.00"` and `"rate": "0.920000"`.
- WHEN billing requests 100 GBP to EUR THEN the result is `"116.46"`.

Source: stakeholder-answers.md Q1, Q2.

### PRD-2: Round the way finance audits

The result SHALL be rounded to 2 decimal places with banker's rounding
(`ROUND_HALF_EVEN`), computed from the unrounded rate. The rate SHALL be
shown to 6 decimal places with the same rule.

- WHEN the unrounded result is exactly 0.125 THEN the result is `"0.12"`.
- WHEN the unrounded result is exactly 0.135 THEN the result is `"0.14"`.
- WHEN the unrounded result is exactly 2.675 THEN the result is `"2.68"`
  (a binary float gives 2.67, which is why money is never a float).

Source: stakeholder-answers.md Q3.

### PRD-3: Rates come from a file read once at startup

The service SHALL load rates from `rates.json` (one rate per currency, per
1 USD) once at startup and MUST NOT read the file or make any network call
while serving a request.

- WHEN the rates file is deleted after startup THEN conversions still
  succeed with the rates loaded at startup.

Source: stakeholder-answers.md Q2, Q4.

### PRD-4: Reject an invalid amount

The service SHALL respond 400 `{"error": "invalid_amount"}` when `amount`
is missing, not a decimal, NaN or Infinity, negative, or larger than
1,000,000,000,000.

- WHEN `amount` is absent THEN the response is 400 `invalid_amount`.
- WHEN `amount` is `-5` THEN the response is 400 `invalid_amount`.
- WHEN `amount` is `ten` THEN the response is 400 `invalid_amount`.
- WHEN `amount` is `1e30` THEN the response is 400 `invalid_amount`.

Source: stakeholder-answers.md Q5.

### PRD-5: Reject an unknown currency

The service SHALL respond 404 `{"error": "unknown_currency", "currency": "<code>"}`
when `from` or `to` is missing or not in the rates file.

- WHEN `to` is `XYZ` THEN the response is 404 with `"currency": "XYZ"`.

Source: stakeholder-answers.md Q5.

### PRD-6: Unsupported routes and methods

The service SHALL respond 404 `{"error": "not_found"}` for any path other
than `/convert` and `/healthz`, and 405 `{"error": "method_not_allowed"}`
for any method other than GET, HEAD and OPTIONS included.

- WHEN a client requests `GET /rates` THEN the response is 404 `not_found`.
- WHEN a client sends `POST /convert` THEN the response is 405.
- WHEN a client sends `HEAD` or `OPTIONS` THEN the response is 405.

Source: stakeholder-answers.md Q5.

### PRD-7: Health check

The service SHALL answer `GET /healthz` with 200 `{"status": "ok"}`.

- WHEN ops requests `/healthz` THEN the response is 200 `{"status": "ok"}`.

Source: stakeholder-answers.md Q6.

### PRD-8: Container packaging

The function SHALL ship as an image built `FROM python:3.12-slim` that
listens on port 8080 unless the `PORT` environment variable overrides it,
runs as a non-root user, and installs no third-party packages.

- WHEN the container starts with no `PORT` set THEN it listens on 8080.
- WHEN `PORT=9090` is set THEN it listens on 9090.
- WHEN the Dockerfile is inspected THEN its final `USER` is not root.

Source: stakeholder-answers.md Q7.

## Non-goals

- Live or fetched rates — the file is the contract.
- Authentication — internal network only (Q7). A decision, not a gap.
- POST, batch conversion, a list-currencies endpoint, any UI (Q8).
- A latency target. "Fast" was resolved to PRD-3; nobody could name a
  number, and inventing one would be a requirement nobody asked for.

## Open questions

None open. Resolved during review:

- "Should be fast" → PRD-3 (no per-request I/O). Resolved with the PO.
- "Handle errors properly" → PRD-4, PRD-5, PRD-6. Resolved with the PO.
- "Should be secure" → PRD-8 non-root, plus the auth non-goal. Resolved.
