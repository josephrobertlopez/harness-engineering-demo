# PRD — Dockerize the FX conversion function (OPS-1432)

## Problem

Billing needs a REST API to convert invoice amounts between currencies. The current process requires manual lookups or external API calls, which is slow and not integrated into their workflow.

## Users

Billing team at the organization, calling the service from internal systems to convert amounts between currencies.

## Requirements

### PRD-1: Currency conversion endpoint, query parameters, and responses

The service SHALL provide a currency conversion endpoint accessible via `GET /convert?amount=<decimal>&from=<code>&to=<code>`. Currency codes MUST be ISO 4217 upper-case codes. This is the only endpoint that performs currency conversions. The endpoint accepts exactly three required query parameters: `amount` (a decimal number), `from` (an ISO 4217 currency code), and `to` (an ISO 4217 currency code). Query parameters MAY be provided in any order. The path `/convert/` with trailing slash SHALL be treated identically to `/convert`.

On HTTP 200 success, the response SHALL be JSON with exactly these fields (all as strings, never as JSON numbers) and no additional fields: `{"amount": "100.00", "from": "USD", "to": "EUR", "rate": "0.920000", "result": "92.00"}`. The Content-Type response header SHALL be `application/json; charset=utf-8`.

Parameter validation rules:
- The `amount` parameter MUST be a valid decimal number, not NaN, not Infinity, not negative, and not greater than 1,000,000,000,000
- The `from` and `to` parameters MUST be ISO 4217 currency codes in upper case

Error responses:
- HTTP 400 with exact JSON `{"error": "invalid_amount"}` if amount is missing, not a number, NaN, Infinity, negative, or > 1,000,000,000,000
- HTTP 404 with exact JSON `{"error": "unknown_currency", "currency": "<the code>"}` if from or to is missing or not in rates
- HTTP 405 with exact JSON `{"error": "method_not_allowed"}` if any HTTP method other than GET is used

- WHEN GET /convert?amount=100&from=USD&to=EUR is requested THEN response is HTTP 200 with body exactly `{"amount": "100.00", "from": "USD", "to": "EUR", "rate": "0.920000", "result": "92.00"}` and Content-Type header `application/json; charset=utf-8`
- WHEN GET /convert?from=USD&to=EUR&amount=100 is requested (different parameter order) THEN response is identical to above
- WHEN GET /convert/ (with trailing slash) is requested THEN it is treated identically to GET /convert
- WHEN amount is invalid THEN response is HTTP 400 with body exactly `{"error": "invalid_amount"}` and Content-Type header `application/json; charset=utf-8`
- WHEN from or to is missing or unknown THEN response is HTTP 404 with body exactly `{"error": "unknown_currency", "currency": "<the code>"}` and Content-Type header `application/json; charset=utf-8`
- WHEN a non-GET method (POST, PUT, DELETE, etc.) is used on /convert THEN response is HTTP 405 with body exactly `{"error": "method_not_allowed"}` and Content-Type header `application/json; charset=utf-8`

Source: interview.md Q3, Q5, Q17

### PRD-2: Rate data source and in-memory loading

The service SHALL load currency exchange rates from a file named `rates.json` located next to the function at startup. Each line contains one exchange rate per currency, with each rate expressed as the amount of that currency equal to 1 USD. The rates SHALL be loaded into memory once at startup and remain unchanged during operation. The service SHALL make no network calls to fetch rates.

- WHEN the service starts THEN it reads rates.json and loads all rates into memory
- WHEN a conversion is requested THEN no external network calls are made to fetch or verify rates
- WHEN billing replaces rates.json and redeploys the service THEN the new rates are used for all subsequent conversions
- WHEN converting between two non-USD currencies (e.g., GBP to EUR) THEN the conversion is performed by going through USD as an intermediate currency

Source: interview.md Q1, Q2

### PRD-3: Response format, field types, and rounding

The service SHALL return all conversion results as JSON with exactly these fields in this order: `amount`, `from`, `to`, `rate`, `result`. All monetary values (`amount` and `result`) and the rate field SHALL be represented as strings, never as JSON numbers. All values SHALL be rounded using banker's rounding (ROUND_HALF_EVEN): `amount` and `result` to exactly 2 decimal places, and `rate` to exactly 6 decimal places. The rate shown in the response is the exact unrounded rate value from the rates file, displayed to exactly 6 decimal places using banker's rounding; the actual conversion computation uses the full unrounded rate value, not the rounded display value.

- WHEN converting 100 USD to EUR at a stored rate of 0.92 THEN the response body is exactly `{"amount": "100.00", "from": "USD", "to": "EUR", "rate": "0.920000", "result": "92.00"}` with no additional or missing fields
- WHEN a monetary value requires rounding THEN banker's rounding (ROUND_HALF_EVEN) is applied and the result is displayed with exactly the specified decimal places
- WHEN a rate is displayed in the response THEN it displays the unrounded rate from rates.json formatted to exactly 6 decimal places

Source: interview.md Q5, Q15

### PRD-4: Unknown path handling

