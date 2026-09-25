# Tasks

## 1. Conversion

- [x] 1.1 Load `rates.json` into `Decimal`s once, in `FxApp.__init__`
- [x] 1.2 `GET /convert` with cross rates through USD
- [x] 1.3 Quantize result (2 dp) and rate (6 dp) with `ROUND_HALF_EVEN`

## 2. Error contract

- [x] 2.1 400 `invalid_amount` for missing, non-decimal, non-finite, negative
- [x] 2.2 404 `unknown_currency` naming the offending code
- [x] 2.3 404 `not_found` and 405 `method_not_allowed`

## 3. Operations

- [x] 3.1 `GET /healthz`
- [x] 3.2 `PORT` override, default 8080
- [x] 3.3 Dockerfile: `python:3.12-slim`, non-root `USER`, `EXPOSE 8080`

## 4. Verification

- [x] 4.1 One test per scenario, each naming its scenario
- [x] 4.2 `spec_fidelity.py` passes all three stages
