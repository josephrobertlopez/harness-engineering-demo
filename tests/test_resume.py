"""Crash and resume must land in the same place as an uninterrupted run.

This is the highest-value test in the suite: the loop's whole claim to being
restartable rests on every phase being idempotent and on HEAD moving only
after the decision that justifies it is durable.
"""

import hashlib
import re
import tempfile
import unittest
from pathlib import Path

from tests import context  # noqa: F401

from wikiskill.config import RunConfig
from wikiskill.loop import EvolutionLoop


class Boom(RuntimeError):
    pass


#: The evolution log stamps every entry with the wall clock, so two runs are
#: identical in content but not in bytes. Normalising the stamp keeps the
#: comparison honest rather than quietly excluding the log from it.
_TIMESTAMP = re.compile(rb"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z")


def workspace_fingerprint(root: Path) -> str:
    """Hash the durable layers, ignoring harness scratch and the LLM cache."""
    h = hashlib.blake2b(digest_size=16)
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(root).as_posix()
        if rel.startswith(".state/llmcache/") or rel.startswith(".state/iter-"):
            continue
        if rel == ".state/journal.jsonl":
            continue
        h.update(rel.encode())
        body = path.read_bytes().replace(b"\r\n", b"\n")
        h.update(_TIMESTAMP.sub(b"<TS>", body))
    return h.hexdigest()


def make(ws: Path) -> EvolutionLoop:
    return EvolutionLoop(
        RunConfig(workspace=ws, backend="mock", extra={"decoy_iteration": "3"})
    )


class TestResume(unittest.TestCase):
    def test_resume_matches_an_uninterrupted_run(self):
        with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
            clean_ws = Path(a) / "workspace"
            make(clean_ws).run(8)
            expected = workspace_fingerprint(clean_ws)

            crashed_ws = Path(b) / "workspace"
            loop = make(crashed_ws)

            # Die partway through iteration 3 -- the iteration that gets
            # rejected, so the resume path has to reproduce a rollback too.
            original = loop.proposer.run
            calls = {"n": 0}

            def exploding(*args, **kwargs):
                calls["n"] += 1
                if calls["n"] == 3:
                    raise Boom("process died mid-iteration")
                return original(*args, **kwargs)

            loop.proposer.run = exploding  # type: ignore[method-assign]
            with self.assertRaises(Boom):
                loop.run(8)

            # A fresh process picks up from the journal.
            make(crashed_ws).run(8)

            self.assertEqual(workspace_fingerprint(crashed_ws), expected)

    def test_no_duplicate_traces_after_resume(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp) / "workspace"
            make(ws).run(2)
            before = sorted(p.as_posix() for p in ws.rglob("*.trace.json"))
            make(ws).run(2)
            after = sorted(p.as_posix() for p in ws.rglob("*.trace.json"))
            self.assertEqual(len(after), len(set(after)))
            self.assertEqual(before, after[: len(before)])

    def test_rerunning_a_converged_run_is_a_no_op(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp) / "workspace"
            make(ws).run(8)
            fingerprint = workspace_fingerprint(ws)
            make(ws).run(8)
            self.assertEqual(workspace_fingerprint(ws), fingerprint)


class TestDeterminism(unittest.TestCase):
    def test_two_cold_runs_agree(self):
        with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
            one, two = Path(a) / "workspace", Path(b) / "workspace"
            make(one).run(8)
            make(two).run(8)
            self.assertEqual(workspace_fingerprint(one), workspace_fingerprint(two))


if __name__ == "__main__":
    unittest.main()
