"""FX conversion as a single HTTP function.

Spec: openspec/changes/add-fx-convert/specs/fx/spec.md

    docker build -t fx . && docker run --rm -p 8080:8080 fx
    curl 'localhost:8080/convert?amount=100&from=USD&to=EUR'
"""

from __future__ import annotations

import json
import os
import sys
from decimal import ROUND_HALF_EVEN, Decimal, InvalidOperation
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

CENT = Decimal("0.01")
MAX_AMOUNT = Decimal("1000000000000")
RATE_PLACES = Decimal("0.000001")
DEFAULT_PORT = 8080
RATES_PATH = Path(__file__).with_name("rates.json")


def load_rates(path: Path) -> dict[str, Decimal]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    # Strings in the file, Decimals in memory: a JSON float would already
    # have lost the value before we could round it.
    return {code: Decimal(value) for code, value in data["rates"].items()}


class FxApp:
    """Request line in, ``(status, body)`` out -- no sockets, no disk.

    Keeping the HTTP layer out of here is what lets every spec scenario be a
    plain unit test.
    """

    def __init__(self, rates: dict[str, Decimal]):
        self.rates = dict(rates)

    @classmethod
    def from_file(cls, path: Path = RATES_PATH) -> "FxApp":
        return cls(load_rates(path))

    def handle(self, method: str, target: str) -> tuple[int, dict]:
        url = urlsplit(target)
        if method != "GET":
            return 405, {"error": "method_not_allowed"}
        if url.path == "/healthz":
            return 200, {"status": "ok"}
        if url.path == "/convert":
            return self._convert(parse_qs(url.query, keep_blank_values=True))
        return 404, {"error": "not_found"}

    def _convert(self, params: dict[str, list[str]]) -> tuple[int, dict]:
        try:
            amount = Decimal(params.get("amount", [""])[0])
        except InvalidOperation:
            return 400, {"error": "invalid_amount"}
        # The ceiling is the product owner's, and it also keeps every result
        # inside Decimal's default 28-digit precision -- above it, quantize
        # raises instead of rounding.
        if not amount.is_finite() or amount < 0 or amount > MAX_AMOUNT:
            return 400, {"error": "invalid_amount"}

        codes = [params.get(k, [""])[0] for k in ("from", "to")]
        for code in codes:
            if code not in self.rates:
                return 404, {"error": "unknown_currency", "currency": code}
        source, target = codes

        rate = self.rates[target] / self.rates[source]
        # Round the result from the unrounded rate. Rounding the rate first
        # and multiplying drifts by a cent on large invoices.
        result = (amount * rate).quantize(CENT, rounding=ROUND_HALF_EVEN)
        return 200, {
            "amount": str(amount.quantize(CENT, rounding=ROUND_HALF_EVEN)),
            "from": source,
            "to": target,
            "rate": str(rate.quantize(RATE_PLACES, rounding=ROUND_HALF_EVEN)),
            "result": str(result),
        }


def resolve_port(env: dict[str, str]) -> int:
    return int(env.get("PORT") or DEFAULT_PORT)


HTTP_METHODS = ("GET", "HEAD", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "TRACE", "CONNECT")


def make_handler(app: FxApp) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        def _respond(self) -> None:
            status, body = app.handle(self.command, self.path)
            payload = json.dumps(body).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            if self.command != "HEAD":  # HEAD responses carry headers only
                self.wfile.write(payload)

    # BaseHTTPRequestHandler answers 501 to any method without a do_<METHOD>;
    # the spec says every non-GET method is a 405, so route them all.
    for method in HTTP_METHODS:
        setattr(Handler, f"do_{method}", Handler._respond)
    return Handler


def main() -> int:
    app = FxApp.from_file()
    port = resolve_port(dict(os.environ))
    server = ThreadingHTTPServer(("0.0.0.0", port), make_handler(app))
    print(f"fx listening on :{port}", file=sys.stderr, flush=True)
    server.serve_forever()
    return 0


if __name__ == "__main__":
    sys.exit(main())
