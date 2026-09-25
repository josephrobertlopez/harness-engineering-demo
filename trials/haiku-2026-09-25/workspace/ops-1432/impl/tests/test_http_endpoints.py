import json
import unittest
from http.server import HTTPServer
from threading import Thread
import socket
import time
import sys
import os
from urllib.request import urlopen, Request
from urllib.error import HTTPError

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import FXConversionHandler, load_rates


def find_free_port():
    """Find a free port to use for testing."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))
        s.listen(1)
        port = s.getsockname()[1]
    return port


class HTTPTestServer:
    """Context manager for test HTTP server."""

    def __init__(self):
        self.port = find_free_port()
        self.server = None
        self.thread = None

    def __enter__(self):
        # Load test rates
        rates = load_rates(os.path.join(os.path.dirname(__file__), '..', 'rates.json'))
        FXConversionHandler.rates = rates

        # Start server
        self.server = HTTPServer(('127.0.0.1', self.port), FXConversionHandler)
        self.thread = Thread(target=self.server.serve_forever)
        self.thread.daemon = True
        self.thread.start()
        time.sleep(0.1)
        return self

    def __exit__(self, *args):
        if self.server:
            self.server.shutdown()
            self.server.server_close()

    def get(self, path):
        """Make GET request."""
        url = f'http://127.0.0.1:{self.port}{path}'
        try:
            with urlopen(url) as response:
                return response.status, response.headers.get('Content-Type'), response.read().decode()
        except HTTPError as e:
            return e.code, e.headers.get('Content-Type'), e.read().decode()

    def post(self, path):
        """Make POST request."""
        url = f'http://127.0.0.1:{self.port}{path}'
        try:
            request = Request(url, method='POST')
            with urlopen(request) as response:
                return response.status, response.headers.get('Content-Type'), response.read().decode()
        except HTTPError as e:
            return e.code, e.headers.get('Content-Type'), e.read().decode()


class TestHTTPEndpoints(unittest.TestCase):
    """Tests for HTTP endpoints."""

    def test_valid_conversion_standard_parameters(self):
        """Scenario: Valid conversion with standard parameters"""
        with HTTPTestServer() as server:
            status, content_type, body = server.get('/convert?amount=100&from=USD&to=EUR')

            self.assertEqual(status, 200)
            self.assertEqual(content_type, 'application/json; charset=utf-8')
            data = json.loads(body)

            self.assertEqual(data['amount'], '100.00')
            self.assertEqual(data['from'], 'USD')
            self.assertEqual(data['to'], 'EUR')
            self.assertEqual(data['result'], '92.00')

    def test_query_parameters_different_order(self):
        """Scenario: Query parameters in different order"""
        with HTTPTestServer() as server:
            status, _, body = server.get('/convert?from=USD&to=EUR&amount=100')

            self.assertEqual(status, 200)
            data = json.loads(body)
            self.assertEqual(data['amount'], '100.00')
            self.assertEqual(data['result'], '92.00')

    def test_trailing_slash_on_convert_path(self):
        """Scenario: Trailing slash on convert path"""
        with HTTPTestServer() as server:
            status, _, body = server.get('/convert/?amount=100&from=USD&to=EUR')

            self.assertEqual(status, 200)
            data = json.loads(body)
            self.assertEqual(data['result'], '92.00')

    def test_invalid_amount_missing_parameter(self):
        """Scenario: Invalid amount - missing parameter"""
        with HTTPTestServer() as server:
            status, content_type, body = server.get('/convert?from=USD&to=EUR')

            self.assertEqual(status, 400)
            self.assertEqual(content_type, 'application/json; charset=utf-8')
            data = json.loads(body)
            self.assertEqual(data, {'error': 'invalid_amount'})

    def test_invalid_amount_not_a_number(self):
        """Scenario: Invalid amount - not a number"""
        with HTTPTestServer() as server:
            status, _, body = server.get('/convert?amount=abc&from=USD&to=EUR')

            self.assertEqual(status, 400)
            data = json.loads(body)
            self.assertEqual(data, {'error': 'invalid_amount'})

    def test_invalid_amount_nan_or_infinity(self):
        """Scenario: Invalid amount - NaN or Infinity"""
        with HTTPTestServer() as server:
            status, _, body = server.get('/convert?amount=NaN&from=USD&to=EUR')
            self.assertEqual(status, 400)

            status, _, body = server.get('/convert?amount=Infinity&from=USD&to=EUR')
            self.assertEqual(status, 400)

    def test_invalid_amount_negative_value(self):
        """Scenario: Invalid amount - negative value"""
        with HTTPTestServer() as server:
            status, _, body = server.get('/convert?amount=-100&from=USD&to=EUR')

            self.assertEqual(status, 400)
            data = json.loads(body)
            self.assertEqual(data, {'error': 'invalid_amount'})

    def test_invalid_amount_exceeds_maximum(self):
        """Scenario: Invalid amount - exceeds maximum (1 trillion)"""
        with HTTPTestServer() as server:
            status, _, body = server.get('/convert?amount=1000000000001&from=USD&to=EUR')

            self.assertEqual(status, 400)
            data = json.loads(body)
            self.assertEqual(data, {'error': 'invalid_amount'})

    def test_unknown_currency_missing_parameter(self):
        """Scenario: Unknown currency - missing parameter"""
        with HTTPTestServer() as server:
            status, content_type, body = server.get('/convert?amount=100&from=USD')

            self.assertEqual(status, 404)
            self.assertEqual(content_type, 'application/json; charset=utf-8')
            data = json.loads(body)
            self.assertEqual(data['error'], 'unknown_currency')

    def test_unknown_currency_code_not_in_rates(self):
        """Scenario: Unknown currency - code not in rates"""
        with HTTPTestServer() as server:
            status, _, body = server.get('/convert?amount=100&from=XYZ&to=EUR')

            self.assertEqual(status, 404)
            data = json.loads(body)
            self.assertEqual(data['error'], 'unknown_currency')
            self.assertEqual(data['currency'], 'XYZ')

    def test_non_get_http_method(self):
        """Scenario: Non-GET HTTP method"""
        with HTTPTestServer() as server:
            status, content_type, body = server.post('/convert?amount=100&from=USD&to=EUR')

            self.assertEqual(status, 405)
            self.assertEqual(content_type, 'application/json; charset=utf-8')
            data = json.loads(body)
            self.assertEqual(data, {'error': 'method_not_allowed'})

    def test_unknown_path_returns_404(self):
        """Scenario: Unknown path returns 404"""
        with HTTPTestServer() as server:
            status, content_type, body = server.get('/foo')

            self.assertEqual(status, 404)
            self.assertEqual(content_type, 'application/json; charset=utf-8')
            data = json.loads(body)
            self.assertEqual(data, {'error': 'not_found'})

    def test_health_check_endpoint_returns_ok(self):
        """Scenario: Health check endpoint returns ok"""
        with HTTPTestServer() as server:
            status, content_type, body = server.get('/healthz')

            self.assertEqual(status, 200)
            self.assertEqual(content_type, 'application/json; charset=utf-8')
            data = json.loads(body)
            self.assertEqual(data, {'status': 'ok'})

    def test_health_check_with_trailing_slash(self):
        """Scenario: Health check with trailing slash"""
        with HTTPTestServer() as server:
            status, _, body = server.get('/healthz/')

            self.assertEqual(status, 200)
            data = json.loads(body)
            self.assertEqual(data, {'status': 'ok'})

    def test_response_has_exactly_required_fields(self):
        """Scenario: Response has exactly required fields"""
        with HTTPTestServer() as server:
            status, _, body = server.get('/convert?amount=100&from=USD&to=EUR')
            data = json.loads(body)

            expected_keys = {'amount', 'from', 'to', 'rate', 'result'}
            self.assertEqual(set(data.keys()), expected_keys)

    def test_monetary_values_are_strings(self):
        """Scenario: Monetary values are strings"""
        with HTTPTestServer() as server:
            status, _, body = server.get('/convert?amount=100&from=USD&to=EUR')
            data = json.loads(body)

            self.assertIsInstance(data['amount'], str)
            self.assertIsInstance(data['rate'], str)
            self.assertIsInstance(data['result'], str)

    def test_amounts_displayed_with_2_decimal_places(self):
        """Scenario: Amounts displayed with 2 decimal places"""
        with HTTPTestServer() as server:
            status, _, body = server.get('/convert?amount=100&from=USD&to=EUR')
            data = json.loads(body)

            self.assertRegex(data['amount'], r'^\d+\.\d{2}$')
            self.assertRegex(data['result'], r'^\d+\.\d{2}$')

    def test_rates_displayed_with_6_decimal_places(self):
        """Scenario: Rates displayed with 6 decimal places"""
        with HTTPTestServer() as server:
            status, _, body = server.get('/convert?amount=100&from=USD&to=EUR')
            data = json.loads(body)

            self.assertRegex(data['rate'], r'^\d+\.\d{6}$')


if __name__ == '__main__':
    unittest.main()