The service SHALL return an HTTP 404 error with a JSON error response for any GET request to a path that is not `/convert`, `/convert/`, or `/healthz` (or `/healthz/`). The Content-Type response header SHALL be `application/json; charset=utf-8`.

- WHEN a GET request is made to an unknown path (e.g., `/foo` or `/convert/extra`) THEN the response is HTTP 404 with body exactly `{"error": "not_found"}` and Content-Type header `application/json; charset=utf-8`

Source: interview.md Q12

### PRD-5: Health check endpoint

The service SHALL provide a `GET /healthz` endpoint (and `/healthz/` with trailing slash treated identically) that returns HTTP 200 with a JSON response indicating the service is operational. The Content-Type response header SHALL be `application/json; charset=utf-8`.

- WHEN GET /healthz is called THEN the response is HTTP 200 with body exactly `{"status": "ok"}` and Content-Type header `application/json; charset=utf-8`
- WHEN GET /healthz/ (with trailing slash) is called THEN the response is identical to above

Source: interview.md Q11

### PRD-6: Docker base image

The service Docker image SHALL be built using `FROM python:3.12-slim` as the base image.

- WHEN the Dockerfile is built THEN it uses python:3.12-slim as the base image

Source: interview.md Q13

### PRD-7: Network port configuration

The service SHALL listen on TCP port 8080 by default. The port SHALL be overridable via the `PORT` environment variable.

- WHEN the service starts without a PORT environment variable THEN it listens on port 8080
- WHEN the service starts with PORT=9000 THEN it listens on port 9000

Source: interview.md Q13

### PRD-8: Container execution and package constraints

The service container SHALL run as a non-root user. The Docker image SHALL be built with no third-party packages installed: no additional Python packages (via pip or otherwise), and no additional system packages (via apt-get or other package managers). Only the Python 3.12 runtime and standard library from the base `python:3.12-slim` image are included.

- WHEN the container is started THEN the process runs as a non-root user
- WHEN the Dockerfile is built THEN no third-party Python packages are installed (e.g., no pip packages beyond Python's standard library)
- WHEN the Dockerfile is built THEN no additional system packages are installed (e.g., no apt-get install commands beyond the base python:3.12-slim image)

Source: interview.md Q14

## Non-goals

- Startup error handling for missing or malformed rates.json
- Precision handling for cross-rate conversions (calculation order and intermediate rounding)
- Acceptance and integration testing strategy
- Custom HTTP response headers beyond Content-Type (Cache-Control, CORS, etc.)
- Request timeout handling
- Authentication and authorization (service is internal-network only)
- Specific non-root user identity
- Handling of unknown or extra query parameters
- The service makes no external network calls, ever (confirmed for rate fetching; scope for all other calls deferred)

## Open questions

- "Should be fast" → PRD-2 (rates loaded at startup, no per-request disk/network access)
- "Should be secure" → Non-goal (internal network, no authentication required)

## Gaps Requiring Product Owner Decision

The following gaps were identified in the adversarial review and require clarification from the product owner before implementation can proceed:

### Critical (blocking implementation)
1. **Error routing priority (affects PRD-1, PRD-4)**: When a request violates both path and HTTP method rules, which error takes priority? For example, POST /foo should it return 404 (unknown path) or 405 (wrong method)?
2. **rates.json file format (affects PRD-2)**: What is the exact format of rates.json? JSON object? CSV? Space-separated? One entry per line? (Currently only stated as "one rate per currency")
3. **Input amount decimal precision (affects PRD-1)**: How many decimal places are allowed in the input `amount` parameter? (e.g., is "100.123456789" valid or must it be limited?)

### Major (affects production reliability)
4. **Currency code handling (affects PRD-1)**: What response should be returned if currency codes are provided in lowercase (e.g., `from=usd`)? 400 Bad Request or 404 Not Found?
5. **Currency code whitespace (affects PRD-1)**: Should the service trim whitespace from currency codes (e.g., `from="USD "`) or return an error?
6. **Empty/null parameter handling (affects PRD-1)**: What response should be returned if a parameter is present but empty (e.g., `?amount=&from=USD&to=EUR`)?
7. **PORT environment variable validation (affects PRD-7)**: What happens if PORT is set to invalid values? Examples: PORT=abc (non-numeric), PORT=-1 (negative), PORT=65536 (> 65535), PORT=443 (< 1024, requires root)?
8. **Rate value constraints (affects PRD-2)**: Can rates in rates.json be zero, negative, or non-numeric? What error handling is required?
9. **Network binding address (affects PRD-7)**: Should the service bind to localhost (127.0.0.1), all interfaces (0.0.0.0), or a specific address?
10. **Decimal display format (affects PRD-3)**: Should decimal values always display with trailing zeros (e.g., "92.00", "0.500000") or can they be omitted when zero?
11. **Health check semantics (affects PRD-5)**: If rates.json is missing or malformed and startup error handling is deferred, what should GET /healthz return? Is the service considered "ok" if it's running but can't serve requests?
