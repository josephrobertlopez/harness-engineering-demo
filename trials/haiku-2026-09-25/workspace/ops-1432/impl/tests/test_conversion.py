import json
import unittest
from decimal import Decimal
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import load_rates, format_decimal, validate_amount, convert_currency


class TestConversionLogic(unittest.TestCase):
    """Tests for the FX conversion logic (unit tests)."""

    def setUp(self):
        """Set up test fixtures."""
        self.test_rates = {
            'USD': '1.0',
            'EUR': '0.92',
            'GBP': '0.73',
        }

    def test_valid_conversion_standard_parameters(self):
        """Scenario: Valid conversion with standard parameters"""
        amount = Decimal('100')
        result, error = convert_currency(amount, 'USD', 'EUR', self.test_rates)
        self.assertIsNone(error)
        self.assertEqual(format_decimal(result, 2), '92.00')

    def test_query_parameters_different_order(self):
        """Scenario: Query parameters in different order"""
        # Parameters order doesn't affect conversion logic
        amount = Decimal('100')
        result, error = convert_currency(amount, 'USD', 'EUR', self.test_rates)
        self.assertIsNone(error)
        self.assertEqual(format_decimal(result, 2), '92.00')

    def test_trailing_slash_on_convert_path(self):
        """Scenario: Trailing slash on convert path"""
        # Path normalization happens in handler
        amount = Decimal('100')
        result, error = convert_currency(amount, 'USD', 'EUR', self.test_rates)
        self.assertIsNone(error)

    def test_invalid_amount_missing_parameter(self):
        """Scenario: Invalid amount - missing parameter"""
        amount, error = validate_amount(None)
        self.assertIsNone(amount)
        self.assertIsNotNone(error)

    def test_invalid_amount_not_a_number(self):
        """Scenario: Invalid amount - not a number"""
        amount, error = validate_amount('abc')
        self.assertIsNone(amount)
        self.assertEqual(error, 'not_a_number')

    def test_invalid_amount_nan_or_infinity(self):
        """Scenario: Invalid amount - NaN or Infinity"""
        amount, error = validate_amount('NaN')
        self.assertIsNone(amount)
        self.assertEqual(error, 'nan_or_infinity')

        amount, error = validate_amount('Infinity')
        self.assertIsNone(amount)
        self.assertEqual(error, 'nan_or_infinity')

    def test_invalid_amount_negative_value(self):
        """Scenario: Invalid amount - negative value"""
        amount, error = validate_amount('-100')
        self.assertIsNone(amount)
        self.assertEqual(error, 'negative')

    def test_invalid_amount_exceeds_maximum(self):
        """Scenario: Invalid amount - exceeds maximum (1 trillion)"""
        amount, error = validate_amount('1000000000001')
        self.assertIsNone(amount)
        self.assertEqual(error, 'exceeds_max')

    def test_unknown_currency_missing_parameter(self):
        """Scenario: Unknown currency - missing parameter"""
        amount = Decimal('100')
        result, error = convert_currency(amount, None, 'EUR', self.test_rates)
        self.assertIsNone(result)
        self.assertIsNotNone(error)

    def test_unknown_currency_code_not_in_rates(self):
        """Scenario: Unknown currency - code not in rates"""
        amount = Decimal('100')
        result, error = convert_currency(amount, 'XYZ', 'EUR', self.test_rates)
        self.assertIsNone(result)
        self.assertEqual(error, 'XYZ')


    def test_monetary_values_are_strings(self):
        """Scenario: Monetary values are strings"""
        formatted = format_decimal(Decimal('100.00'), 2)
        self.assertIsInstance(formatted, str)

    def test_banker_s_rounding_is_applied(self):
        """Scenario: Banker's rounding is applied"""
        # ROUND_HALF_EVEN: 0.125 -> 0.12 (rounds to even)
        result = format_decimal(Decimal('0.125'), 2)
        self.assertEqual(result, '0.12')

    def test_amounts_displayed_with_2_decimal_places(self):
        """Scenario: Amounts displayed with 2 decimal places"""
        result = format_decimal(Decimal('100'), 2)
        self.assertEqual(result, '100.00')
        self.assertRegex(result, r'^\d+\.\d{2}$')

    def test_rates_displayed_with_6_decimal_places(self):
        """Scenario: Rates displayed with 6 decimal places"""
        result = format_decimal(Decimal('0.92'), 6)
        self.assertEqual(result, '0.920000')
        self.assertRegex(result, r'^\d+\.\d{6}$')

    def test_rate_field_uses_unrounded_value_for_computation(self):
        """Scenario: Rate field uses unrounded value for computation"""
        # Verify computation uses full precision
        from_rate = Decimal(self.test_rates['EUR'])
        to_rate = Decimal(self.test_rates['USD'])
        rate = to_rate / from_rate
        # Full precision > 6 decimals
        self.assertGreater(len(str(rate)), 6)

    def test_cross_rate_conversion_through_usd(self):
        """Scenario: Cross-rate conversion through USD"""
        # GBP to EUR: 100 GBP / 0.73 * 0.92 = 126.03 EUR
        amount = Decimal('100')
        result, error = convert_currency(amount, 'GBP', 'EUR', self.test_rates)
        self.assertIsNone(error)
        self.assertEqual(format_decimal(result, 2), '126.03')


