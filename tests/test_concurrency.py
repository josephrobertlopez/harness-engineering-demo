"""Parallel rollouts must be indistinguishable from sequential ones.

Speed is worthless if it changes the answer. These assert that concurrency
affects only wall time: identical traces, identical ordering, identical
workspace, and no lost or duplicated rollouts.
"""

import tempfile
import threading
import unittest
from pathlib import Path

from tests import context  # noqa: F401
from tests.test_resume import workspace_fingerprint

from wikiskill.config import RunConfig
from wikiskill.loop import EvolutionLoop


def make(ws: Path, concurrency: int) -> EvolutionLoop:
    return EvolutionLoop(
        RunConfig(
            workspace=ws,
            backend="mock",
            concurrency=concurrency,
            extra={"decoy_iteration": "3"},
        )
    )


class TestParallelMatchesSequential(unittest.TestCase):
    def test_same_traces_same_order(self):
        with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
            seq = make(Path(a) / "ws", 1)
            par = make(Path(b) / "ws", 6)
            tasks = seq.split("train")

            from wikiskill.types import SkillSet

            s_traces = seq.evaluator.run(tasks, SkillSet(), iteration=1)
            p_traces = par.evaluator.run(tasks, SkillSet(), iteration=1)

            # Order must follow the task list, not completion order -- the
            # maintainer's sample and the scores depend on it.
            self.assertEqual([t.task_id for t in s_traces], [t.task_id for t in tasks])
            self.assertEqual([t.task_id for t in p_traces], [t.task_id for t in tasks])
            self.assertEqual(
                [t.to_dict() for t in s_traces], [t.to_dict() for t in p_traces]
            )

    def test_full_run_workspace_is_identical(self):
        with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
            seq_ws, par_ws = Path(a) / "ws", Path(b) / "ws"
            seq_results = make(seq_ws, 1).run(8)
            par_results = make(par_ws, 6).run(8)
            self.assertEqual(
                [r.to_dict() for r in seq_results], [r.to_dict() for r in par_results]
            )
            self.assertEqual(workspace_fingerprint(seq_ws), workspace_fingerprint(par_ws))

    def test_every_task_produces_exactly_one_trace(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp) / "ws"
            loop = make(ws, 6)
            from wikiskill.types import SkillSet

            tasks = loop.split("train")
            loop.evaluator.run(tasks, SkillSet(), iteration=1)
            written = list(ws.rglob("iter-01/train/**/*.trace.json"))
            self.assertEqual(len(written), len(tasks))
            self.assertEqual(len(written), len({p.name for p in written}))

    def test_cached_rollouts_are_reused_not_rerun(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp) / "ws"
            loop = make(ws, 6)
            from wikiskill.types import SkillSet

            tasks = loop.split("train")
            first = loop.evaluator.run(tasks, SkillSet(), iteration=1)

            calls = {"n": 0}
            original = loop.evaluator._rollout

            def counting(*args, **kwargs):
                calls["n"] += 1
                return original(*args, **kwargs)

            loop.evaluator._rollout = counting  # type: ignore[method-assign]
            second = loop.evaluator.run(tasks, SkillSet(), iteration=1)

            self.assertEqual(calls["n"], 0, "cached rollouts should not re-run")
            self.assertEqual([t.to_dict() for t in first], [t.to_dict() for t in second])


class TestThreadSafety(unittest.TestCase):
    def test_cost_accumulation_does_not_lose_updates(self):
        from unittest import mock

        from wikiskill.backends.base import LLMRequest
        from wikiskill.backends.claude_cli import ClaudeCliBackend

        backend = ClaudeCliBackend(executable="claude")

        class Completed:
            returncode = 0
            stdout = '{"result":"ok","total_cost_usd":0.01}'
            stderr = ""

        req = LLMRequest(role="inference", model="m", system="s", prompt="p")
        with mock.patch("subprocess.run", return_value=Completed()):
            threads = [
                threading.Thread(target=lambda: [backend.complete(req) for _ in range(20)])
                for _ in range(8)
            ]
            for t in threads:
                t.start()
            for t in threads:
                t.join()

        self.assertAlmostEqual(backend.total_cost_usd, 8 * 20 * 0.01, places=6)


if __name__ == "__main__":
    unittest.main()
