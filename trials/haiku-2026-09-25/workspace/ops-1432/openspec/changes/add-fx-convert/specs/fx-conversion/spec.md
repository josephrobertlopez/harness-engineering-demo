# FX Conversion API Service Specification

## ADDED Requirements

### Requirement: Currency Conversion Endpoint

The service SHALL provide a currency conversion endpoint accessible via `GET /convert?amount=<decimal>&from=<code>&to=<code>`. The endpoint accepts exactly three required query parameters: `amount` (a decimal number), `from` (an ISO 4217 currency code), and `to` (an ISO 4217 currency code). Query parameters MAY be provided in any order. The path `/convert/` with trailing slash SHALL be treated identically to `/convert`.

Trace: PRD-1

#### Scenario: Valid conversion with standard parameters

- **WHEN** GET /convert?amount=100&from=USD&to=EUR is requested
- **THEN** response is HTTP 200 with body exactly `{"amount": "100.00", "from": "USD", "to": "EUR", "rate": "0.920000", "result": "92.00"}` and Content-Type header `application/json; charset=utf-8`

#### Scenario: Query parameters in different order

- **WHEN** GET /convert?from=USD&to=EUR&amount=100 is requested
- **THEN** response is identical to valid conversion scenario

#### Scenario: Trailing slash on convert path

- **WHEN** GET /convert/ (with trailing slash) is requested with valid parameters
- **THEN** it is treated identically to GET /convert

#### Scenario: Invalid amount - missing parameter

- **WHEN** GET /convert?from=USD&to=EUR (amount parameter missing)
- **THEN** response is HTTP 400 with body exactly `{"error": "invalid_amount"}` and Content-Type header `application/json; charset=utf-8`

#### Scenario: Invalid amount - not a number

- **WHEN** GET /convert?amount=abc&from=USD&to=EUR
- **THEN** response is HTTP 400 with body exactly `{"error": "invalid_amount"}`

#### Scenario: Invalid amount - NaN or Infinity

- **WHEN** GET /convert?amount=NaN&from=USD&to=EUR or amount=Infinity
- **THEN** response is HTTP 400 with body exactly `{"error": "invalid_amount"}`

#### Scenario: Invalid amount - negative value

- **WHEN** GET /convert?amount=-100&from=USD&to=EUR
- **THEN** response is HTTP 400 with body exactly `{"error": "invalid_amount"}`

#### Scenario: Invalid amount - exceeds maximum (1 trillion)

- **WHEN** GET /convert?amount=1000000000001&from=USD&to=EUR
- **THEN** response is HTTP 400 with body exactly `{"error": "invalid_amount"}`

#### Scenario: Unknown currency - missing parameter

- **WHEN** GET /convert?amount=100&from=USD (to parameter missing)
- **THEN** response is HTTP 404 with body exactly `{"error": "unknown_currency", "currency": ""}` and Content-Type header `application/json; charset=utf-8`

#### Scenario: Unknown currency - code not in rates

- **WHEN** GET /convert?amount=100&from=XYZ&to=EUR (XYZ not in rates.json)
- **THEN** response is HTTP 404 with body exactly `{"error": "unknown_currency", "currency": "XYZ"}`

#### Scenario: Non-GET HTTP method

- **WHEN** POST /convert?amount=100&from=USD&to=EUR
- **THEN** response is HTTP 405 with body exactly `{"error": "method_not_allowed"}` and Content-Type header `application/json; charset=utf-8`

---

### Requirement: Rate Data Source and In-Memory Loading

The service SHALL load currency exchange rates from a file named `rates.json` located next to the service at startup. Each rate is expressed as the amount of that currency equal to 1 USD. The rates SHALL be loaded into memory once at startup and remain unchanged during operation. The service SHALL make no network calls to fetch or verify rates at runtime.

Trace: PRD-2

#### Scenario: Service reads rates.json on startup

- **WHEN** the service process starts
- **THEN** it reads rates.json and loads all rates into memory

#### Scenario: No network calls during conversion

- **WHEN** a conversion is requested after startup
- **THEN** no external network calls are made to fetch or verify rates

#### Scenario: New rates used after redeployment

- **WHEN** billing replaces rates.json and redeploys the service
- **THEN** the new rates are used for all subsequent conversions

#### Scenario: Cross-rate conversion through USD

- **WHEN** converting between two non-USD currencies (e.g., GBP to EUR)
- **THEN** the conversion is performed by going through USD as an intermediate currency

---

### Requirement: Response Format, Field Types, and Rounding

