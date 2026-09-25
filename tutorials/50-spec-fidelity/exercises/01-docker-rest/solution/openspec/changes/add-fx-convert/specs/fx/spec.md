## ADDED Requirements

### Requirement: Currency conversion endpoint

The service SHALL answer `GET /convert?amount=<decimal>&from=<code>&to=<code>`
with status 200 and a JSON object containing `amount`, `from`, `to`, `rate`
and `result`, where money values and the rate are JSON strings. A conversion
where neither side is USD MUST be computed through USD.

Trace: PRD-1

#### Scenario: Convert USD to EUR

- **WHEN** a client requests `GET /convert?amount=100&from=USD&to=EUR`
- **THEN** the status is 200
- **AND** the body is `{"amount": "100.00", "from": "USD", "to": "EUR", "rate": "0.920000", "result": "92.00"}`

#### Scenario: Cross rate through USD

- **WHEN** a client requests `GET /convert?amount=100&from=GBP&to=EUR`
- **THEN** the result is `"116.46"`

### Requirement: Half-to-even rounding

The service SHALL round `result` to 2 decimal places and `rate` to 6 decimal
places using round-half-to-even, computing `result` from the unrounded rate.

Trace: PRD-2

#### Scenario: Tie rounds down to even

- **WHEN** a client converts `0.125` USD to USD
- **THEN** the result is `"0.12"`

#### Scenario: Tie rounds up to even

- **WHEN** a client converts `0.135` USD to USD
- **THEN** the result is `"0.14"`

#### Scenario: Tie a float cannot represent

- **WHEN** a client converts `2.675` USD to USD
- **THEN** the result is `"2.68"`, where binary floating point gives `"2.67"`

### Requirement: Rates loaded once at startup

The service SHALL read `rates.json` once at startup and MUST NOT read it, or
make any network call, while serving a request.

Trace: PRD-3

#### Scenario: Rates file removed after startup

- **GIVEN** the service started with a valid rates file
- **WHEN** the file is deleted and a client requests a conversion
- **THEN** the conversion succeeds using the rates loaded at startup

### Requirement: Invalid amount rejected

The service SHALL respond 400 `{"error": "invalid_amount"}` when `amount` is
missing, not a decimal, not finite, negative, or larger than
1,000,000,000,000.

Trace: PRD-4

#### Scenario: Missing amount

- **WHEN** a client requests `GET /convert?from=USD&to=EUR`
- **THEN** the status is 400 and the error is `invalid_amount`

#### Scenario: Negative amount

- **WHEN** a client requests `GET /convert?amount=-5&from=USD&to=EUR`
- **THEN** the status is 400 and the error is `invalid_amount`

#### Scenario: Non-numeric amount

- **WHEN** `amount` is `ten` or `NaN`
- **THEN** the status is 400 and the error is `invalid_amount`

#### Scenario: Amount too large

- **WHEN** `amount` is `1e30`, or `1000000000000.01`
- **THEN** the status is 400 and the error is `invalid_amount`

### Requirement: Unknown currency rejected

The service SHALL respond 404 `{"error": "unknown_currency", "currency": "<code>"}`
when `from` or `to` is missing or absent from the rates file.

Trace: PRD-5

#### Scenario: Unknown target currency

- **WHEN** a client requests `GET /convert?amount=1&from=USD&to=XYZ`
- **THEN** the status is 404 and the body names `"currency": "XYZ"`

### Requirement: Unsupported routes and methods

The service SHALL respond 404 `{"error": "not_found"}` to any path other than
`/convert` and `/healthz`, and 405 `{"error": "method_not_allowed"}` to any
method other than GET, whichever HTTP method it is.

Trace: PRD-6

#### Scenario: Unknown path

- **WHEN** a client requests `GET /rates`
- **THEN** the status is 404 and the error is `not_found`

#### Scenario: Wrong method

- **WHEN** a client sends `POST /convert`
- **THEN** the status is 405 and the error is `method_not_allowed`

#### Scenario: Every other method is refused

- **WHEN** a client sends `HEAD`, `OPTIONS`, `PUT`, `PATCH`, `DELETE`, `TRACE` or `CONNECT`
- **THEN** the HTTP server answers 405, never 501

### Requirement: Health check

The service SHALL answer `GET /healthz` with status 200 and `{"status": "ok"}`.

Trace: PRD-7

#### Scenario: Health check responds

- **WHEN** ops requests `GET /healthz`
- **THEN** the status is 200 and the body is `{"status": "ok"}`

### Requirement: Container packaging

The function SHALL ship as an image built `FROM python:3.12-slim`, running as
a non-root user, installing no third-party packages, and listening on port
8080 unless `PORT` overrides it.

Trace: PRD-8

#### Scenario: Default port

- **WHEN** the service starts with no `PORT` set
- **THEN** it listens on 8080

#### Scenario: Port override

- **WHEN** the service starts with `PORT=9090`
- **THEN** it listens on 9090

#### Scenario: Non-root image

- **WHEN** the Dockerfile is inspected
- **THEN** it builds from `python:3.12-slim`, its last `USER` is not root, and it runs no `pip install`
