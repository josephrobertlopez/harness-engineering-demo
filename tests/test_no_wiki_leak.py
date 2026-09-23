"""The ablation the paper says matters most, enforced as a test.

Letting the Inference Agent read the wiki drops average benchmark performance
from 63.7% to 60.9%; removing the wiki from the Proposer as well drops it to
48.7%. So the wiki must reach the Proposer and must not reach inference.

A prompt instruction would be one refactor away from silently breaking. These
tests check the structure instead.
"""

import inspect
import unittest

from tests import context  # noqa: F401

from wikiskill.agents.inference import InferenceAgent
from wikiskill.bench import starter
from wikiskill.layers.wiki import WikiStore
from wikiskill.types import Skill, SkillSet


class TestInferenceCannotSeeTheWiki(unittest.TestCase):
    def test_constructor_takes_no_wiki(self):
        params = set(inspect.signature(InferenceAgent.__init__).parameters)
        self.assertNotIn("wiki", params)
        self.assertEqual(params, {"self", "backend", "model", "max_steps"})

    def test_run_takes_no_wiki(self):
        self.assertNotIn("wiki", inspect.signature(InferenceAgent.run).parameters)

    def test_module_does_not_import_the_wiki_layer(self):
        source = inspect.getsource(inspect.getmodule(InferenceAgent))
        self.assertNotIn("layers.wiki", source)
        self.assertNotIn("WikiStore", source)

    def test_system_prompt_contains_skills_but_no_wiki_text(self):
        agent = InferenceAgent(backend=None, model="m")  # type: ignore[arg-type]
        skillset = SkillSet(
            (Skill(name="s", description="d", body="THE-SKILL-RULE", purpose="p"),)
        )
        env = starter.StarterEnv(starter.tasks()[0])
        prompt = agent.system_prompt(env, skillset)
        self.assertIn("THE-SKILL-RULE", prompt)
        for leaked in ("patterns/", "skill-impact", "logs.md", "Root cause"):
            self.assertNotIn(leaked, prompt)


class TestProposerCanSeeTheWiki(unittest.TestCase):
    def test_proposer_signature_takes_the_wiki(self):
        from wikiskill.agents.proposer import SkillProposer

        params = inspect.signature(SkillProposer.run).parameters
        self.assertIn("wiki", params)
        # `from __future__ import annotations` keeps annotations as strings.
        self.assertEqual(params["wiki"].annotation, WikiStore.__name__)


if __name__ == "__main__":
    unittest.main()
