# Design: FX conversion function

## Technical Approach

One stdlib module. `FxApp.handle(method, target)` is a pure function from a
request line to `(status, json_body)`; the `http.server` handler is a thin
shell around it. That split is what makes every scenario testable without
opening a socket or starting Docker.

## Architecture Decisions

### Decision: `decimal.Decimal`, never `float`

Money values must round-trip exactly and round half-to-even. Floats cannot
represent 0.135, so a float implementation passes most tests and fails
finance's audit on ties. The response carries strings for the same reason.

### Decision: an explicit `do_<METHOD>` for every HTTP method

`BaseHTTPRequestHandler` answers 501 to any method it has no `do_` method
for. The PRD says every non-GET method is a 405, so the handler defines all
of them rather than the handful a quick test would try.

### Decision: stdlib `http.server`, no framework

The PRD forbids third-party packages (PRD-8). `ThreadingHTTPServer` is
enough for one internal caller, and there is nothing to patch.

### Decision: load rates in the constructor

"Fast" was resolved to "no per-request I/O" (PRD-3). Loading in `FxApp`'s
constructor makes that structural, and the test proves it by deleting the
file after startup.

## Data Flow

`GET /convert?...` → `FxApp.handle` → parse query → validate amount →
look up both rates → `amount * rate_to / rate_from` → quantize → JSON.

## File Changes

- `impl/app.py` (new)
- `impl/rates.json` (new)
- `impl/Dockerfile` (new)
- `impl/tests/test_app.py` (new)
