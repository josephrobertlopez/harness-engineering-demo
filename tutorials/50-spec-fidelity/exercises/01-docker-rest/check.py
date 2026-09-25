"""Exercise 1: a vague ticket becomes a container, judged for fidelity."""

from __future__ import annotations

import sys
from pathlib import Path

TRACK = Path(__file__).resolve().parents[2]
if str(TRACK) not in sys.path:
    sys.path.insert(0, str(TRACK))

from exercise_api import Context, Result  # noqa: E402
from spec_fidelity import grade  # noqa: E402

TITLE = "OPS-1432: ticket -> PRD -> OpenSpec -> Dockerised REST function"


def check(ctx: Context) -> Result:
    ok, message, hint = grade(ctx.exercise_dir)
    return Result.passed(message) if ok else Result.failed(message, hint)
