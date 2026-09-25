"""Safety detection for card numbers and passwords."""
import re


class SafetyDetector:
    """Detects sensitive data (card numbers, passwords) in messages."""

    def __init__(self):
        """Initialize the safety detector."""
        pass

    def check_message(self, message):
        """Check if a message contains sensitive data.

        Args:
            message: The message to check

        Returns:
            dict with keys:
                - contains_sensitive: bool
                - type: "card" or "password" (if sensitive)
        """
        # Check for card numbers first
        if self._contains_card_number(message):
            return {"contains_sensitive": True, "type": "card"}

        # Check for passwords
        if self._contains_password(message):
            return {"contains_sensitive": True, "type": "password"}

        return {"contains_sensitive": False}

    def _contains_card_number(self, message):
        """Check if message contains a valid card number (Luhn check)."""
        # Find sequences of 13-19 digits (with optional spaces/dashes)
        # Remove spaces and dashes to validate
        card_pattern = r"[\d\s\-]{15,23}"  # 13-19 digits plus separators

        for match in re.finditer(card_pattern, message):
            candidate = match.group()
            digits_only = re.sub(r"[\s\-]", "", candidate)

            # Must be 13-19 digits
            if 13 <= len(digits_only) <= 19 and digits_only.isdigit():
                if self._luhn_check(digits_only):
                    return True

        return False

    def _luhn_check(self, card_number):
        """Validate a card number using the Luhn algorithm.

        Args:
            card_number: String of digits

        Returns:
            bool: True if passes Luhn check
        """
        digits = [int(d) for d in card_number]
        checksum = 0

        # Process digits from right to left
        for i, digit in enumerate(reversed(digits)):
            if i % 2 == 1:  # Every second digit from the right
                digit *= 2
                if digit > 9:
                    digit -= 9
            checksum += digit

        return checksum % 10 == 0

    def _contains_password(self, message):
        """Check if message contains a password pattern."""
        # Case-insensitive pattern: "password is", "password:", or "pwd="
        # followed by word containing digit or symbol
        password_patterns = [
            r"password\s+is\s+[\w@#$%^&*!]+[\d@#$%^&*!]+",
            r"password\s*:\s*[\w@#$%^&*!]+[\d@#$%^&*!]+",
            r"pwd\s*=\s*[\w@#$%^&*!]+[\d@#$%^&*!]+",
        ]

        for pattern in password_patterns:
            if re.search(pattern, message, re.IGNORECASE):
                return True

        return False
