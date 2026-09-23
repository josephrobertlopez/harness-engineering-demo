"""Regression guard on per-model request shape.

These are the exact API drifts that silently 400 a whole run:

* ``temperature`` / ``top_p`` / ``top_k`` are removed on Opus 5 and Sonnet 5.
* ``budget_tokens`` is removed on those models; they take adaptive thinking
  plus ``output_config.effort``.
* Haiku 4.5 is the inverse -- it needs ``budget_tokens`` and errors on
  ``effort``.
* Model ids are complete as written. Appending a date suffix 404s.
"""

import unittest

from tests import context  # noqa: F401

from wikiskill.backends.anthropic_api import AnthropicBackend
from wikiskill.backends.base import LLMRequest
from wikiskill.config import MODEL_INFERENCE, MODEL_MAINTAINER, MODEL_PROPOSER, caps_for


class FakeMessages:
    def __init__(self):
        self.kwargs = None

    def create(self, **kwargs):
        self.kwargs = kwargs
        return FakeMessage()


class FakeMessage:
    stop_reason = "end_turn"
    content = [type("B", (), {"type": "text", "text": "hello"})()]
    usage = type("U", (), {"input_tokens": 1, "output_tokens": 2})()


class FakeClient:
    def __init__(self):
        self.messages = FakeMessages()


def send(model: str, effort: str | None = "high"):
    client = FakeClient()
    AnthropicBackend(client=client).complete(
        LLMRequest(role="proposer", model=model, system="s", prompt="p", effort=effort)
    )
    return client.messages.kwargs


class TestModelIds(unittest.TestCase):
    def test_no_date_suffixes(self):
        for model in (MODEL_INFERENCE, MODEL_MAINTAINER, MODEL_PROPOSER):
            with self.subTest(model=model):
                self.assertNotRegex(model, r"-\d{8}$")

    def test_defaults_are_current_generation(self):
        self.assertEqual(MODEL_INFERENCE, "claude-haiku-4-5")
        self.assertEqual(MODEL_MAINTAINER, "claude-sonnet-5")
        self.assertEqual(MODEL_PROPOSER, "claude-opus-5")


class TestRequestShape(unittest.TestCase):
    def test_opus5_gets_adaptive_thinking_and_effort(self):
        kwargs = send("claude-opus-5")
        self.assertEqual(kwargs["thinking"], {"type": "adaptive"})
        self.assertEqual(kwargs["output_config"], {"effort": "high"})

    def test_sonnet5_gets_adaptive_thinking(self):
        self.assertEqual(send("claude-sonnet-5")["thinking"], {"type": "adaptive"})

    def test_no_sampling_params_on_opus_or_sonnet(self):
        for model in ("claude-opus-5", "claude-sonnet-5"):
            kwargs = send(model)
            for banned in ("temperature", "top_p", "top_k"):
                with self.subTest(model=model, param=banned):
                    self.assertNotIn(banned, kwargs)

    def test_no_budget_tokens_on_opus_or_sonnet(self):
        for model in ("claude-opus-5", "claude-sonnet-5"):
            self.assertNotIn("budget_tokens", send(model)["thinking"])

    def test_haiku_gets_budget_tokens_and_no_effort(self):
        kwargs = send("claude-haiku-4-5")
        self.assertEqual(kwargs["thinking"]["type"], "enabled")
        self.assertGreaterEqual(kwargs["thinking"]["budget_tokens"], 1024)
        self.assertLess(kwargs["thinking"]["budget_tokens"], kwargs["max_tokens"])
        self.assertNotIn("output_config", kwargs)

    def test_unknown_model_defaults_to_the_modern_shape(self):
        caps = caps_for("claude-something-new")
        self.assertEqual(caps.thinking, "adaptive")
        self.assertFalse(caps.supports_sampling)


class TestRefusal(unittest.TestCase):
    def test_refusal_is_raised_not_silently_read(self):
        class Refusing(FakeMessages):
            def create(self, **kwargs):
                msg = FakeMessage()
                msg.stop_reason = "refusal"
                return msg

        client = FakeClient()
        client.messages = Refusing()
        with self.assertRaises(RuntimeError):
            AnthropicBackend(client=client).complete(
                LLMRequest(role="proposer", model="claude-opus-5", system="s", prompt="p")
            )


if __name__ == "__main__":
    unittest.main()
