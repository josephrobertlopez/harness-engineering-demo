import unittest

from tests import context  # noqa: F401

from wikiskill.patching import PatchError, apply_batch, validate_path
from wikiskill.types import PatchOp

PAGE = "patterns/thing.md"


def create(**kw):
    base = dict(op="create_page", path=PAGE, title="Thing", content="body", evidence_traces=("t1",))
    base.update(kw)
    return PatchOp(**base)


class TestPathValidation(unittest.TestCase):
    def test_rejects_traversal(self):
        for bad in ("patterns/../../SKILL.md", "../x.md", "/etc/passwd", "patterns/../x.md"):
            with self.subTest(bad=bad), self.assertRaises(PatchError) as cm:
                validate_path(bad)
            self.assertEqual(cm.exception.code, "E_PATH")

    def test_rejects_non_pattern_locations(self):
        for bad in ("skills/x/SKILL.md", "logs.md", "patterns/Thing.md", "patterns/x.txt"):
            with self.subTest(bad=bad), self.assertRaises(PatchError):
                validate_path(bad)

    def test_accepts_slug(self):
        validate_path("patterns/iso-z.md")


class TestApply(unittest.TestCase):
    def test_create_then_append_in_one_batch(self):
        out = apply_batch({}, [create(), PatchOp(op="append", path=PAGE, content="more")])
        self.assertTrue(out.ok)
        self.assertIn("body", out.pages[PAGE])
        self.assertIn("more", out.pages[PAGE])

    def test_create_requires_evidence(self):
        out = apply_batch({}, [create(evidence_traces=())])
        self.assertFalse(out.ok)
        self.assertIn("E_EVIDENCE", out.errors[0][1])

    def test_evidence_must_resolve(self):
        out = apply_batch({}, [create()], trace_exists=lambda t: False)
        self.assertFalse(out.ok)
        self.assertIn("E_EVIDENCE", out.errors[0][1])

    def test_anchor_must_be_unique(self):
        pages = {PAGE: "# T\n\nalpha\nalpha\n"}
        out = apply_batch(pages, [PatchOp(op="replace", path=PAGE, anchor="alpha", content="beta")])
        self.assertFalse(out.ok)
        self.assertIn("E_ANCHOR_AMBIGUOUS", out.errors[0][1])

    def test_missing_anchor(self):
        pages = {PAGE: "# T\n\nalpha\n"}
        out = apply_batch(pages, [PatchOp(op="replace", path=PAGE, anchor="zeta", content="beta")])
        self.assertFalse(out.ok)
        self.assertIn("E_ANCHOR_MISSING", out.errors[0][1])

    def test_insert_after_keeps_anchor(self):
        pages = {PAGE: "# T\n\nalpha\n"}
        out = apply_batch(pages, [PatchOp(op="insert_after", path=PAGE, anchor="alpha", content="beta")])
        self.assertTrue(out.ok)
        self.assertIn("alpha\nbeta", out.pages[PAGE])

    def test_batch_is_all_or_nothing(self):
        """A later failure must leave the earlier edits unapplied."""
        pages = {PAGE: "# T\n\nalpha\n"}
        out = apply_batch(
            pages,
            [
                PatchOp(op="append", path=PAGE, content="first"),
                PatchOp(op="replace", path=PAGE, anchor="nope", content="x"),
            ],
        )
        self.assertFalse(out.ok)
        self.assertEqual(out.pages, pages)
        self.assertNotIn("first", out.pages[PAGE])

    def test_create_on_existing_page_is_rejected(self):
        out = apply_batch({PAGE: "# T\n"}, [create()])
        self.assertFalse(out.ok)
        self.assertIn("E_PATH_EXISTS", out.errors[0][1])


if __name__ == "__main__":
    unittest.main()
