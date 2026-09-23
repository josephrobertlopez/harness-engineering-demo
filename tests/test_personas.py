"""The four persona surfaces must never drift from their source.

Hand-maintaining a persona as a subagent, a skill, and a doc is how the
three quietly stop agreeing with each other. Everything is generated from
one neutral source file, and this asserts the committed output still matches
what the generator produces.
"""

import subprocess
import sys
import unittest
from pathlib import Path

from tests import context  # noqa: F401

REPO = Path(__file__).resolve().parents[1]
PERSONAS = REPO / "personas"
EXPORT = PERSONAS / "export"


class TestPersonaExports(unittest.TestCase):
    def test_check_reports_no_drift(self):
        """The committed exports match a fresh regeneration."""
        proc = subprocess.run(
            [sys.executable, str(PERSONAS / "export.py"), "--check"],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            cwd=str(REPO), timeout=300,
        )
        self.assertEqual(
            proc.returncode, 0,
            f"exports are stale -- run `python personas/export.py`\n{proc.stdout}{proc.stderr}",
        )

    def test_every_source_produces_every_surface(self):
        sources = sorted(p.stem.removesuffix(".persona") for p in PERSONAS.glob("*.persona.md"))
        self.assertTrue(sources, "no persona sources found")
        for ident in sources:
            with self.subTest(persona=ident):
                self.assertTrue((EXPORT / "claude-agents" / f"{ident}.md").is_file())
                self.assertTrue((EXPORT / "claude-skills" / ident / "SKILL.md").is_file())
                self.assertTrue((EXPORT / "cards" / f"{ident}.md").is_file())

    def test_portable_json_covers_every_persona(self):
        """The JSON is what makes the claim 'tool-agnostic' true.

        Someone on Codex or Cursor reads this one file and builds their own
        system prompt. If it lags the markdown, the claim is false.
        """
        import json

        data = json.loads((EXPORT / "personas.json").read_text(encoding="utf-8"))
        entries = data["personas"] if isinstance(data, dict) and "personas" in data else data
        ids = {e["id"] for e in (entries.values() if isinstance(entries, dict) else entries)}
        sources = {p.stem.removesuffix(".persona") for p in PERSONAS.glob("*.persona.md")}
        self.assertEqual(ids, sources)

    def test_sources_carry_no_tool_specific_fields(self):
        """A Claude-specific field in the source defeats the whole design."""
        banned = ("model:", "allowed-tools:", "argument-hint:", "tools:")
        for src in sorted(PERSONAS.glob("*.persona.md")):
            text = src.read_text(encoding="utf-8")
            front = text.split("---", 2)[1] if text.startswith("---") else ""
            for field in banned:
                with self.subTest(persona=src.name, field=field):
                    self.assertNotIn(field, front)

    def test_everything_is_lf(self):
        """Exports are byte-compared by --check; a CRLF write breaks it on a
        fresh clone, where git hands you LF."""
        offenders = [
            p.relative_to(REPO).as_posix()
            for p in PERSONAS.rglob("*")
            if p.is_file() and p.suffix in {".md", ".json", ".py"} and b"\r" in p.read_bytes()
        ]
        self.assertEqual(offenders, [])


if __name__ == "__main__":
    unittest.main()
