import unittest

from tests import context  # noqa: F401

from wikiskill.protocol import (
    ProtocolError,
    parse_action,
    parse_answer,
    parse_json_block,
    parse_thought,
)


class TestParsing(unittest.TestCase):
    def test_action(self):
        name, args = parse_action('THOUGHT: hm\nACTION: search {"query": "x", "page": 2}')
        self.assertEqual(name, "search")
        self.assertEqual(args, {"query": "x", "page": 2})

    def test_answer(self):
        self.assertEqual(parse_answer('ANSWER: {"a": 1}'), {"a": 1})

    def test_answer_tolerates_trailing_prose(self):
        """Models routinely add a sentence after the JSON."""
        self.assertEqual(parse_answer('ANSWER: {"a": 1}  Hope that helps!'), {"a": 1})

    def test_thought(self):
        self.assertEqual(parse_thought("THOUGHT: consider it\nACTION: x {}"), "consider it")

    def test_no_action_when_absent(self):
        self.assertIsNone(parse_action("THOUGHT: thinking"))

    def test_malformed_action_raises(self):
        with self.assertRaises(ProtocolError):
            parse_action("ACTION: search no-json-here")

    def test_json_block_from_fence(self):
        text = 'prose\n```json\n{"edits": [], "log_entry": "x"}\n```\nmore prose'
        self.assertEqual(parse_json_block(text), {"edits": [], "log_entry": "x"})

    def test_json_block_without_fence(self):
        self.assertEqual(parse_json_block('noise {"a": 2} tail'), {"a": 2})

    def test_json_block_skips_an_unparseable_fence(self):
        text = "```json\n{not json\n```\n```json\n{\"ok\": true}\n```"
        self.assertEqual(parse_json_block(text), {"ok": True})


if __name__ == "__main__":
    unittest.main()
