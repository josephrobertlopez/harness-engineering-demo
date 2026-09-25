#!/usr/bin/env python3
"""FX Conversion Service - REST API for currency conversion."""

import json
import os
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs
from decimal import Decimal, ROUND_HALF_EVEN


def load_rates(filename='rates.json'):
    """Load exchange rates from rates.json file."""
    try:
        with open(filename, 'r') as f:
            rates = json.load(f)
        # Normalize rates to strings
        return {code: str(rate) for code, rate in rates.items()}
    except FileNotFoundError:
        print(f"Error: {filename} not found", file=sys.stderr)
        return {}
    except json.JSONDecodeError as e:
        print(f"Error parsing {filename}: {e}", file=sys.stderr)
        return {}


def format_decimal(value, decimal_places):
    """Format decimal with banker's rounding (ROUND_HALF_EVEN)."""
    if isinstance(value, str):
        try:
            value = Decimal(value)
        except:
            return None
    else:
        value = Decimal(str(value))

    quantize_exp = Decimal(10) ** -decimal_places
    return str(value.quantize(quantize_exp, rounding=ROUND_HALF_EVEN))


def validate_amount(amount_str):
    """Validate amount parameter."""
    if amount_str is None:
        return None, "missing"

    # Check for special values
    if amount_str.lower() in ['nan', 'infinity', '+infinity', '-infinity']:
        return None, "nan_or_infinity"

    try:
        amount = Decimal(amount_str)
    except:
        return None, "not_a_number"

    # Check for negative
    if amount < 0:
        return None, "negative"

    # Check for max value (1 trillion)
    if amount > Decimal('1000000000000'):
        return None, "exceeds_max"

    return amount, None


def convert_currency(amount, from_code, to_code, rates):
    """Convert amount from one currency to another."""
    # Check for missing or None codes
    if from_code is None or from_code not in rates:
        return None, from_code or ''
    if to_code is None or to_code not in rates:
        return None, to_code or ''

    from_rate = Decimal(rates[from_code])
    to_rate = Decimal(rates[to_code])

    # Convert: amount * (to_rate / from_rate)
    result = amount * (to_rate / from_rate)

    return result, None


class FXConversionHandler(BaseHTTPRequestHandler):
    """HTTP request handler for FX conversion service."""

    rates = {}  # Class variable, set by server

    def log_message(self, format, *args):
        """Suppress logging."""
        pass

    def do_GET(self):
        """Handle GET requests."""
        parsed_url = urlparse(self.path)
        path = parsed_url.path.rstrip('/')  # Remove trailing slash

        # Route: /convert
        if path == '/convert':
            return self.handle_convert()

        # Route: /healthz
        elif path == '/healthz':
            return self.handle_health()

        # Unknown path
        else:
            return self.respond_json(404, {'error': 'not_found'})

    def do_POST(self):
        """Handle POST requests - return 405."""
        parsed_url = urlparse(self.path)
        path = parsed_url.path.rstrip('/')

        if path == '/convert':
            return self.respond_json(405, {'error': 'method_not_allowed'})
        else:
            return self.respond_json(404, {'error': 'not_found'})

    def do_PUT(self):
        """Handle PUT requests - return 405."""
        return self.do_POST()

    def do_DELETE(self):
        """Handle DELETE requests - return 405."""
        return self.do_POST()

    def handle_convert(self):
        """Handle /convert endpoint."""
        parsed_url = urlparse(self.path)
        params = parse_qs(parsed_url.query)

        # Extract parameters (get first value if list)
        amount_str = params.get('amount', [None])[0]
        from_code = params.get('from', [None])[0]
        to_code = params.get('to', [None])[0]

        # Validate amount
        amount, error = validate_amount(amount_str)
        if error:
            return self.respond_json(400, {'error': 'invalid_amount'})

        # Check currencies
        if from_code is None or to_code is None:
            missing = from_code if from_code is None else to_code
            return self.respond_json(404, {
                'error': 'unknown_currency',
                'currency': missing or ''
            })

        if from_code not in self.rates or to_code not in self.rates:
            missing = from_code if from_code not in self.rates else to_code
            return self.respond_json(404, {
                'error': 'unknown_currency',
                'currency': missing
            })

        # Perform conversion
        result, error = convert_currency(amount, from_code, to_code, self.rates)
        if error:
            return self.respond_json(404, {
                'error': 'unknown_currency',
                'currency': error
            })

        # Format response
        rate = Decimal(self.rates[to_code]) / Decimal(self.rates[from_code])

        response = {
            'amount': format_decimal(amount, 2),
            'from': from_code,
            'to': to_code,
            'rate': format_decimal(rate, 6),
            'result': format_decimal(result, 2)
        }

        return self.respond_json(200, response)

    def handle_health(self):
        """Handle /healthz endpoint."""
        return self.respond_json(200, {'status': 'ok'})

    def respond_json(self, status_code, data):
        """Send JSON response."""
        body = json.dumps(data)

        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', len(body))
        self.end_headers()

        self.wfile.write(body.encode('utf-8'))


def start_server(port=8080, rates_file='rates.json'):
    """Start the FX conversion service."""
    # Load rates
    rates = load_rates(rates_file)
    if not rates:
        print("Error: Failed to load rates", file=sys.stderr)
        sys.exit(1)

    # Set rates on handler
    FXConversionHandler.rates = rates

    # Start server
    server_address = ('', port)
    httpd = HTTPServer(server_address, FXConversionHandler)

    print(f"Starting FX conversion service on port {port}")
    httpd.serve_forever()


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    start_server(port)