The service SHALL return all conversion results as JSON with exactly these fields in this order: `amount`, `from`, `to`, `rate`, `result`. All monetary values (`amount` and `result`) and the rate field SHALL be represented as strings, never as JSON numbers. All values SHALL be rounded using banker's rounding (ROUND_HALF_EVEN): `amount` and `result` to exactly 2 decimal places, and `rate` to exactly 6 decimal places. The rate shown in the response is the exact unrounded rate value from the rates file, displayed to exactly 6 decimal places using banker's rounding; the actual conversion computation uses the full unrounded rate value, not the rounded display value.

Trace: PRD-3

#### Scenario: Response has exactly required fields

- **WHEN** a valid conversion is requested
- **THEN** the response body contains exactly these fields: `amount`, `from`, `to`, `rate`, `result` with no additional fields

#### Scenario: Monetary values are strings

- **WHEN** a valid conversion is requested
- **THEN** the response fields `amount`, `from`, `to`, `rate`, and `result` are all strings, never JSON numbers

#### Scenario: Banker's rounding is applied

- **WHEN** a monetary value requires rounding
- **THEN** banker's rounding (ROUND_HALF_EVEN) is applied and the result is displayed with exactly the specified decimal places

#### Scenario: Amounts displayed with 2 decimal places

- **WHEN** converting amounts
- **THEN** `amount` and `result` fields are displayed with exactly 2 decimal places (e.g., "100.00", "92.00")

#### Scenario: Rates displayed with 6 decimal places

- **WHEN** a rate is displayed in the response
- **THEN** the `rate` field displays the unrounded rate from rates.json formatted to exactly 6 decimal places

#### Scenario: Rate field uses unrounded value for computation

- **WHEN** a conversion is computed and the rate is displayed
- **THEN** the computation uses the full unrounded rate value from the file, and the displayed `rate` field shows that value rounded to 6 decimal places

---

### Requirement: Unknown Path Handling

The service SHALL return an HTTP 404 error with a JSON error response for any GET request to a path that is not `/convert`, `/convert/`, or `/healthz` (or `/healthz/`). The Content-Type response header SHALL be `application/json; charset=utf-8`.

Trace: PRD-4

#### Scenario: Unknown path returns 404

- **WHEN** a GET request is made to an unknown path (e.g., `/foo` or `/convert/extra`)
- **THEN** the response is HTTP 404 with body exactly `{"error": "not_found"}` and Content-Type header `application/json; charset=utf-8`

---

### Requirement: Health Check Endpoint

The service SHALL provide a `GET /healthz` endpoint (and `/healthz/` with trailing slash treated identically) that returns HTTP 200 with a JSON response indicating the service is operational. The Content-Type response header SHALL be `application/json; charset=utf-8`.

Trace: PRD-5

#### Scenario: Health check endpoint returns ok

- **WHEN** GET /healthz is called
- **THEN** the response is HTTP 200 with body exactly `{"status": "ok"}` and Content-Type header `application/json; charset=utf-8`

#### Scenario: Health check with trailing slash

- **WHEN** GET /healthz/ (with trailing slash) is called
- **THEN** the response is identical to the standard health check scenario

---

### Requirement: Docker Base Image

The service Docker image SHALL be built using `FROM python:3.12-slim` as the base image.

Trace: PRD-6

#### Scenario: Dockerfile uses python:3.12-slim

- **WHEN** the Dockerfile is built
- **THEN** it uses python:3.12-slim as the base image

---

### Requirement: Network Port Configuration

The service SHALL listen on TCP port 8080 by default. The port SHALL be overridable via the `PORT` environment variable.

Trace: PRD-7

#### Scenario: Default port is 8080

- **WHEN** the service starts without a PORT environment variable
- **THEN** it listens on TCP port 8080

#### Scenario: PORT environment variable overrides default

- **WHEN** the service starts with PORT=9000 (or any other valid port number)
- **THEN** it listens on the specified port instead of 8080

---

### Requirement: Container Execution and Package Constraints

The service container SHALL run as a non-root user. The Docker image SHALL be built with no third-party packages installed: no additional Python packages (via pip or otherwise), and no additional system packages (via apt-get or other package managers). Only the Python 3.12 runtime and standard library from the base `python:3.12-slim` image are included.

Trace: PRD-8

#### Scenario: Container process runs as non-root user

- **WHEN** the container is started
- **THEN** the process runs as a non-root user

#### Scenario: No third-party Python packages

- **WHEN** the Dockerfile is built
- **THEN** no third-party Python packages are installed (e.g., no pip packages beyond Python's standard library)

#### Scenario: No additional system packages

- **WHEN** the Dockerfile is built
- **THEN** no additional system packages are installed (e.g., no apt-get install commands beyond the base python:3.12-slim image)
