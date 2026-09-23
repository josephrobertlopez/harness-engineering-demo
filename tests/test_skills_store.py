import tempfile
import unittest
from pathlib import Path

from tests import context  # noqa: F401

from wikiskill.layers.skills import SkillSetStore
from wikiskill.types import Skill, SkillSet


def skill(name="alpha", body="do the thing"):
    return Skill(name=name, description=f"{name} desc", body=body, purpose="because", source_patterns=("patterns/a.md",))


class TestSkillSet(unittest.TestCase):
    def test_sha_is_order_independent(self):
        a, b = skill("alpha"), skill("beta")
        self.assertEqual(SkillSet((a, b)).sha, SkillSet((b, a)).sha)

    def test_sha_changes_with_content(self):
        self.assertNotEqual(SkillSet((skill(),)).sha, SkillSet((skill(body="other"),)).sha)

    def test_with_skill_is_pure(self):
        base = SkillSet((skill("alpha"),))
        before = base.sha
        base.with_skill(skill("beta"))
        self.assertEqual(base.sha, before)

    def test_render_excludes_nothing_but_starts_empty(self):
        self.assertEqual(SkillSet().render_for_prompt(), "(no skills yet)")


class TestStore(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.store = SkillSetStore(root / "snapshots", root / "HEAD.json", root / "mirror")

    def tearDown(self):
        self.tmp.cleanup()

    def test_materialize_is_idempotent(self):
        s = SkillSet((skill(),))
        self.assertEqual(self.store.materialize(s), self.store.materialize(s))

    def test_roundtrip_preserves_sha(self):
        s = SkillSet((skill("alpha"), skill("beta")))
        sha = self.store.materialize(s)
        self.assertEqual(self.store.load(sha).sha, sha)

    def test_rejecting_leaves_head_untouched(self):
        """Rollback is 'never move HEAD', so there is no undo to get wrong."""
        parent = SkillSet((skill("alpha"),))
        parent_sha = self.store.materialize(parent)
        self.store.set_head(parent_sha, 1, 0.5)

        candidate_sha = self.store.materialize(parent.with_skill(skill("beta")))
        # ...and then we simply do not point HEAD at it.
        self.assertEqual(self.store.head()["sha"], parent_sha)
        self.assertEqual(self.store.head_skillset().names(), ("alpha",))
        self.assertFalse((self.store.mirror / "beta").exists())
        self.assertTrue(self.store.snapshot_dir(candidate_sha).exists())

    def test_mirror_rebuild_repairs_a_crash(self):
        s = SkillSet((skill("alpha"),))
        sha = self.store.materialize(s)
        self.store.set_head(sha, 1, 0.5)
        (self.store.mirror / "alpha" / "SKILL.md").write_text("corrupted", encoding="utf-8")
        self.assertTrue(self.store.mirror_is_stale())
        self.store.rebuild_mirror(sha)
        self.assertFalse(self.store.mirror_is_stale())

    def test_unified_diff_is_lf_and_addressable(self):
        before = SkillSet((skill("alpha"),))
        after = before.with_skill(skill("beta"))
        diff = self.store.unified_diff(before, after)
        self.assertIn("b/skills/beta/SKILL.md", diff)
        self.assertNotIn("\r", diff)
        self.assertEqual(self.store.unified_diff(before, before), "")


if __name__ == "__main__":
    unittest.main()
