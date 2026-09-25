"""Scenarios that need no LangChain: they run everywhere, including CI."""

import unittest

import policy


class Retrieval(unittest.TestCase):
    def setUp(self):
        self.faq = policy.load_faq()

    def test_five_entries_with_keywords(self):
        self.assertEqual(len(self.faq), 5)
        self.assertTrue(all(e.keywords for e in self.faq))

    def test_most_hits_wins(self):
        """Scenario: Most keyword hits wins"""
        # "charged" and "refund" hit the refund entry twice; "plan" hits
        # billing once.
        entry = policy.retrieve("I was charged for my plan, can I get a refund?", self.faq)
        self.assertEqual(entry.question, "How do I get a refund?")

    def test_uncovered_question_has_no_entry(self):
        self.assertIsNone(policy.retrieve("what is the office dog called?", self.faq))


class Sensitive(unittest.TestCase):
    def test_card_number(self):
        for text in ("4111 1111 1111 1111", "card 4111-1111-1111-1111 pls", "5555555555554444"):
            self.assertTrue(policy.is_sensitive(text), text)

    def test_shared_password(self):
        for text in ("my password is hunter22", "password: hunter22", "PWD=abc123", "my password is p@ss"):
            self.assertTrue(policy.is_sensitive(text), text)

    def test_asking_about_passwords_is_not_refused(self):
        """Scenario: Asking about passwords is not refused"""
        for text in (
            "I forgot my password",
            "how do I reset my password?",
            "my password is not working",
            "My password is expired, how do I reset it?",
            "password: ?",
        ):
            self.assertFalse(policy.is_sensitive(text), text)

    def test_order_number_is_not_refused(self):
        """Scenario: Order number is not refused"""
        self.assertFalse(policy.luhn("1234567890123456"))
        for text in ("refund for order 1234-5678-9012-3456 please", "order 1234567812345678"):
            self.assertFalse(policy.is_sensitive(text), text)


class Configuration(unittest.TestCase):
    def test_model_params(self):
        """Scenario: Model parameters"""
        self.assertEqual(policy.model_params(), {"model": "claude-sonnet-5", "max_tokens": 512})

    def test_window(self):
        self.assertEqual(policy.window(list(range(10))), [4, 5, 6, 7, 8, 9])
        self.assertEqual(policy.window([1, 2]), [1, 2])


if __name__ == "__main__":
    unittest.main()
