## Why

Billing converts invoice amounts by hand from a spreadsheet at month end, and
two people routinely get two answers because they round differently. A single
containerised function that uses the agreed rates file and finance's rounding
rule removes the disagreement. Traces to `prd.md` (OPS-1432).

## What Changes

- Add an HTTP function `GET /convert` that converts an amount between two
  ISO 4217 currencies using a checked-in `rates.json`, rounding half to even.
- Add `GET /healthz` for ops.
- Define the error contract: 400 `invalid_amount`, 404 `unknown_currency`,
  404 `not_found`, 405 `method_not_allowed`.
- Package it as a `python:3.12-slim` image that runs as a non-root user on
  port 8080 (`PORT` overrides).

## Capabilities

### New Capabilities

- `fx`: currency conversion over HTTP, its error contract, and its
  container packaging.

### Modified Capabilities

None.

## Impact

New code only: `impl/app.py`, `impl/rates.json`, `impl/Dockerfile`. No
third-party dependencies. Billing's invoicing job is the only caller.
