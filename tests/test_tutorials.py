"""Tutorial exercises must actually be solvable, and docs links must resolve.

A lesson that references a flag that no longer exists is worse than no
lesson: it costs a teammate an afternoon before they conclude the repo is
broken. These tests make that a CI failure instead.

Each exercise ships a `solution/` used only here. The learner's own `skills/`
folder is empty in git and is never asserted on.
"""

import sys
import unittest
from pathlib import Path

from tests import context  # noqa: F401

REPO = Path(__file__).resolve().parents[1]
TUTORIALS = REPO / "tutorials"
sys.path.insert(0, str(TUTORIALS))

from exercise_api import Context  # noqa: E402
import check as runner  # noqa: E402


class TestExercisesAreSolvable(unittest.TestCase):
    def test_at_least_one_exercise_exists(self):
        self.assertTrue(runner.discover(), "no exercises discovered")

    def test_every_exercise_passes_with_its_reference_solution(self):
        """Proves the exercise is achievable and its check actually runs.

        This is the test that catches a lesson drifting away from the code:
        the solution is graded through the same CLI the lesson tells the
        learner to type.
        """
        import shutil
        import tempfile

        for ex in runner.discover():
            with self.subTest(exercise=ex.slug):
                solution = ex.directory / "solution"
                self.assertTrue(
                    solution.is_dir(), f"{ex.slug} ships no solution/ to verify against"
                )
                scratch = Path(tempfile.mkdtemp(prefix="wikiskill-sol-"))
                try:
                    result = ex.run(Context(exercise_dir=solution, scratch=scratch))
                    self.assertTrue(result.ok, f"{ex.slug}: {result.message}")
                finally:
                    shutil.rmtree(scratch, ignore_errors=True)

    def test_learner_folder_is_empty_and_fails_cleanly(self):
        """An untouched exercise must fail with a hint, not an exception."""
        import shutil
        import tempfile

        for ex in runner.discover():
            with self.subTest(exercise=ex.slug):
                scratch = Path(tempfile.mkdtemp(prefix="wikiskill-empty-"))
                try:
                    result = runner.run_one(ex)
                    self.assertFalse(result.ok)
                    self.assertTrue(result.hint, f"{ex.slug} gives no hint on failure")
                finally:
                    shutil.rmtree(scratch, ignore_errors=True)


class TestDocLinks(unittest.TestCase):
    def test_relative_markdown_links_resolve(self):
        import re

        pattern = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
        broken: list[str] = []
        for md in sorted(REPO.rglob("*.md")):
            if any(part in {".git", "workspace", "solution"} for part in md.parts):
                continue
            text = _strip_code(md.read_bytes().decode("utf-8", "replace"))
            for target in pattern.findall(text):
                if target.startswith(("http://", "https://", "#", "mailto:")):
                    continue
                resolved = (md.parent / target.split("#", 1)[0]).resolve()
                if not resolved.exists():
                    broken.append(f"{md.relative_to(REPO)} -> {target}")
        self.assertEqual(broken, [], "broken relative links:\n" + "\n".join(broken))


def _strip_code(text: str) -> str:
    """Remove fenced blocks and inline code before looking for links.

    A link shown as an *example* is not a link. Teaching material is full of
    them -- the LLM Wiki track demonstrates a dual-link format whose sample
    path deliberately points nowhere -- and flagging those trains people to
    ignore the checker, which defeats the point of having one.

    Done line by line so the patterns never need to match a newline, which
    is what makes this readable rather than a wall of escapes.
    """
    import re

    kept: list[str] = []
    in_fence = False
    for line in text.splitlines():
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        kept.append(re.sub(r"`[^`]*`", "", line))
    return "\n".join(kept)


if __name__ == "__main__":
    unittest.main()
