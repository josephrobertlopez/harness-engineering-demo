# Interview: OPS-1432 — Dockerize the FX conversion function

## Unresolved assumptions

**Success criteria:**
- "works" is circular — how do we know when to stop testing?
- "should be fast" has no definition (latency? throughput?)
- "handles bad input" doesn't specify which inputs, or what "handling" means
- No acceptance test criteria (SLO, uptime, error rates)

**Constraints:**
- FX rate source unspecified ("the usual rates" — which source? fresh or cached? update frequency?)
- Security model undefined ("should be secure" — against what threat? who calls it?)
- No mention of request volume, rate limits, or concurrency expectations
- Deadline is vague ("before month end" — which month?)

**API contract:**
- REST interface is mentioned but not specified (request/response format? status codes?)
- Precision and rounding not defined (2 decimals? banker's rounding?)

**Edge cases:**
- Missing currency pairs — fail or fall back?
- Concurrent requests — any limits?
- Historical rates or only spot rates?

---

## Questions

### Q1. What does "fast" mean for this service? Are we optimizing for latency (e.g., response time < 100ms), throughput (e.g., 1000+ requests/sec), or something else? And how will billing-team measure whether it meets that target?

A: Nobody has a latency number. What billing actually means is that the rates file is read once at startup, not per request, so a request never touches disk or network.

### Q2. Where should the FX rates come from, and how fresh do they need to be? Real-time API like OpenExchangeRates, cached snapshot, or something else? And how often should rates update?

A: From `rates.json`, checked in next to the function: one rate per currency, expressed per 1 USD. Cross rates (GBP→EUR) go through USD. Billing replaces the file and redeploys at month end. No network calls, ever.

### Q3. What happens when billing-team sends a bad input (e.g., unknown currency, negative amount, missing fields)? Should the service reject it with a specific HTTP status, return an error code in the response, or something else?

A: `GET /convert?amount=<decimal>&from=<code>&to=<code>` with currency codes as ISO 4217 upper-case. A 400 returns `{"error": "invalid_amount"}` if amount is missing, not a number, NaN/Infinity, negative, or larger than 1,000,000,000,000. A 404 returns `{"error": "unknown_currency", "currency": "<the code>"}` if `from` or `to` is missing or not in the rates file. A 405 returns `{"error": "method_not_allowed"}` for any method other than GET.

### Q4. What does "should be secure" mean in this context? Are we protecting against: eavesdropping (HTTPS only), unauthorized access (API key / auth token), or both? Who is allowed to call this service?

A: It sits on the internal network, so no authentication — that is a non-goal, not an oversight.

### Q5. What is the exact request and response format? (e.g., `POST /convert` with JSON body `{"amount": 100, "from": "USD", "to": "EUR"}` returning `{"converted": 85.50}`?) And what precision should amounts be returned at?

A: `GET /convert?amount=<decimal>&from=<code>&to=<code>`, currency codes are ISO 4217 upper-case. A 200 returns JSON `{"amount": "100.00", "from": "USD", "to": "EUR", "rate": "0.920000", "result": "92.00"}`. Money values are strings, never JSON floats. Results and amounts are rounded to 2 decimal places using banker's rounding (ROUND_HALF_EVEN); the rate field is shown to 6 decimal places, same rounding.

### Q6. If `rates.json` is missing, malformed, or unreadable when the service starts, should it fail to start entirely, or start and return errors (e.g., 500) for all requests?

A: No decision - treat it as a non-goal.

### Q7. When converting via USD (e.g., GBP→EUR), do you calculate the cross rate as `(1/rate_gbp) * rate_eur`, or do the conversion in two steps with rounding applied at each step?

A: No decision - treat it as a non-goal.

### Q8. How will billing-team verify this works before deploying? Do you need acceptance tests in the image, or will they test by calling the service directly?

A: No decision - treat it as a non-goal.

---

### Q9. Should the service set any special HTTP response headers on success or error? (e.g., Cache-Control, Content-Type charset, X-* headers?)

A: No decision - treat it as a non-goal.

### Q10. If a request takes too long to complete, should it timeout and return an error? If so, what timeout duration and error response?

A: No decision - treat it as a non-goal.

### Q11. Does the service need a separate health check endpoint (e.g., `/health`), or is ops health-checking handled outside the service?

A: Yes. `GET /healthz` → 200 `{"status": "ok"}`.

### Q12. What should the service return if a client makes a GET request to an unknown path (e.g., `/foo` or `/convert/extra`)?

A: Unknown paths return a 404 error with the response `{"error": "not_found"}`.

### Q13. For Docker configuration: what base image should the service use, and what port should it listen on? Should the port be overridable via environment variable?

A: The image should be built `FROM python:3.12-slim` and listen on port **8080** by default, overridable with the `PORT` environment variable.

### Q14. Should the service run as a non-root user inside the container, and if so, which user? Are there any third-party packages or dependencies that should NOT be installed?

A: The container runs as a non-root user, and no third-party packages should be installed. Which specific non-root user: No decision - treat it as a non-goal.

### Q15. When the service returns a rate in the response (e.g., `"rate": "0.920000"`), is this the exact unrounded rate read from `rates.json`, or is it calculated/derived and then rounded to 6 decimal places?

A: The `rate` field is shown to 6 decimal places using banker's rounding (round half to even), the same rounding method applied to the result. The computation itself uses the unrounded rate value from the file.

### Q16. Should the `/convert` endpoint ignore unknown query parameters, or return an error if extra parameters are included in the request?

A: No decision - treat it as a non-goal.

### Q17. Please confirm the complete and exact specification of the `/convert` endpoint: the full URL path, the HTTP method, the exact names and order of query parameters, and what a successful response looks like.

A: GET /convert?amount=<decimal>&from=<code>&to=<code>. Currency codes must be ISO 4217 upper-case. A successful response is HTTP 200 with JSON: `{"amount": "100.00", "from": "USD", "to": "EUR", "rate": "0.920000", "result": "92.00"}`. All monetary values and rate are strings, never floats. This is the only endpoint that converts currencies.

---

## Non-goals

- Startup error handling for missing/malformed rates.json
- Precision handling for cross-rate conversions via USD
- Acceptance/integration testing strategy
- HTTP response headers
- Request timeout handling
- Specific non-root user to run container as
- Handling of unknown/extra query parameters
