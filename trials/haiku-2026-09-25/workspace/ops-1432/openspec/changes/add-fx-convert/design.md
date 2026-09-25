# Design: FX Conversion API Service

## Technical Approach

The service is a stateless HTTP server that loads currency exchange rates into memory at startup and serves conversion requests with minimal latency. No external network calls are made after initialization; all conversions use the pre-loaded rate data.

**Architecture:**
1. On startup: Read `rates.json` and load all exchange rates into memory (one rate per currency, expressed as amount per 1 USD)
2. For each request: Validate input parameters, perform conversion using in-memory rates, return formatted result or error
3. Support both direct conversions (USD → EUR) and cross conversions (GBP → EUR via USD intermediate)

**Key Design Decisions:**

### Decision: In-Memory Rate Loading
Rates are loaded once at startup from a checked-in `rates.json` file. This eliminates runtime network calls and provides consistent, predictable performance. Trade-off: rates only update when the service is redeployed (acceptable monthly cadence for billing rates).

### Decision: Decimal Handling with Banker's Rounding
All monetary values use string representation (never JSON floats) with banker's rounding (ROUND_HALF_EVEN) to 2 decimal places for amounts/results and 6 decimal places for rates. This ensures financial accuracy and explicit precision control.

### Decision: Query Parameter API (Not JSON Body)
The conversion endpoint uses query parameters (`?amount=X&from=Y&to=Z`) instead of JSON request body. This simplifies client implementation and aligns with REST conventions for stateless lookups.

### Decision: HTTP Status Codes for Input Validation
Different HTTP status codes indicate different failure modes:
- 400: Invalid amount (not a number, negative, too large, etc.)
- 404: Unknown currency (code not in rates file)
- 405: Wrong HTTP method (non-GET request)

### Decision: Strict JSON Response Format
All responses must be exactly specified JSON with no extra fields or variations. This prevents subtle client issues from undocumented response variations.

## File Changes

**New files:**
- `service.py` — Main service implementation (HTTP server, rate loading, conversion logic)
- `rates.json` — Exchange rate data (checked-in, updated monthly)
- `Dockerfile` — Container definition (python:3.12-slim, PORT env var, non-root user)
- `openspec/changes/add-fx-convert/proposal.md` — This proposal
- `openspec/changes/add-fx-convert/design.md` — This design document
- `openspec/changes/add-fx-convert/tasks.md` — Implementation tasks
- `openspec/changes/add-fx-convert/specs/fx-conversion/spec.md` — OpenSpec specification

**Modified files:**
- None (new service, no changes to existing code)

**Configuration:**
- Environment variable: `PORT` (default 8080) — Port the service listens on
- File: `rates.json` — Location: same directory as service
