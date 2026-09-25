"""Scenarios that exercise the LangChain chain.

Skipped when langchain-core is not installed. The fidelity judge reports
the skip count, so a green run with skips is visibly not the whole story.
"""

import importlib.util
import io
import unittest

HAS_LANGCHAIN = importlib.util.find_spec("langchain_core") is not None

if HAS_LANGCHAIN:
    from langchain_core.language_models import FakeListChatModel
    from langchain_core.runnables import RunnableLambda

    import policy
    from chatbot import HelpBot, run


def recording_bot(responses):
    """A HelpBot whose model records every prompt it would have been sent."""
    calls = []

    def record(prompt_value):
        calls.append(prompt_value.to_messages())
        return prompt_value

    model = RunnableLambda(record) | FakeListChatModel(responses=responses)
    return HelpBot(model), calls


@unittest.skipUnless(HAS_LANGCHAIN, "pip install langchain-core to run the chain scenarios")
class Chat(unittest.TestCase):
    def test_covered_question(self):
        """Scenario: Question covered by the FAQ"""
        bot, calls = recording_bot(["Use Forgot password on the sign-in page."])
        reply = bot.reply("s1", "I forgot my login, how do I reset it?")
        self.assertEqual(reply.text, "Use Forgot password on the sign-in page.")
        self.assertFalse(reply.escalated)
        system = calls[0][0].content
        self.assertIn("How do I reset my password?", system)
        self.assertNotIn("How do I get a refund?", system)

    def test_uncovered_question(self):
        """Scenario: Question not covered"""
        bot, calls = recording_bot(["unused"])
        reply = bot.reply("s1", "what is the office dog called?")
        self.assertEqual(reply.text, policy.ESCALATION)
        self.assertTrue(reply.escalated)
        self.assertEqual(calls, [])

    def test_follow_up(self):
        """Scenario: Follow-up sees the previous exchange"""
        bot, calls = recording_bot(["first answer", "second answer"])
        bot.reply("s1", "how do I export my data?")
        bot.reply("s1", "is the export a csv?")
        contents = [m.content for m in calls[1]]
        self.assertEqual(
            contents[1:],
            ["how do I export my data?", "first answer", "is the export a csv?"],
        )

    def test_window(self):
        """Scenario: Only the last six messages are sent"""
        bot, calls = recording_bot([f"answer {i}" for i in range(6)])
        for i in range(5):
            bot.reply("s1", f"refund question {i}")
        bot.reply("s1", "refund question 5")
        sent = calls[-1]
        # system + 6 history + the new question
        self.assertEqual(len(sent), 8)
        self.assertEqual(sent[1].content, "refund question 2")
        self.assertEqual(sent[-1].content, "refund question 5")

    def test_sessions_isolated(self):
        """Scenario: Sessions are isolated"""
        bot, _ = recording_bot(["a", "b"])
        bot.reply("alice", "how do I export my data?")
        bot.reply("bob", "how do I delete my account?")
        alice = [m.content for m in bot.history("alice").messages]
        bob = [m.content for m in bot.history("bob").messages]
        self.assertNotIn("how do I delete my account?", alice)
        self.assertNotIn("how do I export my data?", bob)

    def test_card_refused(self):
        """Scenario: Card number refused"""
        bot, calls = recording_bot(["unused"])
        reply = bot.reply("s1", "refund to 4111 1111 1111 1111 please")
        self.assertEqual((reply.text, reply.refused), (policy.REFUSAL, True))
        self.assertEqual(calls, [])

    def test_password_refused(self):
        """Scenario: Shared password refused"""
        bot, calls = recording_bot(["unused"])
        reply = bot.reply("s1", "my password is hunter22, why can't I log in")
        self.assertEqual(reply.text, policy.REFUSAL)
        self.assertEqual(calls, [])

    def test_refused_not_remembered(self):
        """Scenario: Refused message is not remembered"""
        bot, calls = recording_bot(["ok"])
        bot.reply("s1", "my password is hunter22")
        bot.reply("s1", "how do I reset my login?")
        sent = " ".join(m.content for m in calls[0])
        self.assertNotIn("hunter22", sent)
        self.assertEqual(len(bot.history("s1").messages), 2)

    def test_end_of_input(self):
        """Scenario: End of input exits cleanly"""
        bot, _ = recording_bot(["answer"])
        out = io.StringIO()
        code = run(bot, stdin=io.StringIO("how do I export my data?\n"), stdout=out)
        self.assertEqual(code, 0)
        self.assertIn("bot: answer", out.getvalue())


if __name__ == "__main__":
    unittest.main()
