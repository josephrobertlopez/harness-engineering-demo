"""One test per spec scenario. Each names its scenario, so the fidelity judge
can check coverage in both directions -- no scenario untested, no test for
a scenario that does not exist."""

import os
import re
import shutil
import tempfile
import unittest
from pathlib import Path

from app import HTTP_METHODS, RATES_PATH, FxApp, make_handler, resolve_port

HERE = Path(__file__).resolve().parents[1]


class Conversion(unittest.TestCase):
    def setUp(self):
        self.app = FxApp.from_file()

    def test_usd_to_eur(self):
        """Scenario: Convert USD to EUR"""
        status, body = self.app.handle("GET", "/convert?amount=100&from=USD&to=EUR")
        self.assertEqual(status, 200)
        self.assertEqual(
            body,
            {"amount": "100.00", "from": "USD", "to": "EUR", "rate": "0.920000", "result": "92.00"},
        )

    def test_cross_rate(self):
        """Scenario: Cross rate through USD"""
        status, body = self.app.handle("GET", "/convert?amount=100&from=GBP&to=EUR")
        self.assertEqual(status, 200)
        self.assertEqual(body["result"], "116.46")

    def test_tie_down(self):
        """Scenario: Tie rounds down to even"""
        _, body = self.app.handle("GET", "/convert?amount=0.125&from=USD&to=USD")
        # Half-up would give 0.13. This value only passes under half-even.
        self.assertEqual(body["result"], "0.12")

    def test_tie_up(self):
        """Scenario: Tie rounds up to even"""
        _, body = self.app.handle("GET", "/convert?amount=0.135&from=USD&to=USD")
        # Truncation would give 0.13. Paired with the test above, only
        # half-even passes both.
        self.assertEqual(body["result"], "0.14")

    def test_tie_a_float_cannot_represent(self):
        """Scenario: Tie a float cannot represent"""
        # 2.675 and 0.165 are the values where a float and half-even
        # disagree (2.67 vs 2.68, 0.17 vs 0.16). The two ties above round the
        # same either way, so on their own they would pass a float version.
        for amount, expected in (("2.675", "2.68"), ("0.165", "0.16")):
            _, body = self.app.handle("GET", f"/convert?amount={amount}&from=USD&to=USD")
            self.assertEqual(body["result"], expected, amount)

    def test_rates_file_removed_after_startup(self):
        """Scenario: Rates file removed after startup"""
        scratch = Path(tempfile.mkdtemp())
        try:
            copy = scratch / "rates.json"
            shutil.copy(RATES_PATH, copy)
            app = FxApp.from_file(copy)
            copy.unlink()
            status, body = app.handle("GET", "/convert?amount=1&from=USD&to=JPY")
            self.assertEqual((status, body["result"]), (200, "149.50"))
        finally:
            shutil.rmtree(scratch, ignore_errors=True)


class Errors(unittest.TestCase):
    def setUp(self):
        self.app = FxApp.from_file()

    def assertError(self, target, status, error, method="GET"):
        got_status, body = self.app.handle(method, target)
        self.assertEqual((got_status, body.get("error")), (status, error), target)
        return body

    def test_missing_amount(self):
        """Scenario: Missing amount"""
        self.assertError("/convert?from=USD&to=EUR", 400, "invalid_amount")

    def test_negative_amount(self):
        """Scenario: Negative amount"""
        self.assertError("/convert?amount=-5&from=USD&to=EUR", 400, "invalid_amount")

    def test_non_numeric_amount(self):
        """Scenario: Non-numeric amount"""
        for raw in ("ten", "NaN", "Infinity", ""):
            self.assertError(f"/convert?amount={raw}&from=USD&to=EUR", 400, "invalid_amount")

    def test_amount_too_large(self):
        """Scenario: Amount too large"""
        for raw in ("1e30", "1000000000000.01"):
            self.assertError(f"/convert?amount={raw}&from=USD&to=JPY", 400, "invalid_amount")
        status, _ = self.app.handle("GET", "/convert?amount=1000000000000&from=USD&to=JPY")
        self.assertEqual(status, 200)

    def test_unknown_currency(self):
        """Scenario: Unknown target currency"""
        body = self.assertError("/convert?amount=1&from=USD&to=XYZ", 404, "unknown_currency")
        self.assertEqual(body["currency"], "XYZ")

    def test_unknown_path(self):
        """Scenario: Unknown path"""
        self.assertError("/rates", 404, "not_found")

    def test_wrong_method(self):
        """Scenario: Wrong method"""
        self.assertError("/convert?amount=1&from=USD&to=EUR", 405, "method_not_allowed", method="POST")


    def test_every_other_method(self):
        """Scenario: Every other method is refused"""
        handler = make_handler(FxApp.from_file())
        for method in HTTP_METHODS[1:]:
            # The HTTP layer must route it (else http.server sends 501) ...
            self.assertTrue(hasattr(handler, f"do_{method}"), method)
            # ... and the app must refuse it.
            self.assertError("/convert?amount=1&from=USD&to=EUR", 405, "method_not_allowed", method=method)


class Operations(unittest.TestCase):
    def test_health(self):
        """Scenario: Health check responds"""
        self.assertEqual(FxApp({}).handle("GET", "/healthz"), (200, {"status": "ok"}))

    def test_default_port(self):
        """Scenario: Default port"""
        self.assertEqual(resolve_port({}), 8080)

    def test_port_override(self):
        """Scenario: Port override"""
        self.assertEqual(resolve_port({"PORT": "9090"}), 9090)

    def test_non_root_image(self):
        """Scenario: Non-root image"""
        dockerfile = (HERE / "Dockerfile").read_text(encoding="utf-8")
        self.assertRegex(dockerfile, r"(?m)^FROM python:3\.12-slim\b")
        users = re.findall(r"(?m)^USER\s+(\S+)", dockerfile)
        self.assertTrue(users, "no USER line")
        self.assertNotIn(users[-1], {"root", "0"})
        self.assertNotRegex(dockerfile, r"(?m)^\s*RUN\b.*pip install")


if __name__ == "__main__":
    unittest.main()
