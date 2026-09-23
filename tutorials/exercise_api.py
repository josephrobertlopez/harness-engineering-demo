"""What an exercise check can use.

Every exercise is a folder containing a `check.py` that defines `TITLE` and a
`check(ctx) -> Result` function. Keeping the surface this small means a
lesson author writes an assertion, not a test harness.

Checks must run **offline**. An exercise that needs an API key is an exercise
most people will skip.
"""

from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC = REPO_ROOT / "src"


@dataclass(frozen=True, slots=True)
class Result:
    ok: bool
    message: str
    hint: str = ""

    @classmethod
    def passed(cls, message: str = "") -> "Result":
        return cls(True, message or "correct")

    @classmethod
    def failed(cls, message: str, hint: str = "") -> "Result":
        return cls(False, message, hint)


@dataclass(frozen=True, slots=True)
class Context:
    """Paths an exercise needs, plus a scratch dir it may write to."""

    exercise_dir: Path
    """Where the exercise's own files live -- including the learner's answer."""
    scratch: Path
    """A temp dir, wiped between runs. Put workspaces here."""
    repo_root: Path = REPO_ROOT

    def answer(self, name: str) -> Path:
        return self.exercise_dir / name

    def read_answer(self, name: str) -> str | None:
        path = self.answer(name)
        if not path.is_file():
            return None
        return path.read_bytes().decode("utf-8").replace("\r\n", "\n")


def run_wikiskill(*args: str, cwd: Path | None = None) -> subprocess.CompletedProcess:
    """Invoke the CLI the same way the lesson text tells the learner to.

    Exercises shell out rather than importing, so a check verifies the
    command in the lesson actually works -- a lesson that documents a flag
    that no longer exists then fails CI instead of failing a teammate.
    """
    return subprocess.run(
        [sys.executable, "-m", "wikiskill.cli", *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=str(cwd or REPO_ROOT),
        env={**_env(), "PYTHONPATH": str(SRC)},
        timeout=900,
    )


def score_skills_dir(skills_dir: Path, scratch: Path, split: str = "test") -> float:
    """Score a folder of hand-written skills. The core grading primitive."""
    workspace = scratch / "ws"
    proc = run_wikiskill(
        "--workspace", str(workspace), "--backend", "mock",
        "eval", "--split", split, "--skills-dir", str(skills_dir),
    )
    if proc.returncode != 0:
        raise RuntimeError(f"eval failed: {(proc.stderr or proc.stdout)[:500]}")
    return _parse_score(proc.stdout)


def score_baseline(scratch: Path, split: str = "test") -> float:
    workspace = scratch / "ws"
    proc = run_wikiskill(
        "--workspace", str(workspace), "--backend", "mock",
        "eval", "--split", split, "--skills", "none",
    )
    if proc.returncode != 0:
        raise RuntimeError(f"baseline failed: {(proc.stderr or proc.stdout)[:500]}")
    return _parse_score(proc.stdout)


def _parse_score(stdout: str) -> float:
    for line in stdout.splitlines():
        if "): " in line:
            try:
                return float(line.split("): ", 1)[1].split()[0])
            except (ValueError, IndexError):
                continue
    raise RuntimeError(f"could not read a score from: {stdout[:300]}")


def _env() -> dict[str, str]:
    import os

    return dict(os.environ)