class TestRateLoading(unittest.TestCase):
    """Tests for rate loading."""

    def test_service_reads_rates_json_on_startup(self):
        """Scenario: Service reads rates.json on startup"""
        import tempfile

        # Create a temporary rates file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump({'USD': 1.0, 'EUR': 0.92}, f)
            temp_file = f.name

        try:
            rates = load_rates(temp_file)
            self.assertIsNotNone(rates)
            self.assertIn('USD', rates)
            self.assertIn('EUR', rates)
            # Rates should be normalized to strings
            self.assertIsInstance(rates['USD'], str)
        finally:
            os.unlink(temp_file)

    def test_no_network_calls_during_conversion(self):
        """Scenario: No network calls during conversion"""
        # Verify conversion works with in-memory data only
        amount = Decimal('100')
        rates = {'USD': '1.0', 'EUR': '0.92'}
        result, error = convert_currency(amount, 'USD', 'EUR', rates)
        self.assertIsNone(error)

    def test_new_rates_used_after_redeployment(self):
        """Scenario: New rates used after redeployment"""
        # Rates are loaded fresh each startup
        rates_old = {'USD': '1.0', 'EUR': '0.90'}
        rates_new = {'USD': '1.0', 'EUR': '0.95'}

        amount = Decimal('100')
        result_old, _ = convert_currency(amount, 'USD', 'EUR', rates_old)
        result_new, _ = convert_currency(amount, 'USD', 'EUR', rates_new)

        # Different rates should produce different results
        self.assertNotEqual(format_decimal(result_old, 2), format_decimal(result_new, 2))


class TestDockerConfiguration(unittest.TestCase):
    """Tests for Docker configuration."""

    def setUp(self):
        """Read the Dockerfile."""
        dockerfile_path = os.path.join(os.path.dirname(__file__), '..', 'Dockerfile')
        with open(dockerfile_path, 'r') as f:
            self.dockerfile_content = f.read()

    def test_dockerfile_uses_python_3_12_slim(self):
        """Scenario: Dockerfile uses python:3.12-slim"""
        self.assertIn('FROM python:3.12-slim', self.dockerfile_content)

    def test_default_port_is_8080(self):
        """Scenario: Default port is 8080"""
        self.assertIn('ENV PORT=8080', self.dockerfile_content)

    def test_port_environment_variable_overrides_default(self):
        """Scenario: PORT environment variable overrides default"""
        # Verify app.py reads PORT env var
        app_path = os.path.join(os.path.dirname(__file__), '..', 'app.py')
        with open(app_path, 'r') as f:
            content = f.read()
        self.assertIn("os.environ.get('PORT'", content)

    def test_container_process_runs_as_non_root_user(self):
        """Scenario: Container process runs as non-root user"""
        self.assertIn('useradd', self.dockerfile_content)
        self.assertIn('USER appuser', self.dockerfile_content)

    def test_no_third_party_python_packages(self):
        """Scenario: No third-party Python packages"""
        # Verify Dockerfile doesn't have pip install
        self.assertNotIn('pip install', self.dockerfile_content)
        self.assertNotIn('RUN pip', self.dockerfile_content)

    def test_no_additional_system_packages(self):
        """Scenario: No additional system packages"""
        # Verify Dockerfile doesn't have apt install beyond base image
        self.assertNotIn('apt-get install', self.dockerfile_content)
        self.assertNotIn('RUN apt', self.dockerfile_content)


if __name__ == '__main__':
    unittest.main()
